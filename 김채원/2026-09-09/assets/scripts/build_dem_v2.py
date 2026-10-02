"""
수치지형도 1:5,000 등고선(N3L_F0010000) + 표고점(N3P_F0020000) → 5m DEM  (다도엽 + 시점 반경 클립)

사용: python build_dem_v2.py <SHP루트> <반경m> <도엽...>
예:   python build_dem_v2.py /mnt/user-data/uploads/landscape_to_3D/DEMs/2MAP5000_SHP_서울_종로구 3000 37608048 ...

시점(37.5816, 126.9710) 중심 정사각 반경으로 입력점을 잘라 Delaunay 비용을 낮춘다.
출력: dem10_5m_5186.tif / dem10_5m_5179.tif
"""
import sys, numpy as np, geopandas as gpd, rasterio, gc
from rasterio.transform import from_origin
from rasterio.warp import calculate_default_transform, reproject, Resampling
from scipy.interpolate import LinearNDInterpolator
from shapely.geometry import LineString
from pyproj import Transformer

RES = 5.0
SAMPLE = 5.0
VP_LAT, VP_LON = 37.5816, 126.9710


def sheet_points(base, s):
    X, Y, Z = [], [], []
    L = gpd.read_file(f"{base}/{s}/N3L_F0010000.shp", encoding="cp949")
    for geom, z in zip(L.geometry, L["등고수치"]):
        if geom is None:
            continue
        parts = [geom] if isinstance(geom, LineString) else list(geom.geoms)
        for g in parts:
            n = max(2, int(g.length // SAMPLE) + 1)
            for d in np.linspace(0, g.length, n):
                p = g.interpolate(d)
                X.append(p.x); Y.append(p.y); Z.append(z)
    P = gpd.read_file(f"{base}/{s}/N3P_F0020000.shp", encoding="cp949")
    X += list(P.geometry.x); Y += list(P.geometry.y); Z += list(P["수치"])
    return np.asarray(X), np.asarray(Y), np.asarray(Z, float), L.crs


def main(base, radius, sheets):
    crs = None
    cx = cy = None
    XS, YS, ZS = [], [], []
    for s in sheets:
        x, y, z, c = sheet_points(base, s)
        if crs is None:
            crs = c
            t = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
            cx, cy = t.transform(VP_LON, VP_LAT)
            print(f"좌표계 {crs.to_string()}  시점 ({cx:.1f}, {cy:.1f})")
        m = (np.abs(x - cx) <= radius) & (np.abs(y - cy) <= radius)
        print(f"  {s}: {len(x):,}점 → 클립 후 {m.sum():,}점")
        if m.any():
            XS.append(x[m]); YS.append(y[m]); ZS.append(z[m])
        del x, y, z; gc.collect()

    X = np.concatenate(XS); Y = np.concatenate(YS); Z = np.concatenate(ZS)
    del XS, YS, ZS; gc.collect()
    print(f"보간 입력점 {len(X):,}개, 고도 {Z.min():.1f}~{Z.max():.1f}m")

    xmin, xmax = np.floor(X.min()/RES)*RES, np.ceil(X.max()/RES)*RES
    ymin, ymax = np.floor(Y.min()/RES)*RES, np.ceil(Y.max()/RES)*RES
    gx = np.arange(xmin+RES/2, xmax, RES)
    gy = np.arange(ymax-RES/2, ymin, -RES)
    print(f"격자 예정 {len(gy)} x {len(gx)}  ({(xmax-xmin):.0f} x {(ymax-ymin):.0f} m)")

    interp = LinearNDInterpolator(np.c_[X, Y], Z)
    dem = np.empty((len(gy), len(gx)), "float32")
    BAND = 256                                    # 메모리 절약: 행 단위 분할 평가
    for i0 in range(0, len(gy), BAND):
        i1 = min(i0+BAND, len(gy))
        GX, GY = np.meshgrid(gx, gy[i0:i1])
        dem[i0:i1] = interp(GX, GY)
        print(f"  보간 {i1}/{len(gy)}", flush=True)
    dem = np.where(np.isnan(dem), -9999.0, dem)
    print(f"격자 {dem.shape}, NoData {100*(dem<=-9998).mean():.2f}%")

    prof = dict(driver="GTiff", height=dem.shape[0], width=dem.shape[1], count=1,
                dtype="float32", crs=crs, transform=from_origin(xmin, ymax, RES, RES),
                nodata=-9999, compress="deflate")
    with rasterio.open("dem10_5m_5186.tif", "w", **prof) as d:
        d.write(dem, 1)

    with rasterio.open("dem10_5m_5186.tif") as src:
        tr, w, h = calculate_default_transform(src.crs, "EPSG:5179", src.width, src.height,
                                               *src.bounds, resolution=RES)
        p2 = src.profile.copy(); p2.update(crs="EPSG:5179", transform=tr, width=w, height=h)
        with rasterio.open("dem10_5m_5179.tif", "w", **p2) as dst:
            reproject(rasterio.band(src, 1), rasterio.band(dst, 1),
                      src_crs=src.crs, dst_crs="EPSG:5179",
                      resampling=Resampling.bilinear, src_nodata=-9999, dst_nodata=-9999)
    print("완료: dem10_5m_5186.tif / dem10_5m_5179.tif")


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]), sys.argv[3:])
