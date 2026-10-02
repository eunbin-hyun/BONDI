"""
먹산 덧칠 층 (terrain_ink_ext) — 원화가 안 칠해진 산 구간을 먹 스타일로 가공 (2026-09-12)
============================================================================================
배경: 런타임 지형(terrain_jeong)은 시점에서 보이는 사면(면의 22.5%)에만 원화가 붙고, 나머지는 평면 베이스컬러(맨땅 톤)라
      VR 에서 고개를 돌리면 산이 텅 비어 보인다. 원화 파일·지형 텍스처는 건드리지 않고, **원화가 없는 면만** 골라
      살짝 띄운 별도 메시를 만들어 그 위에 먹 산수 무늬를 굽는다 → 언리얼에서 액터 하나로 껐다 켰다 가능.
      (고증이 아니라 조형 가공. manifest limitations 에 그렇게 적을 것)

방법
  1) terrain_jeong 면 중 아틀라스 아래쪽(평면 베이스컬러) 을 가리키는 면만 추출 → +LIFT_M 띄움
  2) 지형 높이를 위에서 본 격자(RES²)로 보간 → 경사·향·곡률·음영 계산
  3) 먹 규칙 (정선 인왕제색도의 바위 화법을 흉내):
       · 경사 급할수록 진묵 (적묵: 여러 번 겹친 먹)         · 능선(볼록 곡률) 에 가는 진묵 윤곽
       · 붓결 = 원화의 바위 획(주봉)·능선 wash 조각을 옆에서 투영(세로 = 높이)해 타일링 (노이즈 X)   · 빛 반대편 사면 더 어둡게\n       · 능선엔 원화처럼 태점(점 찍기)
       · 시점에서 멀수록 종이색으로 바램 (원근)             · 평지(경사 < FLAT_DEG) 는 투명 → 원래 지면 그대로
       · 원화 경계에서 FEATHER_M 안쪽은 투명 → 원화 쪽으로 자연스럽게 이어짐
  4) 평면 UV + RGBA 텍스처(alphaMode BLEND) 로 runtime/terrain_ink_ext.glb 저장
언리얼: ue_setup_materials.py v4 → M_InwangInkExt (텍스처 RGB→Emissive, A→Opacity, Translucent). 아웃라이너 눈 아이콘으로 토글.
"""
import os, json, numpy as np, trimesh
from PIL import Image, ImageDraw
from scipy import ndimage
from scipy.interpolate import LinearNDInterpolator

RT = "assets/inwangjesaekdo/runtime"; SRC = "assets/inwangjesaekdo/source/ink_ext"; os.makedirs(SRC, exist_ok=True)
PAL = json.load(open("assets/inwangjesaekdo/records/ink_palette.json", encoding="utf-8"))
JIN, JUNG, DAM, YEOT, PAPER = (np.array(PAL[k], float) for k in ["진묵(0-5%)", "중묵(5-25%)", "담묵(25-55%)", "옅은담묵(55-80%)", "종이(85-95%)"])
RES = 2048
LIFT_M = 0.8              # 지형 위로 띄우는 높이 (z-fighting 방지)
PAINT_V = 1 - 585 / 1024  # 아틀라스 원화 영역 경계 (trimesh 규약 v)
FLAT_DEG, STEEP_DEG = 6.0, 32.0
FEATHER_M = 60.0          # 원화 경계 페이드
EYE = np.array([-1.0, 154.33, 1175.0])   # 진입점(시점) glTF m — 원근 바램 기준
FAR0, FAR1, FAR_MIX = 400.0, 1800.0, 0.55 # 이 거리부터 종이색 쪽으로 최대 55% 바램
LIGHT = np.array([-0.55, 0.75, 0.35])    # 빛 방향 (왼쪽 위, 시점 쪽) — 원화의 명암 관찰에 의한 선택

m = trimesh.load(f"{RT}/terrain_jeong.glb", force="mesh")
V = np.asarray(m.vertices); F = np.asarray(m.faces); UV = np.asarray(m.visual.uv)
fv = UV[F][:, :, 1].mean(1)
unp = F[fv <= PAINT_V]; pnt = F[fv > PAINT_V]
print(f"terrain_jeong 면 {len(F):,} → 원화 없음 {len(unp):,} ({len(unp)/len(F):.1%}) / 원화 있음 {len(pnt):,}")

# ── 위에서 본 격자
b0, b1 = m.bounds; x0, z0 = b0[0], b0[2]; span = max(b1[0] - b0[0], b1[2] - b0[2]); mpp = span / RES
gx, gz = np.meshgrid((np.arange(RES) + 0.5) * mpp + x0, (np.arange(RES) + 0.5) * mpp + z0)
H = LinearNDInterpolator(V[:, [0, 2]], V[:, 1], fill_value=np.nan)(np.c_[gx.ravel(), gz.ravel()]).reshape(RES, RES)
valid = ~np.isnan(H); H = np.where(valid, H, np.nanmin(H))
Hs = ndimage.gaussian_filter(H, 5.0)                                   # 10k 면 메시의 삼각형 자국이 경사·곡률에 찍히지 않게 넉넉히 블러
dzdx = np.gradient(Hs, mpp, axis=1); dzdz = np.gradient(Hs, mpp, axis=0)
slope = np.degrees(np.arctan(np.hypot(dzdx, dzdz)))
nrm = np.dstack([-dzdx, np.ones_like(Hs), -dzdz]); nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
shade = np.clip(nrm @ (LIGHT / np.linalg.norm(LIGHT)), 0, 1)
curv = -ndimage.laplace(ndimage.gaussian_filter(H, 22))                # >0 볼록(능선). 30 m 급 능선만
ridge = np.clip(curv / (np.percentile(curv[valid], 98) + 1e-6), 0, 1) ** 1.5
print(f"격자 {RES}² ({mpp:.2f} m/px)  경사 중앙값 {np.median(slope[valid]):.1f}°  급경사(>{STEEP_DEG}°) 비율 {(slope[valid] > STEEP_DEG).mean():.1%}")

# ── 붓결은 노이즈가 아니라 **원화 자체**에서 가져온다: 바위 획(주봉 부벽준) 과 능선 담묵 wash 두 조각을
#    낙수선 좌표 (a = 경사 방향, c = 직교) 로 타일링 → 획이 항상 산의 낙수선을 따라 흐름
PAINT = "/mnt/user-data/uploads/landscape_to_3D/PICs/inwangjesaekdo.jpg"
art = np.asarray(Image.open(PAINT).convert("L")).astype(float)
def darkness(crop):
    lo, hi = np.percentile(crop, [5, 90]); return np.clip((hi - crop) / max(hi - lo, 1), 0, 1)
ROCK = darkness(art[120:600, 900:1500])        # 주봉 바위 획 (세로 부벽준) — 원화 px 좌표
HILL = darkness(art[600:1000, 100:700])        # 왼쪽 능선의 담묵 wash + 태점
Image.fromarray((ROCK * 255).astype(np.uint8)).save(f"{SRC}/stroke_rock.png"); Image.fromarray((HILL * 255).astype(np.uint8)).save(f"{SRC}/stroke_hill.png")
# 획 방향: 원화의 바위 획은 화면 세로 = 세상의 수직. 그래서 낙수선 좌표 대신 **옆에서 투영**한다 (세로축 = 지형 높이 H).
#   면이 남북을 보면 (x, H) 평면에서, 동서를 보면 (z, H) 평면에서 샘플 → 법선으로 섞음 (triplanar 의 옆면 두 장).
#   ※ 이전 시도(낙수선 좌표 warp) 는 경사 방향이 도는 곳마다 대리석 무늬가 생겨 폐기 (09-12)
wx = np.abs(nrm[..., 0]); wz = np.abs(nrm[..., 2]); wsum = wx + wz + 1e-6; wx /= wsum; wz /= wsum
def side(src, mpp_tex, off=0.0):
    sz = ndimage.map_coordinates(src, [(-H / mpp_tex + off), (gx / mpp_tex + off)], order=1, mode="mirror")   # 행 = 높이(위가 0행)
    sx = ndimage.map_coordinates(src, [(-H / mpp_tex + off), (gz / mpp_tex + off * 0.6)], order=1, mode="mirror")
    return wz * sz + wx * sx
rockA = side(ROCK, 0.9)                                                  # 원화 1 px ≈ 0.9 m → 획 하나가 수 m 폭
hillB = side(HILL, 1.5, 400)
c = gx * 0.7 + gz * 0.7                                                  # 태점 간격용 좌표
wash = ndimage.map_coordinates(ndimage.gaussian_filter(np.random.default_rng(9).random((512, 512)), 6),
                               [(gz / 90.0) % 512, (gx / 90.0) % 512], order=1, mode="wrap"); wash = (wash - wash.mean()) / (wash.std() + 1e-9)
dots = (np.sin(c / 3.5) > 0.35).astype(float)                            # 능선 태점: 능선 방향으로 7 m 마다 점

# ── 먹 농도 (0 종이 → 1 진묵)
s01 = np.clip((slope - FLAT_DEG) / (STEEP_DEG - FLAT_DEG), 0, 1)
rock_w = s01 ** 1.5
dark = 0.06 + 0.22 * s01                                                 # 경사 → 옅은 적묵
dark += 0.50 * rock_w * rockA                                            # 급경사: 원화 바위 획
dark += 0.30 * (1 - rock_w) * np.sqrt(s01) * hillB                       # 완경사: 원화 능선 wash
dark += 0.15 * (1 - shade) * s01                                         # 그늘 사면
dark += 0.05 * wash
dark += 0.55 * ridge * dots                                              # 능선 태점
dist = np.hypot(gx - EYE[0], gz - EYE[2]); far = np.clip((dist - FAR0) / (FAR1 - FAR0), 0, 1)
dark = np.clip(dark, 0, 1) * (1 - FAR_MIX * far)                         # 원근: 멀수록 엷게
stops = np.array([PAPER, YEOT, DAM, JUNG, JIN]); pos = np.array([0, 0.25, 0.5, 0.75, 1.0])
rgb = np.stack([np.interp(dark, pos, stops[:, k]) for k in range(3)], -1)

# ── 알파: 평지 투명, 원화 경계 페이드, 격자 밖 0
alpha = np.clip((slope - FLAT_DEG) / 8.0, 0, 1) * (0.55 + 0.45 * s01)
im = Image.new("L", (RES, RES), 0); dr = ImageDraw.Draw(im)
px = ((V[:, 0] - x0) / mpp).astype(int); pz = ((V[:, 2] - z0) / mpp).astype(int)
for f in pnt: dr.polygon([(int(px[i]), int(pz[i])) for i in f], fill=255)
painted = np.asarray(im) > 0
d_paint = ndimage.distance_transform_edt(~painted) * mpp
alpha *= np.clip(d_paint / FEATHER_M, 0, 1)
alpha *= valid
tex = np.dstack([rgb, alpha * 255]).clip(0, 255).astype(np.uint8)
Image.fromarray(tex, "RGBA").save(f"{SRC}/ink_ext_texture.png")
Image.fromarray(tex[..., :3]).resize((1024, 1024)).save(f"{SRC}/ink_ext_preview_top.jpg", quality=85)

# ── 메시: 원화 없는 면만, 띄움, 평면 UV
vi, inv = np.unique(unp, return_inverse=True)
V2 = V[vi].copy(); V2[:, 1] += LIFT_M; F2 = inv.reshape(-1, 3)
u = (V2[:, 0] - x0) / (RES * mpp); v = 1 - (V2[:, 2] - z0) / (RES * mpp)      # trimesh 규약 (v=0 이미지 아래)
mat = trimesh.visual.material.PBRMaterial(baseColorTexture=Image.open(f"{SRC}/ink_ext_texture.png"), alphaMode="BLEND",
                                          doubleSided=False, metallicFactor=0.0, roughnessFactor=1.0)
out = trimesh.Trimesh(V2, F2, process=False, visual=trimesh.visual.TextureVisuals(uv=np.c_[u, v], material=mat))
out.export(f"{RT}/terrain_ink_ext.glb")
chk = trimesh.load(f"{RT}/terrain_ink_ext.glb", force="mesh"); t = np.asarray(chk.visual.material.baseColorTexture.convert("RGBA"))
print(f"terrain_ink_ext.glb: 면 {len(chk.faces):,}  정점 {len(chk.vertices):,}  텍스처 {t.shape[1]}²  "
      f"알파>128 비율 {(t[..., 3] > 128).mean():.1%}  {os.path.getsize(f'{RT}/terrain_ink_ext.glb') // 1024} KB  bounds y {chk.bounds[0][1]:.0f}~{chk.bounds[1][1]:.0f}")
print(">>> 원화 없는 면만 포함 (원화 텍스처·지형 메시는 그대로). 언리얼에서 terrain_ink_ext 액터를 끄면 이전과 동일")
