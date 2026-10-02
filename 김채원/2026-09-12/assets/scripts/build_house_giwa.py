"""
기와집 v3 — 기와 무늬 텍스처 버전 house_giwa.glb (2026-09-13)
==============================================================
원화의 기와집엔 기와 무늬가 없다(먹 면으로만 그림). 그래서 원본 house.glb 는 그대로 두고, 지붕면(담묵 면)에만
기와 무늬 텍스처를 입힌 **별도 메시**를 만든다 → 언리얼에서 house / house_giwa 를 토글 (ue_toggle_giwa.py).

구조: glTF 메시 하나에 프리미티브 2개 (언리얼 머티리얼 슬롯 2개로 들어옴 — 추정, 로그로 확인)
  · 슬롯 0 roof : 지붕면. 평면 UV (처마 방향 = 기와 열, 높이 = 기와 단) + 기와 텍스처 (REPEAT)
  · 슬롯 1 body : 나머지(기단·벽·기둥·처마띠·용마루). 정점색 그대로 (M_InwangVertexUnlit)
기와 텍스처 v2 (source/house/giwa_tile.png, 1024×2048, 가로 8열 반복 / 세로 24단 = 지붕 전체, 처마 단 = 막새):
  · 참고 사진(한옥 지붕)에서 읽은 규칙만 사용, 픽셀 사용 없음 — 규칙은 코드 주석 참조
  · COLOR_PRESET "ink"(먹 팔레트) / "slate"(회청색)
스케일: 기와 한 장 폭 TILE_W m, 한 단 높이(경사면 투영) TILE_H m
출력: runtime/house_giwa.glb, source/house/giwa_tile.png, source/house/preview_house_giwa.jpg
"""
import os, json, struct, numpy as np, trimesh
from PIL import Image
from scipy import ndimage

RT = "assets/inwangjesaekdo/runtime"; SRC = "assets/inwangjesaekdo/source/house"; os.makedirs(SRC, exist_ok=True)
PAL = json.load(open("assets/inwangjesaekdo/records/ink_palette.json", encoding="utf-8"))
JIN, JUNG, DAM, YEOT, PAPER = (np.array(PAL[k], float) for k in ["진묵(0-5%)", "중묵(5-25%)", "담묵(25-55%)", "옅은담묵(55-80%)", "종이(85-95%)"])
TILE_W, TILE_H = 0.30, 0.22        # m — 기와 열 간격(수키와 중심 간) / 한 단의 수직 높이 — 참고 사진 비율에서 추정
ROOF_LIN = np.array([38, 33, 29])  # house.glb 지붕면 정점색 (담묵, linear 바이트)


def srgb_to_linear(c):
    x = np.asarray(c, float) / 255; return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4) * 255


# ── 1) 기와 텍스처 (v2, 09-13: 참고 사진에서 읽은 규칙으로 재구성 — 픽셀은 쓰지 않음)
#   사진에서 읽은 것: ① 수키와 능선이 가늘고 밝은 선으로 도드라지고 그 사이(암키와)는 어둡고 거의 균일
#                    ② 단(가로 이음)은 희미하게만 보임   ③ 처마 끝은 열마다 둥근 수막새가 한 줄, 그 사이 암막새는 어두움
#   세로(경사) 방향은 반복하지 않는다: 텍스처 아래 첫 단 = 막새 줄, 그 위로 ROWS 단이 지붕 전체 높이를 덮음 (wrapT = CLAMP)
#   가로 방향은 8열 반복 (wrapS = REPEAT)
W_, H_ = 1024, 2048; COLS, ROWS = 8, 24; cw, rh = W_ / COLS, H_ / ROWS          # 실수 나눗셈 (2048/24 가 정수가 아니라 끝 8 px 가 튀던 것 수정)
COLOR_PRESET = "ink"     # "ink" = 먹 팔레트(장면 통일) | "slate" = 사진의 회청색
if COLOR_PRESET == "slate":
    FIELD, MID, HILITE, RIM = np.array([46, 54, 63.]), np.array([70, 80, 90.]), np.array([205, 212, 218.]), np.array([150, 158, 165.])
else:
    FIELD, MID, HILITE, RIM = JIN, JUNG, YEOT, DAM
yy, xx = np.mgrid[0:H_, 0:W_]
t = (xx % cw) / cw                                   # 열 안 위치 0~1
row = ROWS - 1 - np.floor(yy / rh).astype(int)                          # 0 = 처마(맨 아래 단) … 이미지 위가 용마루 쪽
s_ = (yy % rh) / rh                                  # 단 안 위치 (0 위 → 1 아래)
b = np.zeros((H_, W_))                               # 밝기 0(FIELD) ~ 1(HILITE)
# 수키와 능선: 열 중심 폭 34%, 능선 꼭대기(가운데 8%)만 강하게 밝고 양옆은 빠르게 어두워짐 (사진 ①)
c_ = (t - 0.5) / 0.17                                # -1~1 이 수키와 구간
su = np.abs(c_) < 1
b = np.where(su, np.clip(1 - c_ ** 2, 0, 1) ** 2.2 * 0.95 + 0.12, b)         # 좁고 밝은 능선
b = np.where(su & (c_ > 0.45), b * 0.45, b)                                    # 오른쪽 그늘
# 암키와 골: 거의 균일하게 어둡고 수키와 밑동 쪽으로 살짝 더 어두움 (사진 ①)
am = ~su; edge = np.minimum(np.abs(t - 0.33), np.abs(t - 0.67)) / 0.33
b = np.where(am, 0.10 + 0.06 * edge, b)
# 단 이음: 희미한 어두운 선 + 단 아래쪽 살짝 밝게 (겹친 기와 끝) (사진 ②)
b += 0.10 * np.exp(-((s_ - 0.96) ** 2) / 0.0012) * -1
b += 0.05 * np.clip((s_ - 0.85) / 0.15, 0, 1) * su
# 막새 줄 (row 0): 수막새 = 열마다 둥근 원판 (밝은 테, 어두운 중심, 가운데 작은 돌기), 암막새 = 어두운 띠 (사진 ③)
mk = row == 0
cx_, cy_ = 0.5, 0.55; r_ = np.hypot((t - cx_) * (cw / rh), (s_ - cy_)) / 0.42      # 원판 반지름 (단 높이 기준)
disc = r_ < 1
b = np.where(mk, 0.08, b)                                                      # 암막새 띠
b = np.where(mk & disc, 0.35 + 0.45 * np.clip((r_ - 0.62) / 0.38, 0, 1) - 0.25 * (r_ < 0.15), b)  # 밝은 테 + 어두운 중심 + 돌기
b = np.where(mk & disc & (np.abs(r_ - 0.98) < 0.06), 0.9, b)                   # 테두리 하이라이트
# 세월: 저주파 얼룩 + 단마다 밝기 편차
rng = np.random.default_rng(5)
nz = ndimage.gaussian_filter(rng.random((H_, W_)), 24); nz = (nz - nz.mean()) / nz.std()
rowvar = rng.uniform(-0.04, 0.04, ROWS)[np.clip(row, 0, ROWS - 1)]
b = np.clip(b + 0.06 * nz + rowvar, 0, 1)
# 밝기 → 색 (FIELD → MID → RIM → HILITE)
stops = np.array([FIELD, MID, RIM, HILITE]); pos = np.array([0, 0.3, 0.65, 1.0])
rgb = np.stack([np.interp(b, pos, stops[:, k]) for k in range(3)], -1).astype(np.uint8)
Image.fromarray(rgb).save(f"{SRC}/giwa_tile.png")
Image.fromarray(rgb[int(H_ - 4 * rh):, :int(4 * cw)]).resize((int(8 * cw), int(8 * rh)), Image.LANCZOS).save(f"{SRC}/giwa_tile_zoom.jpg", quality=90)

# ── 2) 지붕면 / 몸체 분리
m = trimesh.load(f"{RT}/house.glb", force="mesh")
V = np.asarray(m.vertices); F = np.asarray(m.faces); C = np.asarray(m.visual.vertex_colors)
roof = (C[F[:, 0], :3] == ROOF_LIN).all(1)
print(f"house.glb 면 {len(F)} → 지붕면 {roof.sum()} / 몸체 {(~roof).sum()}")
Fr, Fb = F[roof], F[~roof]
# 지붕: 면마다 정점 분리 후 평면 UV (법선이 x 쪽이면 z 를 열 방향으로, z 쪽이면 x 를)
Nn = np.asarray(m.face_normals)[roof]
Vr = V[Fr].reshape(-1, 3); Cr = C[Fr].reshape(-1, 4)
# ── 열의 흐름 (09-13 v3): 열은 평행이 아니라 **용마루에서 처마로 내려오며 모서리 쪽으로 펼쳐진다** (사진·요청 스케치)
#   앞뒤 경사면 = 사다리꼴 (위 = 용마루 길이, 아래 = 처마 길이). 높이 h 에서의 좌우 경계(모서리→용마루 끝)를 잇는 선 사이를
#   등분해 열 좌표를 잡으면 가운데 열은 곧고 양끝 열은 용마루 끝으로 모이며 기울어짐.
#   양옆 경사면 = 삼각형 (두 모서리 → 같은 용마루 끝). 같은 식이면 열이 꼭짓점으로 부채꼴로 모임 (추녀 쪽 기와 흐름).
#   열 간격은 처마에서 TILE_W, 위로 갈수록 폭 비율만큼 좁아짐.
roofV_all = V[np.unique(Fr)]
def building_frame(P):
    y_e, y_r = P[:, 1].min(), P[:, 1].max()
    E = P[np.abs(P[:, 1] - y_e) < 0.3]; T = P[np.abs(P[:, 1] - y_r) < 0.3]
    cen = E[:, [0, 2]].mean(0); X = E[:, [0, 2]] - cen
    _, _, vt = np.linalg.svd(X, full_matrices=False); uax, wax = vt[0], vt[1]
    pu, pw = X @ uax, X @ wax; su, sw = pu / (np.abs(pu).max() + 1e-9), pw / (np.abs(pw).max() + 1e-9)
    corners = {(sgu, sgw): E[np.argmax(sgu * su + sgw * sw)] for sgu in (1, -1) for sgw in (1, -1)}
    tu = (T[:, [0, 2]] - cen) @ uax; R = {-1: T[np.argmin(tu)], 1: T[np.argmax(tu)]}
    return dict(y_e=y_e, y_r=y_r, cen=cen, uax=uax, wax=wax, corners=corners, R=R)
frames = [building_frame(roofV_all[roofV_all[:, 0] < 10]), building_frame(roofV_all[roofV_all[:, 0] >= 10])]
along = np.zeros(len(Vr)); eave = np.zeros(len(Vr))
for fi in range(len(Fr)):
    tri = Vr[3 * fi:3 * fi + 3]; fr = frames[0] if tri[:, 0].mean() < 10 else frames[1]
    n = Nn[fi]; nu, nw = np.dot([n[0], n[2]], fr["uax"]), np.dot([n[0], n[2]], fr["wax"])
    for k in range(3):
        p = tri[k]; xy = np.array([p[0], p[2]]) - fr["cen"]; pu_, pw_ = xy @ fr["uax"], xy @ fr["wax"]
        h = np.clip((p[1] - fr["y_e"]) / max(fr["y_r"] - fr["y_e"], 1e-6), 0, 1)
        proj = lambda q: (np.array([q[0], q[2]]) - fr["cen"])
        if abs(nw) >= abs(nu):                                   # 앞/뒤 경사면 (사다리꼴): 열 축 = 용마루 축
            sgw = 1 if nw > 0 else -1
            cL, cR = fr["corners"][(-1, sgw)], fr["corners"][(1, sgw)]
            eL, eR = proj(cL) @ fr["uax"], proj(cR) @ fr["uax"]; rL, rR = proj(fr["R"][-1]) @ fr["uax"], proj(fr["R"][1]) @ fr["uax"]
            coord = pu_
        else:                                                     # 양옆 경사면 (삼각형): 열 축 = 폭 축, 위쪽은 용마루 끝 한 점
            sgu = 1 if nu > 0 else -1
            cL, cR = fr["corners"][(sgu, -1)], fr["corners"][(sgu, 1)]
            eL, eR = proj(cL) @ fr["wax"], proj(cR) @ fr["wax"]; rw = proj(fr["R"][sgu]) @ fr["wax"]; rL = rR = rw
            coord = pw_
        L = eL + (rL - eL) * h; Rr = eR + (rR - eR) * h; width = max(Rr - L, 0.3)
        rel = (coord - L) / width                                 # 0~1 경계 사이 위치
        along[3 * fi + k] = rel * abs(eR - eL)                    # 처마 길이 기준 m → 처마에서 TILE_W 간격
        eave[3 * fi + k] = fr["y_e"]
uv = np.c_[along / (COLS * TILE_W), (Vr[:, 1] - eave) / (ROWS * TILE_H)]      # v: 0 처마 → 1 은 ROWS 단 위 (CLAMP)
print(f"지붕 높이 최대 {float((Vr[:,1]-eave).max()):.1f} m → v 최대 {float(((Vr[:,1]-eave)/(ROWS*TILE_H)).max()):.2f} (1 미만이어야 막새가 한 줄만)  "
      f"열 좌표 범위 {along.min():.1f}~{along.max():.1f} m")
mat = trimesh.visual.material.PBRMaterial(baseColorTexture=Image.open(f"{SRC}/giwa_tile.png"), metallicFactor=0.0, roughnessFactor=1.0)
roof_m = trimesh.Trimesh(Vr, np.arange(len(Vr)).reshape(-1, 3), process=False, visual=trimesh.visual.TextureVisuals(uv=uv, material=mat))
vi, inv = np.unique(Fb, return_inverse=True)   # 몸체 (정점색) + 아래 부속 기하
BV = [list(v) for v in V[vi]]; BF = [list(f) for f in inv.reshape(-1, 3)]; BC = [list(c) for c in C[vi]]

# ── 2b) 지붕 부속 기하 (09-13, 참고 사진의 지붕 '전체' 구조에서 읽은 것 — 텍스처가 아니라 기하로 넣음, 색은 정점색 → 몸체 슬롯)
#   사진에서 읽은 것: ④ 용마루는 두툼한 검은 띠, 양 끝이 위로 들린 망와   ⑤ 네 모서리로 내려오는 추녀마루가 두툼하게 솟고
#                    그 아랫단에 밝은 회(양성) 선이 따라감, 끝에도 망와      ⑥ 처마 밑엔 서까래 끝이 밝은 점으로 한 줄
LIN = lambda c: srgb_to_linear(np.array(c, float))
JIN_L, JUNG_L, YEOT_L = LIN(JIN), LIN(JUNG), LIN(YEOT)
RIDGE_W, RIDGE_H = 0.85, 0.55          # 용마루 폭·높이 (m)
HIP_W, HIP_H = 0.55, 0.40              # 추녀마루 폭·높이
LIME_H = 0.08                          # 양성(밝은 회) 띠 두께
MANGWA = (0.45, 0.85, 0.45)            # 망와 블록 (폭, 높이, 깊이)
RAFTER_R, RAFTER_L, RAFTER_GAP = 0.09, 0.9, 0.45   # 서까래 반지름·길이·간격
trim_faces0 = len(BF)


def add_box(p0, p1, w, h, col, y_off=0.0, ext=0.0):
    """p0→p1 방향 상자. 폭 w(수평 직교), 높이 h(위), y_off 만큼 띄움, 양 끝 ext 만큼 연장"""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float); a = p1 - p0; L = np.linalg.norm(a); a /= L
    p0 = p0 - a * ext; p1 = p1 + a * ext
    r = np.cross(a, [0, 1, 0]); r /= np.linalg.norm(r) + 1e-9; u = np.cross(r, a); u = u if u[1] >= 0 else -u
    o = len(BV)
    for p in (p0, p1):
        for sw, sh in ((-1, 0), (1, 0), (1, 1), (-1, 1)):
            BV.append(list(p + r * sw * w / 2 + u * (sh * h) + [0, y_off, 0])); BC.append([*col, 255])
    q = [[0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7], [0, 3, 2, 1], [4, 5, 6, 7]]
    for a_, b_, c_, d_ in q: BF.extend([[o + a_, o + b_, o + c_], [o + a_, o + c_, o + d_]])


def add_cyl(p0, p1, rad, sides, col, cap_col):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float); a = p1 - p0; a /= np.linalg.norm(a)
    r = np.cross(a, [0, 1, 0]); r /= np.linalg.norm(r) + 1e-9; u = np.cross(r, a); o = len(BV)
    for p in (p0, p1):
        for k in range(sides):
            t_ = 2 * np.pi * k / sides; BV.append(list(p + rad * (np.cos(t_) * r + np.sin(t_) * u))); BC.append([*col, 255])
    for k in range(sides):
        j = (k + 1) % sides; BF.extend([[o + k, o + j, o + sides + j], [o + k, o + sides + j, o + sides + k]])
    c = len(BV); BV.append(list(p1)); BC.append([*cap_col, 255])
    for k in range(sides): BF.append([o + sides + k, o + sides + (k + 1) % sides, c])


roofV = V[np.unique(Fr)]
bld = [roofV[roofV[:, 0] < 10], roofV[roofV[:, 0] >= 10]]              # 건물 둘 (x 로 갈림 — house.glb 배치 기준)
for P in bld:
    y_e, y_r = P[:, 1].min(), P[:, 1].max()
    E = P[np.abs(P[:, 1] - y_e) < 0.3]; T = P[np.abs(P[:, 1] - y_r) < 0.3]
    cen = E[:, [0, 2]].mean(0); X = E[:, [0, 2]] - cen
    _, _, vt = np.linalg.svd(X, full_matrices=False); uax, wax = vt[0], vt[1]
    pu, pw = X @ uax, X @ wax; su, sw = pu / (np.abs(pu).max() + 1e-9), pw / (np.abs(pw).max() + 1e-9)
    corners = [E[np.argmax(sgu * su + sgw * sw)] for sgu, sgw in ((1, 1), (1, -1), (-1, 1), (-1, -1))]
    tu = (T[:, [0, 2]] - cen) @ uax; R1, R2 = T[np.argmin(tu)], T[np.argmax(tu)]
    # ④ 용마루 + 망와
    add_box(R1, R2, RIDGE_W, RIDGE_H, JIN_L, y_off=-0.15, ext=0.25)
    a = (R2 - R1) / np.linalg.norm(R2 - R1); r_ = np.cross(a, [0, 1, 0]); r_ /= np.linalg.norm(r_)
    for sgn in (-1, 1):
        add_box(R1 + r_ * sgn * RIDGE_W / 2, R2 + r_ * sgn * RIDGE_W / 2, 0.07, LIME_H, YEOT_L, y_off=-0.15, ext=0.25)   # 양성 선
    for Rp, d in ((R1, -a), (R2, a)):
        add_box(Rp + d * 0.3, Rp + d * (0.3 + MANGWA[2]), MANGWA[0], MANGWA[1], JIN_L, y_off=-0.15)                 # 망와
    # ⑤ 추녀마루 4개 + 양성 선 + 끝 망와
    for c in corners:
        Rn = R1 if np.linalg.norm(c - R1) < np.linalg.norm(c - R2) else R2
        c_lift = c + [0, 0.10, 0]; top = Rn + [0, 0.05, 0]
        add_box(c_lift, top, HIP_W, HIP_H, JIN_L)
        a_ = (top - c_lift) / np.linalg.norm(top - c_lift); r_ = np.cross(a_, [0, 1, 0]); r_ /= np.linalg.norm(r_)
        for sgn in (-1, 1):
            add_box(c_lift + r_ * sgn * HIP_W / 2, top + r_ * sgn * HIP_W / 2, 0.07, LIME_H, YEOT_L)
        out = c_lift - a_ * 0.35
        add_box(out, c_lift + a_ * 0.25, HIP_W * 0.8, HIP_H + 0.25, JIN_L)                                            # 모서리 망와(들림)
    # ⑥ 서까래: 처마 링을 각도순으로 돌며 간격마다 원통
    ang = np.arctan2(X[:, 1], X[:, 0]); order = np.argsort(ang); ring = E[order]
    n_r = 0
    for i in range(len(ring)):
        p, q = ring[i], ring[(i + 1) % len(ring)]; seg = q - p; L = np.linalg.norm(seg); d = seg / L
        out_n = np.cross(d, [0, 1, 0]); out_n[1] = 0; out_n /= np.linalg.norm(out_n) + 1e-9
        if np.dot(out_n, np.array([p[0] - cen[0], 0, p[2] - cen[1]])) < 0: out_n = -out_n                          # 바깥쪽
        k = 0.5 * RAFTER_GAP
        while k < L:
            b_ = p + d * k + [0, -0.30, 0]
            add_cyl(b_ - out_n * (RAFTER_L * 0.6) + [0, 0.12, 0], b_ + out_n * (RAFTER_L * 0.4), RAFTER_R, 5, JUNG_L, YEOT_L)
            k += RAFTER_GAP; n_r += 1
    print(f"  건물: 처마 y {y_e:.1f} 용마루 y {y_r:.1f} 길이 {np.linalg.norm(R2 - R1):.1f} m, 추녀마루 4, 서까래 {n_r}")
print(f"지붕 부속 기하 추가: 면 {len(BF) - trim_faces0:,}")
body_m = trimesh.Trimesh(np.array(BV, float), np.array(BF), process=False, visual=trimesh.visual.ColorVisuals(vertex_colors=np.array(BC, np.uint8)))
roof_m.export(f"{SRC}/_roof.glb"); body_m.export(f"{SRC}/_body.glb")


# ── 3) 두 glb 를 프리미티브 2개짜리 메시 하나로 합침 (바이너리 버퍼 이어붙이기)
def read_glb(p):
    b = open(p, "rb").read(); jl = struct.unpack_from("<I", b, 12)[0]
    j = json.loads(b[20:20 + jl]); bl = struct.unpack_from("<I", b, 20 + jl)[0]
    return j, bytearray(b[28 + jl:28 + jl + bl])


jr, br = read_glb(f"{SRC}/_roof.glb"); jb, bb = read_glb(f"{SRC}/_body.glb")
while len(br) % 4: br.append(0)
off = len(br)
for bv in jb["bufferViews"]: bv["byteOffset"] = bv.get("byteOffset", 0) + off; bv["buffer"] = 0
nbv, nacc = len(jr["bufferViews"]), len(jr["accessors"])
for a in jb["accessors"]: a["bufferView"] += nbv
prim = jb["meshes"][0]["primitives"][0]
prim["attributes"] = {k: v + nacc for k, v in prim["attributes"].items()}
if "indices" in prim: prim["indices"] += nacc
prim.pop("material", None)                                   # 몸체는 머티리얼 없음 (정점색) → 언리얼 슬롯 1
jr["samplers"] = [{"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 33071}]   # 가로 반복, 세로 클램프
for tx in jr.get("textures", []): tx["sampler"] = 0
jr["bufferViews"] += jb["bufferViews"]; jr["accessors"] += jb["accessors"]
jr["meshes"][0]["primitives"].append(prim); jr["meshes"][0]["name"] = "house_giwa"
jr["nodes"] = [{"mesh": 0, "name": "house_giwa"}]; jr["scenes"] = [{"nodes": [0]}]; jr["scene"] = 0
buf = br + bb; jr["buffers"] = [{"byteLength": len(buf)}]
js = json.dumps(jr, separators=(",", ":")).encode("utf-8")
while len(js) % 4: js += b" "
out = bytearray(b"glTF") + struct.pack("<II", 2, 12 + 8 + len(js) + 8 + len(buf))
out += struct.pack("<II", len(js), 0x4E4F534A) + js + struct.pack("<II", len(buf), 0x004E4942) + buf
open(f"{RT}/house_giwa.glb", "wb").write(out); os.remove(f"{SRC}/_roof.glb"); os.remove(f"{SRC}/_body.glb")

# ── 4) 검증: 다시 읽어 프리미티브 2개, 텍스처, 바운드가 house.glb 와 같은지
sc = trimesh.load(f"{RT}/house_giwa.glb")
geoms = list(sc.geometry.values()) if isinstance(sc, trimesh.Scene) else [sc]
jj, _ = read_glb(f"{RT}/house_giwa.glb")
nprim = len(jj["meshes"][0]["primitives"]); has_tex = "baseColorTexture" in json.dumps(jj["materials"][0])
allv = np.vstack([np.asarray(g.vertices) for g in geoms])
same = np.allclose(allv.min(0), m.bounds[0], atol=1.0) and np.allclose(allv.max(0), m.bounds[1], atol=1.0)
print(f"house_giwa.glb: 프리미티브 {nprim} (roof 텍스처 {has_tex}, body 정점색)  면 {sum(len(g.faces) for g in geoms)}  "
      f"바운드 house.glb 와 동일(부속 기하로 조금 커짐, ±1 m 허용) {same}  {os.path.getsize(f'{RT}/house_giwa.glb') // 1024} KB")
print(">>> " + ("OK — 언리얼에서 house 와 같은 자리에 두고 토글" if (nprim == 2 and has_tex and same) else "!! 검증 실패"))
