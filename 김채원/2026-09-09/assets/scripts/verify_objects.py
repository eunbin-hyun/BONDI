"""지형 렌더 위에 나무·기와집·운무를 깊이순으로 합성해 원화와 대조."""
import json, numpy as np, trimesh, raycast
from PIL import Image, ImageDraw

c = json.load(open("/mnt/user-data/outputs/best_fit.json", encoding="utf-8"))
cam = c["camera"]; PW, PH = c["painting_size"]
W, H = 1200, int(1200*PH/PW)
F = cam["focal_px"]*W/PW
PPX = cam["principal_x_px"]*W/PW
PPY = cam["horizon_y_px"]*H/PH

sc = raycast.Scene()
eye = (sc.vx, sc.vy, sc.cam_z)

jx, jy = np.meshgrid(np.arange(W)-PPX+.5, np.arange(H)-PPY+.5)
d = np.stack([jx.ravel(), -jy.ravel(), np.full(W*H, F)], 1)
d /= np.linalg.norm(d, axis=1, keepdims=True)
dirs = np.stack([d[:, 0]*sc.rgt[0]+d[:, 2]*sc.fwd[0],
                 d[:, 0]*sc.rgt[1]+d[:, 2]*sc.fwd[1], d[:, 1]], 1)
dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
P, m = sc.trace(eye, dirs, exag=True, tmax=3000., step=6., refine=5)
img = Image.fromarray(sc.shade(P, m).reshape(H, W, 3))

zbuf = np.full(W*H, np.inf)
E = P[:, 0]-sc.vx; N = P[:, 1]-sc.vy
zbuf[m] = (E*sc.fwd[0]+N*sc.fwd[1])[m]
zbuf = zbuf.reshape(H, W)

dr = ImageDraw.Draw(img, "RGBA")
LAY = [("obj_fog.glb", (238, 234, 226, 150)),
       ("obj_house.glb", (86, 78, 68, 255)),
       ("obj_trees.glb", (52, 58, 46, 255))]
faces = []
for path, col in LAY:
    mesh = trimesh.load(path, force="mesh")
    V = np.asarray(mesh.vertices); Fc = np.asarray(mesh.faces)
    z = -V[:, 2]
    u = PPX + F*V[:, 0]/np.maximum(z, 1e-6)
    v = PPY - F*V[:, 1]/np.maximum(z, 1e-6)
    for f in Fc:
        zz = z[f]
        if zz.min() < 5:
            continue
        faces.append((float(zz.mean()), [(u[i], v[i]) for i in f], col))

faces.sort(key=lambda t: -t[0])
drawn = 0
for zc, poly, col in faces:
    xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
    if max(xs) < 0 or min(xs) > W or max(ys) < 0 or min(ys) > H:
        continue
    cx = int(np.clip(np.mean(xs), 0, W-1)); cy = int(np.clip(np.mean(ys), 0, H-1))
    if zc > zbuf[cy, cx] + 12:            # 지형에 가려지면 생략
        continue
    dr.polygon(poly, fill=col)
    drawn += 1
print(f"합성 면 {drawn:,}/{len(faces):,}")

art = Image.open(raycast.Scene.__init__.__defaults__[2]).convert("RGB").resize((W, H), Image.LANCZOS)
cv = Image.new("RGB", (W, H*2+16), (255, 255, 255))
cv.paste(art, (0, 0)); cv.paste(img, (0, H+16))
cv.save("/mnt/user-data/outputs/개체분리_검증.jpg", quality=90)
print("저장: 개체분리_검증.jpg  (위=원화 / 아래=지형+나무+기와집+운무)")
