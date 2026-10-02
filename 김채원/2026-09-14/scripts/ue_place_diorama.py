# -*- coding: utf-8 -*-
"""
산수분경(디오라마) 배치 + 표석 — 손으로 짚어 이동 (2026-09-14)
================================================================
관람자 앞 허리~가슴 높이에 축소 모형을 띄우고, 그 위의 표석 4개(전경·중경·후경·입구) 를 짚으면 그 자리로 이동한다.
모형은 실제 지형과 **같은 방향으로** 놓는다 (모형에서 저쪽 = 실제로도 저쪽) — 머릿속 지도가 맞아떨어지게.

이 스크립트가 하는 일
  1) diorama.glb 임포트 — 지형·집·안내판·나무 4덩어리를 **같은 원점**에 배치 (Diorama_<이름>), 각자 Unlit 텍스처 머티리얼
  2) 표석 위치에 작은 구 4개 배치 — DioMark_전경 / DioMark_중경 / DioMark_후경 / DioMark_입구
     BP_DioMark 가 있으면 그 블루프린트로, 없으면 미리보기용 구 메시로.
  3) 표석마다 목적지 월드 좌표·yaw 를 로그로 찍는다 (BP 변수에 넣을 값)

좌표 변환은 지형 액터 바운드 ↔ 원본 glb 바운드로 계수를 구하고, 부호는 기준 액터 두 개의 좌표 차이로 확정한다.

사용법 (L_Inwang 열린 상태, 언리얼 콘솔):
    py "C:/KCW_SSAFY/특화/S15P21C201/김채원/2026-09-14/scripts/ue_place_diorama.py"
확인 지표: '기준점 대조 … 오차 … cm' (몇 십 cm 이내), '표석 4개 배치', 각 표석의 '목적지 (x, y, z) yaw'

블루프린트 순서표 — BP_DioMark (한 번만, 10분)
  1. /Game/Museum/Inwang 우클릭 → 블루프린트 클래스 → 부모 Actor → 이름 BP_DioMark
  2. 컴포넌트:
       + Static Mesh : Sphere(엔진),  Scale 0.02,  Material M_InwangMark,  Collision NoCollision
       + Sphere Collision : Sphere Radius 4.0,  Collision Presets OverlapAllDynamic,  Generate Overlap Events 체크
  3. 변수 (전부 '인스턴스 편집 가능' 체크):
       DestLoc  : Vector   — 목적지 월드 좌표 (아래 로그의 값)
       DestYaw  : Float    — 목적지에서 바라볼 방위
  4. 이벤트 그래프:
       On Component Begin Overlap (Sphere Collision)
       → Get Display Name (Other Comp) → Contains "Capsule" → Branch
            False(=캡슐이 아니면, 즉 손·컨트롤러면) →
            Do Once (Reset 은 Delay 0.6 초 뒤)
            → Get Player Pawn → Set Actor Location (New Location = DestLoc, Sweep 해제)
            → Get Player Controller → Set Control Rotation (Pitch 0, Yaw = DestYaw, Roll 0)
     ※ 'Capsule 아니면' 조건이 핵심 — 안 넣으면 걸어가다 몸이 스쳐도 순간이동한다.
     ※ 손 트래킹이 꺼져 있으면 컨트롤러 메시로도 그대로 동작한다 (둘 다 캡슐이 아님).
  5. 컴파일 → 저장 → 이 스크립트를 다시 실행하면 구 대신 BP 로 배치되고 변수까지 채워진다.
"""
import os, json, unreal

DIO_FORWARD_CM = 55.0     # PlayerStart 앞으로 이만큼
DIO_HEIGHT_CM = 105.0     # 바닥에서 모형 밑판까지 (허리~가슴)
MARK_SCALE = 0.02         # 표석 구 크기 (엔진 Sphere 100 cm → 2 cm)
EYE_DROP_M = 1.6          # viewpoints 의 eye_y 는 눈높이 → 폰 발밑으로 내림

RT = r"C:\Users\SSAFY\Desktop\SSAFY_2학기\02_특화 프로젝트\특화PJT_\landscape_to_3D\Claude outputs\VR_inwangjesaekdo_v0.11\inwangjesaekdo_VR_v0.11\runtime"
RECD = os.path.join(os.path.dirname(RT), "records")
PKG = "/Game/Museum/Inwang"

EAL = unreal.EditorAssetLibrary; ML = unreal.MaterialEditingLibrary; TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem); LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
reg = unreal.AssetRegistryHelpers.get_asset_registry()


def log(m): unreal.log("[INWANG] %s" % m)


A = {x.get_actor_label(): x for x in sub.get_all_level_actors()}

# ── 좌표 변환 계수 (지형 기준) ──────────────────────────────────
EV = json.load(open(os.path.join(RECD, "terrain_evidence.json"), encoding="utf-8"))
g_lo = {"x": EV["x_min_m"], "z": EV["z_min_m"]}; g_hi = {"x": EV["x_max_m"], "z": EV["z_max_m"]}
ter = A.get("terrain_jeong")
if ter is None: log("!! terrain_jeong 액터 없음"); raise SystemExit
o, e = ter.get_actor_bounds(False)
w_lo = [o.x - e.x, o.y - e.y, o.z - e.z]; w_hi = [o.x + e.x, o.y + e.y, o.z + e.z]
g_size = {k: g_hi[k] - g_lo[k] for k in ("x", "z")}
pair = {i: min(g_size, key=lambda k: abs((w_hi[i] - w_lo[i]) / 100.0 - g_size[k])) for i in (0, 1)}
if pair[0] == pair[1]: log("!! 축 대응 겹침"); raise SystemExit
sign = {0: 1.0, 1: 1.0}
have = [(n, v) for n, v in EV.get("landmarks_glb_m", {}).items() if n in A]
if len(have) >= 2:
    (n1, v1), (n2, v2) = have[0], have[1]
    p1, p2 = A[n1].get_actor_location(), A[n2].get_actor_location()
    dw = [p2.x - p1.x, p2.y - p1.y]; dg = {"x": v2[0] - v1[0], "z": v2[2] - v1[2]}
    for i in (0, 1):
        if abs(dg[pair[i]]) >= 1.0: sign[i] = 1.0 if dw[i] * dg[pair[i]] > 0 else -1.0
KC = {}
for i in (0, 1):
    key = pair[i]
    k = (w_hi[i] - w_lo[i]) / ((g_size[key]) if sign[i] > 0 else (-g_size[key]))
    KC[i] = (k, w_lo[i] - k * (g_lo[key] if sign[i] > 0 else g_hi[key]), key)
log("축 대응: 월드 X ← glb %s(%+.0f), 월드 Y ← glb %s(%+.0f)" % (pair[0], sign[0], pair[1], sign[1]))
for n, v in have:
    p = A[n].get_actor_location()
    pr = [KC[i][0] * (v[0] if KC[i][2] == "x" else v[2]) + KC[i][1] for i in (0, 1)]
    log("기준점 대조 %-18s 예측 (%.0f, %.0f) vs 실제 (%.0f, %.0f)  오차 (%.0f, %.0f) cm" % (n, pr[0], pr[1], p.x, p.y, abs(pr[0] - p.x), abs(pr[1] - p.y)))


def to_world(gx, gy, gz):
    """glb(m) → 월드(cm). Z 는 지형 액터의 높이 대응으로 (gY × 100 + 오프셋)"""
    xy = [KC[i][0] * (gx if KC[i][2] == "x" else gz) + KC[i][1] for i in (0, 1)]
    return unreal.Vector(xy[0], xy[1], gy * 100.0)


# ── 1) 모형 임포트 + 배치 ──────────────────────────────────────
src = os.path.join(RT, "diorama.glb")
if not os.path.exists(src): log("!! %s 없음" % src); raise SystemExit
t = unreal.AssetImportTask()
t.set_editor_property("filename", src); t.set_editor_property("destination_path", PKG + "/diorama")
t.set_editor_property("replace_existing", True); t.set_editor_property("automated", True); t.set_editor_property("save", True)
TOOLS.import_asset_tasks([t])
# v2: diorama.glb 은 지형·집·안내판·나무 4덩어리 → 임포트된 스태틱메시를 전부 모은다
meshes = []
for p_ in [str(x) for x in t.get_editor_property("imported_object_paths")]:
    ob = EAL.load_asset(p_.split(".")[0] if "." in p_.rsplit("/", 1)[-1] else p_)
    if isinstance(ob, unreal.StaticMesh): meshes.append(ob)
if not meshes:
    for p_ in EAL.list_assets(PKG + "/diorama", recursive=True, include_folder=False):
        ob = EAL.load_asset(p_)
        if isinstance(ob, unreal.StaticMesh): meshes.append(ob)
if not meshes: log("!! diorama 메시 임포트 실패"); raise SystemExit
log("모형 덩어리 %d개: %s" % (len(meshes), ", ".join(m_.get_name() for m_ in meshes)))


def mesh_tex(sm):
    try:
        for smat in sm.get_editor_property("static_materials"):
            mi = smat.get_editor_property("material_interface")
            if mi is None: continue
            for tp in mi.get_editor_property("texture_parameter_values"):
                tv = tp.get_editor_property("parameter_value")
                if isinstance(tv, unreal.Texture2D): return tv
    except Exception: pass
    return None


def unlit_tex_material(name, tex, masked=False):
    mp = "%s/%s" % (PKG, name)
    if EAL.does_asset_exist(mp): mt = EAL.load_asset(mp); ML.delete_all_material_expressions(mt)
    else: mt = TOOLS.create_asset(name, PKG, unreal.Material, unreal.MaterialFactoryNew())
    mt.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    mt.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED if masked else unreal.BlendMode.BLEND_OPAQUE)
    mt.set_editor_property("two_sided", masked)
    if tex is not None:
        ts = ML.create_material_expression(mt, unreal.MaterialExpressionTextureSample, -400, 0)
        ts.set_editor_property("texture", tex)
        ok = ML.connect_material_property(ts, "RGB", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        if masked: ML.connect_material_property(ts, "A", unreal.MaterialProperty.MP_OPACITY_MASK)
    else:
        c3 = ML.create_material_expression(mt, unreal.MaterialExpressionConstant3Vector, -400, 0)
        c3.set_editor_property("constant", unreal.LinearColor(0.73, 0.67, 0.59, 1.0))
        ok = ML.connect_material_property(c3, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    ML.recompile_material(mt); EAL.save_asset(mp)
    log("  %-26s Emissive %s  %s%s" % (name, ok, tex.get_name() if tex else "단색", " (마스크)" if masked else ""))
    return mt


# 표석용 단색(주황) 머티리얼
mp = "%s/M_InwangMark" % PKG
if EAL.does_asset_exist(mp): mark_mat = EAL.load_asset(mp); ML.delete_all_material_expressions(mark_mat)
else: mark_mat = TOOLS.create_asset("M_InwangMark", PKG, unreal.Material, unreal.MaterialFactoryNew())
mark_mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
c3 = ML.create_material_expression(mark_mat, unreal.MaterialExpressionConstant3Vector, -400, 0)
c3.set_editor_property("constant", unreal.LinearColor(1.0, 0.62, 0.18, 1.0))
log("  M_InwangMark Emissive %s (주황)" % ML.connect_material_property(c3, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR))
ML.recompile_material(mark_mat); EAL.save_asset(mp)

for lab in list(A):
    if lab.startswith("Diorama_") or lab.startswith("DioMark_"): sub.destroy_actor(A[lab])
ps = next((x for x in sub.get_all_level_actors() if isinstance(x, unreal.PlayerStart)), None)
if ps is None: log("!! PlayerStart 없음"); raise SystemExit
p0 = ps.get_actor_location()
import math
yaw0 = ps.get_actor_rotation().yaw
base = unreal.Vector(p0.x + math.cos(math.radians(yaw0)) * DIO_FORWARD_CM,
                     p0.y + math.sin(math.radians(yaw0)) * DIO_FORWARD_CM,
                     p0.z - 90.0 + DIO_HEIGHT_CM)
for sm in meshes:
    nm = sm.get_name()
    masked = "tree" in nm.lower()
    mt = unlit_tex_material("M_InwangDio_%s" % nm, mesh_tex(sm), masked)
    a_ = sub.spawn_actor_from_object(sm, base, unreal.Rotator(0, 0, 0))      # 실제 지형과 같은 방향, 같은 원점
    a_.set_actor_label("Diorama_%s" % nm); a_.set_folder_path("Inwang/Diorama")
    c_ = a_.get_component_by_class(unreal.StaticMeshComponent)
    for i in range(c_.get_num_materials()): c_.set_material(i, mt)
    try:
        c_.set_editor_property("cast_shadow", False); c_.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    except Exception: pass
    bo_, be_ = a_.get_actor_bounds(False)
    log(">>> %-22s 크기 %.1f×%.1f×%.1f cm" % (a_.get_actor_label(), be_.x * 2, be_.y * 2, be_.z * 2))
log(">>> 모형 원점 (%.0f, %.0f, %.0f)  — PlayerStart 앞 %.0f cm, 높이 %.0f cm" % (base.x, base.y, base.z, DIO_FORWARD_CM, DIO_HEIGHT_CM))

# ── 2) 표석 ────────────────────────────────────────────────────
DJ = json.load(open(os.path.join(RECD, "diorama.json"), encoding="utf-8"))
hits = [str(x.package_name) for x in reg.get_assets_by_class(unreal.TopLevelAssetPath("/Script/Engine", "Blueprint"), True)
        if str(x.asset_name) == "BP_DioMark"]
bp_cls = EAL.load_blueprint_class(hits[0]) if hits else None
sphere = EAL.load_asset("/Engine/BasicShapes/Sphere")
n = 0
for mk in DJ["표석"]:
    mx, my, mz = mk["모형_xyz_m"]
    loc = unreal.Vector(base.x + mx * 100.0, base.y + mz * 100.0, base.z + my * 100.0)   # 모형은 회전 0 → glb(x,z,y) = UE(X,Y,Z)
    dx, dy, dz = mk["목적지_xyz_m"]
    dest = to_world(dx, dy - EYE_DROP_M, dz)
    if bp_cls is not None:
        a = sub.spawn_actor_from_class(bp_cls, loc, unreal.Rotator(0, 0, 0))
        for prop, val in (("DestLoc", dest), ("DestYaw", float(mk["목적지_yaw_deg"]))):
            try: a.set_editor_property(prop, val)
            except Exception as ex: log("   !! %s 변수 %s 설정 실패 (순서표 3번): %s" % (mk["name"], prop, ex))
    else:
        a = sub.spawn_actor_from_object(sphere, loc, unreal.Rotator(0, 0, 0))
        a.set_actor_scale3d(unreal.Vector(MARK_SCALE, MARK_SCALE, MARK_SCALE))
        c = a.get_component_by_class(unreal.StaticMeshComponent)
        for i in range(c.get_num_materials()): c.set_material(i, mark_mat)
        try:
            c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION); c.set_editor_property("cast_shadow", False)
        except Exception: pass
    a.set_actor_label("DioMark_%s" % mk["name"]); a.set_folder_path("Inwang/Diorama"); n += 1
    log("  표석 %-4s 모형 위 (%.0f, %.0f, %.0f) → 목적지 (%.0f, %.0f, %.0f) yaw %.0f°  근거 %.0f %%"
        % (mk["name"], loc.x, loc.y, loc.z, dest.x, dest.y, dest.z, mk["목적지_yaw_deg"], mk["근거비율"] * 100))
log(">>> 표석 %d개 배치 (%s)" % (n, "BP_DioMark" if bp_cls else "미리보기 구 — 순서표대로 BP 만들면 다음 실행 때 교체"))
log("레벨 저장 %s" % LES.save_current_level())
