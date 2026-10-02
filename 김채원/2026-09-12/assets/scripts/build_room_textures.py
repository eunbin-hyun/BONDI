"""
전시실 텍스처 — 수묵 벽지 + 목재 액자  (2026-09-13)
====================================================
원화 픽셀은 쓰지 않음 (전부 절차 생성, 팔레트만 원화 측정값). 벽지·목재 모두 이음새 없이 타일됨(wrap 노이즈).
출력:
  runtime/wall_ink.png     2048² — 종이색(원화 가장 밝은 1 %: 203,187,168) 바탕 + 옅은담묵 wash 구름 + 종이결 + 드문 마른붓 결. 평균색 = 종이색 유지.
                           언리얼: M_InwangRoom_Wall 이 월드 좌표 기준으로 WALL_TILE_CM(400 cm) 마다 반복 (ue_build_room_inwang.py)
  runtime/frame_inwang.glb 액자 메시에 목재 텍스처(wood_frame.png 1024×256, 결이 u 방향) — 가로 살은 x, 세로 살은 y 를 따라 결이 흐르게 UV
검증 로그: 벽지 평균색·타일 이음새 차이, 목재 평균색, 액자 UV 범위.
"""
import os, numpy as np, trimesh
from PIL import Image
from scipy import ndimage

RT = "assets/inwangjesaekdo/runtime"; SRC = "assets/inwangjesaekdo/source/room"; os.makedirs(SRC, exist_ok=True)
PAPER = np.array([203, 187, 168], float); WASH = np.array([157, 146, 131], float)     # 원화 측정: 가장 밝은 1 % / 옅은담묵
WOOD = np.array([104, 66, 40], float); WOOD_DARK = np.array([62, 38, 22], float)      # 목재 밝은 결 / 어두운 결 (sRGB)
N = 2048; rng = np.random.default_rng(11)


def wrap_noise(shape, sigma, seed):
    r = np.random.default_rng(seed).random(shape); n = ndimage.gaussian_filter(r, sigma, mode="wrap"); return (n - n.mean()) / (n.std() + 1e-9)


# ── 1) 벽지
big = wrap_noise((N, N), 140, 1)                       # 큰 wash 구름
mid = wrap_noise((N, N), 40, 2)
fine = wrap_noise((N, N), 1.2, 3)                      # 종이 섬유
streak = wrap_noise((N, N // 8), (2.5, 60), 4); streak = np.repeat(streak, 8, axis=1)[:, :N]   # 가로로 긴 마른붓 결 (드물게)
streak = np.clip(streak - 1.6, 0, None) * 0.25
wash = np.clip(0.5 + 0.35 * big + 0.15 * mid, 0, 1)   # 0 종이 … 1 옅은담묵 (평균 0.5 근처)
wash = wash * 0.55 + streak                            # 전체를 절반만 적용해 은은하게
tex = PAPER[None, None] * (1 - wash[..., None]) + WASH[None, None] * wash[..., None]
tex = tex * (1 + 0.025 * fine[..., None])
tex = tex - (tex.reshape(-1, 3).mean(0) - PAPER)       # 평균색을 종이색으로 맞춤
wall = np.clip(tex, 0, 255).astype(np.uint8); Image.fromarray(wall).save(f"{RT}/wall_ink.png"); Image.fromarray(wall[::4, ::4]).save(f"{SRC}/wall_ink_preview.png")
seam = np.abs(wall[:, 0].astype(int) - wall[:, -1].astype(int)).mean() + np.abs(wall[0].astype(int) - wall[-1].astype(int)).mean()
print(f"wall_ink.png {N}x{N}: 평균색 {wall.reshape(-1,3).mean(0).round(0)} (목표 {PAPER.astype(int)})  타일 이음새 평균차 {seam/2:.1f}/255 (작을수록 좋음, 이웃 픽셀 차이 {np.abs(np.diff(wall[:, :2, 0].astype(int), axis=1)).mean():.1f} 수준이면 OK)")

# ── 2) 목재 텍스처 1024×256, 결 = u(가로) 방향
W, H = 1024, 256
g = wrap_noise((H, W), (6, 90), 5) * 0.6 + wrap_noise((H, W), (2, 30), 6) * 0.3 + wrap_noise((H, W), (1, 3), 7) * 0.15
rings = np.sin((np.arange(H)[:, None] / H * 2 * np.pi * 3.0) + 1.2 * wrap_noise((H, W), (10, 120), 8))   # 나이테 띠 (v 방향 3줄, 살짝 물결)
t = np.clip(0.5 + 0.35 * g + 0.25 * rings, 0, 1)
wood = (WOOD[None, None] * t[..., None] + WOOD_DARK[None, None] * (1 - t[..., None])).astype(np.uint8)
Image.fromarray(wood).save(f"{SRC}/wood_frame.png")
print(f"wood_frame.png {W}x{H}: 평균색 {wood.reshape(-1,3).mean(0).round(0)}  u 이음새 차 {np.abs(wood[:, 0].astype(int) - wood[:, -1].astype(int)).mean():.1f}/255")

# ── 3) 액자 메시 다시 만들기 (build_painting_frame.py 와 같은 치수) + 결 방향 UV
PW, PH = 1.380, 0.792; FRAME_W, FRAME_T, LIP = 0.09, 0.045, 0.012
hx, hy = PW / 2, PH / 2; ox, oy = hx + FRAME_W, hy + FRAME_W; z0, z1 = -FRAME_T * 0.6, FRAME_T * 0.4
Vo, Fo, UVo = [], [], []
def box(x0, x1, y0, y1, zz0, zz1, along):
    """along='x' 면 결이 x 를 따라(u = x), 'y' 면 y 를 따라(u = y). v 는 나머지 두 축 합 → 면마다 다른 결 위치"""
    c = np.array([[x, y, z] for x in (x0, x1) for y in (y0, y1) for z in (zz0, zz1)]); ctr = c.mean(0)
    quads = [[1, 5, 7, 3], [4, 0, 2, 6], [5, 4, 6, 7], [0, 1, 3, 2], [3, 7, 6, 2], [0, 4, 5, 1]]
    rep = 2.0                                                            # 텍스처 1장 = 액자 긴 변의 1/2 길이
    for q in quads:
        n0 = len(Vo)
        for i in q:
            p = c[i]
            u = (p[0] - (-ox)) / (2 * ox) * rep if along == "x" else (p[1] - (-oy)) / (2 * oy) * rep
            v = ((p[1] - y0) + (p[2] - zz0)) / ((y1 - y0) + (zz1 - zz0)) if along == "x" else ((p[0] - x0) + (p[2] - zz0)) / ((x1 - x0) + (zz1 - zz0))
            Vo.append(p.tolist()); UVo.append([u, v * 0.9 + 0.05])
        P = c[q]; nrm = np.cross(P[1] - P[0], P[2] - P[0]); flip = np.dot(nrm, P.mean(0) - ctr) < 0
        for t_ in ([0, 1, 2], [0, 2, 3]):
            Fo.append([n0 + i for i in (t_[::-1] if flip else t_)])
box(-ox, -hx, -oy, oy, z0, z1, "y"); box(hx, ox, -oy, oy, z0, z1, "y")          # 세로 살
box(-hx, hx, -oy, -hy, z0, z1, "x"); box(-hx, hx, hy, oy, z0, z1, "x")          # 가로 살
lz0, lz1 = 0.0005, FRAME_T * 0.25
box(-hx, -hx + LIP, -hy, hy, lz0, lz1, "y"); box(hx - LIP, hx, -hy, hy, lz0, lz1, "y"); box(-hx, hx, -hy, -hy + LIP, lz0, lz1, "x"); box(-hx, hx, hy - LIP, hy, lz0, lz1, "x")
mat = trimesh.visual.material.PBRMaterial(baseColorTexture=Image.fromarray(wood), metallicFactor=0.0, roughnessFactor=0.55)
frame = trimesh.Trimesh(np.array(Vo), np.array(Fo), process=False, visual=trimesh.visual.TextureVisuals(uv=np.array(UVo), material=mat))
frame.export(f"{RT}/frame_inwang.glb", include_normals=True)
chk = trimesh.load(f"{RT}/frame_inwang.glb", force="mesh"); uv = np.asarray(chk.visual.uv); b = chk.bounds
print(f"frame_inwang.glb (목재): 면 {len(chk.faces)}  텍스처 {np.asarray(chk.visual.material.baseColorTexture).shape[1]}x{np.asarray(chk.visual.material.baseColorTexture).shape[0]}  UV u {uv[:,0].min():.2f}~{uv[:,0].max():.2f} (0~2 반복) v {uv[:,1].min():.2f}~{uv[:,1].max():.2f}  바깥 {(b[1][0]-b[0][0])*100:.1f}×{(b[1][1]-b[0][1])*100:.1f} cm  {os.path.getsize(f'{RT}/frame_inwang.glb')//1024} KB")
