"""
화제(畫題) 안내판 inscription_board.glb  (2026-09-13)
=====================================================
요청: 원화 위치에 떠 있던 화제 글씨(inscription.glb) 대신, 큰 기와집 앞에 세운 안내판에 화제의 뜻을 풀어 쓴다.
내용 근거: 국립중앙박물관 큐레이터 추천 소장품 페이지 (museum.go.kr, relicRecommendId=962060) — 설명은 우리 문장으로 다시 씀.
           원화 픽셀은 쓰지 않음 (글자는 폰트로 렌더: Noto Serif CJK KR — SIL OFL).
형태: 판 2.4 × 1.4 m, 두께 6 cm, 뒤로 12° 기울임, 기둥 2개(9 cm 각), 판 아랫변 높이 0.9 m. 종이색 판 + 진묵 테두리 + 먹 글씨.
위치: 큰 채(건물 1) 처마의 +z 쪽(진입 지점 쪽) 바깥 5 m, 건물 중심 x, 바닥은 terrain_jeong 높이. 앞면이 +z(관람자 쪽)를 향함.
      v2: 메시는 **밑동 중심이 원점**(pivot) 이고 실제 위치는 records/inscription_board_place.json 에 기록 → 언리얼에서 ue_place_board.py 가 옮김.
          (pivot 이 밑동이라 에디터 기즈모로 이동·회전·크기 조절이 자연스럽게 됨)
      v2: 기둥은 판과 같이 12° 기울여 판 **뒤에** 붙임 (전엔 수직 기둥이 기울어진 판을 관통).
출력: runtime/inscription_board.glb, records/inscription_board_place.json, source/board/board_tex.png (확인용)
언리얼: ue_import_parts.py → ue_setup_materials.py v7.3 (M_InwangBoard, 예전 inscription 숨김) → ue_place_board.py (위치 이동)
검증 로그: 면 수·텍스처 크기·UV 범위·위치(집과의 거리)·바닥 높이.
"""
import os, json, numpy as np, trimesh
from PIL import Image, ImageDraw, ImageFont
from scipy.interpolate import LinearNDInterpolator

RT = "assets/inwangjesaekdo/runtime"; SRC = "assets/inwangjesaekdo/source/board"; os.makedirs(SRC, exist_ok=True)
S = 2                                   # v2: 텍스처 2배 해상도 — 획이 얇아 멀리서 옅게 보이던 문제 (2026-09-14)
W_, H_ = 2048 * S, 1024 * S
PANEL_W, PANEL_H, PANEL_T = 2.4, 1.4, 0.06
TILT_DEG, BOTTOM_M, POST_W, OFFSET_M = 12.0, 0.9, 0.09, 5.0
PAPER, INK, WOOD, FRAME = (240, 234, 221), (12, 10, 9), (58, 48, 40), (26, 22, 20)   # v2: 종이 더 밝게 · 먹 진묵으로
FONT = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc"; FONT_B = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc"; KR = 1   # ttc 안의 KR 페이스

# ── 1) 텍스처: 판 앞면 = 왼쪽 위 (2.4:1.4 비율), 나머지 = 나무색
tex = Image.new("RGB", (W_, H_), WOOD); dr = ImageDraw.Draw(tex)
glow = Image.new("L", (W_, H_), 0); dg = ImageDraw.Draw(glow)      # v3: 글자 전용 마스크 → 텍스처 알파 채널 (금빛 반짝임이 글씨에만 얹히게)
PW, PH = 1536 * S, 896 * S
dr.rectangle([0, 0, PW - 1, PH - 1], fill=PAPER); dr.rectangle([0, 0, PW - 1, PH - 1], outline=FRAME, width=22 * S)
def f(size, bold=False): return ImageFont.truetype(FONT_B if bold else FONT, int(size * S), index=KR)
def txt(xy, t, font, fill, shine=True):
    """판에 글씨를 쓰고, shine 이면 같은 자리를 마스크에도 흰색으로 찍는다 (테두리·종이는 마스크 0)."""
    dr.text(xy, t, font=font, fill=fill)
    if shine: dg.text(xy, t, font=font, fill=255)
y = 52 * S
txt((70 * S, y), "仁王霽色圖  인왕제색도 — 그림 위 글씨(화제)의 뜻", f(58, True), INK); y += 92 * S
txt((70 * S, y), "「仁王霽色  辛未閏月下浣  謙齋」", f(54, True), INK); y += 88 * S
lines = [
    ("仁王霽色  인왕제색", "비가 갠(霽) 뒤 인왕산의 빛깔(色) — 이 그림의 제목"),
    ("辛未閏月下浣  신미윤월하완", "신미년(1751) 윤5월 하순 — 그린 때. 양력 7월 무렵"),
    ("謙齋  겸재", "정선(1676–1759)의 호. 76세에 그림"),
]
for a, b in lines:
    txt((90 * S, y), a, f(42, True), INK); txt((640 * S, y + 4 * S), b, f(36, True), INK); y += 64 * S
y += 18 * S
body = ["화가가 제목·날짜·호와 도장을 직접 남겨, 언제 무엇을 그렸는지 알 수 있는 그림입니다.",
        "평생의 벗 사천 이병연(1671–1751)의 쾌유를 빌며 그렸다고 미술사학계는 추정하며,",
        "이 무렵 실제로 비가 내렸다는 기록이 있습니다.",
        "국보 · 종이에 먹 · 79.2 × 138.0 cm · 2021년 이건희 기증 · 국립중앙박물관 소장"]
for t in body:
    txt((90 * S, y), t, f(34, True), INK); y += 54 * S
txt((90 * S, PH - 70 * S), "출처: 국립중앙박물관 큐레이터 추천 소장품 (museum.go.kr) 설명을 바탕으로 정리", f(26, True), (64, 56, 48), shine=False)
print(f"텍스트 마지막 줄 y={y} (판 높이 {PH} 안이어야 함: {'OK' if y < PH - 80 * S else '!! 넘침'})")
tex = tex.convert("RGBA"); tex.putalpha(glow)                      # v3: A = 글자 마스크
_g = np.asarray(glow, float)
print(f"글자 마스크: 흰 픽셀(>128) 비율 {float((_g > 128).mean()) * 100:.2f} % (판 밖은 0 이어야 함 — 판 밖 최대 {float(_g[:, PW:].max()):.0f})")
_a = np.asarray(tex.crop((0, 0, PW, PH)).convert("L"), float)
print(f"판 앞면 밝기: 글씨 픽셀(<128) 비율 {float((_a < 128).mean())*100:.1f} %, 가장 어두운 값 {_a.min():.0f} (0 에 가까울수록 진함), 해상도 {PW}×{PH}")
tex.save(f"{SRC}/board_tex.png")

# ── 2) 위치: 큰 채 프레임
house = trimesh.load(f"{RT}/house.glb", force="mesh"); V = np.asarray(house.vertices); F = np.asarray(house.faces)
C = np.asarray(house.visual.vertex_colors)[:, :3]; roof = np.all(C[F[:, 0]] == [38, 33, 29], 1); cen_f = V[F].mean(1)
big = roof & (cen_f[:, 0] >= 10); P = V[np.unique(F[big])]
cx = P[:, 0].mean(); z_front = P[:, 2].max()                                  # +z 쪽 처마 끝
terr = trimesh.load(f"{RT}/terrain_jeong.glb", force="mesh"); TV = np.asarray(terr.vertices)
Hf = LinearNDInterpolator(TV[:, [0, 2]], TV[:, 1])
bz = z_front + OFFSET_M; by = float(Hf(cx, bz))
print(f"큰 채 중심 x {cx:.1f}, +z 처마 {z_front:.1f} → 안내판 (x {cx:.1f}, z {bz:.1f}), 바닥 y {by:.2f} (집 처마 y {P[:,1].min():.1f})")

# ── 3) 메시: 상자들을 한 프리미티브로. 판은 뒤로 기울임(윗변이 -z 쪽으로)
Vo, Fo, UVo = [], [], []
def box(center, size, R=np.eye(3), uv=None):
    """축 정렬 상자 → 회전 R → 평행이동. uv: (u0,u1,v0,v1) 를 +z 면(앞면)에, 나머지 면은 나무색 패치"""
    sx, sy, sz = np.array(size) / 2; o = len(Vo)
    corners = np.array([[x, y, z] for x in (-sx, sx) for y in (-sy, sy) for z in (-sz, sz)])
    faces = {"+z": [1, 5, 7, 3], "-z": [4, 0, 2, 6], "+x": [5, 4, 6, 7], "-x": [0, 1, 3, 2], "+y": [3, 7, 6, 2], "-y": [0, 4, 5, 1]}
    wood = (1600 * S / W_, 2000 * S / W_, 1 - 1000 * S / H_, 1 - 920 * S / H_)
    for k, idx in faces.items():
        q = corners[idx]; u0, u1, v0, v1 = uv if (k == "+z" and uv) else wood
        quv = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
        n = len(Vo)
        for p, t in zip(q, quv): Vo.append((R @ p) + center); UVo.append(t)
        Fo.extend([[n, n + 1, n + 2], [n, n + 2, n + 3]])
tilt = np.radians(TILT_DEG); R = np.array([[1, 0, 0], [0, np.cos(tilt), np.sin(tilt)], [0, -np.sin(tilt), np.cos(tilt)]])   # x축 회전: 윗변이 -z 로(뒤로 기움), 앞면 법선 (0, sin, cos)
# 판 프레임 = 밑동(0,0,0) 에서 BOTTOM_M 위, 판 중심까지 기울인 축을 따라 올라감. 기둥도 같은 축(기울어진 y) 위에, 판 뒤(-z 쪽)
up = R @ np.array([0, 1, 0]); back = R @ np.array([0, 0, -1])
pc = up * (BOTTOM_M + PANEL_H / 2)
box(pc, (PANEL_W, PANEL_H, PANEL_T), R, uv=(0, PW / W_, 1 - PH / H_, 1.0))
post_top, post_bot = BOTTOM_M + PANEL_H - 0.3, -0.15                      # 판 윗변 30 cm 아래까지, 땅 속 15 cm 까지
for sx in (-PANEL_W / 2 + 0.25, PANEL_W / 2 - 0.25):
    c = up * (post_top + post_bot) / 2 + back * (PANEL_T / 2 + POST_W / 2 + 0.005) + np.array([sx, 0, 0])
    box(c, (POST_W, post_top - post_bot, POST_W), R)
json.dump({"설명": "inscription_board.glb 의 밑동(pivot) 을 놓을 glTF 좌표(m). 앞면 = 메시 로컬 +z", "xyz_m": [float(cx), float(by), float(bz)],
           "근거": "큰 채 +z 처마 %.1f m + %.0f m, 건물 중심 x, terrain_jeong 높이" % (z_front, OFFSET_M)},
          open("assets/inwangjesaekdo/records/inscription_board_place.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
Vo = np.array(Vo); Fo = np.array(Fo); UVo = np.array(UVo)
# 면 방향: 상자 중심 기준 바깥 (house_ink 에서 쓴 규칙)
for i in range(0, len(Fo), 12):
    bc = Vo[Fo[i:i + 12].ravel()].mean(0)
    for j in range(i, i + 12):
        a, b, c = Vo[Fo[j]]; n = np.cross(b - a, c - a)
        if np.dot(n, (a + b + c) / 3 - bc) < 0: Fo[j] = Fo[j][::-1]
mat = trimesh.visual.material.PBRMaterial(baseColorTexture=tex, metallicFactor=0.0, roughnessFactor=1.0)
out = trimesh.Trimesh(Vo, Fo, process=False, visual=trimesh.visual.TextureVisuals(uv=UVo, material=mat))
out.export(f"{RT}/inscription_board.glb", include_normals=True)
chk = trimesh.load(f"{RT}/inscription_board.glb", force="mesh"); t = np.asarray(chk.visual.material.baseColorTexture)
uv = np.asarray(chk.visual.uv); front_n = chk.face_normals[0]
print(f"inscription_board.glb: 면 {len(chk.faces)} (기대 36)  텍스처 {t.shape[1]}x{t.shape[0]}  UV {uv.min(0).round(2)}~{uv.max(0).round(2)}  "
      f"바운드 x {chk.bounds[0][0]:.1f}~{chk.bounds[1][0]:.1f} y {chk.bounds[0][1]:.1f}~{chk.bounds[1][1]:.1f} z {chk.bounds[0][2]:.1f}~{chk.bounds[1][2]:.1f}")
print(f"앞면 법선 {front_n.round(2)} (z 가 +0.98 근처여야 함 — 관람 진입 방향 +z 를 향함)  {os.path.getsize(f'{RT}/inscription_board.glb') // 1024} KB")
# 관통 검사: 기둥 상자의 정점이 판 상자 안에 있으면 안 됨 (판 로컬 좌표로 되돌려 검사)
panel_v = Vo[:24]; post_v = Vo[24:]; Rt = R.T
loc = (post_v - pc) @ Rt.T; inside = (np.abs(loc[:, 0]) < PANEL_W / 2) & (np.abs(loc[:, 1]) < PANEL_H / 2) & (np.abs(loc[:, 2]) < PANEL_T / 2)
print(f"기둥 정점 {len(post_v)}개 중 판 안에 들어간 것 {int(inside.sum())}개 (0 이어야 함)  기둥-판 뒷면 간격 {(-loc[:, 2].max() - PANEL_T / 2) * 100:.1f} cm")
print(f"pivot: 바운드 최소 y {chk.bounds[0][1]:.2f} (땅속 기둥 -0.15), x 중심 {(chk.bounds[0][0] + chk.bounds[1][0]) / 2:.2f} (0 이어야 함)  배치 좌표 저장: records/inscription_board_place.json {[round(cx, 1), round(by, 2), round(bz, 1)]}")
