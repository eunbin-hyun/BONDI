"""
지형 표면 요철 + 베이스컬러.

런타임 지형은 1만 면이라 굴곡이 뭉개진다. 폴리곤을 늘리는 대신
표면 법선을 이미지로 굽는다. 세 가지를 합친다.

  (A) 기하 고주파  : 5 m DEM이 갖고 있지만 1만 면 메시가 잃어버린 잔굴곡
  (B) 먹 범프      : 정선의 붓질(부벽준)을 실제 요철로. 먹이 짙은 곳 = 파인 곳
                     ★ 원화(마스크 전)에서 읽되, 클린플레이트로 지운 자리는 뺀다
  (C) 절차적 미세 기복 : 수치지형도가 평탄화해 버린 전경에만 얹는 잔결.
                     측정값이 아니라 조형적 추가 — manifest에 그렇게 기록한다

베이스컬러는 스침각(grazing) 보정을 넣는다. 시선과 지면이 거의 평행한
전경에서는 원화 화소 하나가 수십 배로 늘어나 검은 띠가 된다. 그 구역은
원화를 '흐린 톤'으로만 쓰고 명암은 지형에서 만든다.

출력: tex_terrain_normal(.png/_1k) · tex_terrain_basecolor(.png/_1k) · terrain_uv_extent.json
"""
import json, numpy as np, rasterio
from PIL import Image
from pyproj import Transformer
from scipy.ndimage import gaussian_filter
from curves import Curves
Image.MAX_IMAGE_PIXELS = None

CFG = "/mnt/user-data/outputs/best_fit.json"
DEM = "dem10_5m_5179_filled.tif"
PAINT_ORIG = "/mnt/user-data/uploads/landscape_to_3D/PICs/inwangjesaekdo.jpg"
PAINT = "inwang_masked.jpg"                 # 클린 플레이트 (나무·집·화제 지워진 것)
CPMASK = "cleanplate_mask.png"
RES = 2048
HALF_W, DEPTH, BACK = 1250.0, 2600.0, 250.0
GEO_HP_M = 26.0        # 이보다 완만한 굴곡은 메시가 이미 갖고 있다 → 고주파만 남긴다
INK_AMP = 2.2          # 먹 범프 진폭 (m)
GEO_AMP = 0.70         # 기하 고주파 배율
MICRO_AMP = 0.85       # 절차적 미세 기복 진폭 (m) — 평탄한 곳에서만 최대
MICRO_WAVES = [(38.0, 1.00), (17.0, 0.55), (7.5, 0.30), (3.2, 0.17)]
STRETCH_OK = 5.0       # 이 배율까지는 원화를 그대로 (=입사각 78.5°)
STRETCH_CUT = 13.0     # 이 배율을 넘으면 원화는 '지면공간 저주파 톤'으로만 (=입사각 85.6°)
TONE_SIG_M = 45.0      # 스침 구역 톤을 지면공간에서 뭉개는 반경 (m) — 방사 줄무늬 제거
STRETCH_HARD = 40.0    # 이 배율을 넘으면 투영을 아예 버리고 '원화 하단 지면 톤'을 쓴다
GROUND_BAND = 0.90     # 원화 하단 이 비율 아래를 '전경 지면' 표본으로 삼는다

c = json.load(open(CFG, encoding="utf-8"))
cam = c["camera"]; F, PPX, PPY = cam["focal_px"], cam["principal_x_px"], cam["horizon_y_px"]
AZ0 = np.radians(cam["azimuth_deg"]); PW, PH = c["painting_size"]
G0 = c["viewpoint"]["ground_elev_m"]
CV = Curves(json.load(open("distortion_curves.json", encoding="utf-8")))
CAMZ = G0 + CV.h0

s = rasterio.open(DEM); D = s.read(1).astype("float32"); D[D <= -9998] = np.nan
INV = ~s.transform; HH, WW = D.shape
t = Transformer.from_crs("EPSG:4326", "EPSG:5179", always_xy=True)
VX, VY = t.transform(c["viewpoint"]["lon"], c["viewpoint"]["lat"])
FWD = np.array([np.sin(AZ0), np.cos(AZ0)]); RGT = np.array([np.cos(AZ0), -np.sin(AZ0)])


def elev(x, y):
    cc, rr = INV*(x, y)
    ok = (cc >= 0)&(cc < WW-1)&(rr >= 0)&(rr < HH-1)
    cc = np.clip(cc-.5, 0, WW-1.001); rr = np.clip(rr-.5, 0, HH-1.001)
    c0 = cc.astype(np.int32); r0 = rr.astype(np.int32); fc = cc-c0; fr = rr-r0
    return np.where(ok, (D[r0,c0]*(1-fc)*(1-fr)+D[r0,c0+1]*fc*(1-fr)
                         + D[r0+1,c0]*(1-fc)*fr+D[r0+1,c0+1]*fc*fr), np.nan)


# ── 메시가 놓인 평면 격자 (export_glb / build_blend2와 같은 범위)
nx = RES
nz = int(round(RES*(DEPTH+BACK)/(2*HALF_W)))
xs = np.linspace(-HALF_W, HALF_W, nx)
zs = np.linspace(-BACK, DEPTH, nz)
Xc, Zc = np.meshgrid(xs, zs)
X = VX + Xc*RGT[0] + Zc*FWD[0]
Y = VY + Xc*RGT[1] + Zc*FWD[1]
Z = elev(X, Y)
Z = np.where(np.isfinite(Z), Z, np.nanmin(Z))
hz = np.maximum(np.hypot(X-VX, Y-VY), 1e-6)
Zd = CV.deform(Z, hz, G0)                 # 변형(정선) 지형 높이

px_x = 2*HALF_W/(nx-1)                    # 화소 한 칸의 실거리 (m)
px_z = (DEPTH+BACK)/(nz-1)
print(f"평면 격자 {nz} x {nx}  화소 {px_x:.2f} x {px_z:.2f} m")

# ── (A) 기하 고주파
sig_x = max(GEO_HP_M/px_x, 0.6); sig_z = max(GEO_HP_M/px_z, 0.6)
geo_hp = (Zd - gaussian_filter(Zd, (sig_z, sig_x)))*GEO_AMP
print(f"기하 고주파  진폭 {np.percentile(np.abs(geo_hp),99):.2f} m (99퍼센타일)")

# ── (C) 절차적 미세 기복 — 평탄한 곳일수록 세게
rng = np.random.default_rng(20260910)
wn = rng.standard_normal((nz, nx)).astype("float32")
micro = np.zeros_like(Zd, dtype="float32")
for wl, amp in MICRO_WAVES:
    b = gaussian_filter(wn, (max(wl/px_z, .5), max(wl/px_x, .5)))
    b /= (b.std() + 1e-9)
    micro += b*amp
micro /= (micro.std() + 1e-9)
# 실제 기복이 큰 사면에서는 줄인다 (측정 지형을 흐리지 않기 위해)
relief = gaussian_filter(np.abs(geo_hp), (sig_z, sig_x))
flatw = np.clip(1.0 - relief/3.0, 0.25, 1.0)       # 기복 3 m 이상이면 25%만
micro = micro*MICRO_AMP*flatw
print(f"미세 기복    진폭 {np.percentile(np.abs(micro),99):.2f} m (99퍼센타일)  "
      f"평탄부 가중 중앙 {np.median(flatw):.2f}")

# ── 화면 투영 좌표 (원화 읽기 공용)
E, N = X-VX, Y-VY
Zcam = E*FWD[0]+N*FWD[1]; Xcam = E*RGT[0]+N*RGT[1]
with np.errstate(divide="ignore", invalid="ignore"):
    u = PPX + F*Xcam/Zcam
    v = PPY - F*(Zd-CAMZ)/Zcam
inb = (Zcam > 30) & (u >= 0) & (u < PW) & (v >= 0) & (v < PH)
ui = np.clip(np.nan_to_num(u), 0, PW-1).astype(np.int32)
vi = np.clip(np.nan_to_num(v), 0, PH-1).astype(np.int32)

# ── 스침각(입사각) → 원화 화소 신축 배율
gzx = np.gradient(Zd, px_x, axis=1); gzz = np.gradient(Zd, px_z, axis=0)
nrm = np.dstack([-gzx, -gzz, np.ones_like(Zd)])
nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
ray = np.dstack([X-VX, Y-VY, Zd-CAMZ])
ray /= np.maximum(np.linalg.norm(ray, axis=2, keepdims=True), 1e-6)
cosi = np.abs(np.sum(nrm*ray, axis=2)).clip(1e-3, 1.0)
stretch = 1.0/cosi
inc_deg = np.degrees(np.arccos(cosi))
for lo, hi in [(0, 200), (200, 400), (400, 800), (800, 1500)]:
    m = inb & (hz >= lo) & (hz < hi)
    if m.sum():
        print(f"  {lo:5d}~{hi:5d} m  입사각 중앙 {np.median(inc_deg[m]):5.1f}°  "
              f"신축 중앙 {np.median(stretch[m]):6.1f}배")

# 원화를 그대로 쓸 가중치 (1=선명 투영, 0=톤만)
wsharp = np.clip((np.log(STRETCH_CUT) - np.log(stretch)) /
                 (np.log(STRETCH_CUT) - np.log(STRETCH_OK)), 0, 1)
wsharp = gaussian_filter(wsharp, (3.0, 3.0))

# ── (B) 먹 범프 : 원화(마스크 전)에서 읽고, 지운 자리는 뺀다
art = np.asarray(Image.open(PAINT_ORIG).convert("L").resize((PW, PH)), float)
cpm = np.asarray(Image.open(CPMASK).convert("L").resize((PW, PH)), float)/255.0
cpm = gaussian_filter(cpm, 6.0)
paper = np.percentile(art, 88); ink = np.percentile(art, 4)
L = np.full(Zd.shape, paper); L[inb] = art[vi[inb], ui[inb]]
Kp = np.zeros(Zd.shape); Kp[inb] = cpm[vi[inb], ui[inb]]     # 1 = 3D로 대체돼 지운 자리
darkness = np.clip((paper - L)/max(paper-ink, 1e-6), 0, 1)*(1.0 - Kp)
ink_bump = -darkness*INK_AMP                       # 먹이 짙을수록 파인다
ink_bump = ink_bump - gaussian_filter(ink_bump, (sig_z*2.5, sig_x*2.5))   # 저주파 제거
# 스침각 구역에서는 붓질 한 획이 수십 배로 늘어나 방사 줄무늬가 된다 → 완전히 뺀다
ink_bump *= wsharp
print(f"먹 범프    원화 안 화소 {100*inb.mean():.1f}%  "
      f"지운자리 제외 {100*(Kp>0.5).mean():.1f}%  진폭 {np.percentile(np.abs(ink_bump),99):.2f} m")

Hh = geo_hp + ink_bump + micro

# ── 높이장 → 접선공간 노멀
dhdx = np.gradient(Hh, px_x, axis=1)
dhdz = np.gradient(Hh, px_z, axis=0)
Nx = -dhdx; Ny = -dhdz; Nz = np.ones_like(Hh)
ln = np.sqrt(Nx*Nx + Ny*Ny + Nz*Nz)
nm = np.dstack([Nx/ln, Ny/ln, Nz/ln])
img = ((nm*0.5 + 0.5)*255).clip(0, 255).astype(np.uint8)
Image.fromarray(img, "RGB").resize((RES, RES), Image.LANCZOS).save("tex_terrain_normal.png")

tilt = np.degrees(np.arctan(np.hypot(dhdx, dhdz)))
print(f"노멀맵 저장 tex_terrain_normal.png {RES}x{RES}  "
      f"기울기 중앙 {np.median(tilt):.1f}°  95퍼센타일 {np.percentile(tilt,95):.1f}°")

json.dump({"half_width_m": HALF_W, "depth_m": DEPTH, "back_m": BACK,
           "uv_note": "u = (Xc + HALF_W)/(2*HALF_W), v = (Zc + BACK)/(DEPTH + BACK)  "
                      "(Xc = 메시 X, Zc = -메시 Z). 감면 후에도 정점 좌표로 재계산 가능",
           "geo_highpass_m": GEO_HP_M, "ink_amp_m": INK_AMP,
           "micro_amp_m": MICRO_AMP, "micro_note":
               "절차적 프랙탈 잔결. 측정값이 아니라 조형적 추가 "
               "(수치지형도가 평탄화한 전경이 유리처럼 매끈해 보이는 것을 막는 용도)",
           "grazing": {"stretch_ok": STRETCH_OK, "stretch_cut": STRETCH_CUT,
                       "note": "화소 신축이 이 배율을 넘는 구역은 원화를 선명 투영하지 않고 "
                               "흐린 톤 + 지형 음영으로 대체"},
           "res": RES},
          open("terrain_uv_extent.json", "w"), ensure_ascii=False, indent=2)

# ── 같은 평면 공간의 베이스컬러
from matplotlib.colors import LightSource
ls = LightSource(azdeg=315, altdeg=45)
Zsh = np.nan_to_num(Zd, nan=np.nanmin(Zd)) + micro + geo_hp*0.5
sh = ls.hillshade(Zsh, vert_exag=1.6, dx=px_x, dy=px_z)
sh = np.clip((sh-0.15)/0.75, 0, 1)[..., None]
_rgb = np.asarray(Image.open(PAINT).convert("RGB"))
_flat = _rgb[::7, ::7].reshape(-1, 3)
PAPER3 = np.percentile(_flat, 88, axis=0); INK3 = np.percentile(_flat, 5, axis=0)*1.12
hill = (INK3 + (PAPER3-INK3)*sh).clip(0, 255)

# 스침 구역 톤: 화면공간에서 흐리면 방사 줄무늬가 그대로 남는다.
# 투영값을 '지면공간'에서 뭉개야 줄무늬(폭 1 m · 길이 수백 m)가 평균으로 사라진다.

# 시점에서 보이는 면만 원화를 쓴다 (가려진 뒷사면은 음영기복)
mx = np.full(Zd.shape, -np.pi/2)
el = np.arctan2(Zd-CAMZ, hz)
for sf in np.linspace(0.04, 0.97, 64):        # 표본이 적으면 시선 방향 줄무늬가 생긴다
    xx = VX+(X-VX)*sf; yy = VY+(Y-VY)*sf
    zz = CV.deform(elev(xx, yy), np.maximum(hz*sf, 1e-6), G0)-CAMZ
    mx = np.maximum(mx, np.arctan2(np.where(np.isnan(zz), -1e4, zz), hz*sf))
vis = el >= mx-np.radians(0.25)
# 스침각에서는 가림 판정이 원래 불안정하다 → 한 칸씩 튀는 것을 정리
vis = gaussian_filter(vis.astype(float), 2.5) > 0.55

use = inb & vis
sharp = hill.copy()
sharp[use] = _rgb[vi[use], ui[use]]

# 지면공간 저주파 톤 (줄무늬 제거)
ts_x = max(TONE_SIG_M/px_x, 1.0); ts_z = max(TONE_SIG_M/px_z, 1.0)
tone_raw = np.zeros(Zd.shape); tone_w = use.astype(float)
tone_raw[use] = _rgb[vi[use], ui[use]].mean(axis=1)
num = gaussian_filter(tone_raw, (ts_z, ts_x)); den = gaussian_filter(tone_w, (ts_z, ts_x))
tone = np.where(den > 1e-4, num/np.maximum(den, 1e-6), np.percentile(_rgb, 88))
tone_n = np.clip((tone - INK3.mean())/max(PAPER3.mean()-INK3.mean(), 1e-6), 0, 1)
tone_c = INK3 + (PAPER3-INK3)*tone_n[..., None]

# 극단 스침 구역(전경 지면)은 투영 자체가 뒤에 있는 산을 끌어와 짙게 만든다.
# 그 자리는 '원화 하단 지면'의 먹 톤 평균으로 대체한다.
_band = _rgb[int(PH*GROUND_BAND):, :, :].reshape(-1, 3)
GROUND3 = np.percentile(_band, 60, axis=0)
wtone = np.clip((np.log(STRETCH_HARD) - np.log(stretch)) /
                (np.log(STRETCH_HARD) - np.log(STRETCH_CUT)), 0, 1)
wtone = gaussian_filter(wtone, (3.0, 3.0))[..., None]
soft = (tone_c*wtone + GROUND3*(1-wtone)) * (0.72 + 0.50*sh)
soft = soft.clip(0, 255)
print(f"전경 지면 톤 RGB {GROUND3.round(0)}  (원화 하단 {int(PH*GROUND_BAND)}행 이하 60퍼센타일)")

ws = (wsharp*use)[..., None]
alb = sharp*ws + soft*(1-ws)
w = np.clip(gaussian_filter(use.astype(float), 4.0)*1.15, 0, 1)[..., None]
alb = (alb*w + hill*(1-w)).clip(0, 255).astype(np.uint8)
ai = Image.fromarray(alb, "RGB")
ai.resize((RES, RES), Image.LANCZOS).save("tex_terrain_basecolor.png")
ai.resize((1024, 1024), Image.LANCZOS).save("tex_terrain_basecolor_1k.png")
Image.open("tex_terrain_normal.png").resize((1024, 1024), Image.LANCZOS).save("tex_terrain_normal_1k.png")
near = use & (hz < 400)
print(f"베이스컬러 저장  원화 사용 화소 {100*use.mean():.1f}%  "
      f"그중 선명 투영 가중 중앙 {np.median(wsharp[use]):.2f} "
      f"(전경 400 m 이내 {np.median(wsharp[near]) if near.sum() else float('nan'):.2f})")

# 검수용 미리보기
Image.fromarray(img).resize((512, int(512*nz/nx)), Image.LANCZOS).save("normalmap_preview.jpg", quality=88)
ai.resize((512, int(512*nz/nx)), Image.LANCZOS).save("basecolor_preview.jpg", quality=88)
