"""
지형 투영용 '깨끗한 판(clean plate)' 만들기.

3D로 세운 나무·기와집·화제는 원화에도 그려져 있다. 그대로 투영하면
입체 모델 아래에 원화의 그 나무·집이 지면을 따라 길게 늘어져 남는다.

  1. 실제로 세운 3D 개체의 화면 자리를 마스크로 만든다 (trees_manifest / roof / 화제)
  2. 그 자리를 주변 산 지형 화소로 인페인팅해 지운다 (cv2 TELEA)
  3. 결과를 지형 투영 텍스처로 쓴다

출력: inwang_masked.jpg (지형 투영용) · cleanplate_mask.png (검수용)
"""
import json, numpy as np, cv2
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

PAINT = "/mnt/user-data/uploads/landscape_to_3D/PICs/inwangjesaekdo.jpg"
INSC = (2752, 196, 2934, 512)          # 화제·인장
TREE_W = 0.30                          # 수관 가로 반경 = 높이 x 이 값
TREE_UP = 0.95                         # 밑동에서 위로 (높이 x)

im = Image.open(PAINT).convert("RGB")
A = np.asarray(im).copy()
H, W = A.shape[:2]
mask = np.zeros((H, W), np.uint8)

# ── 나무: 실제로 세운 그루만
tm = json.load(open("trees_manifest.json", encoding="utf-8"))["trees"]
MASK_BELOW = 1150          # 이 화면행 위쪽(원경)은 늘어짐이 안 보이므로 건드리지 않는다
for t in tm:
    if t["py"] < MASK_BELOW:
        continue
    hp = max(t["h_px"], 14.0)
    cy = t["py"] - 0.58*hp
    cv2.ellipse(mask, (int(t["px"]), int(cy)),
                (int(TREE_W*hp), int(0.46*hp)), 0, 0, 360, 255, -1)   # 수관
    cv2.rectangle(mask, (int(t["px"]-0.055*hp), int(cy)),
                  (int(t["px"]+0.055*hp), int(t["py"]+0.03*hp)), 255, -1)  # 줄기
n_tree = len(tm)

# ── 기와집: 지붕선 다각형 + 기둥
ann = json.load(open("/mnt/user-data/outputs/manual_annotations.json", encoding="utf-8"))
for seg in ann["layers"]["roof"]["segments"]:
    a = np.array(seg, float)
    if len(a) < 2:
        continue
    x0, x1 = a[:, 0].min(), a[:, 0].max()
    y0, y1 = a[:, 1].min(), a[:, 1].max()
    pad = max(10.0, (x1-x0)*0.03)
    cv2.rectangle(mask, (int(x0-pad), int(y0-pad)),
                  (int(x1+pad), int(y1+(y1-y0)*0.55+pad)), 255, -1)
for seg in ann["layers"]["post"]["segments"]:
    a = np.array(seg, float)
    if len(a) < 1:
        continue
    cv2.rectangle(mask, (int(a[:, 0].min()-8), int(a[:, 1].min()-6)),
                  (int(a[:, 0].max()+8), int(a[:, 1].max()+8)), 255, -1)

# ── 화제·인장
cv2.rectangle(mask, (INSC[0]-6, INSC[1]-6), (INSC[2]+6, INSC[3]+6), 255, -1)

mask = cv2.dilate(mask, np.ones((5, 5), np.uint8), iterations=1)
cov = 100*mask.mean()/255
print(f"마스크: 나무 {n_tree}그루 + 기와집 + 화제 → 화면의 {cov:.1f}%")

# ── 인페인팅 (해상도가 커서 절반으로 줄여 처리한 뒤 되돌린다)
sc = 0.6
small = cv2.resize(A, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
msmall = cv2.resize(mask, None, fx=sc, fy=sc, interpolation=cv2.INTER_NEAREST)
fill = cv2.inpaint(small, msmall, 9, cv2.INPAINT_TELEA)
fill = cv2.resize(fill, (W, H), interpolation=cv2.INTER_CUBIC)

# 경계가 티나지 않게 부드럽게 섞는다
soft = cv2.GaussianBlur(mask.astype(np.float32)/255.0, (0, 0), 3.0)[..., None]
out = (fill*soft + A*(1-soft)).astype(np.uint8)

Image.fromarray(out).save("inwang_masked.jpg", quality=94)
Image.fromarray(mask).save("cleanplate_mask.png")
side = np.concatenate([A[1150:1715, 1850:2700], out[1150:1715, 1850:2700]], axis=0)
Image.fromarray(side).save("cleanplate_check.jpg")
print("저장: inwang_masked.jpg (지형 투영용) / cleanplate_mask.png / cleanplate_check.jpg")
json.dump({"masked_pct": float(cov), "trees": n_tree,
           "method": "3D로 세운 개체의 화면 자리를 cv2.INPAINT_TELEA 로 주변 지형 화소로 메움",
           "tree_ellipse": {"rx_over_h": TREE_W, "ry_over_h": 0.46}},
          open("cleanplate_manifest.json", "w"), ensure_ascii=False, indent=2)
