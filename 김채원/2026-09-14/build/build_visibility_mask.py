"""
원화 근거 지도(가시성 마스크) — terrain_evidence.png   (2026-09-14)
====================================================================
왜: 자유 이동을 넣으면 관람자가 정선의 시점에서 '보이지 않던' 산 뒤편까지 걸어갈 수 있다.
    그 구역의 지형 표면에는 원화에서 가져올 화소가 없다 = 지금 보이는 색은 전부 추정치.
    → 근거가 있는 곳과 없는 곳을 데이터로 갈라, 없는 곳은 종이색 여백으로 흐려지게 만든다.

무엇을: 정선 시점(records/entry_point.json)에서 원화 화각(records/best_fit.json 의 카메라)으로
    지형(terrain_jeong.glb)을 바라볼 때 각 지점이
      (1) 화각 안인가  (2) 원화 화면(3000×1715 px) 안에 들어오는가  (3) 앞 능선에 가리지 않는가
    를 계산해 0~1 값으로 굽는다. 가장자리는 부드럽게 번지게 한다.

출력: runtime/terrain_evidence.png  (2048², 회색조 — 흰색 = 원화 근거 있음)
      records/terrain_evidence.json (이미지가 덮는 지형 좌표 범위 — 언리얼이 월드 좌표로 샘플링할 때 씀)
      source/terrain/evidence_preview.jpg (눈으로 확인용)

확인 지표: 아래 표의 '보임' 비율. 전경이 중경보다 높고 후경이 가장 낮아야 지형 상식과 맞는다.
"""
import json, os, numpy as np, trimesh
from PIL import Image
from scipy import ndimage
from scipy.interpolate import griddata

RT = "assets/inwangjesaekdo/runtime"; REC = "assets/inwangjesaekdo/records"
SRC = "assets/inwangjesaekdo/source/terrain"; os.makedirs(SRC, exist_ok=True)
GRID = 768            # 계산 격자 (한 변)
STEPS = 256           # 시선 하나를 따라 훑는 횟수
OUT_RES = 2048        # 내보낼 마스크 크기
EDGE_DEG = 2.0        # 화각 가장자리를 부드럽게 하는 폭 (도)
OCC_DEG = 0.4         # 능선에 가림 판정의 여유 (도) — 클수록 관대
BLUR_PX = 9           # 마스크 번짐 (출력 해상도 기준)

fit = json.load(open(f"{REC}/best_fit.json", encoding="utf-8"))
ent = json.load(open(f"{REC}/entry_point.json", encoding="utf-8"))
cam = fit["camera"]; PW, PH = fit["painting_size"]
FOCAL, HORIZON = cam["focal_px"], cam["horizon_y_px"]
HFOV = cam["hfov_deg"]
eye = np.array(ent["eye_xyz_m"], float)

m = trimesh.load(f"{RT}/terrain_jeong.glb", force="mesh")
V = np.asarray(m.vertices); lo, hi = V.min(0), V.max(0)
print(f"지형 {hi[0]-lo[0]:.0f} × {hi[2]-lo[2]:.0f} m, 높이 {lo[1]:.0f}~{hi[1]:.0f} m / 시점 {np.round(eye,1).tolist()}")
print(f"원화 카메라: 화각 {HFOV}°, 초점 {FOCAL:.0f} px, 수평선 y {HORIZON:.0f} px, 화면 {PW}×{PH} px")

gx = np.linspace(lo[0], hi[0], GRID); gz = np.linspace(lo[2], hi[2], GRID)
GXm, GZm = np.meshgrid(gx, gz)                       # 행 = z, 열 = x
H = griddata(V[:, [0, 2]], V[:, 1], (GXm, GZm), method="linear")
H = np.nan_to_num(H, nan=float(np.nanmin(V[:, 1])))

dx = GXm - eye[0]; dz = GZm - eye[2]
dist = np.hypot(dx, dz)
ang = np.degrees(np.arctan2(dx, -dz))                # 0 = 정면(-Z)
elev = np.degrees(np.arctan2(H - eye[1], np.maximum(dist, 1e-6)))

# (1) 화각 안 — 가장자리 EDGE_DEG 만큼 부드럽게
in_h = np.clip((HFOV / 2 - np.abs(ang)) / max(EDGE_DEG, 1e-6), 0, 1)
# (2) 원화 화면 세로 범위 안 (수평선 위/아래로 화면 밖은 그려지지 않은 곳)
y_px = HORIZON - FOCAL * np.tan(np.radians(elev))
edge_px = FOCAL * np.radians(EDGE_DEG)
in_v = np.clip(np.minimum(y_px - 0, PH - y_px) / max(edge_px, 1e-6), 0, 1)
# (3) 앞 능선에 가리는가 — 시선을 따라 최대 앙각을 누적
cellm = max((hi[0] - lo[0]) / (GRID - 1), (hi[2] - lo[2]) / (GRID - 1))
runmax = np.full_like(H, -90.0)
t0 = np.clip(cellm / np.maximum(dist, 1e-6), 0, 1)
for k in range(STEPS - 1):
    t = t0 + (1.0 - t0) * (k / (STEPS - 1.0))
    near_target = (1.0 - t) * dist <= cellm * 1.5    # 목표 바로 앞 샘플은 제외 (자기 자신에 가려지는 것 방지)
    px = eye[0] + dx * t; pz = eye[2] + dz * t
    ii = np.clip(((pz - lo[2]) / (hi[2] - lo[2]) * (GRID - 1)).astype(int), 0, GRID - 1)
    jj = np.clip(((px - lo[0]) / (hi[0] - lo[0]) * (GRID - 1)).astype(int), 0, GRID - 1)
    e = np.degrees(np.arctan2(H[ii, jj] - eye[1], np.maximum(dist * t, 1e-6)))
    runmax = np.where(near_target, runmax, np.maximum(runmax, e))
in_o = np.clip((elev - (runmax - OCC_DEG)) / max(OCC_DEG, 1e-6), 0, 1)

ev = in_h * in_v * in_o
print("\n  구분                      화각 안   화면 안   안 가림   최종 근거")
for a, b, lab in ((0, 400, "전경 0~400 m "), (400, 900, "중경 400~900 m"), (900, 1e9, "후경 900 m~ ")):
    s = (dist >= a) & (dist < b)
    print(f"  {lab}  {in_h[s].mean()*100:6.0f} %  {in_v[s].mean()*100:6.0f} %  {in_o[s].mean()*100:6.0f} %   {ev[s].mean()*100:6.1f} %")
print(f"  지형 전체     {in_h.mean()*100:6.0f} %  {in_v.mean()*100:6.0f} %  {in_o.mean()*100:6.0f} %   {ev.mean()*100:6.1f} %")

img = np.array(Image.fromarray((np.clip(ev, 0, 1) * 255).astype(np.uint8)).resize((OUT_RES, OUT_RES), Image.BILINEAR), float)
img = ndimage.gaussian_filter(img, BLUR_PX)
Image.fromarray(img.astype(np.uint8)).save(f"{RT}/terrain_evidence.png")

json.dump({
    "설명": "정선 시점에서 원화 근거가 있는 지형 구역 (흰색 1 = 근거 있음). 이미지 좌표 → 지형 좌표 대응.",
    "이미지": "terrain_evidence.png", "해상도": OUT_RES,
    "x_min_m": float(lo[0]), "x_max_m": float(hi[0]),          # 이미지 가로: 왼쪽 = x_min
    "z_min_m": float(lo[2]), "z_max_m": float(hi[2]),          # 이미지 세로: 위쪽 = z_min
    "eye_xyz_m": eye.tolist(), "hfov_deg": HFOV,
    "근거비율_전체": float(ev.mean()),
}, open(f"{REC}/terrain_evidence.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# 눈으로 확인: 지형 음영 위에 근거 구역을 흰색으로
sh = np.gradient(ndimage.gaussian_filter(H, 2))
lit = np.clip(0.5 + (sh[1] - sh[0]) * 0.6, 0, 1)
prev = np.dstack([lit * 0.55 + ev * 0.45, lit * 0.55 + ev * 0.45, lit * 0.55 + ev * 0.30])
pi, pj = int((eye[2] - lo[2]) / (hi[2] - lo[2]) * (GRID - 1)), int((eye[0] - lo[0]) / (hi[0] - lo[0]) * (GRID - 1))
prev[max(0, pi - 4):pi + 5, max(0, pj - 4):pj + 5] = [1.0, 0.2, 0.1]     # 시점 표시 (빨강)
Image.fromarray((np.clip(prev, 0, 1) * 255).astype(np.uint8)).save(f"{SRC}/evidence_preview.jpg", quality=90)
print(f"\n>>> terrain_evidence.png {OUT_RES}² 저장 (흰 비율 {float((img>128).mean())*100:.1f} %),  미리보기 {SRC}/evidence_preview.jpg")
