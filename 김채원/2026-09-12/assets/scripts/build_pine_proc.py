"""
절차 생성 소나무·버드나무 (2번 방식) — 2026-09-12
====================================================
정선 인왕제색도 근경 소나무 화법을 규칙으로 옮긴 것:
  · 줄기: 살짝 기울고 굽은 가는 기둥 (아래 굵고 위 가늘게)
  · 가지: 수관 구간(높이 45% 위)에 층층이, 옆으로 뻗다가 끝이 처짐
  · 잎: 가지 끝·중간에 납작한 '먹 덩어리'(needle pad) 를 겹쳐 붙임 → 가지·잎이 전부 한 몸으로 붙어 있음
  · 색: 원화 먹 팔레트(records/ink_palette.json). 아래·안쪽 진묵, 위·바깥 담묵, 저주파 얼룩(먹 번짐)
  · 버드나무: 짧고 굵은 줄기 → 2~3 갈래 → 늘어지는 가닥 수십 개 + 가닥 따라 작은 잎 덩어리

출력 (glTF Y-up, 밑동 중심 pivot, 높이 1 → 언리얼에서 스케일 = h_m, ue_place_trees.py 와 호환)
  runtime/pine_proc_1.glb, pine_proc_2.glb, willow_proc_1.glb   — 정점색 = 먹 팔레트(linear), TEXCOORD_0.x = 흔들림 마스크
  source/proc/preview_*.jpg                                     — 옆에서 본 확인용 렌더 (sRGB 변환)

조정은 아래 P_PINE / P_WILLOW 숫자만 바꾸면 됨. 블렌더에서 손보려면 glb 를 임포트(File > Import > glTF) → 편집 → glTF 로 다시 내보내기
(정점색 Color Attribute 유지, +Y Up 체크). 높이 1·밑동 pivot 만 지키면 ue_place_trees.py 가 그대로 심는다.
"""
import json, os, struct, numpy as np, trimesh
from scipy import ndimage
from PIL import Image

RT = "assets/inwangjesaekdo/runtime"; SRC = "assets/inwangjesaekdo/source/proc"
os.makedirs(SRC, exist_ok=True)
PAL = json.load(open("assets/inwangjesaekdo/records/ink_palette.json", encoding="utf-8"))


def srgb_to_linear(cc):
    x = np.asarray(cc, float) / 255.0
    return np.clip(np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4) * 255.0, 0, 255)


JIN, JUNG, DAM, YEOT = (srgb_to_linear(PAL[k]) for k in ["진묵(0-5%)", "중묵(5-25%)", "담묵(25-55%)", "옅은담묵(55-80%)"])

# ───────────────────────── 조정 파라미터 (여기만 만지면 됨)
P_PINE = dict(
    trunk_lean=0.10,        # 꼭대기가 옆으로 밀리는 정도 (높이 1 기준). 0 = 곧게
    trunk_wobble=0.025,     # 줄기 굽이 진폭
    trunk_r=(0.026, 0.006), # 밑동·꼭대기 반지름
    trunk_segs=16, trunk_sides=8,
    crown_from=0.40,        # 이 높이 비율부터 가지 시작
    tiers=7,                # 가지 층 수 (층 높이는 ±tier_jitter 로 흔듦)
    tier_jitter=0.03,
    branches=(2, 4),        # 층마다 가지 수 범위
    branch_len=(0.26, 0.40),# 맨 아래 층 가지 길이 범위 (위로 갈수록 ×0.45 까지 줄어듦)
    branch_up=0.35,         # 가지가 처음 뻗는 방향의 위 성분 (0 수평, 1 수직)
    branch_droop=0.55,      # 가지 끝이 처지는 정도
    branch_r=(0.012, 0.004),
    pad_r=(0.070, 0.105),   # 가지 끝 큰 덩어리 반지름 범위
    pad_flat=0.42,          # 덩어리 납작함 (세로/가로)
    pad_subdiv=2,           # 큰 덩어리 세분 (2 = 320 면). 작은 덩어리는 1 (80 면)
    pad_noise=0.30,         # 덩어리 표면 울퉁불퉁 정도
    cluster=(4, 6),         # 큰 덩어리 주변에 겹쳐 붙는 작은 덩어리 수 범위 → 촘촘한 먹점 실루엣
    cluster_r=(0.40, 0.70), # 작은 덩어리 반지름 (큰 것 대비)
    inner_pads=1,           # 층마다 줄기 가까이에 붙는 안쪽 덩어리 수
    top_pads=3,             # 꼭대기 덩어리 수
    noise_amp=0.20,         # 먹 번짐 얼룩 세기
)
P_WILLOW = dict(
    trunk_h=0.40, trunk_r=(0.040, 0.020), trunk_segs=8, trunk_sides=8, trunk_lean=0.06,
    limbs=3, limb_len=(0.32, 0.44), limb_r=(0.016, 0.006),
    head_pads=9, head_r=(0.045, 0.075),      # 가지 끝 먹 덩어리(수관 머리) — 줄기·가닥을 한 몸으로 묶음
    strands=80, strand_len=(0.30, 0.58), strand_segs=12, strand_r=(0.005, 0.002), strand_sides=4,
    strand_out=(0.02, 0.16),                 # 가닥이 먼저 옆으로 뻗는 거리 (작을수록 수관에 붙어 늘어짐)
    strand_wave=0.035,                       # 가닥의 구불거림
    leaf_every=2, leaf_r=0.021, leaf_subdiv=0, leaf_flat=0.5,
    noise_amp=0.18,
)


# ───────────────────────── 기하 도우미
class Mesh:
    def __init__(s): s.V, s.F, s.C, s.part = [], [], [], []   # part: 0 줄기 1 가지 2 잎덩어리 3 가닥

    def add(s, V, F, C, part):
        o = len(s.V); s.V += list(V); s.F += [[a + o, b + o, c + o] for a, b, c in F]; s.C += list(C); s.part += [part] * len(V)


def frame(d):
    d = d / (np.linalg.norm(d) + 1e-9)
    up = np.array([0, 1, 0.]) if abs(d[1]) < 0.9 else np.array([1, 0, 0.])
    a = np.cross(d, up); a /= np.linalg.norm(a) + 1e-9; b = np.cross(a, d)
    return a, b


def tube(path, radii, sides, cap=True):
    """폴리라인 따라 원통. path (n,3), radii (n,)"""
    path = np.asarray(path, float); n = len(path); V, F = [], []
    th = np.linspace(0, 2 * np.pi, sides, endpoint=False)
    for i in range(n):
        d = (path[min(i + 1, n - 1)] - path[max(i - 1, 0)]); a, b = frame(d)
        for t in th: V.append(path[i] + radii[i] * (np.cos(t) * a + np.sin(t) * b))
    for i in range(n - 1):
        for k in range(sides):
            j = (k + 1) % sides; p, q = i * sides, (i + 1) * sides
            F += [[p + k, p + j, q + j], [p + k, q + j, q + k]]
    if cap:
        c = len(V); V.append(path[-1]); q = (n - 1) * sides
        F += [[q + k, q + (k + 1) % sides, c] for k in range(sides)]
    return np.array(V), np.array(F)


def blob(center, r, flat, subdiv, noise, rng, up_dir=None):
    """납작한 먹 덩어리: 아이코스피어 + 반지름 노이즈. 위쪽이 살짝 평평하고 아래가 너덜너덜."""
    s = trimesh.creation.icosphere(subdivisions=subdiv, radius=1.0)
    V = np.asarray(s.vertices).copy(); Fc = np.asarray(s.faces)
    G = 8; g = ndimage.gaussian_filter(rng.random((G, G, G)), 1.2); g = (g - g.mean()) / (g.std() + 1e-9)
    idx = np.clip(((V + 1) / 2 * (G - 1)).astype(int), 0, G - 1)
    nz = g[idx[:, 0], idx[:, 1], idx[:, 2]]
    rr = 1 + noise * nz - 0.12 * np.clip(-V[:, 1], 0, 1) * (rng.random(len(V)))   # 아래쪽 더 너덜
    V = V * rr[:, None]
    V[:, 1] *= flat
    V[:, 1] = np.where(V[:, 1] > 0, V[:, 1] * 0.75, V[:, 1])                        # 위 평평
    return V * r + center, Fc


def bake_colors(m, H, noise_amp, rng):
    """정점색: 부위별 기본 먹색 + 위를 보는 정점 담묵 + 높이 따라 엷어짐 + 저주파 얼룩. linear 0-255."""
    V = np.asarray(m.V); part = np.asarray(m.part)
    tm = trimesh.Trimesh(V, np.asarray(m.F), process=False)
    N = np.asarray(tm.vertex_normals); up = np.clip(N[:, 1], 0, 1)
    G = 20; g = ndimage.gaussian_filter(rng.random((G, G, G)), 2.0); g = (g - g.mean()) / (g.std() + 1e-9)
    idx = np.clip(((V - V.min(0)) / (np.ptp(V, axis=0) + 1e-9) * (G - 1)).astype(int), 0, G - 1)
    nz = g[idx[:, 0], idx[:, 1], idx[:, 2]] * noise_amp
    y = np.clip(V[:, 1] / H, 0, 1)
    a = np.zeros(len(V))
    a[part == 0] = 0.30 + 0.25 * up[part == 0] + nz[part == 0]                       # 줄기: 중묵 근처, 세로 얼룩
    a[part == 1] = 0.18 + 0.20 * up[part == 1] + nz[part == 1]                       # 가지: 진묵 쪽
    a[part == 2] = 0.05 + 0.40 * up[part == 2] + 0.25 * y[part == 2] + nz[part == 2] # 잎덩어리: 아래 진묵, 위·꼭대기 담묵
    a[part == 3] = 0.25 + 0.45 * (1 - y[part == 3]) + nz[part == 3]                  # 가닥: 아래(끝)로 갈수록 엷게
    a = np.clip(a, 0, 1)[:, None]
    col = JIN * (1 - a) + DAM * a
    return col


# ───────────────────────── 소나무
def pine(P, seed):
    rng = np.random.default_rng(seed); m = Mesh(); H = 1.0
    # 줄기
    n = P["trunk_segs"]; t = np.linspace(0, 1, n + 1)
    lean_dir = rng.uniform(0, 2 * np.pi); ld = np.array([np.cos(lean_dir), 0, np.sin(lean_dir)])
    wob = np.stack([ndimage.gaussian_filter1d(rng.normal(0, 1, n + 1), 2) for _ in range(2)], 1)
    wob = wob / (np.abs(wob).max() + 1e-9) * P["trunk_wobble"]
    path = np.c_[np.zeros(n + 1), t * H, np.zeros(n + 1)] + (t ** 1.6)[:, None] * P["trunk_lean"] * ld
    path[:, 0] += wob[:, 0] * np.sin(t * np.pi); path[:, 2] += wob[:, 1] * np.sin(t * np.pi)
    radii = P["trunk_r"][0] * (1 - t) ** 0.8 + P["trunk_r"][1]
    V, F = tube(path, radii, P["trunk_sides"]); m.add(V, F, [None] * len(V), 0)

    def trunk_at(h):
        i = np.clip(h / H * n, 0, n - 1e-6); k = int(i); f = i - k
        return path[k] * (1 - f) + path[k + 1] * f, radii[k] * (1 - f) + radii[k + 1] * f

    # 가지 층
    tiers = P["tiers"]; hs = (np.linspace(P["crown_from"], 0.93, tiers) + rng.uniform(-P["tier_jitter"], P["tier_jitter"], tiers)) * H
    az0 = rng.uniform(0, 2 * np.pi)
    for ti, h in enumerate(hs):
        f_top = ti / max(tiers - 1, 1)                                   # 0 아래 → 1 위
        nb = rng.integers(P["branches"][0], P["branches"][1] + 1)
        if ti == tiers - 1: nb = max(nb - 1, 1)
        for bi in range(nb):
            az = az0 + ti * 1.9 + bi * 2 * np.pi / nb + rng.uniform(-0.5, 0.5)
            base, r0 = trunk_at(h + rng.uniform(-0.02, 0.02))
            L = rng.uniform(*P["branch_len"]) * (1 - 0.55 * f_top)
            d = np.array([np.cos(az), P["branch_up"] * rng.uniform(0.6, 1.3), np.sin(az)]); d /= np.linalg.norm(d)
            s = np.linspace(0, 1, 7)
            bp = base + s[:, None] * L * d
            bp[:, 1] -= P["branch_droop"] * L * s ** 2 * 0.5                   # 끝 처짐
            bp[:, 1] += 0.06 * L * np.sin(s * np.pi)                             # 살짝 들렸다 처짐
            br = P["branch_r"][0] * (1 - s) + P["branch_r"][1]
            V, F = tube(bp, br, 6); m.add(V, F, [None] * len(V), 1)
            # 덩어리: 가지 끝에 큰 것 1개 + 그 둘레·가지 바깥 절반에 작은 것들을 겹쳐 붙임 (붓으로 먹점을 겹쳐 찍듯)
            rmax = rng.uniform(*P["pad_r"]) * (1 - 0.30 * f_top)
            tip = bp[-1] + np.array([0, rmax * 0.3 * P["pad_flat"], 0])
            V, F = blob(tip, rmax, P["pad_flat"], P["pad_subdiv"], P["pad_noise"], rng); m.add(V, F, [None] * len(V), 2)
            for ci in range(rng.integers(P["cluster"][0], P["cluster"][1] + 1)):
                sp = rng.uniform(0.45, 1.0)
                k = np.clip(sp * 6, 0, 5.999); kk = int(k); ff = k - kk
                c = bp[kk] * (1 - ff) + bp[kk + 1] * ff
                rr = rmax * rng.uniform(*P["cluster_r"])
                c = c + np.array([rng.uniform(-0.9, 0.9) * rmax, rng.uniform(-0.15, 0.45) * rmax, rng.uniform(-0.9, 0.9) * rmax])
                V, F = blob(c, rr, P["pad_flat"] * rng.uniform(0.9, 1.3), 1, P["pad_noise"], rng); m.add(V, F, [None] * len(V), 2)
        # 안쪽 덩어리: 줄기에 바짝 붙어 층 사이를 메움
        for ii in range(P["inner_pads"]):
            c, r0 = trunk_at(h + rng.uniform(-0.03, 0.03)); az = rng.uniform(0, 2 * np.pi)
            rr = rng.uniform(*P["pad_r"]) * 0.6 * (1 - 0.3 * f_top)
            c = c + np.array([np.cos(az) * rr * 0.9, 0, np.sin(az) * rr * 0.9])
            V, F = blob(c, rr, P["pad_flat"], 1, P["pad_noise"], rng); m.add(V, F, [None] * len(V), 2)
    # 꼭대기
    top, _ = trunk_at(H * 0.985)
    for i in range(P["top_pads"]):
        rr = rng.uniform(*P["pad_r"]) * 0.75
        c = top + np.array([rng.uniform(-0.4, 0.4) * rr, -i * rr * 0.5, rng.uniform(-0.4, 0.4) * rr])
        V, F = blob(c, rr, P["pad_flat"] * 1.1, P["pad_subdiv"], P["pad_noise"], rng); m.add(V, F, [None] * len(V), 2)
    return m, H, rng


# ───────────────────────── 버드나무
def willow(P, seed):
    rng = np.random.default_rng(seed); m = Mesh(); H = 1.0
    n = P["trunk_segs"]; t = np.linspace(0, 1, n + 1)
    ld = rng.uniform(0, 2 * np.pi); ld = np.array([np.cos(ld), 0, np.sin(ld)])
    path = np.c_[np.zeros(n + 1), t * P["trunk_h"], np.zeros(n + 1)] + (t ** 1.5)[:, None] * P["trunk_lean"] * ld
    radii = P["trunk_r"][0] * (1 - t) + P["trunk_r"][1]
    V, F = tube(path, radii, P["trunk_sides"]); m.add(V, F, [None] * len(V), 0)
    top = path[-1]; ends = []
    for li in range(P["limbs"]):
        az = li * 2 * np.pi / P["limbs"] + rng.uniform(-0.4, 0.4)
        L = rng.uniform(*P["limb_len"])
        d = np.array([np.cos(az) * 0.7, 1.0, np.sin(az) * 0.7]); d /= np.linalg.norm(d)
        s = np.linspace(0, 1, 6); lp = top + s[:, None] * L * d
        lp[:, 0] += 0.04 * np.sin(s * np.pi) * np.cos(az + 1.3); lp[:, 2] += 0.04 * np.sin(s * np.pi) * np.sin(az + 1.3)
        lr = P["limb_r"][0] * (1 - s) + P["limb_r"][1]
        V, F = tube(lp, lr, 6, cap=False); m.add(V, F, [None] * len(V), 1)
        for si in range(2, 6): ends.append(lp[si])
        # 수관 머리: 가지 끝에 먹 덩어리
        for hi in range(P["head_pads"] // P["limbs"] + 1):
            rr = rng.uniform(*P["head_r"]) * rng.uniform(0.6, 1.0)
            c = lp[rng.integers(3, 6)] + rng.normal(0, 0.05, 3) * [1, 0.5, 1]
            V, F = blob(c, rr, 0.6, 1, 0.3, rng); m.add(V, F, [None] * len(V), 2)
    ends = np.array(ends)
    for k in range(P["strands"]):
        st = ends[rng.integers(len(ends))] + rng.normal(0, 0.03, 3)
        L = rng.uniform(*P["strand_len"]); az = rng.uniform(0, 2 * np.pi)
        out = np.array([np.cos(az), 0, np.sin(az)]) * rng.uniform(*P["strand_out"])
        s = np.linspace(0, 1, P["strand_segs"] + 1)
        sp = st + out * np.sin(np.clip(s * 1.6, 0, 1) * np.pi / 2)[:, None] - np.c_[np.zeros_like(s), s * L, np.zeros_like(s)]
        sp[:, 1] += 0.06 * L * np.sin(np.clip(s * 2.5, 0, 1) * np.pi)            # 처음엔 살짝 위로 뻗었다가 처짐
        sway = rng.normal(0, 1, 3) * P["strand_wave"]; ph = rng.uniform(0, np.pi)
        sp += np.outer(np.sin(s * np.pi * rng.uniform(1.2, 2.5) + ph), sway) * np.array([1, 0.3, 1])
        sp[:, 1] = np.maximum(sp[:, 1], 0.03)                                    # 땅에 안 닿게
        V, F = tube(sp, P["strand_r"][0] * (1 - s) + P["strand_r"][1], P["strand_sides"], cap=False)
        m.add(V, F, [None] * len(V), 3)
        for si in range(1, len(sp), P["leaf_every"]):
            c = sp[si] + rng.normal(0, 0.006, 3)
            V, F = blob(c, P["leaf_r"] * rng.uniform(0.7, 1.3), P["leaf_flat"], P["leaf_subdiv"], 0.25, rng)
            m.add(V, F, [None] * len(V), 3 if si > len(sp) * 0.6 else 2)         # 아래쪽 잎은 가닥과 같이 엷어짐
    return m, H, rng


# ───────────────────────── 내보내기 (pine_ai 와 같은 규약: 밑동 중심 pivot, 높이 1, COLOR_0 linear, TEXCOORD_0.x 흔들림)
def add_texcoord(path, uv):
    b = open(path, "rb").read(); jl = struct.unpack_from("<I", b, 12)[0]
    j = json.loads(b[20:20 + jl].decode("utf-8")); bl = struct.unpack_from("<I", b, 20 + jl)[0]
    bin_ = bytearray(b[28 + jl:28 + jl + bl]); prim = j["meshes"][0]["primitives"][0]
    n = j["accessors"][prim["attributes"]["POSITION"]]["count"]; assert len(uv) == n, (len(uv), n)
    while len(bin_) % 4: bin_.append(0)
    off = len(bin_); data = np.asarray(uv, np.float32).tobytes(); bin_ += data
    j["bufferViews"].append({"buffer": 0, "byteOffset": off, "byteLength": len(data)})
    j["accessors"].append({"bufferView": len(j["bufferViews"]) - 1, "componentType": 5126, "count": n, "type": "VEC2",
                           "min": [float(uv[:, 0].min()), float(uv[:, 1].min())], "max": [float(uv[:, 0].max()), float(uv[:, 1].max())]})
    prim["attributes"]["TEXCOORD_0"] = len(j["accessors"]) - 1; j["buffers"][0]["byteLength"] = len(bin_)
    js = json.dumps(j, separators=(",", ":")).encode("utf-8")
    while len(js) % 4: js += b" "
    out = bytearray(b"glTF") + struct.pack("<II", 2, 12 + 8 + len(js) + 8 + len(bin_))
    out += struct.pack("<II", len(js), 0x4E4F534A) + js + struct.pack("<II", len(bin_), 0x004E4942) + bin_
    open(path, "wb").write(out)


def export(name, m, H, noise_amp, rng):
    V = np.asarray(m.V, float); F = np.asarray(m.F); part = np.asarray(m.part)
    col = bake_colors(m, H, noise_amp, rng)
    # 밑동 중심 pivot(줄기 밑동 = 원점), 높이 1
    y0, y1 = V[:, 1].min(), V[:, 1].max(); h = y1 - y0
    V = (V - [0, y0, 0]) / h
    tm = trimesh.Trimesh(V, F, process=False, visual=trimesh.visual.ColorVisuals(vertex_colors=np.c_[col, np.full(len(col), 255)].astype(np.uint8)))
    out = f"{RT}/{name}.glb"; tm.export(out)
    chk = trimesh.load(out, force="mesh"); assert np.allclose(np.asarray(chk.vertices), V, atol=1e-5), "정점 순서 바뀜"
    sway = np.clip(V[:, 1], 0, 1) ** 1.5
    sway = np.where(part == 3, np.clip(sway + 0.3, 0, 1), sway)                     # 버드나무 가닥은 더 흔들림
    add_texcoord(out, np.c_[sway, np.zeros(len(sway))])
    chk = trimesh.load(out, force="mesh")
    ncomp = len(chk.split(only_watertight=False))
    print(f"{name}: 면 {len(F):,}  정점 {len(V):,}  컴포넌트 {ncomp} (겹쳐 붙은 조각 수 — 시각적으로는 한 몸)  "
          f"bounds {np.round(chk.bounds, 3).tolist()}  {os.path.getsize(out) // 1024} KB  "
          f"COLOR_0={'있음' if getattr(chk.visual, 'vertex_colors', None) is not None else '없음'}")
    return tm


def preview(name, tm, W=520, H=640):
    """옆에서 본 확인용 렌더: 정점색(linear→sRGB) × 램버트, 종이색 배경."""
    V = np.asarray(tm.vertices); F = np.asarray(tm.faces)
    C = np.asarray(tm.visual.vertex_colors, float)[:, :3] / 255
    C = np.where(C <= 0.0031308, C * 12.92, 1.055 * C ** (1 / 2.4) - 0.055)
    N = np.asarray(tm.face_normals); L = np.array([0.4, 0.8, 0.5]); L /= np.linalg.norm(L)
    sh = 0.72 + 0.28 * np.clip(N @ L, 0, 1)
    img = np.full((H, W, 3), [186, 170, 150.]) ; zb = np.full((H, W), 1e9)
    sc = H * 0.9; ox, oy = W / 2, H * 0.95
    u = ox + V[:, 0] * sc; v = oy - V[:, 1] * sc; z = V[:, 2]
    order = np.argsort(-z[F].mean(1))
    for i in order:
        fa = F[i]; uu, vv = u[fa], v[fa]
        x0, x1 = max(int(uu.min()), 0), min(int(uu.max()) + 1, W); y0, y1 = max(int(vv.min()), 0), min(int(vv.max()) + 1, H)
        if x1 <= x0 or y1 <= y0: continue
        px, py = np.meshgrid(np.arange(x0, x1) + .5, np.arange(y0, y1) + .5)
        d = (vv[1] - vv[2]) * (uu[0] - uu[2]) + (uu[2] - uu[1]) * (vv[0] - vv[2])
        if abs(d) < 1e-9: continue
        l0 = ((vv[1] - vv[2]) * (px - uu[2]) + (uu[2] - uu[1]) * (py - vv[2])) / d
        l1 = ((vv[2] - vv[0]) * (px - uu[2]) + (uu[0] - uu[2]) * (py - vv[2])) / d; l2 = 1 - l0 - l1
        ins = (l0 >= -1e-6) & (l1 >= -1e-6) & (l2 >= -1e-6)
        if not ins.any(): continue
        img[y0:y1, x0:x1][ins] = (C[fa].mean(0) * sh[i] * 255)
    Image.fromarray(img.clip(0, 255).astype(np.uint8)).save(f"{SRC}/preview_{name}.jpg", quality=90)


if __name__ == "__main__":
    outs = {}
    for name, (fn, P, seed) in {"pine_proc_1": (pine, P_PINE, 1), "pine_proc_2": (pine, P_PINE, 7), "willow_proc_1": (willow, P_WILLOW, 3)}.items():
        m, H, rng = fn(P, seed)
        tm = export(name, m, H, P["noise_amp"], rng); preview(name, tm); outs[name] = tm
    # 한 장으로 합침
    ims = [Image.open(f"{SRC}/preview_{n}.jpg") for n in outs]
    sheet = Image.new("RGB", (sum(i.width for i in ims) + 20 * (len(ims) - 1), ims[0].height), (186, 170, 150)); x = 0
    for i in ims: sheet.paste(i, (x, 0)); x += i.width + 20
    sheet.save(f"{SRC}/preview_sheet.jpg", quality=90); print("preview_sheet.jpg 저장")
