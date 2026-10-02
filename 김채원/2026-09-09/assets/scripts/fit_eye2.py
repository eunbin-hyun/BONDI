"""
Q2-c — 과장계수 g(d)를 되돌린 '실물 환산 나무 높이'로 눈높이 h를 찾는다.
정선이 지형을 g배 과장했다면 그 위에 그린 나무도 같은 g로 늘어난다.
따라서 실물 높이 ≈ 화면 함축 높이 / g(d).
"""
import json, numpy as np, rasterio
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from pyproj import Transformer
from curves import Curves

for p in ("/usr/share/fonts/truetype/nanum/NanumGothic.ttf",):
    try: fm.fontManager.addfont(p); plt.rcParams["font.family"] = "NanumGothic"
    except Exception: pass
plt.rcParams["axes.unicode_minus"] = False

c = json.load(open("/mnt/user-data/outputs/best_fit.json", encoding="utf-8"))
ann = json.load(open("/mnt/user-data/outputs/manual_annotations.json", encoding="utf-8"))
CV = Curves(json.load(open("distortion_curves.json", encoding="utf-8")))
cam = c["camera"]; F, PPX, PPY = cam["focal_px"], cam["principal_x_px"], cam["horizon_y_px"]
AZ0 = np.radians(cam["azimuth_deg"])

s = rasterio.open("dem10_5m_5179_filled.tif")
D = s.read(1).astype("float32"); D[D <= -9998] = np.nan
INV = ~s.transform; HH, WW = D.shape

def elev(x, y):
    cc, rr = INV*(x, y)
    ok = (cc >= 0)&(cc < WW-1)&(rr >= 0)&(rr < HH-1)
    cc = np.clip(cc-.5, 0, WW-1.001); rr = np.clip(rr-.5, 0, HH-1.001)
    c0 = cc.astype(np.int32); r0 = rr.astype(np.int32); fc = cc-c0; fr = rr-r0
    v = (D[r0,c0]*(1-fc)*(1-fr)+D[r0,c0+1]*fc*(1-fr)+D[r0+1,c0]*(1-fc)*fr+D[r0+1,c0+1]*fc*fr)
    return np.where(ok, v, np.nan)

t = Transformer.from_crs("EPSG:4326","EPSG:5179",always_xy=True)
VX, VY = t.transform(c["viewpoint"]["lon"], c["viewpoint"]["lat"]); G0 = c["viewpoint"]["ground_elev_m"]
DS = np.arange(4., 3000., 4.)
th = np.array(ann["layers"]["th"]["segments"], float); BASE, TOP = th[:,0], th[:,1]

def hit(px, py, h):
    az = AZ0+np.arctan((px-PPX)/F); el = np.arctan((PPY-py)/F); cz = G0+h
    X = VX+np.sin(az)*DS; Y = VY+np.cos(az)*DS
    Z = CV.deform(elev(X,Y), DS, G0)
    A = np.maximum.accumulate(np.arctan2(np.where(np.isnan(Z),-1e4,Z-cz), DS))
    k = np.searchsorted(A, el)
    return DS[k] if k < len(DS) else np.nan

HS = np.arange(1.6, 45.1, 0.8)
near = BASE[:,1] > 1400
res = []
for h in HS:
    d = np.array([hit(*BASE[i], h) for i in range(len(BASE))])
    elb = np.arctan((PPY-BASE[:,1])/F); elt = np.arctan((PPY-TOP[:,1])/F)
    raw = d*(np.tan(elt)-np.tan(elb))
    real = raw/CV.g(d)                       # 과장 되돌리기
    res.append((h, d.copy(), real.copy()))

def stat(real, m):
    v = real[m & np.isfinite(real) & (real > .2)]
    return (np.log(v).std(), np.exp(np.log(v).mean())) if len(v) >= 3 else (np.nan, np.nan)

sn = np.array([stat(r[2], near) for r in res])
sf = np.array([stat(r[2], ~near) for r in res])
print(f"{'h(m)':>6}{'전경산포':>9}{'전경높이':>9}{'중경산포':>9}{'중경높이':>9}{'집거리':>9}")
for i, h in enumerate(HS):
    if i % 4: continue
    dh = hit(2320., 1480., h)
    print(f"{h:6.1f}{sn[i,0]:9.3f}{sn[i,1]:9.1f}{sf[i,0]:9.3f}{sf[i,1]:9.1f}{dh:9.0f}")

REAL_PINE = 15.0
i_n = int(np.nanargmin(np.abs(sn[:,1]-REAL_PINE)))
i_ns = int(np.nanargmin(sn[:,0]))
print(f"\n전경: 산포최소 h={HS[i_ns]:.1f}m (산포 {sn[i_ns,0]:.3f}, 높이 {sn[i_ns,1]:.1f}m)"
      f" / 실물 15m가 되는 h={HS[i_n]:.1f}m")
print(f"중경: h와 거의 무관 (산포 {np.nanmin(sf[:,0]):.3f}~{np.nanmax(sf[:,0]):.3f}), "
      f"h=1.6m일 때 실물환산 {sf[0,1]:.1f}m")

fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))
ax[0].plot(HS, sn[:,0], "o-", label="전경 나무 7그루")
ax[0].plot(HS, sf[:,0], "s-", label="중경 나무 7그루")
ax[0].set_xlabel("가정한 눈높이 h (m)"); ax[0].set_ylabel("log-높이 표준편차 (작을수록 일관)")
ax[0].set_title("눈높이별 나무 높이 일관성"); ax[0].legend(); ax[0].grid(alpha=.3)

ax[1].plot(HS, sn[:,1], "o-", label="전경")
ax[1].plot(HS, sf[:,1], "s-", label="중경")
ax[1].axhspan(12, 20, color="g", alpha=.15, label="실제 소나무 12~20m")
ax[1].set_xlabel("가정한 눈높이 h (m)"); ax[1].set_ylabel("과장 되돌린 실물 환산 높이 (m)")
ax[1].set_title("실물 환산 나무 높이"); ax[1].legend(); ax[1].grid(alpha=.3)

hh = np.array([hit(2320., 1480., h) for h in HS])
ax[2].plot(HS, hh, "d-", color="crimson")
ax[2].axhline(130, ls="--", c="k"); ax[2].text(20, 140, "각크기 앵커 130m", fontsize=9)
ax[2].set_xlabel("가정한 눈높이 h (m)"); ax[2].set_ylabel("기와집까지 거리 (m)")
ax[2].set_title("기와집이 요구하는 눈높이"); ax[2].grid(alpha=.3)
plt.tight_layout(); plt.savefig("/mnt/user-data/outputs/눈높이_삼원법_판정.jpg", dpi=110)

json.dump({"h_grid": HS.tolist(), "near_logstd": sn[:,0].tolist(), "near_med": sn[:,1].tolist(),
           "far_logstd": sf[:,0].tolist(), "far_med": sf[:,1].tolist(),
           "house_d": hh.tolist(), "real_pine_ref_m": REAL_PINE},
          open("eye_scan2.json","w"), ensure_ascii=False, indent=2)
print("저장: 눈높이_삼원법_판정.jpg")
