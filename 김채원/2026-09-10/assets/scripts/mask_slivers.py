"""
TIN 슬리버 삼각형 제거 — 등고선 자료가 없는 구역을 가로질러 만들어진
'부채살 모양 긴 삼각형'을 결측으로 되돌린다.

원인: LinearNDInterpolator(Delaunay)는 입력점의 볼록껍질 전체를 채운다.
도엽이 없는 쪽에서는 멀리 떨어진 점끼리 이어져 폭 몇 m · 길이 수백 m 짜리
납작한 삼각형이 생기고, 음영기복·노멀맵에 곧은 줄무늬로 찍힌다.

판정: 격자칸에서 가장 가까운 '입력점'까지의 거리가 임계값을 넘으면 보간이
아니라 외삽으로 본다. (등고선은 5 m 간격으로 표본화돼 있으므로 정상 구역은
등고선 간격 안쪽이다.)

출력: dem10_5m_5179.tif 를 갱신(원본은 _raw 백업) → refill_dem.py 재실행 대상
"""
import sys, os, shutil, numpy as np, geopandas as gpd, rasterio, gc
from shapely.geometry import LineString
from pyproj import Transformer
from scipy.spatial import cKDTree

BASE = sys.argv[1]; RADIUS = float(sys.argv[2]); SHEETS = sys.argv[3:]
THRESH = 65.0          # m — 이보다 먼 곳은 외삽으로 간주
VP_LAT, VP_LON = 37.5816, 126.9710
SAMPLE = 20.0          # 위치만 필요하므로 성기게 표본화

XS, YS = [], []
crs = None; cx = cy = None
for s in SHEETS:
    L = gpd.read_file(f"{BASE}/{s}/N3L_F0010000.shp", encoding="cp949")
    if crs is None:
        crs = L.crs
        t = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
        cx, cy = t.transform(VP_LON, VP_LAT)
    x, y = [], []
    for geom in L.geometry:
        if geom is None:
            continue
        for g in ([geom] if isinstance(geom, LineString) else list(geom.geoms)):
            n = max(2, int(g.length // SAMPLE) + 1)
            for d in np.linspace(0, g.length, n):
                p = g.interpolate(d); x.append(p.x); y.append(p.y)
    P = gpd.read_file(f"{BASE}/{s}/N3P_F0020000.shp", encoding="cp949")
    x += list(P.geometry.x); y += list(P.geometry.y)
    x = np.asarray(x); y = np.asarray(y)
    m = (np.abs(x-cx) <= RADIUS) & (np.abs(y-cy) <= RADIUS)
    print(f"  {s}: {m.sum():,}점")
    if m.any():
        XS.append(x[m]); YS.append(y[m])
    del L, P, x, y; gc.collect()

X = np.concatenate(XS); Y = np.concatenate(YS)
print(f"입력점 {len(X):,}개 (위치만)")
tree = cKDTree(np.c_[X, Y])

src = rasterio.open("dem10_5m_5186.tif")
Z = src.read(1).astype("float32")
H, W = Z.shape
cols, rows = np.meshgrid(np.arange(W), np.arange(H))
gx, gy = rasterio.transform.xy(src.transform, rows.ravel(), cols.ravel())
d, _ = tree.query(np.c_[gx, gy], k=1, workers=-1)
d = d.reshape(H, W)
bad = (d > THRESH) & (Z > -9998)
print(f"슬리버 판정 {100*bad.mean():.2f}%  (기존 결측 {100*(Z<=-9998).mean():.2f}%)")
Z[bad] = -9999.0

if not os.path.exists("dem10_5m_5186_raw.tif"):
    shutil.copy("dem10_5m_5186.tif", "dem10_5m_5186_raw.tif")
prof = src.profile.copy()
with rasterio.open("dem10_5m_5186.tif", "w", **prof) as dst:
    dst.write(Z, 1)

# 5179로 재투영
from rasterio.warp import calculate_default_transform, reproject, Resampling
if not os.path.exists("dem10_5m_5179_raw.tif"):
    shutil.copy("dem10_5m_5179.tif", "dem10_5m_5179_raw.tif")
with rasterio.open("dem10_5m_5186.tif") as s2:
    tr, w, h = calculate_default_transform(s2.crs, "EPSG:5179", s2.width, s2.height,
                                           *s2.bounds, resolution=5.0)
    p2 = s2.profile.copy(); p2.update(crs="EPSG:5179", transform=tr, width=w, height=h)
    with rasterio.open("dem10_5m_5179.tif", "w", **p2) as dst:
        reproject(rasterio.band(s2, 1), rasterio.band(dst, 1), src_crs=s2.crs,
                  dst_crs="EPSG:5179", resampling=Resampling.bilinear,
                  src_nodata=-9999, dst_nodata=-9999)
print("갱신: dem10_5m_5186.tif / dem10_5m_5179.tif")
