"""
AI 생성(TRELLIS.2) 소나무 → 런타임 자산 (v4: 복셀 300칸 + 떨어진 조각을 가지로 잇기 + 150칸 메시화 + Taubin + 먹 번짐)

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
DILATE = 1             # 팽창 반복 (두께)
CLOSE_IT = 2           # 닫힘(작은 틈 메움)
MIN_VOX = 40           # 이보다 작은 조각(복셀 수)은 버림
BRIDGE_MAX = 28        # 본체에서 이보다 먼 조각은 버림 (300칸 기준 28칸 = 높이의 9%)
BRIDGE_R = 4           # 잇는 가지 굵기 (복셀, 반지름)
SMOOTH = 0.5             # 가우시안 σ (복셀 단위) — 붓 번짐
TARGET_FACES = 20000
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
    # 떨어진 조각을 '가지'로 잇는다: 큰 덩어리(줄기+수관 본체)에서 시작해, 나머지 조각마다 가장 가까운 점끼리
    # 굵기 BRIDGE_R 복셀의 선을 그어 붙인다. 너무 멀거나(BRIDGE_MAX) 너무 작은(MIN_VOX) 조각은 버린다.
    # → 결과는 한 덩어리 = 잎·가지가 전부 줄기와 연결
    lab, n = ndimage.label(mat)
    sizes = ndimage.sum(mat, lab, range(1, n + 1))
    order = np.argsort(-sizes) + 1
    main = (lab == order[0])
    bridged = dropped_small = dropped_far = 0
    for k in order[1:]:
        if sizes[k - 1] < MIN_VOX:
            dropped_small += 1; continue
        pts_c = np.argwhere(lab == k)
        pts_m = np.argwhere(main)
        if len(pts_m) > 60000:                                  # KD-tree 크기 제한: 표면 근처만 써도 충분
            pts_m = pts_m[np.random.default_rng(0).choice(len(pts_m), 60000, replace=False)]
        d, idx = cKDTree(pts_m).query(pts_c)
        j = int(np.argmin(d)); a = pts_c[j]; b = pts_m[idx[j]]
        if d[j] > BRIDGE_MAX:
            dropped_far += 1; continue
        L = int(np.ceil(d[j])) + 1
        line = np.rint(np.linspace(a, b, max(L, 2))).astype(int)
        bridge = np.zeros_like(mat); bridge[line[:, 0], line[:, 1], line[:, 2]] = True
        bridge = ndimage.binary_dilation(bridge, iterations=BRIDGE_R)
        main |= (lab == k) | bridge
        bridged += 1
    mat = main
    print(f"  {name}: 조각 {n}개 → 가지로 이음 {bridged}, 작아서 버림 {dropped_small}, 멀어서 버림 {dropped_far}  (남은 복셀 {int(mat.sum()):,})")
    # 감면(fast_simplification)이 가는 가지를 끊어 먹어서, 300칸에서 잇기까지 한 뒤 2x2x2 max-pool 로 150칸으로 내려 메시화
    # (연결은 유지, 감면 비율이 완만해져 가지가 살아남음. 09-12 실측: 300칸 직접 감면 = 7~14 조각, 150칸 = 1 조각)
    sh = [(d // 2) * 2 for d in mat.shape]; m2 = mat[:sh[0], :sh[1], :sh[2]]
    m2 = m2.reshape(sh[0] // 2, 2, sh[1] // 2, 2, sh[2] // 2, 2).max(axis=(1, 3, 5))
    field = ndimage.gaussian_filter(m2.astype(np.float32), SMOOTH)
    verts, faces, _, _ = measure.marching_cubes(field, level=0.4)
    # 복셀 인덱스 → 월드 좌표 (vg.transform: 인덱스→월드)
    Vw = trimesh.transform_points(verts * 2.0, vg.transform)          # 150칸 인덱스 → 300칸 인덱스 → 월드
    # 계단(복셀 자국) 제거: 부피 보존형 Taubin 스무딩 → 붓 번짐처럼 둥글게
    mc = trimesh.Trimesh(Vw, faces, process=False)
    trimesh.smoothing.filter_taubin(mc, lamb=0.5, nu=-0.53, iterations=TAUBIN_IT)
    Vd, Fd = fast_simplification.simplify(np.asarray(mc.vertices, np.float32), np.asarray(mc.faces, np.int64), target_count=TARGET_FACES, agg=2)
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
    ncomp = len(td.split(only_watertight=False))
    print(f"{name}: 최종 컴포넌트 {ncomp} | 원 {len(Fs):,}면(조각) → 복셀 {mat.shape} → 마칭큐브 {len(faces):,} → 감면 {len(Fd):,}  크기 {np.round(e,3).tolist()}  "
          f"watertight={td.is_watertight}  {__import__('os').path.getsize(out)//1024} KB")
