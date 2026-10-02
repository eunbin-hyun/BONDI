"""
DEM 결측 구멍 재충전 — 최근접 채움이 남긴 '방사 줄무늬'를 없앤다.

10장 도엽 바깥(전체의 10.2%, 한 덩어리)은 수치지형도가 없다. 이전 채움은
최근접값 + 확산이라 시점에서 뻗어나가는 가느다란 띠가 남았고, 그게
음영기복·노멀맵에 그대로 줄무늬로 찍혔다.

여기서는 구멍 안을 라플라스 막(membrane)으로 푼다. 경계값만 쓰고 내부는
매끈하게 이어지므로 줄무늬가 생기지 않는다. 피라미드(거친 격자→고운 격자)로
풀어 수십 초면 수렴한다. **알려진 값은 한 칸도 바뀌지 않는다.**

입력 dem10_5m_5179.tif · 출력 dem10_5m_5179_filled.tif (이전 것은 _nn 백업)
"""
import os, shutil, numpy as np, rasterio

SRC = "dem10_5m_5179.tif"
OUT = "dem10_5m_5179_filled.tif"

s = rasterio.open(SRC)
Z0 = s.read(1).astype("float64")
Z0[Z0 <= -9998] = np.nan
hole0 = ~np.isfinite(Z0)
print(f"격자 {Z0.shape}  결측 {100*hole0.mean():.2f}%  "
      f"유효 {np.nanmin(Z0):.1f}~{np.nanmax(Z0):.1f} m")


def downsample(z, m):
    """알려진 칸만 평균해 2배 거칠게."""
    H, W = z.shape; H2, W2 = H//2, W//2
    zz = (z*m)[:H2*2, :W2*2].reshape(H2, 2, W2, 2)
    mm = m[:H2*2, :W2*2].reshape(H2, 2, W2, 2)
    num = zz.sum((1, 3)); den = mm.sum((1, 3))
    return np.where(den > 0, num/np.maximum(den, 1), 0.0), (den > 0).astype("float64")


def upsample(z, shape):
    u = np.repeat(np.repeat(z, 2, 0), 2, 1)
    return u[:shape[0], :shape[1]] if u.shape[0] >= shape[0] and u.shape[1] >= shape[1] \
        else np.pad(u, ((0, max(0, shape[0]-u.shape[0])), (0, max(0, shape[1]-u.shape[1]))), "edge")


def jacobi(cur, known, m, iters):
    """구멍 안만 4이웃 평균으로 완화. 알려진 칸은 고정."""
    h = m < 0.5
    for _ in range(iters):
        p = np.pad(cur, 1, "edge")
        avg = 0.25*(p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:])
        cur = np.where(h, avg, known)
    return cur


# 피라미드 구성
lv = [(np.nan_to_num(Z0), (~hole0).astype("float64"))]
while min(lv[-1][0].shape) > 8:
    lv.append(downsample(*lv[-1]))
print(f"피라미드 {len(lv)}단  가장 거친 격자 {lv[-1][0].shape}")

zk, mk = lv[-1]
cur = np.where(mk > 0.5, zk, zk[mk > 0.5].mean() if (mk > 0.5).any() else 0.0)
cur = jacobi(cur, zk, mk, 600)
for k in range(len(lv)-2, -1, -1):
    zk, mk = lv[k]
    cur = np.where(mk > 0.5, zk, upsample(cur, zk.shape))
    cur = jacobi(cur, zk, mk, 260 if k else 400)

assert np.nanmax(np.abs(cur[~hole0] - Z0[~hole0])) < 1e-9, "알려진 값이 바뀌었다"
gy, gx = np.gradient(cur)
grad = np.hypot(gy, gx)
print(f"채움값 {cur[hole0].min():.1f}~{cur[hole0].max():.1f} m   "
      f"구멍 경사 중앙 {np.median(grad[hole0]):.3f} m/셀 · 99% {np.percentile(grad[hole0],99):.3f}"
      f"  (유효부 99% {np.percentile(grad[~hole0],99):.3f})")

if os.path.exists(OUT) and not os.path.exists(OUT.replace(".tif", "_nn.tif")):
    shutil.copy(OUT, OUT.replace(".tif", "_nn.tif"))
prof = s.profile.copy(); prof.update(dtype="float32", nodata=-9999.0, compress="deflate")
with rasterio.open(OUT, "w", **prof) as d:
    d.write(cur.astype("float32"), 1)
print("저장:", OUT)
