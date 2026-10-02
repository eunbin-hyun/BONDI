"""런타임 GLB를 자기 텍스처/정점색으로 정선 시점에서 그려 본다."""
import json, numpy as np, trimesh
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
ROOT = "assets/inwangjesaekdo/runtime"
PARTS = ["terrain_jeong", "fog", "house", "trees", "inscription"]
W, H = 1400, 800
c = json.load(open("/mnt/user-data/outputs/best_fit.json", encoding="utf-8"))
man = json.load(open("assets/inwangjesaekdo/manifest.json", encoding="utf-8"))
OFF = np.array(man["coordinate_contract"]["pivot_offset_from_camera_frame_m"], float)
f0 = c["camera"]["focal_px"]; PW, PH = c["painting_size"]
sc = W/PW; f = f0*sc
ppx = c["camera"]["principal_x_px"]*sc; ppy = c["camera"]["horizon_y_px"]*sc
img = np.full((H, W, 3), 246.0); zb = np.full((H, W), 1e9)

for name in PARTS:
    m = trimesh.load(f"{ROOT}/{name}.glb", force="mesh")
    V = np.asarray(m.vertices) + OFF          # 카메라 원점 좌표계 (Y-up, -Z 전방)
    F = np.asarray(m.faces)
    tex = None; UV = None; C = None
    if isinstance(m.visual, trimesh.visual.texture.TextureVisuals) and m.visual.uv is not None:
        UV = np.asarray(m.visual.uv)
        _t = m.visual.material.baseColorTexture
        tex = np.asarray(_t.convert("RGBA"), float)   # 알파 유지 (화제는 투명 배경)
    else:
        try:
            C = np.asarray(m.visual.vertex_colors, float)
        except Exception:
            C = np.tile([150., 150, 150, 255], (len(V), 1))
    x, y, z = V[:, 0], V[:, 1], -V[:, 2]
    u = ppx + f*x/np.maximum(z, 1e-3); v = ppy - f*y/np.maximum(z, 1e-3)
    ok = (z[F] > 25).all(1) & (u[F].max(1) > 0) & (u[F].min(1) < W) & (v[F].max(1) > 0) & (v[F].min(1) < H)
    for i in np.where(ok)[0]:
        fa = F[i]; uu = u[fa]; vv = v[fa]
        x0 = max(int(uu.min()), 0); x1 = min(int(uu.max())+1, W)
        y0 = max(int(vv.min()), 0); y1 = min(int(vv.max())+1, H)
        if x1 <= x0 or y1 <= y0: continue
        px, py = np.meshgrid(np.arange(x0, x1)+.5, np.arange(y0, y1)+.5)
        d = ((vv[1]-vv[2])*(uu[0]-uu[2]) + (uu[2]-uu[1])*(vv[0]-vv[2]))
        if abs(d) < 1e-9: continue
        l0 = ((vv[1]-vv[2])*(px-uu[2]) + (uu[2]-uu[1])*(py-vv[2]))/d
        l1 = ((vv[2]-vv[0])*(px-uu[2]) + (uu[0]-uu[2])*(py-vv[2]))/d
        l2 = 1-l0-l1
        ins = (l0 >= -1e-6) & (l1 >= -1e-6) & (l2 >= -1e-6)
        if not ins.any(): continue
        zz = l0*z[fa[0]] + l1*z[fa[1]] + l2*z[fa[2]]
        sub = zb[y0:y1, x0:x1]; hit = ins & (zz < sub)
        if not hit.any(): continue
        if tex is not None:
            th, tw = tex.shape[:2]
            tu = l0*UV[fa[0], 0] + l1*UV[fa[1], 0] + l2*UV[fa[2], 0]
            tv = l0*UV[fa[0], 1] + l1*UV[fa[1], 1] + l2*UV[fa[2], 1]
            smp = tex[np.clip(((1-tv)*(th-1)).astype(int), 0, th-1),
                      np.clip((tu*(tw-1)).astype(int), 0, tw-1)]
            col = smp[..., :3]
            al = smp[..., 3]/255.0
        else:
            cc = C[fa].mean(0); col = np.broadcast_to(cc[:3], hit.shape+(3,))
            al = np.full(hit.shape, cc[3]/255.)
        tgt = img[y0:y1, x0:x1]
        a3 = al[..., None]
        tgt[hit] = (col[hit] if col.ndim == 3 else col)*a3[hit] + tgt[hit]*(1-a3[hit])
        if (C is None and al[hit].mean() > 0.98) or (C is not None and C[fa, 3].mean() > 250):
            sub[hit] = zz[hit]
Image.fromarray(img.clip(0, 255).astype(np.uint8)).save("/mnt/user-data/outputs/런타임_시점렌더.jpg", quality=90)
print("저장")
