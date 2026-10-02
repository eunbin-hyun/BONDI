"""
명세 19.3 좌표·단위 계약 검사기

핵심 설계 원칙 — 추측하지 않는다.
  "가장 긴 축이 세로일 것" 같은 휴리스틱은 토기에는 맞지만 경관·검·관모에는 틀린다.
  그래서 이 검사기는 추측이 필요 없는 것만 본다.

  A. 포맷        — glTF 2.0 GLB 인가                      (객관)
  B. 단계 정합   — 같은 유물의 ①②③ bbox·pivot 이 같은가  (객관, 19.3 핵심 조항)
  C. 단위 사고   — 단계끼리 크기가 10배 이상 어긋나는가    (객관, mm/m 혼용 탐지)
  D. pivot       — 원점이 bbox 바닥 중심인가              (상하축을 선언받아 판정)

사용:
  python check_coordinate_contract.py <assets경로>              # 유물 모드
  python check_coordinate_contract.py <assets경로> --mode scene # 경관·다파트 모드
  옵션: --up Z|Y  (기본 Z)

필요: pip install trimesh numpy
"""
import sys, os, glob, json, numpy as np

try:
    import trimesh
except ImportError:
    sys.exit("trimesh가 필요합니다:  pip install trimesh")

args = [a for a in sys.argv[1:] if not a.startswith("--")]
opts = sys.argv[1:]
ROOT = args[0] if args else "assets"
MODE = "scene" if "--mode" in opts and opts[opts.index("--mode")+1] == "scene" else "artifact"
UP = "XYZ".index(opts[opts.index("--up")+1].upper()) if "--up" in opts else 2
EXT = (".glb", ".gltf", ".obj", ".fbx", ".ply", ".stl")
OTHER = [i for i in range(3) if i != UP]


def bbox(path):
    m = trimesh.load(path, force="mesh")
    V = np.asarray(m.vertices, float)
    return V.min(0), V.max(0), len(m.faces)


def group_of(path):
    """유물 단위로 묶는다:  assets/<id>/<layer>/<file>  →  (<id>, <layer>)"""
    rel = os.path.relpath(path, ROOT).replace("\\", "/").split("/")
    return (rel[0], rel[1]) if len(rel) >= 3 else (rel[0], "")


files = sorted(f for f in glob.glob(f"{ROOT}/**/*", recursive=True)
               if f.lower().endswith(EXT))
if not files:
    sys.exit(f"{ROOT} 아래에 3D 파일이 없습니다. dev 브랜치를 받아서 실행하세요.")

print(f"명세 19.3 좌표·단위 계약 검사   대상 {len(files)}개   "
      f"모드 {MODE}   상하축 {'XYZ'[UP]}\n")

groups, rows = {}, []
for f in files:
    try:
        lo, hi, tri = bbox(f)
    except Exception as e:
        rows.append(dict(f=f, err=str(e))); continue
    r = dict(f=f, lo=lo, hi=hi, size=hi-lo, tri=tri, err=None)
    rows.append(r)
    groups.setdefault(group_of(f), []).append(r)

W = max(len(os.path.relpath(r["f"], ROOT)) for r in rows) + 2
print(f"{'파일':<{W}}{'면수':>9}   크기 X x Y x Z (선언 단위)")
print("-"*(W+46))
for r in rows:
    n = os.path.relpath(r["f"], ROOT)
    if r["err"]:
        print(f"{n:<{W}}{'—':>9}   읽기 실패: {r['err']}"); continue
    print(f"{n:<{W}}{r['tri']:>9,}   " + " x ".join(f"{v:>9.3f}" for v in r["size"]))

fails = []

# ── A. 포맷
for r in rows:
    if r["err"]:
        fails.append((r["f"], "읽기 실패", r["err"])); continue
    if not r["f"].lower().endswith(".glb"):
        fails.append((r["f"], "A 포맷",
                      "19.3 교환 포맷은 glTF 2.0 GLB. "
                      "OBJ 임포터는 상하축 변환을 해주지 않아 앱 보정이 강제된다"))

# ── B/C. 같은 묶음 안에서의 정합
print("\n" + "="*(W+46))
print("B. 단계 정합 — 19.3 \"①②③이 같은 좌표·같은 pivot·같은 크기여야 한다\"")
print("="*(W+46))
# artifact 모드: 같은 폴더 = 같은 유물의 단계들
# scene 모드  : 파트끼리는 크기가 달라도 정상이므로, 같은 이름의 파일끼리만 비교한다
#               (master/terrain_real  vs  runtime/terrain_real)
if MODE == "scene":
    cmpg = {}
    for r in rows:
        if r["err"]:
            continue
        aid = group_of(r["f"])[0]
        cmpg[(aid, os.path.basename(r["f"]))] = cmpg.get((aid, os.path.basename(r["f"])), []) + [r]
    groups_cmp = cmpg
    print("  (scene 모드: 같은 이름의 파트끼리 master vs runtime 비교)")
else:
    groups_cmp = groups

for key, g in sorted(groups_cmp.items()):
    g = [r for r in g if not r["err"]]
    if len(g) < 2:
        continue
    S = np.array([r["size"] for r in g])
    L = np.array([r["lo"] for r in g])
    ref = S.max(0)
    ratio = S.max(0) / np.maximum(S.min(0), 1e-9)
    lo_spread = L.max(0) - L.min(0)
    tol = 0.02 * np.maximum(ref, 1e-9)
    scale_bad = ratio.max() > 10
    align_bad = np.any(lo_spread > tol)
    tag = "  ".join(key).strip()
    if scale_bad:
        print(f"  [FAIL] {tag}: 단계 간 크기가 최대 {ratio.max():.0f}배 어긋남 → mm/m 단위 혼용 의심")
        fails.append((tag, "C 단위", f"단계 간 크기 비 {ratio.max():.0f}배"))
    elif align_bad and MODE == "artifact":
        print(f"  [FAIL] {tag}: 단계별 원점이 최대 {lo_spread.max():.3f} 어긋남 → 토글할 때 유물이 튄다")
        fails.append((tag, "B 정합", f"원점 편차 {lo_spread.max():.3f}"))
    else:
        note = " (scene 모드: 파트별 위치 차이는 정상)" if MODE == "scene" else ""
        print(f"  [PASS] {tag}: 크기 비 {ratio.max():.2f}배, 원점 편차 {lo_spread.max():.4f}{note}")

# ── D. pivot
print("\n" + "="*(W+46))
print(f"D. pivot — 원점이 bbox 바닥({'XYZ'[UP]} 최소) 중심인가")
print("="*(W+46))
if MODE == "scene":
    targets = []
    for k, grp in sorted(groups.items()):
        ok = [r for r in grp if not r["err"]]
        if ok:
            targets.append((f"{k[0]}/{k[1]}",
                            np.array([r["lo"] for r in ok]).min(0),
                            np.array([r["hi"] for r in ok]).max(0)))
else:
    targets = [(os.path.relpath(r["f"], ROOT), r["lo"], r["hi"])
               for r in rows if not r["err"]]
for name, lo, hi in targets:
    size = hi - lo
    up_off = abs(lo[UP])
    up_tol = max(0.01 * max(size[UP], 1e-9), 1e-4)
    ctr = (lo + hi) / 2
    xy_off = float(np.hypot(ctr[OTHER[0]], ctr[OTHER[1]]))
    xy_tol = 0.02 * max(size[OTHER[0]], size[OTHER[1]], 1e-9)
    bad = []
    if up_off > up_tol:
        bad.append(f"바닥이 원점에서 {lo[UP]:+.3f} 떨어짐")
    if xy_off > xy_tol:
        bad.append(f"수평 중심이 {xy_off:.3f} 벗어남")
    print(("  [PASS] " if not bad else "  [FAIL] ") + name + ("" if not bad else "  " + ", ".join(bad)))
    for b in bad:
        fails.append((name, "D pivot", b))

# ── 결론
print("\n" + "="*(W+46))
if not fails:
    print("전부 통과.")
    print("→ 이 자산들에 대해서는 MeshScale·MeshRollFix 가 전부 1.0 / 0 이 된다.")
    print("→ 필드를 제거하고, 이 스크립트를 자산 검사(FR-OPS-002)로 편입해 재발을 막을 수 있다.")
else:
    print(f"위반 {len(fails)}건\n")
    for name, kind, msg in fails:
        print(f"  [{kind}] {os.path.relpath(name, ROOT) if os.path.exists(name) else name}\n      {msg}")
    print("\n명세 19.3: \"어긋난 자산을 앱에서 보정하지 않는다. … 정렬이 어긋나면 자산을 다시 내보낸다.\"")
    print("→ 위 자산이 재내보내기 대상이며, 그때까지 MeshScale·MeshRollFix 를 남겨 둔다.")
