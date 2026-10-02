"""
기와집 — 수묵 화풍 텍스처판 house_ink.glb  v2 (2026-09-13)
===========================================================
결정: 기와 무늬는 넣지 않는다. 집 전체(지붕·벽·기둥·기단·처마띠·용마루·추녀)를 **원화 먹 wash 한 장의 아틀라스**로 입힌다.
프리미티브 1개 / 텍스처 1장 (2048×1024) → 언리얼 슬롯 1개 (M_InwangHouseInk). 몸체 정점색 슬롯은 더 이상 없음.

원화 관찰 (근경 기와집): 지붕면은 담묵 wash 에 가로 붓결, 벽은 종이에 가까운 옅은 wash, 기둥은 중묵 세로획, 기단은 담묵 얼룩,
                         용마루·추녀·처마선은 진묵 획.
아틀라스 배치 (행 px): 지붕 0~511 (건물별 평면도, 사면마다 붓결 방향을 처마와 나란하게) · 벽 512~703 (4면 띠) ·
                       기단 옆면 704~767 · 기단 윗면 768~895 · 기둥 896~1023 (열 0~255, 세로획) · 진묵 패치 (열 1792~2047)
붓결 소스: 원화 지붕면 안쪽 wash 조각(ROOF_CROP, 우리 원본) 의 어둡기 → 부위마다 다른 농도 범위(DARK) 로 팔레트 착색.
출력: runtime/house_ink.glb, source/house/house_ink_atlas.png
언리얼: ue_setup_materials.py v6 (슬롯 1개면 슬롯 1 배정은 건너뜀). ue_toggle_house.py 로 house ↔ house_ink
"""
import os, json, numpy as np, trimesh
from PIL import Image
from scipy import ndimage

Image.MAX_IMAGE_PIXELS = None
RT = "assets/inwangjesaekdo/runtime"; SRC = "assets/inwangjesaekdo/source/house"; os.makedirs(SRC, exist_ok=True)
PAL = json.load(open("assets/inwangjesaekdo/records/ink_palette.json", encoding="utf-8"))
JIN, JUNG, DAM, YEOT, PAPER = (np.array(PAL[k], float) for k in ["진묵(0-5%)", "중묵(5-25%)", "담묵(25-55%)", "옅은담묵(55-80%)", "종이(85-95%)"])
PAINT = "/mnt/user-data/uploads/landscape_to_3D/PICs/inwangjesaekdo.jpg"
ROOF_CROP = (2170, 1325, 2400, 1385)   # 원화 px — 지붕면 안쪽 wash (획 제외)
# 부위별 먹 농도 범위 (팔레트 위치: 0 종이, 0.25 옅은담묵, 0.5 담묵, 0.75 중묵, 1 진묵)
DARK = {"roof": (0.40, 0.68), "wall": (0.04, 0.20), "stone": (0.26, 0.48), "post": (0.70, 0.86), "line": (1.0, 1.0)}
BRUSH_M = {"roof": 6.0, "wall": 5.0, "stone": 2.5, "post": 1.2}   # 붓 조각 하나가 덮는 실제 길이 (m) — 작을수록 결이 촘촘
W_, H_ = 2048, 1024
ROWS = {"roof": (0, 512), "wall": (512, 704), "stone_side": (704, 768), "stone_top": (768, 896), "post": (896, 1024)}
POST_COLS, LINE_COLS = (0, 256), (1792, 2048)
HIP_W, HIP_H = 0.30, 0.16
COL = {"roof": [38, 33, 29], "line": [10, 8, 8], "post": [16, 14, 13], "yeot": [85, 73, 57]}   # house.glb 정점색(linear) → 부위

# ── 붓결 소스
art = np.asarray(Image.open(PAINT).convert("L")).astype(float)
crop = art[ROOF_CROP[1]:ROOF_CROP[3], ROOF_CROP[0]:ROOF_CROP[2]]
lo, hi = np.percentile(crop, [3, 97]); brush = ndimage.gaussian_filter(np.clip((hi - crop) / max(hi - lo, 1), 0, 1), 0.8)   # 0 밝음 → 1 어두움
brush = np.block([[brush, brush[:, ::-1]], [brush[::-1], brush[::-1, ::-1]]])                     # 거울 2×2 (이음새 없음)
bh, bw = brush.shape


def wash(along_m, up_m, part, rot=False, seed=0.0):
    """실제 좌표(m) 격자에서 붓결 샘플 → 팔레트 위치. rot=True 면 붓결을 90° 돌림(옆 경사면)."""
    s = BRUSH_M[part]; a, u = (up_m, along_m) if rot else (along_m, up_m)
    r = (u / (s * bh / bw) * bh + seed * 37) % bh; c = (a / s * bw + seed * 91) % bw
    d = ndimage.map_coordinates(brush, [r, c], order=1, mode="wrap")
    lo_, hi_ = DARK[part]; return lo_ + (hi_ - lo_) * d


atlas_pos = np.zeros((H_, W_))          # 팔레트 위치
atlas_pos[:, :] = DARK["wall"][0]

# ── 메시 읽기 + 부위 분류
m = trimesh.load(f"{RT}/house.glb", force="mesh")
V = np.asarray(m.vertices); F = np.asarray(m.faces).copy(); C = np.asarray(m.visual.vertex_colors)[:, :3]
_area = np.linalg.norm(np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]), axis=1) / 2
print(f"면적 0 인 퇴화 면 {int((_area < 1e-6).sum())}/{len(F)} 제거 (house.glb 지붕에 72개 — 보이지 않는 면, 법선 계산만 방해)"); F = F[_area >= 1e-6]
fc = C[F[:, 0]]; N = np.asarray(m.face_normals); cen_f = V[F].mean(1)
bld_of = (cen_f[:, 0] >= 10).astype(int)                       # 0 = 작은 채(x<10), 1 = 큰 채
part = np.empty(len(F), dtype=object)
for fi in range(len(F)):
    c = fc[fi].tolist()
    if c == COL["roof"]: part[fi] = "roof"
    elif c == COL["line"]: part[fi] = "line"
    elif c == COL["post"]: part[fi] = "post"
    else: part[fi] = "yeot"
for b in (0, 1):                                                 # 기단 vs 벽: 건물 바닥 + 0.6 m 이하면 기단
    sel = (part == "yeot") & (bld_of == b); ymin = V[F[sel]][:, :, 1].min()
    for fi in np.where(sel)[0]:
        part[fi] = "stone" if V[F[fi]][:, 1].max() <= ymin + 0.6 else "wall"
print("부위별 면:", {k: int((part == k).sum()) for k in ("roof", "wall", "stone", "post", "line")})

# ── 건물 프레임 (지붕 정점 기준 PCA)
frames = []
for b in (0, 1):
    P = V[np.unique(F[(part == "roof") & (bld_of == b)])]
    y_e, y_r = P[:, 1].min(), P[:, 1].max()
    E = P[np.abs(P[:, 1] - y_e) < 0.3]; T = P[np.abs(P[:, 1] - y_r) < 0.3]
    cen = E[:, [0, 2]].mean(0); X = E[:, [0, 2]] - cen
    _, _, vt = np.linalg.svd(X, full_matrices=False); uax, wax = vt[0], vt[1]
    pu, pw = X @ uax, X @ wax; U, Wd = np.abs(pu).max(), np.abs(pw).max()
    Ru = np.abs((T[:, [0, 2]] - cen) @ uax).max()
    frames.append(dict(cen=cen, uax=uax, wax=wax, U=U, W=Wd, Ru=Ru, y_e=y_e, y_r=y_r))
    print(f"  건물 {b}: 처마 {2*U:.1f}×{2*Wd:.1f} m, 용마루 반길이 {Ru:.1f} m, 처마 y {y_e:.1f}, 용마루 y {y_r:.1f}")


def local(p, fr):
    xy = np.array([p[0], p[2]]) - fr["cen"]; return xy @ fr["uax"], xy @ fr["wax"]


# ── 0) 면 방향(winding) 통일 — house.glb 는 면의 앞뒤가 뒤섞여 있음 (지붕 34 %·기단 17 % 만 바깥향).
#   언리얼은 한면(single-sided) 렌더라 안쪽을 향한 면은 컬링되어 구멍 → 그 뒤 안쪽 면이 비쳐 '깨진' 어두운 조각으로 보임.
#   규칙: 면 중심 - 기준점 방향과 법선 내적 < 0 이면 정점 순서 뒤집음. 기준점 = 기둥은 기둥 축, 지붕은 처마·용마루 중간 높이의 중심(위·바깥 향),
#         벽·기단·획은 면 높이의 건물 중심(수평 바깥 향).
post_ax = {}
for fi in np.where(part == "post")[0]:                                   # 같은 기둥(xz 0.5 m 안) 면들의 평균 = 기둥 축
    post_ax[fi] = cen_f[(part == "post") & (np.abs(cen_f[:, 0] - cen_f[fi][0]) < 0.5) & (np.abs(cen_f[:, 2] - cen_f[fi][2]) < 0.5)].mean(0)
_m0 = trimesh.Trimesh(V, F, process=False)                                 # 붙어 있는 면 덩어리(기둥 하나, 보 하나, 기단 상자, 지붕 껍질…)
comp_of = np.zeros(len(F), int); comp_cen = []
for ci, comp in enumerate(trimesh.graph.connected_components(_m0.face_adjacency, nodes=np.arange(len(F)))):
    comp_of[comp] = ci; comp_cen.append(V[np.unique(F[comp])].mean(0))
comp_cen = np.array(comp_cen)
flipped = 0; fallback = 0
for fi in range(len(F)):
    b = bld_of[fi]; fr = frames[b]; c = cen_f[fi]; a, bb, cc_ = V[F[fi]]
    n = np.cross(bb - a, cc_ - a); n /= np.linalg.norm(n)
    if part[fi] == "post": ref = np.array([post_ax[fi][0], c[1], post_ax[fi][2]])          # 기둥: 축에서 바깥
    elif part[fi] == "roof": ref = np.array([fr["cen"][0], (fr["y_e"] + fr["y_r"]) / 2, fr["cen"][1]])   # 지붕: 껍질 중심 높이에서 위·바깥
    else: ref = comp_cen[comp_of[fi]]                                                       # 보·벽·기단: 자기 덩어리 중심에서 바깥
    d = c - ref; dot = np.dot(n, d)
    if abs(dot) < 1e-3 * (np.linalg.norm(d) + 1e-9):                                        # 덩어리 중심이 면 위에 있는 얇은 판 → 건물 중심 기준, 그래도 0이면 위쪽
        fallback += 1; d = c - np.array([fr["cen"][0], c[1], fr["cen"][1]]); dot = np.dot(n, d)
        if abs(dot) < 1e-6: dot = n[1]
    if dot < 0: F[fi] = F[fi][::-1]; flipped += 1
m = trimesh.Trimesh(V, F, process=False); N = np.asarray(m.face_normals)
def _ref(fi):
    c = cen_f[fi]; fr = frames[bld_of[fi]]
    if part[fi] == "post": return np.array([post_ax[fi][0], c[1], post_ax[fi][2]])
    if part[fi] == "roof": return np.array([fr["cen"][0], (fr["y_e"] + fr["y_r"]) / 2, fr["cen"][1]])
    return comp_cen[comp_of[fi]]
out_ratio = {k: round(float(np.mean([np.dot(N[fi], cen_f[fi] - _ref(fi)) >= -1e-9 for fi in np.where(part == k)[0]])), 2) for k in ("roof", "wall", "stone", "post", "line")}
print(f"면 방향 통일: 덩어리 {len(comp_cen)}개, {flipped}/{len(F)} 면 뒤집음 (얇은 판 예외 {fallback}) → 바깥향 비율 {out_ratio}  (모두 1.0 이어야 함)")


# 아틀라스 열 구간: 건물 1(큰 채) 0~1535, 건물 0(작은 채) 1536~2047 (지붕·벽·기단 공통)
COLR = {1: (0, 1536), 0: (1536, 2048)}

# ── 1) 지붕 영역: 건물별 평면도. 텍셀마다 어느 사면인지 판정해 붓결 방향 결정
r0, r1 = ROWS["roof"]
for b in (0, 1):
    fr = frames[b]; c0, c1 = COLR[b]; cols = np.arange(c0, c1); rows = np.arange(r0, r1)
    cc, rr = np.meshgrid(cols, rows)
    pu = (cc - c0 + 0.5) / (c1 - c0) * 2 * fr["U"] - fr["U"]; pw = (rr - r0 + 0.5) / (r1 - r0) * 2 * fr["W"] - fr["W"]
    hip_u = fr["Ru"] + (fr["U"] - fr["Ru"]) * (np.abs(pw) / fr["W"])        # 이 |pu| 보다 바깥이면 옆 경사면
    side = np.abs(pu) > hip_u
    front = wash(pu + fr["U"], np.abs(pw), "roof", rot=False, seed=b)       # 앞/뒤: 붓결이 용마루와 나란
    sides = wash(pw + fr["W"], np.abs(pu), "roof", rot=False, seed=b + 2)   # 옆: 붓결이 옆 처마와 나란
    atlas_pos[r0:r1, c0:c1] = np.where(side, sides, front)

# ── 2) 벽·기단 옆면 띠: 4면을 열 구간 4등분. 기단 윗면: 평면도. 기둥: 세로획. 진묵 패치
for key, (rr0, rr1), partname in (("wall", ROWS["wall"], "wall"), ("stone_side", ROWS["stone_side"], "stone")):
    for b in (0, 1):
        fr = frames[b]; c0, c1 = COLR[b]; cols = np.arange(c0, c1); rows = np.arange(rr0, rr1)
        cc, rr = np.meshgrid(cols, rows)
        per = (cc - c0 + 0.5) / (c1 - c0) * 2 * (2 * fr["U"] + 2 * fr["W"])   # 둘레 좌표 m (4면 이어 붙임)
        up = (rr - rr0 + 0.5) / (rr1 - rr0) * (3.0 if key == "wall" else 0.6)
        atlas_pos[rr0:rr1, c0:c1] = wash(per, up, partname, seed=b + 4)
rr0, rr1 = ROWS["stone_top"]
for b in (0, 1):
    fr = frames[b]; c0, c1 = COLR[b]; cols = np.arange(c0, c1); rows = np.arange(rr0, rr1); cc, rr = np.meshgrid(cols, rows)
    atlas_pos[rr0:rr1, c0:c1] = wash((cc - c0 + 0.5) / (c1 - c0) * 2 * fr["U"], (rr - rr0 + 0.5) / (rr1 - rr0) * 2 * fr["W"], "stone", seed=b + 6)
rr0, rr1 = ROWS["post"]; pc0, pc1 = POST_COLS
cc, rr = np.meshgrid(np.arange(pc0, pc1), np.arange(rr0, rr1))
atlas_pos[rr0:rr1, pc0:pc1] = wash((rr - rr0 + 0.5) / (rr1 - rr0) * 3.0, (cc - pc0 + 0.5) / (pc1 - pc0) * 0.8, "post", seed=9)   # 세로획: along = 높이
atlas_pos[rr0:rr1, LINE_COLS[0]:LINE_COLS[1]] = 1.0
# 기단 얼룩(돌): 저주파 노이즈 살짝
rng = np.random.default_rng(3); nz = ndimage.gaussian_filter(rng.random((H_, W_)), 6); nz = (nz - nz.mean()) / nz.std()
for (rr0, rr1) in (ROWS["stone_side"], ROWS["stone_top"]): atlas_pos[rr0:rr1] += 0.05 * nz[rr0:rr1]
stops = np.array([PAPER, YEOT, DAM, JUNG, JIN]); pos = np.array([0, 0.25, 0.5, 0.75, 1.0])
rgb = np.stack([np.interp(np.clip(atlas_pos, 0, 1), pos, stops[:, k]) for k in range(3)], -1).astype(np.uint8)
Image.fromarray(rgb).save(f"{SRC}/house_ink_atlas.png")

# ── 3) UV: 면마다 정점 분리, 부위별 매핑. 추녀 획 상자도 추가(진묵 패치)
Vo = V[F].reshape(-1, 3); UV = np.zeros((len(Vo), 2)); Fo = np.arange(len(Vo)).reshape(-1, 3)
def px2uv(col, row): return np.array([col / W_, 1 - row / H_])              # trimesh 규약 (v=0 이미지 아래)
def uv_line(): return px2uv((LINE_COLS[0] + LINE_COLS[1]) / 2, (ROWS["post"][0] + ROWS["post"][1]) / 2)
post_axis = {}                                                            # 기둥 중심 (같은 기둥 = 같은 xz)
for fi in range(len(F)):
    b = bld_of[fi]; fr = frames[b]; c0, c1 = COLR[b]; tri = Vo[3 * fi:3 * fi + 3]; p = part[fi]
    for k in range(3):
        q = tri[k]; pu, pw = local(q, fr)
        if p == "roof":
            col = c0 + (pu + fr["U"]) / (2 * fr["U"]) * (c1 - c0); row = ROWS["roof"][0] + (pw + fr["W"]) / (2 * fr["W"]) * (ROWS["roof"][1] - ROWS["roof"][0])
        elif p in ("wall", "stone"):
            n = N[fi]; nu, nw = np.dot([n[0], n[2]], fr["uax"]), np.dot([n[0], n[2]], fr["wax"])
            if p == "stone" and abs(n[1]) > 0.7:                                  # 기단 윗면(또는 밑면): 평면도
                rr0, rr1 = ROWS["stone_top"]
                col = c0 + (pu + fr["U"]) / (2 * fr["U"]) * (c1 - c0); row = rr0 + (pw + fr["W"]) / (2 * fr["W"]) * (rr1 - rr0)
            else:
                Lp = 2 * fr["U"] + 2 * fr["W"]                                    # 둘레: +w면 0~2U, +u면 2U~2U+2W, -w면 …, -u면 …
                if abs(nw) >= abs(nu): per = (pu + fr["U"]) + (0 if nw > 0 else 2 * fr["U"] + 2 * fr["W"])
                else:                  per = (pw + fr["W"]) + (2 * fr["U"] if nu > 0 else 2 * (2 * fr["U"] + fr["W"]))
                rr0, rr1 = ROWS["wall"] if p == "wall" else ROWS["stone_side"]
                ymin = V[F[(part == p) & (bld_of == b)]][:, :, 1].min(); hspan = 3.0 if p == "wall" else 0.6
                col = c0 + (per / (2 * Lp)) * (c1 - c0); row = rr1 - np.clip((q[1] - ymin) / hspan, 0, 1) * (rr1 - rr0)
        elif p == "post":
            key = (round(float(cen_f[fi][0]), 0), round(float(cen_f[fi][2]), 0))
            ax = post_axis.setdefault(key, cen_f[(part == "post") & (np.abs(cen_f[:, 0] - cen_f[fi][0]) < 0.5) & (np.abs(cen_f[:, 2] - cen_f[fi][2]) < 0.5)].mean(0))
            ang = (np.arctan2(q[2] - ax[2], q[0] - ax[0]) / (2 * np.pi)) % 1.0
            rr0, rr1 = ROWS["post"]; ymin = V[F[(part == "post") & (bld_of == b)]][:, :, 1].min()
            col = POST_COLS[0] + ang * (POST_COLS[1] - POST_COLS[0] - 1); row = rr1 - np.clip((q[1] - ymin) / 3.0, 0, 1) * (rr1 - rr0)
        else:
            col, row = (LINE_COLS[0] + LINE_COLS[1]) / 2, (ROWS["post"][0] + ROWS["post"][1]) / 2
        UV[3 * fi + k] = px2uv(col, row)
Vo = list(map(list, Vo)); UVl = list(map(list, UV)); Fo = list(map(list, Fo))


def add_box(p0, p1, w, h, ext=0.0):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float); a = p1 - p0; a /= np.linalg.norm(a); p0 = p0 - a * ext; p1 = p1 + a * ext
    r = np.cross(a, [0, 1, 0]); r /= np.linalg.norm(r) + 1e-9; u = np.cross(r, a); u = u if u[1] >= 0 else -u; o = len(Vo)
    for p in (p0, p1):
        for sw, sh in ((-1, 0), (1, 0), (1, 1), (-1, 1)): Vo.append(list(p + r * sw * w / 2 + u * (sh * h))); UVl.append(list(uv_line()))
    bc = np.mean(Vo[o:o + 8], 0)
    for a_, b_, c_, d_ in [[0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7], [0, 3, 2, 1], [4, 5, 6, 7]]:
        for tri in ([o + a_, o + b_, o + c_], [o + a_, o + c_, o + d_]):
            P3 = np.array([Vo[i] for i in tri]); n = np.cross(P3[1] - P3[0], P3[2] - P3[0])
            Fo.append(tri if np.dot(n, P3.mean(0) - bc) >= 0 else tri[::-1])   # 상자 중심 기준 바깥향으로


for b in (0, 1):                                                          # 추녀 획 (원화의 모서리 능선 획)
    fr = frames[b]; P = V[np.unique(F[(part == "roof") & (bld_of == b)])]
    E = P[np.abs(P[:, 1] - fr["y_e"]) < 0.3]; T = P[np.abs(P[:, 1] - fr["y_r"]) < 0.3]
    lu = np.array([local(p, fr)[0] for p in E]); lw = np.array([local(p, fr)[1] for p in E])
    corners = [E[np.argmax(su * lu / fr["U"] + sw * lw / fr["W"])] for su, sw in ((1, 1), (1, -1), (-1, 1), (-1, -1))]
    tu = np.array([local(p, fr)[0] for p in T]); R1, R2 = T[np.argmin(tu)], T[np.argmax(tu)]
    for c in corners:
        Rn = R1 if np.linalg.norm(c - R1) < np.linalg.norm(c - R2) else R2
        add_box(c + [0, 0.03, 0], Rn + [0, 0.03, 0], HIP_W, HIP_H, ext=0.15)

mat = trimesh.visual.material.PBRMaterial(baseColorTexture=Image.open(f"{SRC}/house_ink_atlas.png"), metallicFactor=0.0, roughnessFactor=1.0)
out = trimesh.Trimesh(np.array(Vo), np.array(Fo), process=False, visual=trimesh.visual.TextureVisuals(uv=np.array(UVl), material=mat))
out.vertex_normals = np.repeat(out.face_normals, 3, axis=0)              # 면마다 정점 분리 → 정점 법선 = 면 법선 (평면 음영)
out.export(f"{RT}/house_ink.glb", include_normals=True)
chk = trimesh.load(f"{RT}/house_ink.glb", force="mesh"); t = np.asarray(chk.visual.material.baseColorTexture.convert("RGB"))
uvc = np.asarray(chk.visual.uv)
# 자체 검증: 다시 읽은 파일에서 지붕 면(y 가 처마 이상, 획 상자 제외 = 원본 면 인덱스 범위)의 법선이 위를 향하는 비율
Nc = np.asarray(chk.face_normals); roof_i = np.where(part == "roof")[0]
up_ratio = float(np.mean(Nc[roof_i][:, 1] > 0))
import json as _json, struct as _st
with open(f"{RT}/house_ink.glb", "rb") as fh:
    fh.seek(12); ln = _st.unpack("<I", fh.read(4))[0]; fh.read(4); gj = _json.loads(fh.read(ln))
has_nrm = "NORMAL" in gj["meshes"][0]["primitives"][0]["attributes"]
print(f"검증: 지붕 면 법선 위쪽 비율 {up_ratio:.2f} (1.00 이어야 함)  glb 에 NORMAL 속성 {'있음' if has_nrm else '없음!!'}  두면 doubleSided {gj['materials'][0].get('doubleSided', False)}")
print(f"house_ink.glb v2: 면 {len(chk.faces)} (원본 {len(F)} 유효면 + 추녀 획 96)  텍스처 {t.shape[1]}×{t.shape[0]}  UV 범위 {uvc.min(0).round(2)}~{uvc.max(0).round(2)} (0~1 안이어야 함)  "
      f"바운드 house.glb 와 동일(±0.5) {np.allclose(chk.bounds, m.bounds, atol=0.5)}  {os.path.getsize(f'{RT}/house_ink.glb') // 1024} KB")
print(">>> " + ("OK — 프리미티브 1개, 슬롯 1개" if (uvc.min() >= -1e-6 and uvc.max() <= 1 + 1e-6) else "!! UV 범위 벗어남"))
