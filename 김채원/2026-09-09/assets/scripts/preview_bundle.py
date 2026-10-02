"""내보낸 자산 번들(Z-up, 바닥중심 pivot)을 화가 알고리즘으로 미리보기."""
import sys, numpy as np, trimesh
from PIL import Image, ImageDraw

ROOT = "assets/inwangjesaekdo"
KIND = sys.argv[1] if len(sys.argv) > 1 else "runtime"
PARTS = ["terrain_jeong", "fog", "house", "trees"]
W, H = 1400, 800


def render(eye, target, fov=55., bg=(246, 244, 238)):
    eye = np.array(eye, float); target = np.array(target, float)
    fwd = target-eye; fwd /= np.linalg.norm(fwd)
    up0 = np.array([0, 0, 1.])
    rgt = np.cross(fwd, up0); rgt /= np.linalg.norm(rgt)
    up = np.cross(rgt, fwd)
    f = (W/2)/np.tan(np.radians(fov)/2)
    img = Image.new("RGB", (W, H), bg)
    dr = ImageDraw.Draw(img, "RGBA")
    tris = []
    for name in PARTS:
        m = trimesh.load(f"{ROOT}/{KIND}/{name}.glb", force="mesh")
        V = np.asarray(m.vertices); F = np.asarray(m.faces)
        try:
            C = np.asarray(m.visual.vertex_colors)
        except Exception:
            C = np.tile([150, 150, 150, 255], (len(V), 1))
        if C is None or len(C) != len(V):
            C = np.tile([150, 150, 150, 255], (len(V), 1))
        d = V-eye
        z = d @ fwd; x = d @ rgt; y = d @ up
        u = W/2 + f*x/np.maximum(z, 1e-3); v = H/2 - f*y/np.maximum(z, 1e-3)
        n = np.cross(V[F[:, 1]]-V[F[:, 0]], V[F[:, 2]]-V[F[:, 0]])
        ln = np.linalg.norm(n, axis=1, keepdims=True); ln[ln == 0] = 1
        n = n/ln
        lamb = np.clip(n @ np.array([-.4, -.5, .77]), .25, 1.)
        zc = z[F].mean(1)
        ok = (zc > 1) & (np.abs(u[F]).max(1) < 4*W) & (np.abs(v[F]).max(1) < 4*H)
        for i in np.where(ok)[0]:
            fa = F[i]
            col = C[fa].mean(0)
            sh = lamb[i]
            tris.append((zc[i], [(u[j], v[j]) for j in fa],
                         (int(col[0]*sh), int(col[1]*sh), int(col[2]*sh), int(col[3]))))
    tris.sort(key=lambda t: -t[0])
    for _, poly, col in tris:
        dr.polygon(poly, fill=col)
    print(f"  삼각형 {len(tris):,}")
    return img


imgs = [render((0, -1500, 260), (0, 200, 120), 52.),         # 정선 시점 뒤쪽
        render((-1500, -1400, 900), (0, 0, 120), 55.),       # 좌상 조감
        render((900, -300, 300), (-200, 300, 120), 60.)]     # 우측 근접
cv = Image.new("RGB", (W, H*3+32), (255, 255, 255))
for i, im in enumerate(imgs):
    cv.paste(im, (0, i*(H+16)))
out = f"/mnt/user-data/outputs/번들미리보기_{KIND}.jpg"
cv.resize((W//2, (H*3+32)//2), Image.LANCZOS).save(out, quality=88)
print("저장:", out)
