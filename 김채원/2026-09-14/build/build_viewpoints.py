"""
전경·중경·후경 감상 지점 자동 선정 — viewpoints.json   (2026-09-14)
=====================================================================
왜: 자유 이동만 두면 관람자가 원화 근거 없는 구역으로 흘러간다. '여기서 보면 가장 그림 같다' 는 지점을
    데이터로 골라 텔레포트 표석을 놓는다. 감으로 찍지 않고 점수로 고른다.

점수: 그 지점의 눈높이(지형 + 1.6 m)에서 방위 24 방향으로 지형을 훑어,
      **눈에 보이는 지형이 차지하는 각도 중 원화 근거가 있는 몫**을 잰다 (입체각 가중).
      보이는 것 = 시선을 따라가며 앙각의 최댓값을 갱신하는 구간 (수평선 알고리즘).
      같이 재는 값: 지형이 가리는 시야 각도(너무 좁으면 답답), 발밑 경사(서기 불편한 곳 제외).
      바라볼 방향(yaw)도 방위별 점수에서 가장 좋은 쪽으로 정한다.

구간: 정선 시점에서의 거리로 전경 / 중경 / 후경 을 나눠 구간마다 최고점을 하나씩 고른다.

출력: records/viewpoints.json, source/terrain/viewpoints_preview.jpg
확인 지표: 지점마다 '근거 비율' 이 60 % 이상이면 쓸 만하다. 전경 > 중경 > 후경 순으로 낮아지는 게 정상.
"""
import json, os, numpy as np, trimesh
from PIL import Image
from scipy import ndimage
from scipy.interpolate import griddata

RT = "assets/inwangjesaekdo/runtime"; REC = "assets/inwangjesaekdo/records"
SRC = "assets/inwangjesaekdo/source/terrain"; os.makedirs(SRC, exist_ok=True)
EYE_M = 1.6
GRID = 220             # 지형 높이 격자
AZ = 24                # 훑는 방위 수
STEPS = 150
REACH_M = 1400.0
CAND_STEP_M = 25.0     # 후보 지점 간격
BANDS = [("전경", 60, 220), ("중경", 220, 520), ("후경", 520, 950)]
MIN_EV = 0.45          # 후보가 서 있을 수 있는 최소 근거값 (그 자리 자체가 근거 구역이어야 함)
MAX_SLOPE = 0.42       # 발밑 경사 탄젠트 상한 (약 23°)
FACE_TOL_DEG = 70.0    # 바라볼 방향은 '정선 시점에서 멀어지는 쪽' ±이 각도 안에서만 고름

R = json.load(open(f"{REC}/terrain_evidence.json", encoding="utf-8"))
eye0 = np.array(R["eye_xyz_m"], float)
EVimg = np.asarray(Image.open(f"{RT}/terrain_evidence.png").convert("L"), float) / 255.0

m = trimesh.load(f"{RT}/terrain_jeong.glb", force="mesh")
V = np.asarray(m.vertices); lo, hi = V.min(0), V.max(0)
gx = np.linspace(lo[0], hi[0], GRID); gz = np.linspace(lo[2], hi[2], GRID)
GX, GZ = np.meshgrid(gx, gz)
H = np.nan_to_num(griddata(V[:, [0, 2]], V[:, 1], (GX, GZ), method="linear"), nan=float(np.nanmin(V[:, 1])))
cell = max((hi[0] - lo[0]) / (GRID - 1), (hi[2] - lo[2]) / (GRID - 1))


def hgt(x, z):
    i = np.clip((z - lo[2]) / (hi[2] - lo[2]) * (GRID - 1), 0, GRID - 1)
    j = np.clip((x - lo[0]) / (hi[0] - lo[0]) * (GRID - 1), 0, GRID - 1)
    return ndimage.map_coordinates(H, [[i], [j]], order=1)[0]


def evid(x, z):
    r = np.clip((z - R["z_min_m"]) / (R["z_max_m"] - R["z_min_m"]) * (EVimg.shape[0] - 1), 0, EVimg.shape[0] - 1)
    c = np.clip((x - R["x_min_m"]) / (R["x_max_m"] - R["x_min_m"]) * (EVimg.shape[1] - 1), 0, EVimg.shape[1] - 1)
    return float(ndimage.map_coordinates(EVimg, [[r], [c]], order=1)[0])


def score_at(x, z):
    """그 지점에서 보이는 지형 중 원화 근거가 있는 몫 (입체각 가중) + 가장 좋은 방위"""
    ey = hgt(x, z) + EYE_M
    per_az = []
    for k in range(AZ):
        a = 2 * np.pi * k / AZ
        dx, dz = np.sin(a), -np.cos(a)                 # a=0 → -Z (정선이 보던 방향)
        run = -np.pi / 2; wsum = 0.0; esum = 0.0
        for s in range(1, STEPS + 1):
            d = REACH_M * (s / STEPS) ** 1.6           # 가까운 쪽을 촘촘히
            px, pz = x + dx * d, z + dz * d
            if not (lo[0] < px < hi[0] and lo[2] < pz < hi[2]): break
            e = np.arctan2(hgt(px, pz) - ey, d)
            if e > run:                                # 이 구간이 새로 보이는 지형
                w = e - run; run = e
                wsum += w; esum += w * evid(px, pz)
        per_az.append((esum / wsum if wsum > 1e-9 else 0.0, wsum, a))
    # 바라볼 방향: 앞 90° 부채꼴(방위 ±3칸) 평균이 가장 큰 쪽.
    # 단 '정선 시점에서 멀어지는 쪽' 을 정면으로 보는 방향만 후보 — 그림의 대상(산)을 등지고 서는 걸 막는다.
    away = np.arctan2(x - eye0[0], -(z - eye0[2]))
    span = 3
    best = None
    for k in range(AZ):
        a_k = 2 * np.pi * k / AZ
        if abs(((a_k - away + np.pi) % (2 * np.pi)) - np.pi) > np.radians(FACE_TOL_DEG): continue
        idx = [(k + t) % AZ for t in range(-span, span + 1)]
        w = sum(per_az[i][1] for i in idx)
        v = sum(per_az[i][0] * per_az[i][1] for i in idx) / w if w > 1e-9 else 0.0
        if best is None or v > best[0]: best = (v, w, per_az[k][2])
    if best is None: return 0.0, 0.0, float(np.degrees(away)), ey
    return best[0], best[1], np.degrees(best[2]), ey


# ── 후보 지점: 근거 구역 안, 경사 완만, 정선 시점에서 일정 거리
cands = []
for x in np.arange(lo[0] + 50, hi[0] - 50, CAND_STEP_M):
    for z in np.arange(lo[2] + 50, hi[2] - 50, CAND_STEP_M):
        d = float(np.hypot(x - eye0[0], z - eye0[2]))
        if d < BANDS[0][1] or d > BANDS[-1][2]: continue
        if evid(x, z) < MIN_EV: continue
        s = (abs(hgt(x + cell, z) - hgt(x - cell, z)) + abs(hgt(x, z + cell) - hgt(x, z - cell))) / (2 * cell)
        if s > MAX_SLOPE: continue
        cands.append((x, z, d, s))
print(f"후보 지점 {len(cands)}개 (근거 {MIN_EV} 이상, 경사 {np.degrees(np.arctan(MAX_SLOPE)):.0f}° 이하)")

rows = []
for x, z, d, s in cands:
    ev, w, yaw, ey = score_at(x, z)
    rows.append(dict(x=float(x), z=float(z), dist=d, slope=float(s), ev=ev, span=float(w), yaw=float(yaw), eye_y=float(ey)))

out = []
print("\n  구간   거리    근거비율   시야점수   발밑경사   좌표(x, z)          바라볼 방위")
for name, a, b in BANDS:
    pool = [r for r in rows if a <= r["dist"] < b]
    if not pool: print(f"  {name}: 후보 없음"); continue
    best = max(pool, key=lambda r: r["ev"] * min(r["span"], 0.9))     # 근거 높고 시야가 너무 좁지 않은 곳
    best = dict(best, name=name)
    out.append(best)
    print(f"  {name}  {best['dist']:5.0f} m   {best['ev']*100:5.1f} %   {np.degrees(best['span']):7.1f}°        "
          f"{np.degrees(np.arctan(best['slope'])):4.1f}°   ({best['x']:7.1f}, {best['z']:7.1f})   {best['yaw']:6.1f}°")

json.dump({"설명": "전경·중경·후경 감상 지점. 좌표는 glTF(m). yaw 는 -Z 를 0 으로 시계방향(도). eye_y 는 눈높이(지형+1.6 m).",
           "점수기준": "눈에 보이는 지형이 차지하는 각도 중 원화 근거(terrain_evidence)가 있는 몫",
           "시점": R["eye_xyz_m"], "지점": out},
          open(f"{REC}/viewpoints.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# 미리보기
pv = np.dstack([EVimg, EVimg, EVimg * 0.7])
def to_px(x, z):
    return (int((x - R["x_min_m"]) / (R["x_max_m"] - R["x_min_m"]) * (EVimg.shape[1] - 1)),
            int((z - R["z_min_m"]) / (R["z_max_m"] - R["z_min_m"]) * (EVimg.shape[0] - 1)))
px, pz = to_px(eye0[0], eye0[2]); pv[max(0, pz - 8):pz + 9, max(0, px - 8):px + 9] = [1, 0.2, 0.1]
for r in out:
    qx, qz = to_px(r["x"], r["z"]); pv[max(0, qz - 10):qz + 11, max(0, qx - 10):qx + 11] = [0.2, 0.5, 1.0]
Image.fromarray((np.clip(pv, 0, 1) * 255).astype(np.uint8)).save(f"{SRC}/viewpoints_preview.jpg", quality=90)
print(f"\n>>> records/viewpoints.json 저장 (빨강 = 정선 시점, 파랑 = 감상 지점)  미리보기 {SRC}/viewpoints_preview.jpg")
