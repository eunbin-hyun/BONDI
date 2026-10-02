"""
Q2 — 나무 밑동을 제약으로 시점 재정합.

가설 (a) 개체 단위 크기 과장  vs  (b) 근경 시점 오류
판정: 시점을 흔들면서 (1) 스카이라인 정합 (2) 나무 14그루의 함축 높이 산포
      두 지표를 동시에 본다. (b)가 맞으면 스카이라인을 거의 안 망치면서
      산포가 크게 줄어드는 시점이 존재한다.
"""
import json, numpy as np, rasterio
from pyproj import Transformer
from curves import Curves

CFG = "/mnt/user-data/outputs/best_fit.json"
ANN = "/mnt/user-data/outputs/manual_annotations.json"
DEM = "dem10_5m_5179_filled.tif"

c = json.load(open(CFG, encoding="utf-8"))
ann = json.load(open(ANN, encoding="utf-8"))
CV = Curves(json.load(open("distortion_curves.json", encoding="utf-8")))

PW, PH = c["painting_size"]
cam = c["camera"]
F, PPX, PPY = cam["focal_px"], cam["principal_x_px"], cam["horizon_y_px"]
AZ0 = np.radians(cam["azimuth_deg"])
H0 = CV.h0

s = rasterio.open(DEM)
D = s.read(1).astype("float32"); D[D <= -9998] = np.nan
INV = ~s.transform; HH, WW = D.shape


def elev(x, y):
    cc, rr = INV * (x, y)
    ok = (cc >= 0) & (cc < WW-1) & (rr >= 0) & (rr < HH-1)
    cc = np.clip(cc-.5, 0, WW-1.001); rr = np.clip(rr-.5, 0, HH-1.001)
    c0 = cc.astype(np.int32); r0 = rr.astype(np.int32); fc = cc-c0; fr = rr-r0
    v = (D[r0, c0]*(1-fc)*(1-fr) + D[r0, c0+1]*fc*(1-fr)
         + D[r0+1, c0]*(1-fc)*fr + D[r0+1, c0+1]*fc*fr)
    return np.where(ok, v, np.nan)


t = Transformer.from_crs("EPSG:4326", "EPSG:5179", always_xy=True)
VX0, VY0 = t.transform(c["viewpoint"]["lon"], c["viewpoint"]["lat"])

sky = np.load("painting_skyline.npy")                     # 열별 y (원본 픽셀)
SKY_U = np.linspace(0, PW-1, len(sky))
th = np.array(ann["layers"]["th"]["segments"], float)      # (14,2,2) 밑동→꼭대기
BASE, TOP = th[:, 0], th[:, 1]

STEP = 5.0
DMAX = 3000.0
DS = np.arange(STEP, DMAX, STEP)


def profile(vx, vy, ground0, az):
    """방위각 az(rad, 배열)에 대해 거리별 변형 지형의 앙각 누적최대."""
    cz = ground0 + H0
    X = vx + np.sin(az)[:, None]*DS[None, :]
    Y = vy + np.cos(az)[:, None]*DS[None, :]
    Z = elev(X, Y)
    Zd = CV.deform(Z, np.broadcast_to(DS, Z.shape), ground0)
    A = np.arctan2(np.where(np.isnan(Zd), -1e4, Zd - cz), DS[None, :])
    return A


def evaluate(vx, vy):
    ground0 = float(elev(np.array([vx]), np.array([vy]))[0])
    if not np.isfinite(ground0):
        return None
    cz = ground0 + H0

    # --- 스카이라인
    az = AZ0 + np.arctan((SKY_U - PPX)/F)
    A = profile(vx, vy, ground0, az)
    top = A.max(axis=1)
    v_pred = PPY - F*np.tan(top)
    rms = float(np.sqrt(np.nanmean((v_pred - sky)**2)))

    # --- 나무: 밑동 광선이 지형에 닿는 거리 → 함축 높이
    azb = AZ0 + np.arctan((BASE[:, 0] - PPX)/F)
    elb = np.arctan((PPY - BASE[:, 1])/F)
    elt = np.arctan((PPY - TOP[:, 1])/F)
    Ab = profile(vx, vy, ground0, azb)
    Cm = np.maximum.accumulate(Ab, axis=1)
    hits = []
    for i in range(len(BASE)):
        k = np.searchsorted(Cm[i], elb[i])          # 앙각이 지형선과 만나는 첫 거리
        hits.append(DS[k] if k < len(DS) else np.nan)
    d = np.array(hits)
    hgt = d*(np.tan(elt) - np.tan(elb))             # 변형 프레임에서의 나무 높이
    ok = np.isfinite(hgt) & (hgt > 0.3)
    if ok.sum() < 8:
        return None
    lg = np.log(hgt[ok])
    return dict(vx=vx, vy=vy, ground0=ground0, sky_rmse_px=rms,
                n=int(ok.sum()), logstd=float(lg.std()),
                med_h=float(np.exp(lg.mean())), d=d, hgt=hgt)


base = evaluate(VX0, VY0)
print("기준 시점: 스카이라인 RMSE %.1f px, 나무 %d그루 log표준편차 %.3f, 중앙높이 %.1f m"
      % (base["sky_rmse_px"], base["n"], base["logstd"], base["med_h"]))
print("  거리(m):", np.round(base["d"], 0))
print("  높이(m):", np.round(base["hgt"], 1))

rows = []
for dx in np.arange(-240, 241, 30.):
    for dy in np.arange(-240, 241, 30.):
        r = evaluate(VX0+dx, VY0+dy)
        if r:
            r["dx"], r["dy"] = dx, dy
            rows.append(r)

rows.sort(key=lambda r: r["logstd"])
print("\n--- 나무 높이 산포가 가장 작은 시점 10개 ---")
print(f"{'dx':>6}{'dy':>6}{'지반m':>8}{'스카이RMSE':>12}{'log표준편차':>12}{'중앙높이':>10}")
for r in rows[:10]:
    print(f"{r['dx']:6.0f}{r['dy']:6.0f}{r['ground0']:8.1f}{r['sky_rmse_px']:12.1f}"
          f"{r['logstd']:12.3f}{r['med_h']:10.1f}")

ok = [r for r in rows if r["sky_rmse_px"] <= base["sky_rmse_px"]*1.15]
ok.sort(key=lambda r: r["logstd"])
print(f"\n--- 스카이라인 RMSE가 기준의 1.15배 이내인 후보 {len(ok)}개 중 상위 5 ---")
for r in ok[:5]:
    print(f"{r['dx']:6.0f}{r['dy']:6.0f}{r['ground0']:8.1f}{r['sky_rmse_px']:12.1f}"
          f"{r['logstd']:12.3f}{r['med_h']:10.1f}")

json.dump({"base": {k: v for k, v in base.items() if k not in ("d", "hgt")},
           "base_d": base["d"].tolist(), "base_h": base["hgt"].tolist(),
           "best_uncon": {k: v for k, v in rows[0].items() if k not in ("d", "hgt")},
           "best_con": ({k: v for k, v in ok[0].items() if k not in ("d", "hgt")} if ok else None)},
          open("tree_refit.json", "w"), ensure_ascii=False, indent=2)
