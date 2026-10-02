"""
디오라마 받침 — 지형 가장자리를 수직으로 잘라 내리고 바닥을 덮는다.

1:1로 서면 지형이 끊긴 자리가 '미완성'으로 보이지만,
받침을 두면 박물관 지형 모형처럼 '의도된 단면'이 된다.
축소 전시(디오라마)와 1:1 몰입 중 어느 쪽을 택해도 손해가 없다.

출력: obj_base.glb
"""
import json, numpy as np, rasterio, trimesh
from PIL import Image
from pyproj import Transformer
from curves import Curves
Image.MAX_IMAGE_PIXELS = None

CFG = "/mnt/user-data/outputs/best_fit.json"
DEM = "dem10_5m_5179_filled.tif"
PAINT = "/mnt/user-data/uploads/landscape_to_3D/PICs/inwangjesaekdo.jpg"
HALF_W, DEPTH, BACK = 1250.0, 2600.0, 250.0
STEP = 12.0                 # 가장자리 표본 간격 (m)
DROP = 140.0                # 바닥면을 지형 최저점보다 이만큼 더 아래로

c = json.load(open(CFG, encoding="utf-8"))
cam = c["camera"]; AZ0 = np.radians(cam["azimuth_deg"])
G0 = c["viewpoint"]["ground_elev_m"]
CV = Curves(json.load(open("distortion_curves.json", encoding="utf-8")))
CAMZ = G0 + CV.h0
s = rasterio.open(DEM); D = s.read(1).astype("float32"); D[D <= -9998] = np.nan
INV = ~s.transform; HH, WW = D.shape
t = Transformer.from_crs("EPSG:4326", "EPSG:5179", always_xy=True)
VX, VY = t.transform(c["viewpoint"]["lon"], c["viewpoint"]["lat"])
FWD = np.array([np.sin(AZ0), np.cos(AZ0)]); RGT = np.array([np.cos(AZ0), -np.sin(AZ0)])


def elev(x, y):
    cc, rr = INV*(x, y)
    ok = (cc >= 0)&(cc < WW-1)&(rr >= 0)&(rr < HH-1)
    cc = np.clip(cc-.5, 0, WW-1.001); rr = np.clip(rr-.5, 0, HH-1.001)
    c0 = cc.astype(np.int32); r0 = rr.astype(np.int32); fc = cc-c0; fr = rr-r0
    return np.where(ok, (D[r0,c0]*(1-fc)*(1-fr)+D[r0,c0+1]*fc*(1-fr)
                         + D[r0+1,c0]*(1-fc)*fr+D[r0+1,c0+1]*fc*fr), np.nan)


def surf_local(Xc, Zc):
    X = VX + Xc*RGT[0] + Zc*FWD[0]; Y = VY + Xc*RGT[1] + Zc*FWD[1]
    Z = elev(X, Y); Z = np.where(np.isfinite(Z), Z, np.nanmin(D))
    hz = np.maximum(np.hypot(X-VX, Y-VY), 1e-6)
    return CV.deform(Z, hz, G0) - CAMZ


xs = np.arange(-HALF_W, HALF_W+STEP, STEP)
zs = np.arange(-BACK, DEPTH+STEP, STEP)
# 시계 방향 테두리 (Xc, Zc)
ring = ([(x, -BACK) for x in xs] + [(HALF_W, z) for z in zs[1:]] +
        [(x, DEPTH) for x in xs[::-1][1:]] + [(-HALF_W, z) for z in zs[::-1][1:-1]])
ring = np.array(ring, float)
top_y = surf_local(ring[:, 0], ring[:, 1])
base_y = float(np.nanmin(top_y) - DROP)

V, Fc = [], []
n = len(ring)
for i, (xc, zc) in enumerate(ring):
    V.append([xc, float(top_y[i]), -zc])          # 위 테두리
for i, (xc, zc) in enumerate(ring):
    V.append([xc, base_y, -zc])                   # 아래 테두리
for i in range(n):
    j = (i+1) % n
    Fc += [[i, j, n+j], [i, n+j, n+i]]            # 옆벽
cb = len(V); V.append([0.0, base_y, -(DEPTH-BACK)/2])
for i in range(n):
    j = (i+1) % n
    Fc.append([n+j, n+i, cb])                     # 바닥

V = np.array(V, float); Fc = np.array(Fc, int)


def srgb_to_linear(cc):
    x = np.asarray(cc, float)/255.0
    return np.clip(np.where(x <= 0.04045, x/12.92, ((x+0.055)/1.055)**2.4)*255.0, 0, 255)


a = np.asarray(Image.open(PAINT).convert("RGB")).reshape(-1, 3)
ink = np.percentile(a, 4, axis=0)
paper = np.percentile(a, 88, axis=0)
wall = srgb_to_linear(ink + (paper-ink)*0.18)      # 옆벽: 짙은 먹
floor = srgb_to_linear(ink + (paper-ink)*0.06)     # 바닥: 더 짙게
col = np.vstack([np.tile(np.r_[srgb_to_linear(paper*0.72), 255], (n, 1)),   # 위 테두리는 지본 쪽
                 np.tile(np.r_[wall, 255], (n, 1)),
                 np.r_[floor, 255][None, :]]).astype(np.uint8)

m = trimesh.Trimesh(vertices=V, faces=Fc, process=False,
                    visual=trimesh.visual.ColorVisuals(vertex_colors=col))
m.export("obj_base.glb")
print(f"받침  테두리 {n}점  면 {len(Fc):,}  "
      f"윗면 높이 {top_y.min():.0f}~{top_y.max():.0f} m  바닥 {base_y:.0f} m  "
      f"두께 {top_y.min()-base_y:.0f}~{top_y.max()-base_y:.0f} m")
json.dump({"ring_points": int(n), "faces": int(len(Fc)),
           "base_y_m": base_y, "drop_below_min_m": DROP,
           "extent_m": {"half_width": HALF_W, "depth": DEPTH, "back": BACK},
           "note": "지형 가장자리를 수직으로 잘라 내린 벽 + 바닥. 축소 디오라마·1:1 양쪽에 쓴다"},
          open("base_manifest.json", "w"), ensure_ascii=False, indent=2)
