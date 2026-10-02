"""
Q3 — 나무 · 기와집 · 운무를 지형에서 떼어내 독립 3D 개체로 만든다.

배치 근거
  - 중경 나무 / 기와집 : 눈높이 1.6 m 광선  (각크기 앵커 132 m와 일치, fit_eye2 검증)
  - 전경 나무          : 눈높이 17 m 광선   (전경 밴드는 별도 시점 = 삼원법)
  - 운무               : 사람이 채집한 운무 상단선 광선을 변형지형과 교차 → 3D 곡선 → 커튼면

좌표계는 export_glb.py와 동일 (X=우, Y=상, -Z=전방, 카메라=원점, meter).
출력: obj_trees.glb  obj_house.glb  obj_fog.glb  objects_manifest.json
"""
import json, os, numpy as np, rasterio, trimesh
from PIL import Image
Image.MAX_IMAGE_PIXELS=None
from pyproj import Transformer
from curves import Curves

CFG = "/mnt/user-data/outputs/best_fit.json"
ANN = "/mnt/user-data/outputs/manual_annotations.json"
DEM = "dem10_5m_5179_filled.tif"
PAINT = "/mnt/user-data/uploads/landscape_to_3D/PICs/inwangjesaekdo.jpg"
EYE_NEAR = 17.0            # 전경 밴드 시점 (fit_eye2: 산포 최소 16.8 m)
Y_NEAR = 1400              # 이 화면행보다 아래 = 전경 밴드
PINE_FAR, PINE_NEAR = 12.8, 8.3   # 과장 되돌린 실물 환산 높이 (m)

c = json.load(open(CFG, encoding="utf-8"))
ann = json.load(open(ANN, encoding="utf-8"))
CV = Curves(json.load(open("distortion_curves.json", encoding="utf-8")))
cam = c["camera"]; F, PPX, PPY = cam["focal_px"], cam["principal_x_px"], cam["horizon_y_px"]
AZ0 = np.radians(cam["azimuth_deg"]); PW, PH = c["painting_size"]
G0 = c["viewpoint"]["ground_elev_m"]; H0 = CV.h0

s = rasterio.open(DEM); D = s.read(1).astype("float32"); D[D <= -9998] = np.nan
INV = ~s.transform; HH, WW = D.shape
t = Transformer.from_crs("EPSG:4326", "EPSG:5179", always_xy=True)
VX, VY = t.transform(c["viewpoint"]["lon"], c["viewpoint"]["lat"])
FWD = np.array([np.sin(AZ0), np.cos(AZ0)]); RGT = np.array([np.cos(AZ0), -np.sin(AZ0)])
CAMZ = G0 + H0
DS = np.arange(3., 3000., 3.)


def elev(x, y):
    cc, rr = INV*(x, y)
    ok = (cc >= 0)&(cc < WW-1)&(rr >= 0)&(rr < HH-1)
    cc = np.clip(cc-.5, 0, WW-1.001); rr = np.clip(rr-.5, 0, HH-1.001)
    c0 = cc.astype(np.int32); r0 = rr.astype(np.int32); fc = cc-c0; fr = rr-r0
    v = (D[r0,c0]*(1-fc)*(1-fr)+D[r0,c0+1]*fc*(1-fr)+D[r0+1,c0]*(1-fc)*fr+D[r0+1,c0+1]*fc*fr)
    return np.where(ok, v, np.nan)


def surf(x, y):
    d = np.maximum(np.hypot(x-VX, y-VY), 1e-6)
    return CV.deform(elev(x, y), d, G0)


def cast(px, py, h):
    """화면점 → (거리 d, 월드 x, y, 변형고도 z). 못 맞으면 NaN."""
    az = AZ0 + np.arctan((px-PPX)/F); el = np.arctan((PPY-py)/F); cz = G0+h
    X = VX+np.sin(az)*DS; Y = VY+np.cos(az)*DS
    Z = surf(X, Y)
    A = np.maximum.accumulate(np.arctan2(np.where(np.isnan(Z), -1e4, Z-cz), DS))
    k = np.searchsorted(A, el)
    if k >= len(DS):
        return (np.nan,)*4
    d = DS[k]
    x = VX+np.sin(az)*d; y = VY+np.cos(az)*d
    return d, x, y, float(surf(np.array([x]), np.array([y]))[0])


def srgb_to_linear(c):
    """glTF COLOR_0는 linear로 해석된다. 원화에서 뽑은 sRGB 먹색을 그대로 넣으면
    블렌더·언리얼 양쪽에서 밝게 뜬다. 쓰기 전에 변환한다."""
    x = np.asarray(c, float)/255.0
    lin = np.where(x <= 0.04045, x/12.92, ((x+0.055)/1.055)**2.4)
    return np.clip(lin*255.0, 0, 255)


def local(x, y, z):
    """월드 → 카메라 정렬 로컬 (export_glb와 동일 규약)."""
    e, n = x-VX, y-VY
    return np.array([e*RGT[0]+n*RGT[1], z-CAMZ, -(e*FWD[0]+n*FWD[1])])


# ───────────────────────── 나무
def pine(h, r=None, seg=7):
    """저폴리 소나무: 기둥 + 2단 원뿔. 높이 h."""
    r = r or h*0.22
    V, Fc = [], []
    tr = h*0.10
    th = np.linspace(0, 2*np.pi, seg, endpoint=False)
    # 기둥
    for z in (0.0, h*0.42):
        for a in th: V.append([tr*np.cos(a), z, tr*np.sin(a)])
    for i in range(seg):
        j = (i+1) % seg
        Fc += [[i, j, seg+j], [i, seg+j, seg+i]]
    b = 2*seg
    # 원뿔 2단
    for k, (z0, z1, rr) in enumerate([(h*0.34, h*0.74, r), (h*0.62, h*1.0, r*0.66)]):
        o = len(V)
        for a in th:
            V.append([rr*np.cos(a), z0, rr*np.sin(a)])
        V.append([0, z1, 0])
        tip = len(V)-1
        for i in range(seg):
            j = (i+1) % seg
            Fc.append([o+i, o+j, tip])
        # 밑면
        oc = len(V); V.append([0, z0, 0])
        for i in range(seg):
            j = (i+1) % seg
            Fc.append([o+j, o+i, oc])
    return np.array(V, float), np.array(Fc, int)


pts = np.array(ann["layers"]["tree"]["segments"][0], float)
th_pairs = np.array(ann["layers"]["th"]["segments"], float)

# 측정된 14그루의 화면높이 → 근처 점에 높이 배분
meas = []
for b, tp in th_pairs:
    hgt_px = b[1]-tp[1]
    meas.append((b[0], b[1], hgt_px))
meas = np.array(meas)

# 사람이 잰 14그루의 '실물 환산 높이' — 자동 추출은 실패했으므로(상관 0.094) 이것만 쓴다
MEAS = []
for b, tp in th_pairs:
    nr = b[1] > Y_NEAR
    dm, _, _, _ = cast(b[0], b[1], EYE_NEAR if nr else H0)
    if not np.isfinite(dm):
        continue
    raw = dm*(np.tan(np.arctan((PPY-tp[1])/F)) - np.tan(np.arctan((PPY-b[1])/F)))
    MEAS.append((b[0], b[1], float(np.clip(raw/CV.g(dm), 3.0, 24.0))))
MEAS = np.array(MEAS)
print(f"사람 측정 나무 {len(MEAS)}그루 실물환산 높이 "
      f"{MEAS[:,2].min():.1f}~{MEAS[:,2].max():.1f} m (중앙 {np.median(MEAS[:,2]):.1f} m)")

RNG = np.random.default_rng(20260909)
Vs, Fs, info = [], [], []
nv = 0
for px, py in pts:
    near = py > Y_NEAR
    h_eye = EYE_NEAR if near else H0
    d, x, y, z = cast(px, py, h_eye)
    if not np.isfinite(d) or d < 8:
        continue
    # 화면상 가장 가까운 '사람이 잰 나무'의 실물 높이를 물려받는다
    k = int(np.argmin((MEAS[:, 0]-px)**2 + (MEAS[:, 1]-py)**2))
    real = float(np.clip(MEAS[k, 2]*float(np.exp(RNG.normal(0, 0.18))), 3.0, 24.0))
    hdef = real*CV.g(d)                      # 화면에서 정선의 비율로 보이게 과장 적용
    v, f = pine(hdef)
    o = local(x, y, z)
    v = v + o[None, :]
    Vs.append(v); Fs.append(f+nv); nv += len(v)
    info.append(dict(px=float(px), py=float(py), band="near" if near else "far",
                     dist_m=float(d), real_h_m=real, drawn_h_m=float(hdef)))

TV = np.vstack(Vs); TF = np.vstack(Fs)
col = np.tile(np.array([[54, 60, 48, 255]], np.uint8), (len(TV), 1))
tm = trimesh.Trimesh(vertices=TV, faces=TF, process=False,
                     visual=trimesh.visual.ColorVisuals(vertex_colors=col))
tm.export("obj_trees_legacy.glb")   # 나무는 build_trees2.py가 최종본을 만든다
print(f"나무 {len(info)}그루  정점 {len(TV):,} 면 {len(TF):,}  "
      f"{os.path.getsize('obj_trees_legacy.glb')/1e6:.1f} MB")
nb = sum(1 for i in info if i["band"] == "near")
print(f"  전경 밴드 {nb}그루 (눈높이 {EYE_NEAR}m) / 중경·원경 {len(info)-nb}그루 (눈높이 {H0}m)")
print(f"  거리 {min(i['dist_m'] for i in info):.0f}~{max(i['dist_m'] for i in info):.0f} m, "
      f"실물높이 중앙 {np.median([i['real_h_m'] for i in info]):.1f} m")


# ───────────────────────── 기와집
def hall(w, dpt, wall, roof_h, eave):
    """단순 팔작지붕 건물: 벽 상자 + 용마루 지붕 + 처마."""
    hw, hd = w/2, dpt/2
    V = [[-hw, 0, -hd], [hw, 0, -hd], [hw, 0, hd], [-hw, 0, hd],
         [-hw, wall, -hd], [hw, wall, -hd], [hw, wall, hd], [-hw, wall, hd]]
    Fc = [[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]]
    ew, ed = hw+eave, hd+eave
    o = len(V)
    V += [[-ew, wall, -ed], [ew, wall, -ed], [ew, wall, ed], [-ew, wall, ed],
          [-hw*0.55, wall+roof_h, 0], [hw*0.55, wall+roof_h, 0]]
    a, b, cc, d_, r0, r1 = o, o+1, o+2, o+3, o+4, o+5
    Fc += [[a, b, r1], [a, r1, r0],          # 앞 사면
           [cc, d_, r0], [cc, r0, r1],       # 뒤 사면
           [b, cc, r1], [d_, a, r0],         # 좌우 합각
           [a, r0, d_], [b, r1, cc]]
    return np.array(V, float), np.array(Fc, int)


raw = [np.array(s_, float) for s_ in ann["layers"]["roof"]["segments"] if len(s_) >= 3]
raw.sort(key=lambda a: a[:, 0].min())
roofs = []                                   # x 구간이 붙어 있는 획은 한 채로 합친다
for a in raw:
    if roofs and a[:, 0].min() - roofs[-1][:, 0].max() < 60:
        roofs[-1] = np.vstack([roofs[-1], a])
    else:
        roofs.append(a)
print(f"지붕선 획 {len(raw)}개 → 건물 {len(roofs)}동으로 병합")
posts = ann["layers"]["post"]["segments"]
# 1차 통과: 각 지붕의 광선 거리 (본채 = 폭이 가장 큰 것, 각크기 앵커로 검증된 141 m)
raw_d = []
for a in roofs:
    if np.ptp(a[:, 0]) < 60:
        raw_d.append(None); continue
    dd, _, _, _ = cast(float(a[:, 0].mean()), float(a[:, 1].max()), H0)
    raw_d.append(dd if np.isfinite(dd) else None)
main_i = int(np.nanargmax([(np.ptp(a[:, 0]) if raw_d[i] else np.nan)
                           for i, a in enumerate(roofs)]))
MAIN_D = raw_d[main_i]
print(f"본채 = 지붕 폭 {np.ptp(roofs[main_i][:,0]):.0f}px, 광선 거리 {MAIN_D:.0f} m (각크기 앵커 132 m와 정합)")

HV, HF, hinfo = [], [], []
nv = 0
for ai, a in enumerate(roofs):
    if np.ptp(a[:, 0]) < 60:
        continue
    px = float(a[:, 0].mean()); ridge = float(a[:, 1].min()); eaveY = float(a[:, 1].max())
    d, x, y, z = cast(px, eaveY, H0)
    if not np.isfinite(d):
        continue
    forced = False
    if ai != main_i and MAIN_D and d < MAIN_D:
        # 원화 관찰 제약: 작은 집은 본채보다 뒤에 있다.
        # 광선 거리(63 m)는 평탄해진 전경 지형 탓에 짧게 나온 값이라 신뢰하지 않는다.
        d = MAIN_D*1.25
        az_ = AZ0 + np.arctan((px-PPX)/F)
        x, y = VX+np.sin(az_)*d, VY+np.cos(az_)*d
        z = float(surf(np.array([x]), np.array([y]))[0])
        forced = True
    mpp = d/F                                     # 1 px = mpp m (그 거리에서)
    w = float(np.ptp(a[:, 0])*mpp)
    roof_h = float((eaveY-ridge)*mpp)*0.72
    wall = max(2.4, roof_h*0.55)
    v, f = hall(w, w*0.45, wall, roof_h, w*0.05)
    ang = np.arctan2(x-VX, y-VY) - AZ0            # 카메라를 향하도록 회전
    ca, sa = np.cos(-ang), np.sin(-ang)
    R = np.array([[ca, 0, sa], [0, 1, 0], [-sa, 0, ca]])
    v = v @ R.T + local(x, y, z)[None, :]
    HV.append(v); HF.append(f+nv); nv += len(v)
    hinfo.append(dict(dist_m=float(d), width_m=w, roof_h_m=roof_h, wall_h_m=float(wall),
                      distance_source=("본채보다 뒤 (원화 관찰 제약, 본채x1.25)" if forced
                                       else "눈높이 1.6 m 광선")))

HVs = np.vstack(HV); HFs = np.vstack(HF)
hm = trimesh.Trimesh(vertices=HVs, faces=HFs, process=False,
                     visual=trimesh.visual.ColorVisuals(
                         vertex_colors=np.tile(np.r_[
                             srgb_to_linear(lambda_dummy) if False else srgb_to_linear(
                             (lambda a: (np.percentile(a,5,axis=0)*1.05 +
                              (np.percentile(a,88,axis=0)-np.percentile(a,5,axis=0)*1.05)*0.12)
                             )(np.asarray(Image.open(PAINT).convert("RGB")).reshape(-1,3))),
                             255].astype(np.uint8)[None, :], (len(HVs), 1))))
hm.export("obj_house.glb")
print(f"기와집 {len(hinfo)}동  면 {len(HFs)}  " +
      ", ".join(f"{h['dist_m']:.0f}m/폭{h['width_m']:.1f}m/지붕{h['roof_h_m']:.1f}m" for h in hinfo))


# ───────────────────────── 운무 (등고도 층운)
# 사람이 채집한 운무 상단선을 변형지형과 교차시키면 절대고도 157 +- 21 m 에 모인다.
# 귀무(열별 무작위 교란) 40.5 +- 4.3 m 대비 0.51배 → 무작위 곡선보다 뚜렷하게 등고도.
FOG_ALT = 157.0
fog = np.array(ann["layers"]["fog"]["segments"][0], float)
fog = fog[np.argsort(fog[:, 0])]
alts = []
for px, py in fog:
    d, x, y, z = cast(px, py, H0)
    if np.isfinite(d):
        alts.append(z)
alts = np.array(alts)
FOG_ALT = float(np.median(alts))

def build_fog(GS, out):
    u = np.arange(-1250., 1250.1, GS); w = np.arange(0., 2200.1, GS)
    U, Wv = np.meshgrid(u, w)
    X = VX + U*RGT[0] + Wv*FWD[0]; Y = VY + U*RGT[1] + Wv*FWD[1]
    Zt = surf(X, Y)
    dist = np.hypot(X-VX, Y-VY)
    inband = np.isfinite(Zt) & (Zt < FOG_ALT) & (Zt > FOG_ALT-BAND) & (dist > DMIN)
    ny, nx = U.shape
    idx = np.arange(ny*nx).reshape(ny, nx)
    Zs = np.where(np.isfinite(Zt), Zt, FOG_ALT) + 1.5
    V = np.stack([U.ravel(), (Zs-CAMZ).ravel(), -Wv.ravel()], 1)
    a_, b_, c_, d_ = idx[:-1, :-1], idx[:-1, 1:], idx[1:, 1:], idx[1:, :-1]
    kf = (inband[:-1, :-1] & inband[:-1, 1:] & inband[1:, 1:] & inband[1:, :-1]).ravel()
    Fc = np.vstack([np.stack([a_.ravel(), b_.ravel(), c_.ravel()], 1)[kf],
                    np.stack([a_.ravel(), c_.ravel(), d_.ravel()], 1)[kf]])
    t_ = np.clip((FOG_ALT-Zs.ravel())/BAND, 0, 1)
    al = (18 + 218*t_**0.7).astype(np.uint8)
    cols = np.c_[np.tile(srgb_to_linear([246, 246, 246]), (len(V), 1)), al].astype(np.uint8)
    fm = trimesh.Trimesh(vertices=V, faces=Fc, process=False,
                         visual=trimesh.visual.ColorVisuals(vertex_colors=cols))
    fm.remove_unreferenced_vertices(); fm.export(out)
    return fm

BAND = 80.0
DMIN = 380.0
fmesh = build_fog(12.0, "obj_fog.glb")
flod = build_fog(45.0, "obj_fog_lod.glb")
print(f"운무 사면껍질  상단고도 {FOG_ALT:.0f} m, 두께 {BAND:.0f} m, {DMIN:.0f} m 이후")
print(f"  master 면 {len(fmesh.faces):,} / runtime LOD 면 {len(flod.faces):,}  "
      f"채집선 고도 표준편차 {alts.std():.1f} m")
_unused = """GS = 12.0                                    # 운무면 격자 (m)
BAND = 80.0                                  # 운무가 사면을 덮는 두께 (m)
DMIN = 380.0                                 # 이보다 가까운 전경은 맑다 (원화 관찰)
u = np.arange(-1250., 1250.1, GS); w = np.arange(0., 2200.1, GS)
U, Wv = np.meshgrid(u, w)
X = VX + U*RGT[0] + Wv*FWD[0]; Y = VY + U*RGT[1] + Wv*FWD[1]
Zt = surf(X, Y)
dist = np.hypot(X-VX, Y-VY)
inband = np.isfinite(Zt) & (Zt < FOG_ALT) & (Zt > FOG_ALT-BAND) & (dist > DMIN)
ny, nx = U.shape
idx = np.arange(ny*nx).reshape(ny, nx)
Zs = np.where(np.isfinite(Zt), Zt, FOG_ALT) + 1.5      # 지형에 살짝 띄운 껍질
V = np.stack([U.ravel(), (Zs-CAMZ).ravel(), -Wv.ravel()], 1)
a_, b_, c_, d_ = idx[:-1, :-1], idx[:-1, 1:], idx[1:, 1:], idx[1:, :-1]
keepf = (inband[:-1, :-1] & inband[:-1, 1:] & inband[1:, 1:] & inband[1:, :-1]).ravel()
Fc = np.vstack([np.stack([a_.ravel(), b_.ravel(), c_.ravel()], 1)[keepf],
                np.stack([a_.ravel(), c_.ravel(), d_.ravel()], 1)[keepf]])
t_ = np.clip((FOG_ALT-Zs.ravel())/BAND, 0, 1)          # 상단선에서 0 → 아래로 짙어짐
al = (18 + 218*t_**0.7).astype(np.uint8)
cols = np.c_[np.full((len(V), 3), 246, np.uint8), al].astype(np.uint8)
fmesh = trimesh.Trimesh(vertices=V, faces=Fc, process=False,
                        visual=trimesh.visual.ColorVisuals(vertex_colors=cols))
fmesh.remove_unreferenced_vertices()
fmesh.export("obj_fog.glb")
"""

json.dump({"frame": "export_glb.py와 동일 (X=우, Y=상, -Z=전방, 카메라=원점, meter)",
           "eye_near_m": EYE_NEAR, "eye_far_m": H0, "near_band_screen_y": Y_NEAR,
           "trees": info, "houses": hinfo,
           "fog": {"model": "등고도 상단선 + 사면 껍질", "altitude_m": FOG_ALT,
                   "band_m": BAND, "clear_within_m": DMIN,
                   "traced_alt_std_m": float(alts.std()),
                   "null_alt_std_m": 40.5, "ratio_vs_null": float(alts.std()/40.5),
                   "faces": int(len(fmesh.faces))}},
          open("objects_manifest.json", "w"), ensure_ascii=False, indent=2)
