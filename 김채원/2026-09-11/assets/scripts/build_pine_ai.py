"""
AI 생성(TRELLIS.2) 소나무 → 런타임 자산 (v3: 복셀 300칸 리메시 + Taubin 스무딩 + 먹 번짐 농담)

입력: pine_4_trellis2.glb  (원화 크롭 pine_4_isolated_nobg.png → TRELLIS.2, 29만 면, 조각 3.4만 개)
처리:
  1) 종이 시트(z≈-0.42 평면) · 얇은 카드 · 틀 막대 제거, 오른쪽 나무 영역만
  2) 앞뒤 두 그루로 분리 (z 0.06 기준)
  3) **복셀화 → 팽창(1) → 닫힘 → 마칭큐브**  ← 흩어진 붓 자국 조각이 이어진 수관이 됨
  4) 감면 → 바닥 중심 pivot, 높이 1 정규화 (Y-up) → 먹 팔레트 정점색 (원 텍스처 밝기 + 위를 보는 면)
출력: runtime/pine_ai_1.glb, pine_ai_2.glb
조절: VOX_RES (복셀 해상도, 높이 기준 칸 수), DILATE (잇는 정도), TARGET_FACES
"""
import json, numpy as np, trimesh, fast_simplification
from scipy import ndimage
from scipy.spatial import cKDTree
from skimage import measure

VOX_RES = 300          # 높이 1 을 몇 칸으로 — 클수록 세밀, 작을수록 덩어리
DILATE = 2             # 팽창 반복 (조각을 잇는 힘)
CLOSE_IT = 1           # 닫힘(작은 구멍 메움)
SMOOTH = 1.0             # 가우시안 σ (복셀 단위) — 붓 번짐
TARGET_FACES = 14000
TAUBIN_IT = 12         # 스무딩 반복 (복셀 계단 제거)
NOISE_AMP = 0.22       # 먹 번짐 얼룩 세기 (0~1)

m = trimesh.load("pine_4_trellis2.glb", force="mesh")
V = np.asarray(m.vertices); F = np.asarray(m.faces)
C = np.asarray(m.visual.to_color().vertex_colors)[:, :3].astype(float)
keep = np.load("/tmp/keep_tree.npy")            # 09-11 추출 마스크 (종이·카드·틀 제거 + x>0.12)
F2 = F[keep]
fz = V[F2][:, :, 2].mean(1)

PAL = json.load(open("assets/inwangjesaekdo/records/ink_palette.json", encoding="utf-8"))
def s2l(c): x = np.asarray(c, float) / 255; return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4) * 255
JIN = s2l(PAL["진묵(0-5%)"]); DAM = s2l(PAL["담묵(25-55%)"])

for name, sel in (("pine_ai_1", fz < 0.06), ("pine_ai_2", fz >= 0.06)):
    Fs = F2[sel]; vi, inv = np.unique(Fs, return_inverse=True); Vs = V[vi]; Fs = inv.reshape(-1, 3); Cs = C[vi]
    src = trimesh.Trimesh(Vs, Fs, process=False)
    b0, b1 = src.bounds; h = b1[1] - b0[1]
    pitch = h / VOX_RES
    # 복셀화 (표면 복셀) → 이진 볼륨
    vg = src.voxelized(pitch)
    mat = vg.matrix.copy()
    mat = ndimage.binary_dilation(mat, iterations=DILATE)
    mat = ndimage.binary_closing(mat, iterations=CLOSE_IT)
    mat = ndimage.binary_fill_holes(mat)
    # 가장 큰 연결 덩어리만 (떠 있는 잔여 조각 제거)
    lab, n = ndimage.label(mat)
    if n > 1:
        sizes = ndimage.sum(mat, lab, range(1, n + 1)); big = np.argmax(sizes) + 1
        # 큰 덩어리 부피의 2% 미만인 조각 제거
        keep_lab = [i + 1 for i, s in enumerate(sizes) if s >= 0.02 * sizes.max()]
        mat = np.isin(lab, keep_lab)
    field = ndimage.gaussian_filter(mat.astype(np.float32), SMOOTH)
    verts, faces, _, _ = measure.marching_cubes(field, level=0.5)
    # 복셀 인덱스 → 월드 좌표 (vg.transform: 인덱스→월드)
    Vw = trimesh.transform_points(verts, vg.transform)
    # 계단(복셀 자국) 제거: 부피 보존형 Taubin 스무딩 → 붓 번짐처럼 둥글게
    mc = trimesh.Trimesh(Vw, faces, process=False)
    trimesh.smoothing.filter_taubin(mc, lamb=0.5, nu=-0.53, iterations=TAUBIN_IT)
    Vd, Fd = fast_simplification.simplify(np.asarray(mc.vertices, np.float32), np.asarray(mc.faces, np.int64), target_count=TARGET_FACES)
    td = trimesh.Trimesh(Vd, Fd, process=False)
    # pivot 바닥 중심, 높이 1
    b0, b1 = td.bounds; h = b1[1] - b0[1]
    td.vertices = (td.vertices - [(b0[0] + b1[0]) / 2, b0[1], (b0[2] + b1[2]) / 2]) / h
    # 줄기 아래쪽(높이 30% 미만)에서 중심축에서 8% 이상 벗어난 조각(옆으로 튄 가지) 제거 → 다시 정규화
    Vt = np.asarray(td.vertices); Ft = np.asarray(td.faces)
    c = Vt[Ft].mean(1); stray = (c[:, 1] < 0.30) & (np.hypot(c[:, 0], c[:, 2]) > 0.08)
    Ft = Ft[~stray]; vi2, inv2 = np.unique(Ft, return_inverse=True)
    td = trimesh.Trimesh(Vt[vi2], inv2.reshape(-1, 3), process=False)
    # 남은 잔조각(면 수 1% 미만 컴포넌트) 제거
    parts = td.split(only_watertight=False)
    if len(parts) > 1:
        big = max(len(p.faces) for p in parts)
        td = trimesh.util.concatenate([p for p in parts if len(p.faces) >= 0.01 * big])
    Vd = np.asarray(td.vertices); Fd = np.asarray(td.faces)
    b0, b1 = td.bounds; h = b1[1] - b0[1]
    td.vertices = (td.vertices - [(b0[0] + b1[0]) / 2, b0[1], (b0[2] + b1[2]) / 2]) / h
    Vd = np.asarray(td.vertices)
    # 색: 원 정점색(텍스처) 밝기 → 진묵/담묵, 위를 보는 면 → 담묵
    Cd = Cs[cKDTree(Vs).query(Vd)[1]]
    lum = Cd.mean(1); lo, hi = np.percentile(lum, [5, 95]); ln = np.clip((lum - lo) / max(hi - lo, 1), 0, 1)
    up = np.clip(np.asarray(td.vertex_normals)[:, 1], 0, 1)
    # 먹 번짐: 저주파 3D 노이즈(무작위 격자를 가우시안으로 뭉갠 것)를 정점 위치에서 샘플 → 얼룩덜룩한 농담
    rng = np.random.default_rng(11)
    G = 24; noise = ndimage.gaussian_filter(rng.random((G, G, G)), 2.0); noise = (noise - noise.mean()) / (noise.std() + 1e-9)
    idx = np.clip(((Vd - Vd.min(0)) / (np.ptp(Vd, axis=0) + 1e-9) * (G - 1)).astype(int), 0, G - 1)
    nz = noise[idx[:, 0], idx[:, 1], idx[:, 2]] * NOISE_AMP
    top = np.clip(Vd[:, 1], 0, 1) * 0.25                       # 위로 갈수록 담묵 쪽 (엷어짐)
    a = np.clip(0.35 * ln + 0.35 * up + top + nz, 0, 1)[:, None]
    col = JIN * (1 - a) + DAM * a
    td.visual = trimesh.visual.ColorVisuals(vertex_colors=np.c_[col, np.full(len(col), 255)].astype(np.uint8))
    out = f"assets/inwangjesaekdo/runtime/{name}.glb"; td.export(out)
    e = td.bounds[1] - td.bounds[0]
    print(f"{name}: 원 {len(Fs):,}면(조각) → 복셀 {mat.shape} → 마칭큐브 {len(faces):,} → 감면 {len(Fd):,}  크기 {np.round(e,3).tolist()}  "
          f"watertight={td.is_watertight}  {__import__('os').path.getsize(out)//1024} KB")
