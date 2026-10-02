"""
운무 v3 — 부피감 + 뭉툭하고 흐릿한 가장자리 (2026-09-13)
==========================================================
v2 는 얇은 한 겹이라 옆에서 보면 종이처럼 보였고 가장자리도 v1 폴리곤 윤곽을 따라감.
v3: 사람 채집 운무 상단면(v1)을 기준면으로 삼아 **위아래로 NL 겹을 쌓고**, 발자국을 바깥으로 DILATE_M 넓힌 뒤
    FADE_M 에 걸쳐 서서히 투명해지게 → 두께가 생기고 경계가 뭉게구름처럼 흐려짐.
    겹마다 노이즈 시드·가로 어긋남이 달라 층층이 다른 모양 → 부피감.
출력 (겹마다 파일 하나 — 언리얼에서 각각 액터, 머티리얼은 검증된 '텍스처 RGB→Emissive, A→Opacity' 그대로):
  runtime/fog_l0.glb … fog_l{NL-1}.glb   (l0 이 맨 위)
  source/fog/fog_v3_alpha_l*.png (확인용)
언리얼: ue_setup_materials.py v5 가 fog_l* 를 자동 배치·머티리얼 부여, 예전 'fog' 액터는 숨김. 아웃라이너 폴더 Inwang/Fog 로 한 번에 토글.
조정: NL·OFFS_M(겹 높이)·DILATE_M·FADE_M·ALPHA_LAYER·NOISE_SIGMA
"""
import os, numpy as np, trimesh
from PIL import Image, ImageDraw
from scipy import ndimage
from scipy.interpolate import LinearNDInterpolator

RT = "assets/inwangjesaekdo/runtime"; SRC = "assets/inwangjesaekdo/source/fog"; os.makedirs(SRC, exist_ok=True)
RES = 1024
NL = 5
OFFS_M = [30.0, 15.0, 0.0, -15.0, -30.0]   # 기준면 대비 겹 높이 (m). l0 맨 위
DILATE_M = 70.0                            # 발자국을 바깥으로 넓히는 거리 (뭉툭한 가장자리)
FADE_M = 120.0                             # 넓힌 가장자리에서 안쪽으로 이 거리에 걸쳐 투명 → 불투명
ALPHA_LAYER = [0.30, 0.40, 0.48, 0.42, 0.32]   # 겹별 최대 불투명도 (가운데 겹이 가장 짙음). 5겹 합쳐 중심부 ≈ 90 %
NOISE_SIGMA = 70                           # 뭉게 노이즈 크기 (px; 1 px ≈ 2.7 m)
NOISE_MIN = 0.35
FOG_RGB = (232, 226, 216)
GRID_M = 22.0                              # 겹 메시 격자 간격 (m)
SHIFT_M = 25.0                             # 겹마다 가로로 어긋나는 최대 거리

src = f"{RT}/fog_v1.glb" if os.path.exists(f"{RT}/fog_v1.glb") else f"{RT}/fog.glb"
m = trimesh.load(src, force="mesh"); V = np.asarray(m.vertices); F = np.asarray(m.faces)
b0, b1 = m.bounds; pad = DILATE_M + FADE_M * 0.3
x0, z0 = b0[0] - pad, b0[2] - pad; span = max(b1[0] - b0[0], b1[2] - b0[2]) + 2 * pad; mpp = span / RES
print(f"기준 {os.path.basename(src)}: 면 {len(F):,}  y {b0[1]:.0f}~{b1[1]:.0f}  격자 {mpp:.2f} m/px")

# 발자국 + 기준면 높이
im = Image.new("L", (RES, RES), 0); dr = ImageDraw.Draw(im)
px = (V[:, 0] - x0) / mpp; pz = (V[:, 2] - z0) / mpp
for f in F: dr.polygon([(float(px[i]), float(pz[i])) for i in f], fill=255)
foot = np.asarray(im) > 0
gx, gz = np.meshgrid((np.arange(RES) + 0.5) * mpp + x0, (np.arange(RES) + 0.5) * mpp + z0)
Y = LinearNDInterpolator(V[:, [0, 2]], V[:, 1], fill_value=np.nan)(np.c_[gx.ravel(), gz.ravel()]).reshape(RES, RES)
nan = np.isnan(Y); idx = ndimage.distance_transform_edt(nan, return_distances=False, return_indices=True)
Y = Y[idx[0], idx[1]]                                                        # 밖은 가장 가까운 값으로 연장
Y = ndimage.gaussian_filter(Y, 8)
big = ndimage.distance_transform_edt(~foot) * mpp <= DILATE_M                # 넓힌 발자국
dist_in = ndimage.distance_transform_edt(big) * mpp
fade = np.clip(dist_in / FADE_M, 0, 1); fade = fade * fade * (3 - 2 * fade)
print(f"발자국 {foot.mean():.1%} → 넓힘 {big.mean():.1%} (+{DILATE_M:.0f} m), 페이드 {FADE_M:.0f} m")

rng = np.random.default_rng(7)
ys, xs = np.where(big); r0, r1, c0, c1 = ys.min(), ys.max(), xs.min(), xs.max()
step = max(1, int(round(GRID_M / mpp)))
rows = np.arange(r0, r1 + step, step); cols = np.arange(c0, c1 + step, step)
tot_faces = 0
for k in range(NL):
    # 겹 알파: 페이드 × 뭉게 노이즈(겹마다 다른 시드) × 겹 최대값
    nz = ndimage.gaussian_filter(rng.random((RES, RES)), NOISE_SIGMA); nz = (nz - nz.min()) / (nz.max() - nz.min())
    nz2 = ndimage.gaussian_filter(rng.random((RES, RES)), NOISE_SIGMA * 0.4); nz2 = (nz2 - nz2.min()) / (nz2.max() - nz2.min())
    noise = 0.7 * nz + 0.3 * nz2
    alpha = fade * (NOISE_MIN + (1 - NOISE_MIN) * noise) * ALPHA_LAYER[k]
    alpha = ndimage.gaussian_filter(alpha, 3)                                # 텍스처 자체도 흐리게
    tex = np.zeros((RES, RES, 4), np.uint8); tex[..., :3] = FOG_RGB; tex[..., 3] = (np.clip(alpha, 0, 1) * 255).astype(np.uint8)
    tpath = f"{SRC}/fog_v3_tex_l{k}.png"; Image.fromarray(tex, "RGBA").save(tpath); Image.fromarray(tex[..., 3]).save(f"{SRC}/fog_v3_alpha_l{k}.png")
    # 겹 메시: 격자, 넓힌 발자국 안 정점만
    sx, sz = rng.uniform(-SHIFT_M, SHIFT_M, 2)
    R, Cc = np.meshgrid(rows, cols, indexing="ij"); Rr = np.clip(R, 0, RES - 1); Cc_ = np.clip(Cc, 0, RES - 1)
    keep = ndimage.binary_dilation(big, iterations=step)[Rr, Cc_]
    vid = -np.ones(R.shape, int); vid[keep] = np.arange(keep.sum())
    X = (Cc_ + 0.5) * mpp + x0 + sx; Z = (Rr + 0.5) * mpp + z0 + sz
    Yk = Y[Rr, Cc_] + OFFS_M[k] + rng.normal(0, 2.0, R.shape)
    Vk = np.c_[X[keep], Yk[keep], Z[keep]]
    u = (Vk[:, 0] - x0) / (RES * mpp); v = 1 - (Vk[:, 2] - z0) / (RES * mpp)   # trimesh 규약 (v=0 이미지 아래)
    Fk = []
    for i in range(R.shape[0] - 1):
        for j in range(R.shape[1] - 1):
            a, b, c, d = vid[i, j], vid[i, j + 1], vid[i + 1, j + 1], vid[i + 1, j]
            if min(a, b, c, d) >= 0: Fk += [[a, b, c], [a, c, d]]
    mat = trimesh.visual.material.PBRMaterial(baseColorTexture=Image.open(tpath), alphaMode="BLEND", doubleSided=True, metallicFactor=0.0, roughnessFactor=1.0)
    out = trimesh.Trimesh(Vk, np.array(Fk), process=False, visual=trimesh.visual.TextureVisuals(uv=np.c_[u, v], material=mat))
    out.export(f"{RT}/fog_l{k}.glb"); tot_faces += len(Fk)
    chk = trimesh.load(f"{RT}/fog_l{k}.glb", force="mesh"); t = np.asarray(chk.visual.material.baseColorTexture.convert("RGBA"))
    print(f"fog_l{k}.glb: 높이 {OFFS_M[k]:+.0f} m  면 {len(Fk):,}  알파 최대 {t[..., 3].max()/255:.2f}  중앙값(발자국 안) {np.median(t[..., 3][foot])/255:.2f}  {os.path.getsize(f'{RT}/fog_l{k}.glb') // 1024} KB")
print(f">>> {NL}겹 합계 면 {tot_faces:,}. 중심부 합산 불투명도 ≈ {1 - np.prod([1 - a for a in ALPHA_LAYER]):.0%}")
