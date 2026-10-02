"""
산수분경 — 손으로 짚어 이동하는 축소 모형  diorama.glb   (2026-09-14)
=======================================================================
왜: 전경·중경·후경으로 순간이동할 때 '어디로 갈지' 를 말이 아니라 **모형 위의 자리**로 고르게 한다.
    관람자가 그림의 어디쯤에 서게 되는지, 그리고 원화 근거가 어디까지인지를 한눈에 본다.

무엇을 (v2, 2026-09-14): 레벨에 있는 것들(지형·집·안내판·나무)을 **그대로 잘라 한 덩어리로 축소**한다.
    v1 은 지형 표면만 줄였는데, 집과 나무가 빠져 모형 같지 않았다. v2 는 실제 배치된 메시를 같은 축척으로 같이 줄인다.
    근거 구역(terrain_evidence)이 덮는 범위를 자른다.
    - 색: 지형의 각 점을 **정선의 카메라로 원화 화면에 투영**해 그 화소를 가져온다 (원화가 실제로 그린 색).
          화면 밖이거나 앞 능선에 가린 곳은 근거가 없으므로 종이색으로 뺀다 — 큰 공간의 여백 규칙과 같다.
    - 크기: 긴 변이 DIORAMA_CM. 높이는 실제 비율 그대로 (과장하지 않음).
    - 밑판: 얇은 판을 깔아 모형처럼 보이게.
출력: runtime/diorama.glb (지형·집·안내판·나무 4덩어리), runtime/diorama_tex.png, records/diorama.json (표석 위치 = 모형 로컬 좌표)
확인 지표: '표석 3개 모형 좌표', '원화 근거 화소 비율', 모형 크기(cm).
"""
import json, os, numpy as np, trimesh
from PIL import Image
from scipy import ndimage
from scipy.interpolate import griddata

Image.MAX_IMAGE_PIXELS = None
RT = "assets/inwangjesaekdo/runtime"; REC = "assets/inwangjesaekdo/records"
PAINT = "/mnt/user-data/uploads/landscape_to_3D/PICs/inwangjesaekdo.jpg"
DIORAMA_CM = 80.0      # 긴 변 길이 (v2: 60 → 80, 집·나무가 너무 작아지지 않게)
GRID = 72              # 모형 격자 (면 = GRID² × 2)
TEX = 1024
PAPER = (186, 170, 150)
BASE_CM = 1.2          # 밑판 두께
MARGIN_M = 60.0        # 근거 구역 바깥 여유

fit = json.load(open(f"{REC}/best_fit.json", encoding="utf-8"))
cam = fit["camera"]; PW, PH = fit["painting_size"]
FOCAL, HORIZON, PX = cam["focal_px"], cam["horizon_y_px"], cam["principal_x_px"]
HFOV = cam["hfov_deg"]
R = json.load(open(f"{REC}/terrain_evidence.json", encoding="utf-8"))
eye = np.array(R["eye_xyz_m"], float)
VP = json.load(open(f"{REC}/viewpoints.json", encoding="utf-8"))["지점"]
EV = np.asarray(Image.open(f"{RT}/terrain_evidence.png").convert("L"), float) / 255.0
ART = np.asarray(Image.open(PAINT).convert("RGB"))

m = trimesh.load(f"{RT}/terrain_jeong.glb", force="mesh")
TV = np.asarray(m.vertices)

# ── 1) 자를 범위: 근거가 있는 곳의 바운딩 박스 + 여유
ys, xs = np.where(EV > 0.25)
x0 = R["x_min_m"] + xs.min() / (EV.shape[1] - 1) * (R["x_max_m"] - R["x_min_m"]) - MARGIN_M
x1 = R["x_min_m"] + xs.max() / (EV.shape[1] - 1) * (R["x_max_m"] - R["x_min_m"]) + MARGIN_M
z0 = R["z_min_m"] + ys.min() / (EV.shape[0] - 1) * (R["z_max_m"] - R["z_min_m"]) - MARGIN_M
z1 = R["z_min_m"] + ys.max() / (EV.shape[0] - 1) * (R["z_max_m"] - R["z_min_m"]) + MARGIN_M
# 정선 시점도 반드시 포함
x0, x1 = min(x0, eye[0] - MARGIN_M), max(x1, eye[0] + MARGIN_M)
z0, z1 = min(z0, eye[2] - MARGIN_M), max(z1, eye[2] + MARGIN_M)
print(f"자른 범위 {x1-x0:.0f} × {z1-z0:.0f} m  (x {x0:.0f}~{x1:.0f}, z {z0:.0f}~{z1:.0f})")

SCALE = (DIORAMA_CM / 100.0) / max(x1 - x0, z1 - z0)        # m(실제) → m(모형)
print(f"축척 1 : {1/SCALE:,.0f}   모형 {(x1-x0)*SCALE*100:.1f} × {(z1-z0)*SCALE*100:.1f} cm")


def project(P):
    """실제 좌표 → 원화 화소 (u_px, v_px). 화면 밖이면 NaN"""
    d = P - eye
    fwd = np.array([0.0, 0.0, -1.0]); right = np.array([1.0, 0.0, 0.0])
    zc = d @ fwd
    with np.errstate(divide="ignore", invalid="ignore"):
        u = PX + FOCAL * (d @ right) / zc
        v = HORIZON - FOCAL * d[:, 1] / zc
    bad = (zc <= 1.0) | (u < 0) | (u >= PW) | (v < 0) | (v >= PH)
    u[bad] = np.nan; v[bad] = np.nan
    return u, v


# ── 2) 텍스처: 위에서 내려다본 평면 UV. 각 텍셀의 지면 점을 원화에 투영
tx = np.linspace(x0, x1, TEX); tz = np.linspace(z0, z1, TEX)
TX, TZ = np.meshgrid(tx, tz)
TH = np.nan_to_num(griddata(TV[:, [0, 2]], TV[:, 1], (TX, TZ), method="linear"), nan=float(np.nanmin(TV[:, 1])))
P = np.stack([TX.ravel(), TH.ravel(), TZ.ravel()], 1)
u, v = project(P)
ok = ~np.isnan(u)
col = np.tile(np.array(PAPER, float), (len(P), 1))
if ok.any():
    col[ok] = ART[np.clip(v[ok].astype(int), 0, PH - 1), np.clip(u[ok].astype(int), 0, PW - 1)]
# 근거 마스크로 여백 처리 (큰 공간과 같은 규칙)
er = np.clip((TZ - R["z_min_m"]) / (R["z_max_m"] - R["z_min_m"]) * (EV.shape[0] - 1), 0, EV.shape[0] - 1)
ec = np.clip((TX - R["x_min_m"]) / (R["x_max_m"] - R["x_min_m"]) * (EV.shape[1] - 1), 0, EV.shape[1] - 1)
ev = ndimage.map_coordinates(EV, [er.ravel(), ec.ravel()], order=1).reshape(-1, 1)
ev = np.clip(ev, 0, 1) ** 1.2
col = col * ev + np.array(PAPER, float) * (1 - ev)
img = col.reshape(TEX, TEX, 3).astype(np.uint8)
Image.fromarray(img).save(f"{RT}/diorama_tex.png")
print(f"텍스처 {TEX}²: 원화가 닿은 화소 {ok.mean()*100:.1f} %,  근거 가중 후 평균 근거 {float(ev.mean()):.2f}")

# ── 3) 모형 메시 (평면 격자 + 밑판)
gx = np.linspace(x0, x1, GRID); gz = np.linspace(z0, z1, GRID)
GX, GZ = np.meshgrid(gx, gz)
GH = np.nan_to_num(griddata(TV[:, [0, 2]], TV[:, 1], (GX, GZ), method="linear"), nan=float(np.nanmin(TV[:, 1])))
y_base = float(GH.min())
Vt = np.stack([((GX - x0) - (x1 - x0) / 2) * SCALE, (GH - y_base) * SCALE, ((GZ - z0) - (z1 - z0) / 2) * SCALE], -1).reshape(-1, 3)
UVt = np.stack([(GX - x0) / (x1 - x0), 1.0 - (GZ - z0) / (z1 - z0)], -1).reshape(-1, 2)
idx = np.arange(GRID * GRID).reshape(GRID, GRID)
a_ = idx[:-1, :-1].ravel(); b_ = idx[:-1, 1:].ravel(); c_ = idx[1:, 1:].ravel(); d_ = idx[1:, :-1].ravel()
Ft = np.vstack([np.stack([a_, c_, b_], 1), np.stack([a_, d_, c_], 1)])

# 밑판: 모형 바닥에 얇은 상자
bx, bz = (x1 - x0) / 2 * SCALE, (z1 - z0) / 2 * SCALE; bt = BASE_CM / 100.0
bv = np.array([[-bx, -bt, -bz], [bx, -bt, -bz], [bx, -bt, bz], [-bx, -bt, bz],
               [-bx, 0.0, -bz], [bx, 0.0, -bz], [bx, 0.0, bz], [-bx, 0.0, bz]])
bf = np.array([[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7], [0, 1, 5], [0, 5, 4],
               [1, 2, 6], [1, 6, 5], [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7]])
buv = np.tile(np.array([[0.02, 0.02]]), (8, 1))            # 밑판은 텍스처 구석(종이색) 한 점
Vall = np.vstack([Vt, bv]); Fall = np.vstack([Ft, bf + len(Vt)]); UVall = np.vstack([UVt, buv])

terr = trimesh.Trimesh(Vall, Fall, process=False)
terr.visual = trimesh.visual.TextureVisuals(uv=UVall, image=Image.open(f"{RT}/diorama_tex.png"))
scene = trimesh.Scene()
scene.add_geometry(terr, geom_name="dio_terrain")

# ── 3-B) 레벨에 있는 것들을 같은 축척으로 (v2)
place_board = json.load(open(f"{REC}/inscription_board_place.json", encoding="utf-8"))["xyz_m"]
PROPS = [("dio_house", "house_ink.glb", np.zeros(3)),
         ("dio_board", "inscription_board.glb", np.array(place_board, float)),
         ("dio_trees", "trees_cards.glb", np.zeros(3))]
for name, fn, off in PROPS:
    fp = f"{RT}/{fn}"
    if not os.path.exists(fp): print(f"  (건너뜀) {fn} 없음"); continue
    g = trimesh.load(fp, force="mesh")
    PV = np.asarray(g.vertices) + off; PF = np.asarray(g.faces)
    cen = PV[PF].mean(1)                                     # 자른 범위 밖은 버린다
    keep = (cen[:, 0] >= x0) & (cen[:, 0] <= x1) & (cen[:, 2] >= z0) & (cen[:, 2] <= z1)
    if keep.sum() == 0: print(f"  (건너뜀) {fn} 이 자른 범위 밖"); continue
    PF = PF[keep]; used = np.unique(PF)
    rm = -np.ones(len(PV), int); rm[used] = np.arange(len(used))
    PVk = PV[used]; PFk = rm[PF]
    PUV = np.asarray(g.visual.uv)[used] if getattr(g.visual, "uv", None) is not None else None
    Q = np.stack([((PVk[:, 0] - x0) - (x1 - x0) / 2) * SCALE,
                  (PVk[:, 1] - y_base) * SCALE,
                  ((PVk[:, 2] - z0) - (z1 - z0) / 2) * SCALE], -1)
    gm = trimesh.Trimesh(Q, PFk, process=False)
    tex_img = getattr(getattr(g.visual, "material", None), "baseColorTexture", None)
    if PUV is not None and tex_img is not None:
        gm.visual = trimesh.visual.TextureVisuals(uv=PUV, image=tex_img)
    scene.add_geometry(gm, geom_name=name)
    siz = (Q.max(0) - Q.min(0)) * 100
    print(f"  {name:11s} 면 {len(PFk):5d} / {len(np.asarray(g.faces)):5d}  모형 크기 {siz[0]:.1f} × {siz[1]:.1f} × {siz[2]:.1f} cm")

scene.export(f"{RT}/diorama.glb")
tot = sum(len(gg.faces) for gg in scene.geometry.values())
print(f"diorama.glb: 덩어리 {len(scene.geometry)}개, 면 합계 {tot}  {os.path.getsize(f'{RT}/diorama.glb')//1024} KB")

# ── 4) 표석 위치 (모형 로컬 좌표, m)
marks = []
for r in VP + [{"name": "입구", "x": float(eye[0]), "z": float(eye[2]), "yaw": 0.0, "eye_y": float(eye[1]), "ev": 1.0}]:
    mx = ((r["x"] - x0) - (x1 - x0) / 2) * SCALE
    mz = ((r["z"] - z0) - (z1 - z0) / 2) * SCALE
    my = (float(griddata(TV[:, [0, 2]], TV[:, 1], ([r["x"]], [r["z"]]), method="linear")[0]) - y_base) * SCALE
    marks.append({"name": r["name"], "모형_xyz_m": [round(mx, 4), round(my, 4), round(mz, 4)],
                  "목적지_xyz_m": [r["x"], r.get("eye_y", 0.0), r["z"]], "목적지_yaw_deg": r.get("yaw", 0.0),
                  "근거비율": round(float(r.get("ev", 0)), 3)})
    print(f"  표석 {r['name']:>3}: 모형 ({mx*100:6.1f}, {my*100:5.1f}, {mz*100:6.1f}) cm  →  실제 ({r['x']:.0f}, {r['z']:.0f}) yaw {r.get('yaw',0):.0f}°")

json.dump({"설명": "산수분경(디오라마). 모형 좌표는 glTF m, 피벗 = 밑판 바닥 한가운데. 표석을 짚으면 목적지로 이동.",
           "축척": round(1 / SCALE, 1), "긴변_cm": DIORAMA_CM,
           "자른범위_m": {"x": [x0, x1], "z": [z0, z1]}, "표석": marks},
          open(f"{REC}/diorama.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(">>> OK — records/diorama.json 과 함께 ue_place_diorama.py 로 배치")
