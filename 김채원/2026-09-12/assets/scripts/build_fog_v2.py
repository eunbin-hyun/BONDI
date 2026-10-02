"""
운무 v2 — 가장자리 부드럽게 + 텍스처 알파 (2026-09-12)
=======================================================
v1 문제: fog.glb 가 정점 알파만 있는 딱딱한 폴리곤 층이라 언리얼에서 '눈 쌓인 판' 처럼 보임.
v2: 기하는 그대로 두고(운무 상단선 61점 기반, 사람 채집), 위에서 본 평면 UV 를 붙이고 1024² RGBA 텍스처를 굽는다.
     알파 = 가장자리 거리 페이드(EDGE_FADE_M) × 저주파 노이즈(뭉게뭉게) × 정점 알파는 메시에 그대로 남김
     색   = 종이색보다 조금 밝은 회백 (원화 운무는 종이 바탕이 그대로 보이는 '비움' 이라 흰색 덩어리로 칠하면 안 됨)
출력: runtime/fog.glb (덮어씀, v1 은 runtime/fog_v1.glb 로 보관), source/fog/fog_alpha.png (확인용)
언리얼: ue_setup_materials.py v4 가 M_InwangFogSoft (텍스처 RGB→Emissive, 텍스처 A × 정점 A → Opacity) 로 붙임
"""
import os, shutil, json, numpy as np, trimesh
from PIL import Image
from scipy import ndimage

RT = "assets/inwangjesaekdo/runtime"; SRC = "assets/inwangjesaekdo/source/fog"; os.makedirs(SRC, exist_ok=True)
RES = 1024
EDGE_FADE_M = 45.0        # 가장자리에서 이 거리 안쪽까지 투명→불투명으로 서서히
NOISE_MIN = 0.60          # 노이즈 최소 (안개 가장 옅은 곳의 불투명도 비율)
FOG_RGB = (232, 226, 216) # sRGB. 종이(186,170,150) 보다 밝지만 순백 X
MAX_ALPHA = 0.95

if not os.path.exists(f"{RT}/fog_v1.glb"):
    shutil.copy(f"{RT}/fog.glb", f"{RT}/fog_v1.glb")
m = trimesh.load(f"{RT}/fog_v1.glb", force="mesh")
V = np.asarray(m.vertices); F = np.asarray(m.faces); VC = np.asarray(m.visual.vertex_colors).copy()
b0, b1 = m.bounds; pad = EDGE_FADE_M * 1.5
x0, x1, z0, z1 = b0[0] - pad, b1[0] + pad, b0[2] - pad, b1[2] + pad
mpp = max(x1 - x0, z1 - z0) / RES                       # m / px
print(f"fog v1: 면 {len(F):,}  범위 x {b0[0]:.0f}~{b1[0]:.0f}  z {b0[2]:.0f}~{b1[2]:.0f}  y {b0[1]:.0f}~{b1[1]:.0f}  → {mpp:.2f} m/px")

# 1) 위에서 본 발자국(footprint) 래스터
foot = np.zeros((RES, RES), bool)
px = ((V[:, 0] - x0) / mpp).astype(int); pz = ((V[:, 2] - z0) / mpp).astype(int)
from PIL import ImageDraw
im = Image.new("L", (RES, RES), 0); dr = ImageDraw.Draw(im)
for f in F:
    dr.polygon([(int(px[i]), int(pz[i])) for i in f], fill=255)
foot = np.asarray(im) > 0
# 2) 가장자리 거리 → 페이드
dist_in = ndimage.distance_transform_edt(foot) * mpp
fade = np.clip(dist_in / EDGE_FADE_M, 0, 1); fade = fade * fade * (3 - 2 * fade)   # smoothstep
# 3) 뭉게 노이즈 (fbm: 여러 스케일의 가우시안 랜덤)
rng = np.random.default_rng(4); nz = np.zeros((RES, RES))
for s, w in ((64, 1.0), (28, 0.5), (12, 0.25)):
    g = ndimage.gaussian_filter(rng.random((RES, RES)), s); g = (g - g.mean()) / (g.std() + 1e-9); nz += w * g
nz = (nz - nz.min()) / (nz.max() - nz.min())
alpha = fade * (NOISE_MIN + (1 - NOISE_MIN) * nz) * MAX_ALPHA
# 4) 텍스처 (RGB 고정, A = alpha). 발자국 밖은 알파 0
tex = np.zeros((RES, RES, 4), np.uint8); tex[..., :3] = FOG_RGB; tex[..., 3] = (alpha * 255).astype(np.uint8)
Image.fromarray(tex, "RGBA").save(f"{SRC}/fog_texture.png"); Image.fromarray(tex[..., 3]).save(f"{SRC}/fog_alpha.png")
# 5) 평면 UV (trimesh 규약: v=0 이 이미지 아래 → 이미지 행 = RES-1-pz)
u = (V[:, 0] - x0) / (RES * mpp); v = 1 - (V[:, 2] - z0) / (RES * mpp)
mat = trimesh.visual.material.PBRMaterial(baseColorTexture=Image.open(f"{SRC}/fog_texture.png"), alphaMode="BLEND",
                                          doubleSided=True, metallicFactor=0.0, roughnessFactor=1.0)
out = trimesh.Trimesh(V, F, process=False, visual=trimesh.visual.TextureVisuals(uv=np.c_[u, v], material=mat))
out.export(f"{RT}/fog.glb")
# 정점 알파(v1 의 두께 정보)는 glTF 텍스처 메시에 COLOR_0 로 같이 못 넣으니(trimesh 제약) 텍스처 알파에 곱해 넣는다:
#   정점 알파를 발자국 래스터에 뿌려 보간 → 텍스처 A 에 곱함
va = np.zeros((RES, RES)); cnt = np.zeros((RES, RES))
np.add.at(va, (np.clip(pz, 0, RES - 1), np.clip(px, 0, RES - 1)), VC[:, 3] / 255.0); np.add.at(cnt, (np.clip(pz, 0, RES - 1), np.clip(px, 0, RES - 1)), 1)
va = ndimage.gaussian_filter(va, 12) / (ndimage.gaussian_filter(cnt, 12) + 1e-6); va = np.clip(va * 1.3, 0.55, 1.0)
tex[..., 3] = (alpha * va * 255).astype(np.uint8)
Image.fromarray(tex, "RGBA").save(f"{SRC}/fog_texture.png")
mat.baseColorTexture = Image.open(f"{SRC}/fog_texture.png"); out.export(f"{RT}/fog.glb")

# 검증: 다시 읽어 UV·텍스처·알파 확인
chk = trimesh.load(f"{RT}/fog.glb", force="mesh")
t = np.asarray(chk.visual.material.baseColorTexture.convert("RGBA"))
uvc = np.asarray(chk.visual.uv)
print(f"fog v2: 면 {len(chk.faces):,}  텍스처 {t.shape[1]}x{t.shape[0]} RGBA  알파 분포(발자국 안) "
      f"{np.percentile(t[..., 3][foot], [5, 50, 95]).round().tolist()}  UV 범위 u {uvc[:,0].min():.2f}~{uvc[:,0].max():.2f} v {uvc[:,1].min():.2f}~{uvc[:,1].max():.2f}  "
      f"{os.path.getsize(f'{RT}/fog.glb') // 1024} KB")
print(">>> 가장자리 %d m 페이드, 노이즈 %.2f~1, 최대 알파 %.2f" % (EDGE_FADE_M, NOISE_MIN, MAX_ALPHA))
