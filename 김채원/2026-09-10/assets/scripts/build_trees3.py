"""
나무 배치 v3 — 채집점을 '위·아래 두 줄'로 올바로 해석한다.

v2의 오류: 297점을 전부 밑동으로 봤다. 실제로는 사람이 나무 띠의
  · 수관 상단선  · 밑동선
을 각각 따라 찍었다. 그래서 그루 수가 두 배가 되고 절반이 수관 높이에 섰다.

v3:
  1. 클릭 순서로 획을 나눈다 (연속 클릭 간격 < 70 px = 같은 획)
  2. x 구간이 겹치고 위아래로 나란한 획 두 개를 짝짓는다 → 위=수관, 아래=밑동
  3. 밑동선을 따라 나무를 세우고, 높이는 같은 x에서 두 선의 세로 간격으로 준다
     → 나무마다 높이가 측정값이 된다 (14그루 전파가 아니라)
  4. 짝이 없는 획·단독 점은 밑동으로 보되 높이는 이웃에서 가져온다
  5. 기와집 발자국 안에는 나무를 세우지 않는다

출력: obj_trees.glb · obj_trees_lod.glb · trees_manifest.json
"""
import json, os, numpy as np, rasterio, trimesh
from PIL import Image
from pyproj import Transformer
from curves import Curves
from scipy.ndimage import binary_opening, binary_closing, uniform_filter
Image.MAX_IMAGE_PIXELS = None

CFG = "/mnt/user-data/outputs/best_fit.json"
ANN = "/mnt/user-data/outputs/manual_annotations.json"
PAINT = "/mnt/user-data/uploads/landscape_to_3D/PICs/inwangjesaekdo.jpg"
DEM = "dem10_5m_5179_filled.tif"

EYE_NEAR, Y_NEAR = 17.0, 1400
WILLOW_X, WILLOW_Y = (900.0, 1660.0), 1430.0
STROKE_GAP = 70.0          # 이보다 멀면 다른 획
BASE_STEP = 34.0           # 밑동선 위에 나무를 세울 간격 (px)
PAIR_MIN, PAIR_MAX = 18.0, 520.0   # 짝지을 두 선의 세로 간격 허용 범위 (px)
HOUSE_CLEAR = 1.35         # 기와집 발자국 여유 배수
GAPFILL_MAX = 90           # 획이 없는 먹 덩어리를 메울 상한

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
    return np.where(ok, (D[r0,c0]*(1-fc)*(1-fr)+D[r0,c0+1]*fc*(1-fr)
                         + D[r0+1,c0]*(1-fc)*fr+D[r0+1,c0+1]*fc*fr), np.nan)


def surf(x, y):
    return CV.deform(elev(x, y), np.maximum(np.hypot(x-VX, y-VY), 1e-6), G0)


def cast(px, py, h):
    az = AZ0 + np.arctan((px-PPX)/F); el = np.arctan((PPY-py)/F); cz = G0+h
    X = VX+np.sin(az)*DS; Y = VY+np.cos(az)*DS
    A = np.maximum.accumulate(np.arctan2(np.where(np.isnan(surf(X, Y)), -1e4, surf(X, Y)-cz), DS))
    k = np.searchsorted(A, el)
    if k >= len(DS):
        return (np.nan,)*4
    d = DS[k]; x = VX+np.sin(az)*d; y = VY+np.cos(az)*d
    return d, x, y, float(surf(np.array([x]), np.array([y]))[0])


def local(x, y, z):
    e, n = x-VX, y-VY
    return np.array([e*RGT[0]+n*RGT[1], z-CAMZ, -(e*FWD[0]+n*FWD[1])])


def srgb_to_linear(cc):
    x = np.asarray(cc, float)/255.0
    return np.clip(np.where(x <= 0.04045, x/12.92, ((x+0.055)/1.055)**2.4)*255.0, 0, 255)


_art = np.asarray(Image.open(PAINT).convert("RGB")).reshape(-1, 3)
PAPER = np.percentile(_art, 88, axis=0); INK = np.percentile(_art, 5, axis=0)*1.05


def ink_color(d, j=0.0):
    tt = float(np.clip((d-150.0)/1000.0, 0, 1))**0.75
    return (INK + (PAPER-INK)*float(np.clip(tt*0.62+j, 0, 0.85))).clip(0, 255)


# ───────── 1. 획 나누기 + 위/아래 짝짓기
P = np.array(ann["layers"]["tree"]["segments"][0], float)
gaps = np.hypot(*(np.diff(P, axis=0).T))
strokes, cur = [], [0]
for i, g in enumerate(gaps):
    if g < STROKE_GAP:
        cur.append(i+1)
    else:
        strokes.append(cur); cur = [i+1]
strokes.append(cur)
S = [P[r] for r in strokes]
S = [q[np.argsort(q[:, 0])] for q in S]

used = set(); pairs = []
order = sorted(range(len(S)), key=lambda i: -len(S[i]))
for i in order:
    if i in used or len(S[i]) < 3:
        continue
    best, bs = None, 1e9
    for j in order:
        if j == i or j in used or len(S[j]) < 3:
            continue
        a, b = S[i], S[j]
        lo, hi = max(a[:, 0].min(), b[:, 0].min()), min(a[:, 0].max(), b[:, 0].max())
        if hi-lo < 0.45*min(np.ptp(a[:, 0]), np.ptp(b[:, 0])):
            continue
        xs = np.linspace(lo, hi, 12)
        dy = np.interp(xs, b[:, 0], b[:, 1]) - np.interp(xs, a[:, 0], a[:, 1])
        if not (np.all(dy > PAIR_MIN) and np.all(dy < PAIR_MAX) and dy.std() < 0.6*dy.mean()):
            continue
        # 거리로 상한을 건다: 그 자리에서 실물 3~25 m 나무가 되는 화면 높이만 허용
        xm = float(np.median(xs))
        dm, _, _, _ = cast(xm, float(np.interp(xm, b[:, 0], b[:, 1])), H0)
        if not np.isfinite(dm):
            continue
        lo_px, hi_px = 3.0*F/dm*CV.g(dm), 25.0*F/dm*CV.g(dm)
        if not (lo_px <= dy.mean() <= hi_px):
            continue
        if dy.mean() < bs:
            bs, best = dy.mean(), j
    if best is not None:
        used.add(i); used.add(best); pairs.append((i, best, bs))     # i=위(수관), best=아래(밑동)

print(f"클릭 {len(P)}점 → 획 {len(S)}개 → 위·아래 짝 {len(pairs)}쌍 "
      f"({sum(len(S[a])+len(S[b]) for a, b, _ in pairs)}점 소비)")
for a, b, dy in sorted(pairs, key=lambda t: -t[2])[:6]:
    print(f"   수관 x{S[a][:,0].min():5.0f}~{S[a][:,0].max():5.0f}  세로간격 {dy:5.0f}px")

BASES = []          # (px, py, hpx, src)
for a, b, _ in pairs:
    top, bot = S[a], S[b]
    lo, hi = max(top[:, 0].min(), bot[:, 0].min()), min(top[:, 0].max(), bot[:, 0].max())
    n = max(2, int((hi-lo)//BASE_STEP)+1)
    for x in np.linspace(lo, hi, n):
        yb = float(np.interp(x, bot[:, 0], bot[:, 1]))
        yt = float(np.interp(x, top[:, 0], top[:, 1]))
        if yb-yt > PAIR_MIN:
            BASES.append((float(x), yb, yb-yt, "paired"))
n_pair = len(BASES)
for i, q in enumerate(S):
    if i in used:
        continue
    for px, py in q:
        BASES.append((float(px), float(py), np.nan, "unpaired"))
print(f"짝지어진 밑동 {n_pair}그루 (높이=측정값) / 짝 없는 점 {len(BASES)-n_pair}그루")

# ───────── 2. 획이 없는 먹 덩어리만 최소한으로 메운다
g = np.asarray(Image.open(PAINT).convert("L"), float)
ink = g < np.percentile(g, 26)
mass = binary_closing(binary_opening(ink, np.ones((7, 7))), np.ones((11, 11)))
dens = uniform_filter(mass.astype(float), size=41)
rng = np.random.default_rng(20260910)
ys, xs = np.where(mass[Y_NEAR:, :]); ys += Y_NEAR
cand = np.c_[xs, ys]
cand = cand[dens[cand[:, 1], cand[:, 0]] > 0.55]
rng.shuffle(cand)
occ = [(b[0], b[1]) for b in BASES]
add = 0
for px, py in cand:
    if add >= GAPFILL_MAX:
        break
    if min((px-ox)**2 + (py-oy)**2 for ox, oy in occ) < 55**2:
        continue
    BASES.append((float(px), float(py), np.nan, "gapfill")); occ.append((px, py)); add += 1
print(f"먹 덩어리 보충 {add}그루 (기존과 55px 이상 떨어진 곳만)")

# 높이 기준 = 짝지은 밑동 + 사람이 개별로 잰 14그루(th 레이어)
# v0.5에서 th를 빼먹어 전경 나무가 3배 작아졌다. 둘 다 써야 한다.
TH = np.array([[b[0], b[1], b[1]-tp[1]] for b, tp in
               np.array(ann["layers"]["th"]["segments"], float)], float)
PB = np.vstack([np.array([[b[0], b[1], b[2]] for b in BASES[:n_pair]], float), TH])
print(f"높이 기준점 {len(PB)}개 = 짝지은 {n_pair} + 개별 측정 {len(TH)}  "
      f"화면높이 {PB[:,2].min():.0f}~{PB[:,2].max():.0f} px")
FULL = []
for px, py, hpx, src in BASES:
    if not np.isfinite(hpx):
        k = int(np.argmin((PB[:, 0]-px)**2 + (PB[:, 1]-py)**2))
        hpx = PB[k, 2]
    FULL.append((px, py, float(hpx), src))

# ───────── 3. 기와집 발자국
HOUSES = []
raw = [np.array(x, float) for x in ann["layers"]["roof"]["segments"] if len(x) >= 3]
raw.sort(key=lambda a: a[:, 0].min())
merged = []
for a in raw:
    if merged and a[:, 0].min()-merged[-1][:, 0].max() < 60:
        merged[-1] = np.vstack([merged[-1], a])
    else:
        merged.append(a)
for a in merged:
    if np.ptp(a[:, 0]) < 60:
        continue
    d, x, y, z = cast(float(a[:, 0].mean()), float(a[:, 1].max()), H0)
    if np.isfinite(d):
        w = float(np.ptp(a[:, 0])*d/F)
        HOUSES.append((local(x, y, z), w*HOUSE_CLEAR/2, w*0.45*HOUSE_CLEAR/2))
print("기와집 발자국:", [(round(float(h[0][0])), round(float(-h[0][2])), round(h[1]*2, 1)) for h in HOUSES])


def in_house(o):
    for c0, rx, rz in HOUSES:
        if abs(o[0]-c0[0]) < rx and abs(o[2]-c0[2]) < max(rz, rx*0.6):
            return True
    return False


# ───────── 4. 형상
def pine(h, seg=7, tiers=3, lean=0.0, rng=None):
    """동양(한국) 소나무 — 굽은 줄기 + 층층이 얹힌 납작한 수관 덩어리.
    정선이 그린 소나무가 정확히 이 형태다: 휘어 오르는 줄기에 가로로 퍼진 먹 덩어리."""
    rng = rng or np.random.default_rng(0)
    V, Fc = [], []
    n = max(5, seg)
    th = np.linspace(0, 2*np.pi, n, endpoint=False)
    NS = 3 if tiers == 3 else 2                     # 줄기 마디
    # 줄기 — 위로 갈수록 가늘어지고 한쪽으로 휜다
    bend = rng.uniform(-0.16, 0.16) + lean
    sway = rng.uniform(-0.10, 0.10)
    cx = 0.0
    prev = None
    trunk_top = h*0.62
    for k in range(NS+1):
        t_ = k/NS
        z = trunk_top*t_
        cx = bend*h*t_**1.6 + sway*h*np.sin(t_*np.pi)*0.5
        r = h*0.070*(1-0.55*t_)
        o = len(V)
        for a in th:
            V.append([cx + r*np.cos(a), z, r*np.sin(a)])
        if prev is not None:
            for i2 in range(n):
                j2 = (i2+1) % n
                Fc += [[prev+i2, prev+j2, o+j2], [prev+i2, o+j2, o+i2]]
        prev = o
    tipx = cx
    # 수관 덩어리 — 납작한 원반. 층마다 좌우로 어긋나게 얹는다
    NC = 3 if tiers == 3 else 2
    for k in range(NC):
        t_ = (k+1)/(NC+0.35)
        zc = trunk_top*0.52 + (h-trunk_top*0.52)*t_
        rr = h*0.255*(1.0-0.30*t_)*rng.uniform(0.82, 1.18)
        off = tipx*t_ + rng.uniform(-0.10, 0.10)*h
        thick = rr*rng.uniform(0.42, 0.62)
        o = len(V)
        for a in th:                                    # 아래 테두리
            V.append([off + rr*np.cos(a), zc, rr*np.sin(a)])
        for a in th:                                    # 위 테두리 (살짝 좁게)
            V.append([off + rr*0.80*np.cos(a), zc+thick, rr*0.80*np.sin(a)])
        cb = len(V); V.append([off, zc-thick*0.30, 0.0])       # 아래 중심
        ct = len(V); V.append([off, zc+thick*1.45, 0.0])       # 위 중심
        for i2 in range(n):
            j2 = (i2+1) % n
            Fc += [[o+i2, o+j2, o+n+j2], [o+i2, o+n+j2, o+n+i2]]   # 옆면
            Fc.append([o+j2, o+i2, cb])                              # 아랫면
            Fc.append([o+n+i2, o+n+j2, ct])                          # 윗면
        # 줄기에서 수관으로 가는 짧은 가지
        if abs(off) > h*0.04:
            b0 = len(V)
            V += [[bend*h*(zc/max(trunk_top, 1e-6))**1.6, zc-thick*0.2, -h*0.012],
                  [bend*h*(zc/max(trunk_top, 1e-6))**1.6, zc-thick*0.2,  h*0.012],
                  [off, zc, 0.0]]
            Fc.append([b0, b0+1, b0+2])
    return np.array(V, float), np.array(Fc, int)


def willow(h, strands=10, segs=4, rng=None):
    rng = rng or np.random.default_rng(0)
    V, Fc = [], []
    tr = h*0.07
    th5 = np.linspace(0, 2*np.pi, 5, endpoint=False)
    for z in (0.0, h*0.55):
        for a in th5:
            V.append([tr*np.cos(a), z, tr*np.sin(a)])
    for i in range(5):
        Fc += [[i, (i+1) % 5, 5+(i+1) % 5], [i, 5+(i+1) % 5, 5+i]]
    top = h*0.58
    for k in range(strands):
        ang = 2*np.pi*k/strands + rng.uniform(-.15, .15)
        R = h*0.34*rng.uniform(0.7, 1.15); drop = h*0.50*rng.uniform(0.75, 1.2)
        o = len(V)
        for t_ in np.linspace(0, 1, segs+1):
            rr = R*np.sin(t_*np.pi/2)
            zz = top + h*0.16*np.sin(t_*np.pi) - drop*t_**2
            w = h*0.030*(1-0.75*t_)
            V.append([rr*np.cos(ang)-w*np.sin(ang), zz, rr*np.sin(ang)+w*np.cos(ang)])
            V.append([rr*np.cos(ang)+w*np.sin(ang), zz, rr*np.sin(ang)-w*np.cos(ang)])
        for i in range(segs):
            a_, b_, c_, d_ = o+2*i, o+2*i+1, o+2*i+2, o+2*i+3
            Fc += [[a_, b_, d_], [a_, d_, c_]]
    return np.array(V, float), np.array(Fc, int)


def build(lod=False):
    Vs, Fs, cols, info = [], [], [], []
    nv = 0
    r2 = np.random.default_rng(4242)
    skipped_house = 0
    for px, py, hpx, src in FULL:
        near = py > Y_NEAR
        d, x, y, z = cast(px, py, H0)
        if not np.isfinite(d) or d < 8:
            continue
        o = local(x, y, z)
        if in_house(o):
            skipped_house += 1
            continue
        real = float(np.clip((d*hpx/F)/CV.g(d), 1.2, 24.0))
        hdef = real*CV.g(d)
        wil = (WILLOW_X[0] <= px <= WILLOW_X[1]) and (py >= WILLOW_Y)
        if wil:
            v, f = willow(hdef, strands=6 if lod else 10, segs=3 if lod else 4, rng=r2)
        else:
            v, f = (pine(hdef, seg=5, tiers=2, rng=r2) if lod
                    else pine(hdef, seg=7, tiers=3, lean=float(r2.normal(0, 0.04)), rng=r2))
        yaw = r2.uniform(0, 2*np.pi); ca, sa = np.cos(yaw), np.sin(yaw)
        v = v @ np.array([[ca, 0, sa], [0, 1, 0], [-sa, 0, ca]]).T + o[None, :]
        cols.append(np.tile(srgb_to_linear(ink_color(d, float(r2.normal(0, 0.05))))[None, :], (len(v), 1)))
        Vs.append(v); Fs.append(f+nv); nv += len(v)
        info.append(dict(px=px, py=py, src=src, species="willow" if wil else "pine",
                         band="near" if near else "far", dist_m=float(d),
                         h_px=float(hpx), real_h_m=real, drawn_h_m=float(hdef)))
    TV = np.vstack(Vs); TF = np.vstack(Fs); C = np.vstack(cols)
    m = trimesh.Trimesh(vertices=TV, faces=TF, process=False,
                        visual=trimesh.visual.ColorVisuals(
                            vertex_colors=np.c_[C, np.full(len(C), 255)].astype(np.uint8)))
    return m, info, skipped_house


for lod, out in ((False, "obj_trees.glb"), (True, "obj_trees_lod.glb")):
    m, info, sk = build(lod)
    m.export(out)
    nw = sum(1 for i in info if i["species"] == "willow")
    nn = sum(1 for i in info if i["band"] == "near")
    print(f"{out:20s} {len(info):4d}그루  면 {len(m.faces):,}  "
          f"버드나무 {nw} / 소나무 {len(info)-nw}  전경 {nn}  "
          f"기와집 겹쳐 제외 {sk}  실물높이 중앙 {np.median([i['real_h_m'] for i in info]):.1f} m")
    if not lod:
        keep = info

json.dump({"method": "채집점을 획으로 나눠 수관선·밑동선을 짝지음. 밑동=아래선, 높이=두 선의 세로 간격",
           "strokes": len(S), "pairs": len(pairs), "paired_trees": n_pair,
           "gapfill": add, "house_clearance": HOUSE_CLEAR,
           "trees": keep}, open("trees_manifest.json", "w"), ensure_ascii=False, indent=2)
