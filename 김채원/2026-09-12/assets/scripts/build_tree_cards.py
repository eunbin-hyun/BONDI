"""
나무 카드 (3번 방식) — 원화 붓자국을 잘라 십자 알파 카드로 세운다.  2026-09-12

  1) 스프라이트: 원화에서 겹침 없는 나무 두 곳을 잘라 국소 배경(중앙값 필터 51 px) 대비 어두운 정도를 알파로.
     워시(담묵 배경)는 0, 붓자국만 남김. 작은 점 조각 제거.
       pine_cone : px 895~990, py 1290~1478 — 근경 왼쪽의 원뿔형 소나무 한 그루
       willow    : px 1040~1240, py 1460~1715 — 근경 버드나무
  2) 아틀라스 1024x512 (source/cards/tree_cards_atlas.png)
  3) tree_positions.json 의 168 밑동에 십자 쿼드 2장씩. 높이 = 원화 측정 h_m(±5%), 폭 = h × 종횡비(±10%), 회전 무작위, 좌우 뒤집기 무작위
  4) glTF: baseColorTexture(알파) · alphaMode MASK 0.4 · doubleSided → 언리얼 Masked 머티리얼 (ue_setup_materials.py v3)
출력: runtime/trees_cards.glb (168 그루, 672 면, ~0.5 MB)
"""
import json, os, numpy as np, trimesh
from PIL import Image
from scipy import ndimage
Image.MAX_IMAGE_PIXELS = None

PAINT = "/mnt/user-data/uploads/landscape_to_3D/PICs/inwangjesaekdo.jpg"
SRC = "assets/inwangjesaekdo/source/cards"; RT = "assets/inwangjesaekdo/runtime"
SPR = {"pine_cone": (895, 1290, 990, 1478), "willow": (1040, 1460, 1240, 1715)}
ALPHA_CUTOFF = 0.4
# 지울 영역 (스프라이트 크롭 기준 비율 x0,y0,x1,y1). 09-12 요청: 옆 나무에서 잘려 들어온 왼쪽 위 덩어리만 지운다.
#   ※ 거울 복사(한쪽을 잘라 좌우대칭) 는 하지 않는다 — 자연물에는 부적절 (09-12 피드백). 다른 산수화 복원에서도 같은 원칙.
ERASE = {"pine_cone": [(0.0, 0.0, 0.257, 0.417)]}
os.makedirs(SRC, exist_ok=True)

art = np.asarray(Image.open(PAINT).convert("RGB")).astype(float)
sprites = {}
for name, (x0, y0, x1, y1) in SPR.items():
    P = art[y0:y1, x0:x1]; lum = P.mean(2)
    bg = np.maximum(ndimage.median_filter(lum, size=51), np.percentile(lum, 65))
    a = np.clip((bg - lum) / max(1.0, (bg.mean() - np.percentile(lum, 3))), 0, 1)
    a = np.clip((a - 0.28) / 0.45, 0, 1) ** 0.85
    a = ndimage.gaussian_filter(a, 0.7)
    # 조각 정리: 가장 큰 덩어리(수관)를 기준으로, 그 가로 범위 안에 중심이 있는 조각만 남김
    # → 옆 나무에서 잘려 들어온 세로 획(수관 오른쪽 위 같은 것)은 제거 (09-12 요청)
    lab, n = ndimage.label(a > 0.2); sizes = ndimage.sum(a > 0.2, lab, range(1, n + 1))
    main = int(np.argmax(sizes)) + 1
    mx = np.where(lab == main)[1]; x_lo, x_hi = mx.min(), mx.max(); span = x_hi - x_lo
    keep = []
    for i, s in enumerate(sizes):
        if i + 1 == main: keep.append(i + 1); continue
        if s < 0.004 * a.size: continue
        cx = np.where(lab == i + 1)[1].mean()
        if x_lo + 0.12 * span <= cx <= x_hi - 0.12 * span: keep.append(i + 1)
    a = a * np.isin(lab, keep)
    ys, xs = np.where(a > 0.2); yb, ye, xb, xe = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    rgba = np.dstack([P, a * 255])[yb:ye, xb:xe]
    for (ex0, ey0, ex1, ey1) in ERASE.get(name, []):                    # 요청된 영역만 알파 0 (경계 1px 부드럽게)
        h_, w_ = rgba.shape[:2]; msk = np.zeros((h_, w_))
        msk[int(round(ey0 * h_)):int(round(ey1 * h_)), int(round(ex0 * w_)):int(round(ex1 * w_))] = 1
        rgba[:, :, 3] *= 1 - ndimage.gaussian_filter(msk, 0.8)
    a2 = rgba[:, :, 3] / 255; ys, xs = np.where(a2 > 0.2)               # 지운 뒤 다시 크롭
    rgba = rgba[ys.min():ys.max() + 1, xs.min():xs.max() + 1].astype(np.uint8)
    Image.fromarray(rgba, "RGBA").save(f"{SRC}/{name}.png"); sprites[name] = rgba
    print(f"{name}: {rgba.shape[1]}x{rgba.shape[0]} px, 알파>0.5 비율 {(a[yb:ye, xb:xe] > 0.5).mean():.2f}")

tiles = {}; x = 0; atlas = np.zeros((512, 1024, 4), np.uint8)
for n, im in sprites.items():
    h, w = im.shape[:2]; W = int(w * 480 / h)
    atlas[16:496, x:x + W] = np.asarray(Image.fromarray(im, "RGBA").resize((W, 480), Image.LANCZOS))
    # UV 세로 규약: trimesh 는 v=0 이 이미지 '아래'(OpenGL식). 내보낼 때 1-v 로 뒤집어 glTF(v=0 이 위) 로 저장한다.
    #   → 여기서는 OpenGL식으로 적는다: 타일 위 = 1-16/512, 타일 아래 = 1-496/512.
    #   (09-12 버그: glTF식으로 적는 바람에 언리얼에서 나무가 전부 거꾸로 섰음. 아래 자체 검증으로 다시는 안 놓치게 함)
    tiles[n] = (x / 1024, (x + W) / 1024, 1 - 16 / 512, 1 - 496 / 512, w / h); x += W + 8
Image.fromarray(atlas, "RGBA").save(f"{SRC}/tree_cards_atlas.png")

POS = "assets/inwangjesaekdo/records/tree_positions_v2.json"      # v2 = 기와집 주변 모은 위치 (cluster_trees.py). v1 은 tree_positions.json
trees = json.load(open(POS, encoding="utf-8"))["trees"]
rng = np.random.default_rng(3); V, F, UV = [], [], []


def quad(cx, cy, cz, w, h, yaw, tile, flip):
    u0, u1, v0, v1, _ = tile
    if flip: u0, u1 = u1, u0
    dx, dz = np.cos(yaw) * w / 2, np.sin(yaw) * w / 2; o = len(V)
    V.extend([[cx - dx, cy, cz - dz], [cx + dx, cy, cz + dz], [cx + dx, cy + h, cz + dz], [cx - dx, cy + h, cz - dz]])
    UV.extend([[u0, v1], [u1, v1], [u1, v0], [u0, v0]]); F.extend([[o, o + 1, o + 2], [o, o + 2, o + 3]])


for t in trees:
    tile = tiles["willow" if t["species"] == "willow" else "pine_cone"]
    h = t["h_m"] * rng.uniform(0.95, 1.05); w = h * tile[4] * rng.uniform(0.9, 1.1); yaw = rng.uniform(0, np.pi)
    quad(t["x"], t["y"], t["z"], w, h, yaw, tile, rng.random() < 0.5)
    quad(t["x"], t["y"], t["z"], w, h, yaw + np.pi / 2, tile, rng.random() < 0.5)
mat = trimesh.visual.material.PBRMaterial(baseColorTexture=Image.open(f"{SRC}/tree_cards_atlas.png"), alphaMode="MASK",
                                          alphaCutoff=ALPHA_CUTOFF, doubleSided=True, metallicFactor=0.0, roughnessFactor=1.0)
m = trimesh.Trimesh(np.array(V), np.array(F), process=False, visual=trimesh.visual.TextureVisuals(uv=np.array(UV), material=mat))
m.export(f"{RT}/trees_cards.glb")
print(f"trees_cards.glb: {len(trees)} 그루, {len(F)} 면, {os.path.getsize(f'{RT}/trees_cards.glb') // 1024} KB, bounds {np.round(m.bounds, 1).tolist()}")

# ── 자체 검증: 저장된 glb 를 trimesh 없이 직접 읽어, 카드 '아래' 정점의 raw v 가 이미지 아래(=0.5 초과) 를 가리키는지 확인
import struct
b = open(f"{RT}/trees_cards.glb", "rb").read(); jl = struct.unpack_from("<I", b, 12)[0]
j = json.loads(b[20:20 + jl]); bl = struct.unpack_from("<I", b, 20 + jl)[0]; bin_ = b[28 + jl:28 + jl + bl]
prim = j["meshes"][0]["primitives"][0]
def acc(i, n, dt=np.float32):
    a = j["accessors"][i]; bv = j["bufferViews"][a["bufferView"]]
    return np.frombuffer(bin_, dt, a["count"] * n, bv.get("byteOffset", 0) + a.get("byteOffset", 0)).reshape(-1, n)
Praw = acc(prim["attributes"]["POSITION"], 3); Traw = acc(prim["attributes"]["TEXCOORD_0"], 2)
lo = Praw[:, 1] < Praw[:, 1].reshape(-1, 4).mean(1).repeat(4)          # 카드마다 아래 2 정점
v_bottom, v_top = Traw[lo, 1].mean(), Traw[~lo, 1].mean()
print(f"검증(raw glTF, v=0 이 이미지 위): 아래 정점 v={v_bottom:.3f}, 위 정점 v={v_top:.3f} → " + (">>> 정방향 OK" if v_bottom > 0.5 > v_top else ">>> !! 거꾸로"))
