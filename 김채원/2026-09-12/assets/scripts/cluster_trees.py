"""
기와집 주변 나무 모으기 → tree_positions_v2.json  (2026-09-12)
================================================================
요청: 집 위치는 고정, 그 주변 나무들만 서로 붙어 있게 (원화에선 기와집이 소나무 숲에 파묻혀 있음).
규칙 (측정값이 아니라 조형 조정 — v1 위치는 그대로 보존):
  1) 집 중심에서 R_NEAR 안의 나무만 대상
  2) 집 중심 쪽으로 반지름을 K 배로 당김 (집에도 가까워지고 서로도 가까워짐)
  3) 집 주변 HOUSE_CLEAR 안으로는 못 들어옴, 나무끼리는 SPACING × (두 나무 평균 높이) 이상 띄움 (반복 완화)
  4) 새 자리의 y 는 terrain_jeong 높이로 다시 얹음
출력: records/tree_positions_v2.json (같은 형식 + meta.v2_note) · source/cluster/before_after_top.png (위에서 본 전후)
연결: ue_place_trees.py 의 POS_JSON, build_tree_cards.py 의 POS 를 v2 로 바꾸면 반영
"""
import json, os, numpy as np, trimesh
from PIL import Image, ImageDraw
from scipy.interpolate import LinearNDInterpolator

REC = "assets/inwangjesaekdo/records"; SRC = "assets/inwangjesaekdo/source/cluster"; os.makedirs(SRC, exist_ok=True)
R_NEAR = 160.0        # m — 이 안의 나무만 이동
K = 0.50              # 집 중심까지 거리를 이 배율로 (0.5 = 절반 거리)
HOUSE_CLEAR = 30.0    # m — 집 중심에서 이 안은 비움 (기와집 반폭 ~24 m + 여유)
SPACING = 0.75        # 나무 간 최소 거리 = SPACING × 평균 높이
ITER = 60

d = json.load(open(f"{REC}/tree_positions.json", encoding="utf-8")); T = d["trees"]
house = trimesh.load("assets/inwangjesaekdo/runtime/house.glb", force="mesh"); hb = house.bounds; hc = (hb[0] + hb[1]) / 2
terr = trimesh.load("assets/inwangjesaekdo/runtime/terrain_jeong.glb", force="mesh"); TV = np.asarray(terr.vertices)
Hf = LinearNDInterpolator(TV[:, [0, 2]], TV[:, 1])

P0 = np.array([[t["x"], t["z"]] for t in T], float); h = np.array([t["h_m"] for t in T])
dist0 = np.hypot(P0[:, 0] - hc[0], P0[:, 1] - hc[2]); sel = dist0 < R_NEAR
P = P0.copy()
P[sel] = [hc[0], hc[2]] + (P0[sel] - [hc[0], hc[2]]) * K
# 완화: 집 여유 + 나무 간격
idx = np.where(sel)[0]
for it in range(ITER):
    moved = 0.0
    for i in idx:
        v = P[i] - [hc[0], hc[2]]; r = np.hypot(*v)
        if r < HOUSE_CLEAR: P[i] = [hc[0], hc[2]] + v / max(r, 1e-6) * HOUSE_CLEAR; moved += HOUSE_CLEAR - r
        for j in idx:
            if j <= i: continue
            w = P[j] - P[i]; dd = np.hypot(*w); need = SPACING * (h[i] + h[j]) / 2
            if dd < need:
                push = (need - dd) / 2 * (w / max(dd, 1e-6)); P[i] -= push; P[j] += push; moved += need - dd
    if moved < 0.05: break
out = []
for k, t in enumerate(T):
    q = dict(t)
    if sel[k]:
        q["x"], q["z"] = float(P[k, 0]), float(P[k, 1]); yy = Hf(q["x"], q["z"]); q["y"] = float(yy) if not np.isnan(yy) else t["y"]
        q["v1_xyz"] = [t["x"], t["y"], t["z"]]
    out.append(q)
meta = dict(d["meta"]); meta["v2_note"] = (f"기와집 중심 {R_NEAR:.0f} m 안 {int(sel.sum())}그루를 집 쪽으로 {K} 배 당김 + 집 여유 {HOUSE_CLEAR:.0f} m + 간격 {SPACING}×높이. "
                                       f"조형 조정이며 원화 측정 위치(v1_xyz) 는 각 나무에 보존. 2026-09-12")
json.dump({"meta": meta, "trees": out}, open(f"{REC}/tree_positions_v2.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

dist1 = np.hypot(P[sel, 0] - hc[0], P[sel, 1] - hc[2])
nn0 = np.sort(np.linalg.norm(P0[sel][:, None] - P0[sel][None], axis=2), 1)[:, 1]; nn1 = np.sort(np.linalg.norm(P[sel][:, None] - P[sel][None], axis=2), 1)[:, 1]
print(f"대상 {int(sel.sum())}그루 (집 {R_NEAR:.0f} m 안)  완화 {it + 1}회")
print(f"  집까지 평균 거리 {dist0[sel].mean():.0f} m → {dist1.mean():.0f} m   가장 가까운 이웃 평균 {nn0.mean():.1f} m → {nn1.mean():.1f} m   최소 {nn1.min():.1f} m")
# 위에서 본 전후 그림
S = 2.0; W = int(R_NEAR * 2 * S) + 40
im = Image.new("RGB", (W * 2 + 20, W), (186, 170, 150)); dr = ImageDraw.Draw(im)
for col, PP, ox in (((120, 90, 60), P0, 0), ((40, 40, 40), P, W + 20)):
    cx, cz = ox + W / 2, W / 2
    dr.rectangle([cx - (hb[1][0] - hb[0][0]) / 2 * S, cz - (hb[1][2] - hb[0][2]) / 2 * S, cx + (hb[1][0] - hb[0][0]) / 2 * S, cz + (hb[1][2] - hb[0][2]) / 2 * S], outline=(150, 40, 40), width=2)
    dr.ellipse([cx - R_NEAR * S, cz - R_NEAR * S, cx + R_NEAR * S, cz + R_NEAR * S], outline=(120, 120, 120))
    for k in range(len(T)):
        x, z = cx + (PP[k, 0] - hc[0]) * S, cz + (PP[k, 1] - hc[2]) * S; r = h[k] * 0.35 * S
        if abs(x - cx) < W / 2 and abs(z - cz) < W / 2: dr.ellipse([x - r, z - r, x + r, z + r], fill=col)
dr.text((10, 5), "before (v1)", fill=(0, 0, 0)); dr.text((W + 30, 5), "after (v2)", fill=(0, 0, 0))
im.save(f"{SRC}/before_after_top.png"); print("저장", f"{SRC}/before_after_top.png  (빨간 사각형 = 기와집, 원 = 대상 반경)")
