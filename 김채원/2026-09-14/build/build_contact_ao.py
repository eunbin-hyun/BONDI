"""
접지 음영(먹 번짐) 굽기 — contact_ao.png   (2026-09-14)
=========================================================
왜: 실시간 그림자만으로는 물체가 땅에 '놓인' 느낌이 약하다. 해가 고도 74° 라 그림자가 짧아 더 그렇다.
    집·안내판 발밑이 먹이 번지듯 어두워지면 공간에 붙는다. 런타임 비용 0 (텍스처 한 장).

무엇을: 집(house_ink) 과 안내판(inscription_board) 이 지면에서 하늘을 얼마나 가리는지를
    수평선 기반 앰비언트 오클루전으로 계산한다. 방위 K 방향으로 R m 까지 훑어 가림 각도를 재고,
    sin(가림각) 평균만큼 어둡게 한다. 지형 전체가 아니라 **집 주변만 잘라 고해상도로** 굽는다
    (지형 전체 2.5 km 를 2048 px 로 덮으면 1 px = 1.2 m 라 집 그림자가 뭉개진다).

출력: runtime/contact_ao.png (회색조, 흰색 1 = 안 가림)  — 가장자리는 흰색이라 언리얼에서 Clamp 로 물려도 바깥이 안 어두워진다
      records/contact_ao.json (이 이미지가 덮는 지형 좌표 범위)
      source/terrain/contact_ao_preview.jpg
확인 지표: '가장 어두운 값', '테두리 최소값 255 (바깥이 안 어두워야 함)', 미리보기에서 집 발밑만 어두운지.
"""
import json, os, numpy as np, trimesh
from PIL import Image
from scipy import ndimage
from scipy.interpolate import griddata

RT = "assets/inwangjesaekdo/runtime"; REC = "assets/inwangjesaekdo/records"
SRC = "assets/inwangjesaekdo/source/terrain"; os.makedirs(SRC, exist_ok=True)
MARGIN_M = 12.0        # 집 바운드에서 이만큼 넓게 굽는다
GRID = 512             # 계산 격자
OUT_RES = 1024         # 내보낼 크기
AZ = 16                # 훑는 방위 수
STEPS = 48             # 방위마다 훑는 횟수
REACH_M = 10.0         # 이 거리까지만 가림을 본다
STRENGTH = 0.85        # 음영 세기 (1 = 계산값 그대로)
FLOOR = 0.30           # 가장 어두운 곳도 이 밝기까지만 (0 이면 새까맣게)
BLUR_PX = 5

place = json.load(open(f"{REC}/inscription_board_place.json", encoding="utf-8"))["xyz_m"]
casters = []
h = trimesh.load(f"{RT}/house_ink.glb", force="mesh")
casters.append((np.asarray(h.vertices), np.asarray(h.faces), "house_ink"))
b = trimesh.load(f"{RT}/inscription_board.glb", force="mesh")
casters.append((np.asarray(b.vertices) + np.array(place), np.asarray(b.faces), "inscription_board"))
for V_, F_, nm in casters:
    print(f"  가리는 것 {nm}: 면 {len(F_)}  바운드 {np.round(V_.min(0),1).tolist()} ~ {np.round(V_.max(0),1).tolist()}")

allV = np.vstack([V_ for V_, _, _ in casters])
x0, x1 = allV[:, 0].min() - MARGIN_M, allV[:, 0].max() + MARGIN_M
z0, z1 = allV[:, 2].min() - MARGIN_M, allV[:, 2].max() + MARGIN_M
print(f"굽는 구역 {x1-x0:.1f} × {z1-z0:.1f} m  → {GRID}² 격자 = 한 칸 {max(x1-x0,z1-z0)/GRID*100:.1f} cm")

gx = np.linspace(x0, x1, GRID); gz = np.linspace(z0, z1, GRID)
GXm, GZm = np.meshgrid(gx, gz)
sx = (GRID - 1) / (x1 - x0); sz = (GRID - 1) / (z1 - z0)

# ── 지면 높이 (terrain_jeong 을 이 구역만 보간)
t = trimesh.load(f"{RT}/terrain_jeong.glb", force="mesh"); TV = np.asarray(t.vertices)
near = TV[(TV[:, 0] > x0 - 200) & (TV[:, 0] < x1 + 200) & (TV[:, 2] > z0 - 200) & (TV[:, 2] < z1 + 200)]
GND = griddata(near[:, [0, 2]], near[:, 1], (GXm, GZm), method="linear")
GND = np.nan_to_num(GND, nan=float(np.nanmedian(near[:, 1])))
print(f"지면 높이 {GND.min():.1f} ~ {GND.max():.1f} m")

# ── 가리는 것의 '윗면 높이' 래스터 (삼각형마다 자기 화면 범위만 칠함)
TOP = np.full((GRID, GRID), -1e9)
for V_, F_, _ in casters:
    for f in F_:
        p = V_[f]
        cx0 = max(0, int(np.floor((p[:, 0].min() - x0) * sx))); cx1 = min(GRID - 1, int(np.ceil((p[:, 0].max() - x0) * sx)))
        cz0 = max(0, int(np.floor((p[:, 2].min() - z0) * sz))); cz1 = min(GRID - 1, int(np.ceil((p[:, 2].max() - z0) * sz)))
        if cx1 < cx0 or cz1 < cz0: continue
        X, Z = np.meshgrid(gx[cx0:cx1 + 1], gz[cz0:cz1 + 1])
        ax, az_, bx, bz, cx_, cz_ = p[0, 0], p[0, 2], p[1, 0], p[1, 2], p[2, 0], p[2, 2]
        den = (bz - cz_) * (ax - cx_) + (cx_ - bx) * (az_ - cz_)
        if abs(den) < 1e-12: continue
        w0 = ((bz - cz_) * (X - cx_) + (cx_ - bx) * (Z - cz_)) / den
        w1 = ((cz_ - az_) * (X - cx_) + (ax - cx_) * (Z - cz_)) / den
        w2 = 1 - w0 - w1
        inside = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        if not inside.any(): continue
        y = w0 * p[0, 1] + w1 * p[1, 1] + w2 * p[2, 1]
        sub = TOP[cz0:cz1 + 1, cx0:cx1 + 1]
        TOP[cz0:cz1 + 1, cx0:cx1 + 1] = np.where(inside, np.maximum(sub, y), sub)
cov = (TOP > -1e8)
print(f"가리는 것이 덮은 격자 {cov.mean()*100:.1f} %  (윗면 높이 {TOP[cov].min():.1f} ~ {TOP[cov].max():.1f} m)")
TOPF = np.where(cov, TOP, -1e9)

# ── 수평선 기반 AO
occ = np.zeros((GRID, GRID))
for k in range(AZ):
    a = 2 * np.pi * k / AZ
    dxm, dzm = np.cos(a), np.sin(a)
    hmax = np.zeros((GRID, GRID))
    for s in range(1, STEPS + 1):
        d = REACH_M * s / STEPS
        jj = np.clip((np.arange(GRID)[None, :] + dxm * d * sx).astype(int), 0, GRID - 1)
        ii = np.clip((np.arange(GRID)[:, None] + dzm * d * sz).astype(int), 0, GRID - 1)
        top = TOPF[ii, jj]
        ang = np.where(top > -1e8, np.arctan2(top - GND, d), 0.0)
        hmax = np.maximum(hmax, np.clip(ang, 0, np.pi / 2))
    occ += np.sin(hmax)
occ /= AZ
ao = np.clip(1.0 - occ * STRENGTH, FLOOR, 1.0)
ao = np.where(cov, FLOOR, ao)                       # 건물이 덮은 칸은 어차피 안 보임 — 경계가 튀지 않게
ao = ndimage.gaussian_filter(ao, 2.0)
ao[0, :] = ao[-1, :] = ao[:, 0] = ao[:, -1] = 1.0   # 테두리는 흰색 (Clamp 로 물려도 바깥이 안 어두워짐)

img = np.array(Image.fromarray((np.clip(ao, 0, 1) * 255).astype(np.uint8)).resize((OUT_RES, OUT_RES), Image.BILINEAR), float)
img = ndimage.gaussian_filter(img, BLUR_PX)
img[:2, :] = img[-2:, :] = img[:, :2] = img[:, -2:] = 255
Image.fromarray(img.astype(np.uint8)).save(f"{RT}/contact_ao.png")
edge = min(img[0, :].min(), img[-1, :].min(), img[:, 0].min(), img[:, -1].min())
print(f"가장 어두운 값 {img.min():.0f}/255,  어두운 칸(<230) 비율 {float((img<230).mean())*100:.1f} %,  테두리 최소값 {edge:.0f} (255 여야 함)")

json.dump({"설명": "집·안내판 발밑 접지 음영 (흰색 1 = 안 가림). 이미지 좌표 → 지형 좌표 대응.",
           "이미지": "contact_ao.png", "해상도": OUT_RES,
           "x_min_m": float(x0), "x_max_m": float(x1), "z_min_m": float(z0), "z_max_m": float(z1),
           "세기": STRENGTH, "최저밝기": FLOOR, "도달거리_m": REACH_M,
           "주의": "언리얼에서 이 텍스처의 샘플러 주소 모드를 Clamp 로 둘 것 (테두리가 흰색이라 바깥은 안 어두워짐)"},
          open(f"{REC}/contact_ao.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

pv = np.dstack([img, img, img]) / 255.0
pv[..., 0] = np.where(np.array(Image.fromarray((cov * 255).astype(np.uint8)).resize((OUT_RES, OUT_RES))) > 128, 1.0, pv[..., 0])
Image.fromarray((np.clip(pv, 0, 1) * 255).astype(np.uint8)).save(f"{SRC}/contact_ao_preview.jpg", quality=90)
print(f">>> contact_ao.png {OUT_RES}² 저장 (빨간 부분 = 건물이 덮은 자리), 미리보기 {SRC}/contact_ao_preview.jpg")
