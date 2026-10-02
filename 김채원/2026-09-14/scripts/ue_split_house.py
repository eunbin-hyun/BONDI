# -*- coding: utf-8 -*-
"""
집 2채를 따로 움직일 수 있게 분리 배치 (2026-09-14)
====================================================
house_ink.glb 한 덩어리를 house_ink_a(작은 채) · house_ink_b(큰 채) 로 잘라 각각 별도 액터로 놓는다.
피벗은 채마다 '발밑 한가운데' 라서 이동·회전·크기 조절이 그 채 기준으로 자연스럽다.

자리 맞추기: 좌표계를 직접 가정하지 않고, 지금 레벨에 있는 house_ink 메시의 로컬 바운드와
   원본 glb 바운드(build_house_split.py 가 기록)를 맞춰 축 대응·부호·배율을 **계산해서** 쓴다.
   그 결과를 로그에 찍고, 배치 후 두 채의 합친 월드 바운드가 원래 house_ink 와 같은지 대조한다.

사용법 (L_Inwang 열린 상태, 언리얼 콘솔):
    py "C:/KCW_SSAFY/특화/S15P21C201/김채원/2026-09-12/scripts/ue_split_house.py"
확인 지표:
    '축 대응: UE X ← glb ±x …  맞춤 오차 … cm'   (오차 1 cm 미만이어야 함)
    '>>> 배치 확인: 합친 바운드 차이 중심 … cm / 크기 … cm'  (둘 다 몇 cm 이내)
그 뒤: 아웃라이너 Inwang/House 에 house_ink_small · house_ink_big 두 개. 원본 house_ink 는 숨김.
되돌리기: RESTORE = True 로 한 번 더 실행하면 원본 house_ink 를 다시 보이게 하고 분리본을 지운다.
"""
import os, json, unreal

RESTORE = False
RT = r"C:\Users\SSAFY\Desktop\SSAFY_2학기\02_특화 프로젝트\특화PJT_\landscape_to_3D\Claude outputs\VR_inwangjesaekdo_v0.11\inwangjesaekdo_VR_v0.11\runtime"
SPLIT_JSON = os.path.join(os.path.dirname(RT), "records", "house_split.json")
PKG = "/Game/Museum/Inwang"
SRC_LABEL = "house_ink"
MAT_NAME = "M_InwangHouseInk"

EAL = unreal.EditorAssetLibrary; TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


def log(m): unreal.log("[INWANG] %s" % m)


def bbox(mesh):
    """스태틱메시 로컬 바운드 (min, max) — API 이름이 버전마다 달라 둘 다 시도"""
    try:
        b = mesh.get_bounding_box(); return (b.min.x, b.min.y, b.min.z), (b.max.x, b.max.y, b.max.z)
    except Exception: pass
    b = mesh.get_bounds(); o, e = b.origin, b.box_extent
    return (o.x - e.x, o.y - e.y, o.z - e.z), (o.x + e.x, o.y + e.y, o.z + e.z)


A = {a.get_actor_label(): a for a in sub.get_all_level_actors()}
for lab in ("house_ink_small", "house_ink_big"):
    if lab in A: sub.destroy_actor(A[lab]); log("기존 %s 제거" % lab)
src = A.get(SRC_LABEL)
if src is None: log("!! 레벨에 '%s' 액터 없음 — 현재 레벨이 L_Inwang 인지 확인" % SRC_LABEL); raise SystemExit

if RESTORE:
    src.set_is_temporarily_hidden_in_editor(False); src.set_actor_hidden_in_game(False)
    try: src.set_editor_property("hidden", False)
    except Exception: pass
    log(">>> 원본 house_ink 복구 완료, 분리본 제거. 레벨 저장 %s" % LES.save_current_level()); raise SystemExit

if not os.path.exists(SPLIT_JSON): log("!! %s 없음" % SPLIT_JSON); raise SystemExit
info = json.load(open(SPLIT_JSON, encoding="utf-8"))
g_lo, g_hi = info["source_bounds_min"], info["source_bounds_max"]

# ── 1) glb → 언리얼 로컬 좌표 대응 계산 (축 순서·부호·배율을 데이터로 확정)
comp0 = src.get_component_by_class(unreal.StaticMeshComponent)
if comp0 is None or comp0.static_mesh is None: log("!! house_ink 메시 없음"); raise SystemExit
u_lo, u_hi = bbox(comp0.static_mesh)
g_size = [g_hi[i] - g_lo[i] for i in range(3)]
u_size = [u_hi[i] - u_lo[i] for i in range(3)]
scale = sum(u_size) / max(sum(g_size), 1e-9)                       # 대개 100 (m → cm)
axis, sign, err = [], [], []
for i in range(3):
    j = min(range(3), key=lambda k: abs(u_size[i] - g_size[k] * scale))
    e_pos = abs(u_lo[i] - g_lo[j] * scale) + abs(u_hi[i] - g_hi[j] * scale)
    e_neg = abs(u_lo[i] + g_hi[j] * scale) + abs(u_hi[i] + g_lo[j] * scale)
    s = 1.0 if e_pos <= e_neg else -1.0
    axis.append(j); sign.append(s); err.append(min(e_pos, e_neg))
log("축 대응: %s   배율 %.2f   맞춤 오차 %.2f cm (1 미만이어야 함)" %
    (", ".join("UE %s ← glb %s%s" % ("XYZ"[i], "+" if sign[i] > 0 else "-", "xyz"[axis[i]]) for i in range(3)), scale, max(err)))
if max(err) > 1.0: log("   !! 오차가 큼 — 원본 glb 와 언리얼 에셋이 다른 판일 수 있음 (ue_reimport_apply.py 먼저)")


def to_ue_local(p):
    return unreal.Vector(sign[0] * scale * p[axis[0]], sign[1] * scale * p[axis[1]], sign[2] * scale * p[axis[2]])


def to_world(v):
    t = src.get_actor_transform()
    try: return unreal.MathLibrary.transform_location(t, v)
    except Exception:
        s, l = t.scale3d, t.translation
        return unreal.Vector(l.x + s.x * v.x, l.y + s.y * v.y, l.z + s.z * v.z)


# ── 2) 임포트 + 배치
mat = EAL.load_asset("%s/%s" % (PKG, MAT_NAME))
rot = src.get_actor_rotation(); sc = src.get_actor_scale3d()
made = []
for key in ("a", "b"):
    d = info["buildings"][key]
    path = os.path.join(RT, d["file"])
    if not os.path.exists(path): log("!! 원본 없음: %s" % path); continue
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", path); t.set_editor_property("destination_path", "%s/%s" % (PKG, d["file"].split(".")[0]))
    t.set_editor_property("replace_existing", True); t.set_editor_property("automated", True); t.set_editor_property("save", True)
    TOOLS.import_asset_tasks([t])
    mesh = None
    for p in [str(x) for x in t.get_editor_property("imported_object_paths")]:
        o = EAL.load_asset(p.split(".")[0] if "." in p.rsplit("/", 1)[-1] else p)
        if isinstance(o, unreal.StaticMesh): mesh = o; break
    if mesh is None:
        for p in EAL.list_assets("%s/%s" % (PKG, d["file"].split(".")[0]), recursive=True, include_folder=False):
            o = EAL.load_asset(p)
            if isinstance(o, unreal.StaticMesh): mesh = o
    if mesh is None: log("!! %s 임포트 실패" % d["file"]); continue
    loc = to_world(to_ue_local(d["pivot_in_source"]))
    a = sub.spawn_actor_from_object(mesh, loc, rot)
    a.set_actor_scale3d(sc); a.set_actor_label(d["label"]); a.set_folder_path("Inwang/House")
    a.set_is_temporarily_hidden_in_editor(False); a.set_actor_hidden_in_game(False)
    try: a.set_editor_property("hidden", False)
    except Exception: pass
    c = a.get_component_by_class(unreal.StaticMeshComponent)
    if mat is not None:
        for s_ in range(c.get_num_materials()): c.set_material(s_, mat)
    made.append(a)
    log("  %-16s 면 %d  위치 (%.0f, %.0f, %.0f)  머티리얼 %s" % (d["label"], mesh.get_num_triangles(0), loc.x, loc.y, loc.z, mat.get_name() if mat else "!! 없음"))

# ── 3) 대조: 두 채 합친 바운드 vs 원본 house_ink
if len(made) == 2:
    o0, e0 = src.get_actor_bounds(False)
    lo = [1e18] * 3; hi = [-1e18] * 3
    for a in made:
        o, e = a.get_actor_bounds(False)
        for i, (oc, ec) in enumerate(((o.x, e.x), (o.y, e.y), (o.z, e.z))):
            lo[i] = min(lo[i], oc - ec); hi[i] = max(hi[i], oc + ec)
    cen = [(lo[i] + hi[i]) / 2 for i in range(3)]; siz = [hi[i] - lo[i] for i in range(3)]
    dc = [abs(cen[0] - o0.x), abs(cen[1] - o0.y), abs(cen[2] - o0.z)]
    ds = [abs(siz[0] - e0.x * 2), abs(siz[1] - e0.y * 2), abs(siz[2] - e0.z * 2)]
    log(">>> 배치 확인: 합친 바운드 차이  중심 (%.0f, %.0f, %.0f) cm / 크기 (%.0f, %.0f, %.0f) cm  — 몇 cm 이내여야 맞음"
        % (dc[0], dc[1], dc[2], ds[0], ds[1], ds[2]))
    src.set_is_temporarily_hidden_in_editor(True); src.set_actor_hidden_in_game(True)
    try: src.set_editor_property("hidden", True)
    except Exception: pass
    log("원본 house_ink 숨김 (되돌리려면 RESTORE = True)")
else:
    log("!! 두 채를 다 못 놓아서 원본은 그대로 둠")
log("레벨 저장 %s" % LES.save_current_level())
