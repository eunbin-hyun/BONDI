"""아틀라스 텍스처가 붙은 지형을 시점에서 그려 본다 (화가 알고리즘, 텍스처 샘플)."""
import sys, json, numpy as np, trimesh
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
SRC = sys.argv[1] if len(sys.argv) > 1 else "inwang_jeongseon.glb"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/mnt/user-data/outputs/지형_시점렌더.jpg"
W, H = 1500, 860

m = trimesh.load(SRC, force="mesh")
V = np.asarray(m.vertices); F = np.asarray(m.faces)
UV = np.asarray(m.visual.uv)
tex = np.asarray(Image.open("tex_inwang.png").convert("RGB"), float)
TH, TW = tex.shape[:2]

c = json.load(open("/mnt/user-data/outputs/best_fit.json", encoding="utf-8"))
f = c["camera"]["focal_px"]; PW, PH = c["painting_size"]
sc = W/PW; f *= sc
ppx = c["camera"]["principal_x_px"]*sc; ppy = c["camera"]["horizon_y_px"]*sc
# GLB 좌표: X=우, Y=위(카메라 기준), -Z=전방. 카메라는 원점.
x, y, z = V[:, 0], V[:, 1], -V[:, 2]
u = ppx + f*x/np.maximum(z, 1e-3); v = ppy - f*y/np.maximum(z, 1e-3)
n = np.cross(V[F[:, 1]]-V[F[:, 0]], V[F[:, 2]]-V[F[:, 0]])
n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
zc = z[F].mean(1)
ok = (z[F] > 25).all(1) & (u[F].max(1) > -50) & (u[F].min(1) < W+50) \
     & (v[F].max(1) > -50) & (v[F].min(1) < H+50)
idx = np.where(ok)[0]; idx = idx[np.argsort(-zc[idx])]
img = np.full((H, W, 3), 246.0)
zbuf = np.full((H, W), 1e9)
for i in idx:                       # 삼각형 래스터 (작은 삼각형이라 bbox 스캔)
    fa = F[i]
    uu = u[fa]; vv = v[fa]
    x0 = max(int(np.floor(uu.min())), 0); x1 = min(int(np.ceil(uu.max()))+1, W)
    y0 = max(int(np.floor(vv.min())), 0); y1 = min(int(np.ceil(vv.max()))+1, H)
    if x1 <= x0 or y1 <= y0:
        continue
    px, py = np.meshgrid(np.arange(x0, x1)+.5, np.arange(y0, y1)+.5)
    d = ((vv[1]-vv[2])*(uu[0]-uu[2]) + (uu[2]-uu[1])*(vv[0]-vv[2]))
    if abs(d) < 1e-9:
        continue
    l0 = ((vv[1]-vv[2])*(px-uu[2]) + (uu[2]-uu[1])*(py-vv[2]))/d
    l1 = ((vv[2]-vv[0])*(px-uu[2]) + (uu[0]-uu[2])*(py-vv[2]))/d
    l2 = 1-l0-l1
    ins = (l0 >= -1e-6) & (l1 >= -1e-6) & (l2 >= -1e-6)
    if not ins.any():
        continue
    zz = l0*z[fa[0]] + l1*z[fa[1]] + l2*z[fa[2]]
    sub = zbuf[y0:y1, x0:x1]
    hit = ins & (zz < sub)
    if not hit.any():
        continue
    tu = (l0*UV[fa[0], 0] + l1*UV[fa[1], 0] + l2*UV[fa[2], 0])
    tv = (l0*UV[fa[0], 1] + l1*UV[fa[1], 1] + l2*UV[fa[2], 1])
    col = tex[np.clip(((1-tv)*(TH-1)).astype(int), 0, TH-1),
              np.clip((tu*(TW-1)).astype(int), 0, TW-1)]
    sh = float(np.clip(np.dot(n[i], [-.35, .78, -.52]), .55, 1.))
    tgt = img[y0:y1, x0:x1]
    tgt[hit] = col[hit]*sh
    sub[hit] = zz[hit]
Image.fromarray(img.clip(0, 255).astype(np.uint8)).save(OUT, quality=90)
print("저장:", OUT)
