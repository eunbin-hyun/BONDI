"""
나무 297그루의 화면 높이를 원화 먹 농도에서 자동 추출하고,
사람이 잰 14그루로 정확도를 검증한다. (자동 추출은 검증된 범위에서만 쓴다)
"""
import json, numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

PAINT = "/mnt/user-data/uploads/landscape_to_3D/PICs/inwangjesaekdo.jpg"
ann = json.load(open("/mnt/user-data/outputs/manual_annotations.json", encoding="utf-8"))

g = np.asarray(Image.open(PAINT).convert("L"), float)
PH, PW = g.shape
thr = np.percentile(g, 30)                      # 먹으로 볼 밝기
ink = g < thr


def height_px(px, py, halfw=14, maxup=520, need=0.30, gap=26):
    x0, x1 = int(max(0, px-halfw)), int(min(PW, px+halfw+1))
    y = int(np.clip(py, 1, PH-1))
    frac = ink[:, x0:x1].mean(axis=1)
    top, miss = y, 0
    for yy in range(y-1, max(0, y-maxup)-1, -1):
        if frac[yy] >= need:
            top = yy; miss = 0
        else:
            miss += 1
            if miss > gap:
                break
    return float(y-top)


th = np.array(ann["layers"]["th"]["segments"], float)
man = th[:, 0, 1]-th[:, 1, 1]
auto = np.array([height_px(*th[i, 0]) for i in range(len(th))])
ok = auto > 5
r = np.corrcoef(man[ok], auto[ok])[0, 1]
mae = np.abs(man[ok]-auto[ok]).mean()
ratio = np.median(auto[ok]/man[ok])
print(f"사람 14그루 대조: 상관 {r:.3f}, MAE {mae:.0f}px, 자동/사람 중앙비 {ratio:.2f}")
for i in np.argsort(-man)[:6]:
    print(f"  x={th[i,0,0]:6.0f} y={th[i,0,1]:6.0f}  사람 {man[i]:5.0f}px  자동 {auto[i]:5.0f}px")

pts = np.array(ann["layers"]["tree"]["segments"][0], float)
hp = np.array([height_px(*p) for p in pts])
hp = np.where(hp < 8, np.nan, hp/ratio)          # 사람 기준으로 보정
print(f"\n297그루 자동 추출: 유효 {np.isfinite(hp).sum()}그루, "
      f"화면높이 중앙 {np.nanmedian(hp):.0f}px, 사분위 {np.nanpercentile(hp,25):.0f}~{np.nanpercentile(hp,75):.0f}px")
np.save("tree_height_px.npy", hp)
json.dump({"corr": float(r), "mae_px": float(mae), "auto_over_manual": float(ratio),
           "n_valid": int(np.isfinite(hp).sum()), "n_total": int(len(pts)),
           "median_px": float(np.nanmedian(hp))},
          open("tree_height_check.json", "w"), ensure_ascii=False, indent=2)
