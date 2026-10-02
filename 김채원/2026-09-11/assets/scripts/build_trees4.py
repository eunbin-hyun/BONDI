"""
나무 v4 + 기와집 v2 — 런타임 품질 보강 (2026-09-11 오후)

v3 → 런타임에는 LOD(줄기 2마디·수관 2층·5각형)가 들어가 버섯처럼 보였다.
v4:
  나무  · 굽은 줄기 5마디 + 비틀림
        · 수관 3~4층, 층마다 가지 끝 '먹 덩어리' 1~2개를 옆으로 덧붙임 (정선의 겹친 먹점)
        · 덩어리 테두리를 울퉁불퉁하게 (반지름·높이 지터), 아래 어둡고 위 밝게 (정점색으로 부피감)
        · 거리별 LOD: 근경(<200 m) 9각형·4층+가지덩어리 / 중경 7각형·3층 / 원경(>600 m) 6각형·2층
  기와집 · 기단 + 기둥 + 벽 + 처마 곡선(모서리 들림) 우진각 지붕 + 용마루
        · 배치·크기·방향은 기존 runtime/house.glb 에서 그대로 복원 (주석 재사용)

입력: trees_manifest.json (px, py, h, 종) · runtime/house.glb (배치)
출력: assets/inwangjesaekdo/runtime/trees.glb, house.glb  (v0.11 좌표계·pivot 동일)
      trees.glb 의 TEXCOORD_0.x = 나무 내 높이 비율 (흔들림 마스크, 언리얼 WPO 용). 정점 알파는 255 고정
"""
import json, numpy as np, trimesh

SRC = open("build_trees3.py", encoding="utf-8").read()
exec(SRC.split("# ───────── 1.")[0])                       # elev/surf/cast/local/ink_color/CV/H0 …
exec(SRC[SRC.index("def willow"):SRC.index("def build(")])  # willow()

RT = "assets/inwangjesaekdo/runtime"

# ── 공통 pivot 오프셋: obj_house.glb(오프셋 전) vs runtime/house.glb(오프셋 후) 첫 정점 차이
_h0 = trimesh.load("obj_house.glb", force="mesh"); _h1 = trimesh.load("house_runtime_v011.glb", force="mesh")   # v0.11 배치 원본(고정)
OFF = np.asarray(_h0.vertices[0]) - np.asarray(_h1.vertices[0])
assert np.allclose(np.asarray(_h0.vertices) - OFF, np.asarray(_h1.vertices), atol=1e-3), "house 오프셋 불일치"
print("pivot 오프셋", OFF.round(2).tolist())


def lin(c):
    return srgb_to_linear(np.asarray(c, float))


# ═══════════════════════ 소나무 v4
def ring(n):
    return np.linspace(0, 2*np.pi, n, endpoint=False)


def pad(V, Fc, C, center, rr, thick, n, rng, col_dark, col_light):
    """먹 덩어리 한 개: 울퉁불퉁한 테두리 두 줄 + 위아래 중심."""
    th = ring(n)
    jit = rng.uniform(0.72, 1.22, n)
    hj = rng.uniform(-0.25, 0.25, n)*thick
    o = len(V)
    for a, j, hh in zip(th, jit, hj):                         # 아래 테두리
        V.append([center[0]+rr*j*np.cos(a), center[1]+hh, center[2]+rr*j*np.sin(a)]); C.append(col_dark)
    for a, j, hh in zip(th, jit, hj):                         # 위 테두리
        V.append([center[0]+rr*j*0.78*np.cos(a), center[1]+thick+hh*0.5, center[2]+rr*j*0.78*np.sin(a)]); C.append(col_light)
    cb = len(V); V.append([center[0], center[1]-thick*0.35, center[2]]); C.append(col_dark)
    ct = len(V); V.append([center[0], center[1]+thick*1.4, center[2]]); C.append(col_light)
    for i in range(n):
        j = (i+1) % n
        Fc += [[o+i, o+j, o+n+j], [o+i, o+n+j, o+n+i], [o+j, o+i, cb], [o+n+i, o+n+j, ct]]


def pine4(h, d, rng, col):
    """h: 그린 높이(m), d: 거리(m), col: 먹색(linear 0-255)."""
    if d < 200:   n, tiers, sub = 9, 4, 1
    elif d < 600: n, tiers, sub = 7, 3, 1
    else:         n, tiers, sub = 6, 2, 0
    V, Fc, C = [], [], []
    # 화면 밝기 기준(sRGB): 옛 v3 나무 = 62. 종이색을 28% 섞었더니 112(중간 회색)가 돼서 6% 로 내림 (09-11 실기)
    dark = np.clip(col*0.80, 0, 255); light = np.clip(col, 0, 255)          # v3 와 같은 먹 톤(화면 62). 위쪽 밝기 차이는 안 줌
    trunk_col = np.clip(col*0.90, 0, 255)
    th = ring(7)
    NS = 5
    bend = rng.uniform(-0.20, 0.20); sway = rng.uniform(-0.12, 0.12); twist = rng.uniform(-0.6, 0.6)
    trunk_top = h*0.64
    prev = None; axis = []
    for k in range(NS+1):
        t_ = k/NS; z = trunk_top*t_
        cx = bend*h*t_**1.7 + sway*h*np.sin(t_*np.pi)*0.5
        cz = twist*h*0.06*np.sin(t_*np.pi)
        r = h*0.075*(1-0.6*t_) + 0.02
        axis.append((cx, z, cz))
        o = len(V)
        for a in th:
            V.append([cx+r*np.cos(a), z, cz+r*np.sin(a)]); C.append(trunk_col)
        if prev is not None:
            for i in range(7):
                j = (i+1) % 7
                Fc += [[prev+i, prev+j, o+j], [prev+i, o+j, o+i]]
        prev = o
    tipx, _, tipz = axis[-1]
    for k in range(tiers):
        t_ = (k+1)/(tiers+0.3)
        zc = trunk_top*0.55 + (h-trunk_top*0.55)*t_
        rr = h*0.27*(1.0-0.32*t_)*rng.uniform(0.85, 1.15)
        ax_i = min(NS, int(round(zc/trunk_top*NS))); cx, _, cz = axis[ax_i]
        offx = cx*0.6 + tipx*t_*0.4 + rng.uniform(-0.12, 0.12)*h
        offz = cz + rng.uniform(-0.10, 0.10)*h
        thick = rr*rng.uniform(0.40, 0.58)
        pad(V, Fc, C, (offx, zc, offz), rr, thick, n, rng, dark, light)
        for s in range(sub):                                  # 옆으로 뻗은 가지 끝 덩어리
            ang = rng.uniform(0, 2*np.pi); L = rr*rng.uniform(0.9, 1.5)
            c2 = (offx+L*np.cos(ang), zc+rng.uniform(-0.15, 0.25)*rr, offz+L*np.sin(ang))
            r2 = rr*rng.uniform(0.38, 0.6)
            pad(V, Fc, C, c2, r2, r2*rng.uniform(0.4, 0.6), max(6, n-4), rng, dark, light)
            b0 = len(V)                                       # 가지 (얇은 삼각 판)
            V += [[cx, zc-thick*0.3, cz-h*0.012], [cx, zc-thick*0.3, cz+h*0.012], [c2[0], c2[1], c2[2]]]
            C += [trunk_col]*3; Fc += [[b0, b0+1, b0+2], [b0+2, b0+1, b0]]
    return np.array(V, float), np.array(Fc, int), np.array(C, float)


man = json.load(open("trees_manifest.json", encoding="utf-8"))["trees"]
rng = np.random.default_rng(777)
Vs, Fs, Cs, As, nv = [], [], [], [], 0
lod_cnt = {"근": 0, "중": 0, "원": 0}
for t in man:
    px, py = t["px"], t["py"]
    d, x, y, z = cast(px, py, H0)
    if not np.isfinite(d):
        continue
    o = local(x, y, z)
    hdef = float(t["drawn_h_m"])
    col = lin(ink_color(d, float(rng.normal(0, 0.05))))
    if t["species"] == "willow":
        v, f = willow(hdef, strands=10, segs=4, rng=rng); c = np.tile(col[None, :], (len(v), 1))
    else:
        v, f, c = pine4(hdef, d, rng, col)
        lod_cnt["근" if d < 200 else ("중" if d < 600 else "원")] += 1
    yaw = rng.uniform(0, 2*np.pi); ca, sa = np.cos(yaw), np.sin(yaw)
    # 흔들림 마스크: 나무 안에서의 높이 비율(0 밑동 → 1 꼭대기)을 정점 알파에 저장.
    # 언리얼 머티리얼이 WorldPositionOffset 세기로 쓴다 (밑동은 고정, 꼭대기만 흔들림).
    sway = np.clip(v[:, 1] / max(hdef, 1e-6), 0, 1)**1.5
    v = v @ np.array([[ca, 0, sa], [0, 1, 0], [-sa, 0, ca]]).T + o[None, :]
    Vs.append(v); Fs.append(f+nv); Cs.append(c); As.append(sway); nv += len(v)
TV = np.vstack(Vs) - OFF; TF = np.vstack(Fs); TC = np.vstack(Cs); TA = np.concatenate(As)
# 흔들림 마스크는 TEXCOORD_0.x 에 넣는다 (아래 add_texcoord). 정점 알파는 255 고정.
# (09-11: 처음엔 '알파≠255 면 임포터가 정점색을 버린다'고 봤는데 틀린 진단이었음 — 회색의 원인은 내 색 값이 밝았던 것.
#  알파를 쓰지 않는 건 glTF 뷰어마다 알파 해석이 달라 안전하지 않기 때문)
trees = trimesh.Trimesh(vertices=TV, faces=TF, process=False,
                        visual=trimesh.visual.ColorVisuals(
                            vertex_colors=np.c_[TC, np.full(len(TC), 255)].astype(np.uint8)))
old = trimesh.load(f"{RT}/trees.glb", force="mesh")
print(f"나무 {len(man)}그루  LOD {lod_cnt}  면 {len(old.faces):,} → {len(trees.faces):,}")
print("  bounds 전", np.round(old.bounds, 1).tolist()); print("  bounds 후", np.round(trees.bounds, 1).tolist())
trees.export(f"{RT}/trees.glb")


def add_texcoord(path, uv):
    """GLB 에 TEXCOORD_0 (float32 vec2) 접근자를 덧붙인다. 정점 순서는 export 순서와 같다."""
    import struct
    b = open(path, "rb").read()
    jl = struct.unpack_from("<I", b, 12)[0]
    j = json.loads(b[20:20+jl].decode("utf-8"))
    bl = struct.unpack_from("<I", b, 20+jl)[0]
    bin_ = bytearray(b[28+jl:28+jl+bl])
    prim = j["meshes"][0]["primitives"][0]
    n = j["accessors"][prim["attributes"]["POSITION"]]["count"]
    assert len(uv) == n, (len(uv), n)
    while len(bin_) % 4: bin_.append(0)
    off = len(bin_)
    data = np.asarray(uv, np.float32).tobytes(); bin_ += data
    j["bufferViews"].append({"buffer": 0, "byteOffset": off, "byteLength": len(data)})
    j["accessors"].append({"bufferView": len(j["bufferViews"])-1, "componentType": 5126, "count": n, "type": "VEC2",
                           "min": [float(uv[:, 0].min()), float(uv[:, 1].min())], "max": [float(uv[:, 0].max()), float(uv[:, 1].max())]})
    prim["attributes"]["TEXCOORD_0"] = len(j["accessors"])-1
    j["buffers"][0]["byteLength"] = len(bin_)
    js = json.dumps(j, separators=(",", ":")).encode("utf-8")
    while len(js) % 4: js += b" "
    out = bytearray(b"glTF") + struct.pack("<II", 2, 12+8+len(js)+8+len(bin_))
    out += struct.pack("<II", len(js), 0x4E4F534A) + js + struct.pack("<II", len(bin_), 0x004E4942) + bin_
    open(path, "wb").write(out)


# trimesh 는 export 시 정점 순서를 유지한다(process=False). 재로드해서 위치가 같은지 확인한 뒤 UV 추가.
_chk = trimesh.load(f"{RT}/trees.glb", force="mesh")
assert np.allclose(np.asarray(_chk.vertices), TV, atol=1e-4), "export 정점 순서 변경됨"
add_texcoord(f"{RT}/trees.glb", np.c_[TA, np.zeros(len(TA))])
_chk = trimesh.load(f"{RT}/trees.glb", force="mesh")
print("  TEXCOORD_0.x(흔들림 마스크) min/max", float(np.asarray(_chk.visual.uv)[:, 0].min()) if hasattr(_chk.visual, "uv") and _chk.visual.uv is not None else "uv 없음(trimesh 는 텍스처 없으면 uv 안 읽음)")


# ═══════════════════════ 기와집 v2 — 기존 house.glb 에서 배치 복원
hv = np.asarray(_h1.vertices)
assert len(hv) % 14 == 0
# 색은 전부 원화에서 뽑은 먹 팔레트(records/ink_palette.json — 마스크된 원화의 밝기 분위별 평균)로 통일 (09-11 요청: 산맥과 같은 색)
PAL = json.load(open("assets/inwangjesaekdo/records/ink_palette.json", encoding="utf-8"))
JIN  = lin(np.array(PAL["진묵(0-5%)"], float))      # (56,52,52)
JUNG = lin(np.array(PAL["중묵(5-25%)"], float))     # (71,67,65)
DAM  = lin(np.array(PAL["담묵(25-55%)"], float))    # (108,101,96)
YEOT = lin(np.array(PAL["옅은담묵(55-80%)"], float)) # (157,146,131)
ROOF = DAM; EAVE = JIN; RIDGE = JIN; POST = JUNG; WALL = YEOT; STONE = YEOT


def hall2(w, dpt, wall, roof_h, eave):
    V, Fc, C = [], [], []

    def box(x0, x1, y0, y1, z0, z1, col):
        o = len(V)
        V.extend([[x0, y0, z0], [x1, y0, z0], [x1, y0, z1], [x0, y0, z1],
                  [x0, y1, z0], [x1, y1, z0], [x1, y1, z1], [x0, y1, z1]]); C.extend([col]*8)
        Fc.extend([[o+a, o+b, o+c] for a, b, c in
                   [(0,1,5),(0,5,4),(1,2,6),(1,6,5),(2,3,7),(2,7,6),(3,0,4),(3,4,7),(4,5,6),(4,6,7),(1,0,3),(1,3,2)]])
    hw, hd = w/2, dpt/2
    base_h = max(0.5, wall*0.18)
    box(-hw-eave*0.7, hw+eave*0.7, -base_h, 0, -hd-eave*0.7, hd+eave*0.7, STONE)   # 기단
    box(-hw*0.92, hw*0.92, 0, wall, -hd*0.85, hd*0.85, WALL)                        # 벽 (안쪽으로 들어감)
    pr = max(0.12, w*0.012)                                                          # 기둥
    nx = max(2, int(round(w/3.0))+1)
    for i in range(nx):
        x = -hw + (2*hw)*i/(nx-1)
        for zz in (-hd, hd):
            o = len(V)
            for a in ring(6):
                V.append([x+pr*np.cos(a), 0, zz+pr*np.sin(a)]); C.append(POST)
            for a in ring(6):
                V.append([x+pr*np.cos(a), wall, zz+pr*np.sin(a)]); C.append(POST)
            for k in range(6):
                j = (k+1) % 6
                Fc += [[o+k, o+j, o+6+j], [o+k, o+6+j, o+6+k]]
    # 지붕: 처마 곡선 — 테두리를 한 바퀴 돌며 모서리 쪽이 들리고 바깥으로 더 뻗는다
    ew, ed = hw+eave, hd+eave
    N = 7                                                    # 변당 분할
    per = []                                                 # (x, z, u: 0~1 변 위치, side)
    for i in range(N):  per.append((-ew + 2*ew*i/N, -ed, "front"))
    for i in range(N):  per.append(( ew, -ed + 2*ed*i/N, "right"))
    for i in range(N):  per.append(( ew - 2*ew*i/N,  ed, "back"))
    for i in range(N):  per.append((-ew,  ed - 2*ed*i/N, "left"))
    lift = roof_h*0.22
    rl = hw*0.55                                             # 용마루 반길이
    ry = wall + roof_h
    o = len(V)
    M = len(per)
    for (x, z, side) in per:
        cx = abs(x)/ew; cz = abs(z)/ed
        k = max(cx, cz)**3                                   # 모서리에서 급히 들림
        s = 1 + 0.06*k
        V.append([x*s, wall - roof_h*0.12 + lift*k, z*s]); C.append(EAVE)      # 처마 테두리는 먹선
    ridge = []
    for (x, z, side) in per:                                 # 각 처마점이 붙는 용마루 위 점
        rx = float(np.clip(x, -rl, rl)) if side in ("front", "back") else (rl if x > 0 else -rl)
        ridge.append([rx, ry, 0.0])
    ro = len(V)
    for r_ in ridge:
        V.append(r_); C.append(ROOF)
    # 처마 먹선은 얇은 띠로만: 처마 테두리(먹) → 안쪽 테두리(담묵, 지붕면 색) → 용마루(담묵)
    oi = len(V)
    for k_, (x, z, side) in enumerate(per):
        e = V[o+k_]; r_ = ridge[k_]
        V.append([e[0]*0.9 + r_[0]*0.1, e[1]*0.9 + r_[1]*0.1, e[2]*0.9 + r_[2]*0.1]); C.append(ROOF)
    for i in range(M):
        j = (i+1) % M
        Fc += [[o+i, o+j, oi+j], [o+i, oi+j, oi+i], [o+j, o+i, oi+i], [o+j, oi+i, oi+j]]        # 처마 띠 (양면)
        Fc += [[oi+i, oi+j, ro+j], [oi+i, ro+j, ro+i], [oi+j, oi+i, ro+i], [oi+j, ro+i, ro+j]]  # 지붕면 (양면)
    box(-rl-eave*0.3, rl+eave*0.3, ry-roof_h*0.05, ry+roof_h*0.08, -w*0.02, w*0.02, RIDGE)  # 용마루
    return np.array(V, float), np.array(Fc, int), np.array(C, float)


HV, HF, HC, nv = [], [], [], 0
for b in range(len(hv)//14):
    q = hv[b*14:(b+1)*14]
    base = q[0:4]; eaveq = q[8:12]; ridge = q[12:14]
    center = base.mean(axis=0)
    wx = eaveq[1]-eaveq[0]; wz = eaveq[3]-eaveq[0]
    ew = np.linalg.norm(wx)/2; ed = np.linalg.norm(wz)/2
    hw = np.linalg.norm(base[1]-base[0])/2; hd = np.linalg.norm(base[3]-base[0])/2
    eave = ew-hw; wall = float(q[4][1]-q[0][1]); roof_h = float(ridge[0][1]-q[4][1])
    ux = wx/np.linalg.norm(wx); uz = wz/np.linalg.norm(wz)
    v, f, c = hall2(hw*2, hd*2, wall, roof_h, eave)
    v = v[:, 0:1]*ux[None, :] + v[:, 1:2]*np.array([[0, 1, 0]]) + v[:, 2:3]*uz[None, :] + center[None, :]
    HV.append(v); HF.append(f+nv); HC.append(c); nv += len(v)
    print(f"기와집 {b+1}: 폭 {hw*2:.1f} m 깊이 {hd*2:.1f} m 벽 {wall:.1f} m 지붕 {roof_h:.1f} m 처마 {eave:.2f} m")
HVs = np.vstack(HV); HFs = np.vstack(HF); HCs = np.vstack(HC)
house = trimesh.Trimesh(vertices=HVs, faces=HFs, process=False,
                        visual=trimesh.visual.ColorVisuals(
                            vertex_colors=np.c_[HCs, np.full(len(HCs), 255)].astype(np.uint8)))
print(f"기와집 면 {len(_h1.faces)} → {len(house.faces)}")
print("  bounds 전", np.round(_h1.bounds, 1).tolist()); print("  bounds 후", np.round(house.bounds, 1).tolist())
house.export(f"{RT}/house.glb")
print("완료 →", f"{RT}/trees.glb", f"{RT}/house.glb")
