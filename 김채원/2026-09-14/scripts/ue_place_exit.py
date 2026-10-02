# -*- coding: utf-8 -*-
"""
L_Inwang 안에 '돌아가는 액자' 배치 (2026-09-14)
================================================
PlayerStart(정선 시점) 바로 뒤에 액자+원화 판을 세우고, 그 앞에 BP_PortalInwang(LevelName = L_Room_Inwang) 을 둔다.
→ 들어온 방향 그대로 뒤돌아 액자로 다가가면 전시실로 복귀.
사용법: L_Inwang 이 열린 상태, 언리얼 콘솔
    py "C:/KCW_SSAFY/특화/S15P21C201/김채원/2026-09-12/scripts/ue_place_exit.py"
확인 지표: '>>> 액자 (x,y,z) yaw …  포털 거리 … cm (PlayerStart 기준, 80 보다 커야 시작하자마자 안 튐)'
"""
import unreal, math

BACK_CM = 700.0        # PlayerStart 뒤로 이 만큼에 액자
                       #   2026-09-14: 200 → 700. 200 이면 포털이 시작 지점에서 1.4 m 라
                       #   플레이하자마자 판정 범위 안에 들어가 바로 되돌아가 버렸다.
EYE_Z = 150.0          # 액자 중심 높이(바닥 기준). PlayerStart z + 이 값의 절반쯤이 눈높이
SCALE = 1.5
STANDOFF = 60.0        # 액자 앞(플레이어 쪽) 포털 위치
TRIGGER_CM = 80.0      # 블루프린트의 판정 거리 (BP 에서 쓰는 값과 같게 적어둘 것 — 아래 경고 판정에 씀)
DEST = "L_Room_Inwang"
PKG = "/Game/Museum/Inwang"
BEAM_D_M, BEAM_H_M, BEAM_OPACITY = 3.0, 150.0, 0.12    # 빛기둥 지름·높이(m)·불투명도 — 멀리서 위치 찾기용

sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem); EAL = unreal.EditorAssetLibrary
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
reg = unreal.AssetRegistryHelpers.get_asset_registry()


def log(m): unreal.log("[INWANG] %s" % m)


def find_mesh(name):
    for p in EAL.list_assets(PKG, recursive=True, include_folder=False):
        if p.rsplit("/", 1)[-1].split(".")[0].lower() == name:
            o = EAL.load_asset(p)
            if isinstance(o, unreal.StaticMesh): return o
    return None


A = list(sub.get_all_level_actors())
for a in A:                                            # 이전 배치 제거
    if a.get_actor_label().startswith(("Exit_", "Portal_To_Room")): sub.destroy_actor(a)
ps = next((a for a in A if isinstance(a, unreal.PlayerStart)), None)
if ps is None: log("!! PlayerStart 없음 — 현재 레벨이 L_Inwang 인지 확인"); raise SystemExit
p0 = ps.get_actor_location(); yaw = ps.get_actor_rotation().yaw
fwd = unreal.Vector(math.cos(math.radians(yaw)), math.sin(math.radians(yaw)), 0.0)
fl = unreal.Vector(p0.x - fwd.x * BACK_CM, p0.y - fwd.y * BACK_CM, p0.z + EYE_Z * 0.5)
rot = unreal.Rotator(0, 0, yaw + 90.0)                 # 메시 기본 법선이 +Y → 플레이어(-fwd 반대)를 보게

for nm, label in (("painting_inwang", "Exit_Painting"), ("frame_inwang", "Exit_Frame")):
    sm = find_mesh(nm)
    if sm is None: log("!! %s 메시 없음" % nm); continue
    a = sub.spawn_actor_from_object(sm, fl, rot); a.set_actor_scale3d(unreal.Vector(SCALE, SCALE, SCALE))
    a.set_actor_label(label); a.set_folder_path("Inwang/Exit")

cls = None
hits = [str(x.package_name) for x in reg.get_assets_by_class(unreal.TopLevelAssetPath("/Script/Engine", "Blueprint"), True) if str(x.asset_name) == "BP_PortalInwang"]
if hits: cls = EAL.load_blueprint_class(hits[0])
if cls is None: log("!! BP_PortalInwang 없음")
else:
    pl = unreal.Vector(fl.x + fwd.x * STANDOFF, fl.y + fwd.y * STANDOFF, fl.z)
    pt = sub.spawn_actor_from_class(cls, pl, unreal.Rotator(0, 0, yaw))
    pt.set_actor_label("Portal_To_Room"); pt.set_folder_path("Inwang/Exit")
    try: pt.set_editor_property("LevelName", unreal.Name(DEST)); log("LevelName = %s" % pt.get_editor_property("LevelName"))
    except Exception as ex: log("!! LevelName 설정 실패: %s" % ex)
    d = math.dist([p0.x, p0.y, p0.z], [pl.x, pl.y, pl.z])
    log(">>> 액자 (%.0f, %.0f, %.0f) yaw %.0f   PlayerStart↔포털 %.0f cm" % (fl.x, fl.y, fl.z, rot.yaw, d))
    if d <= TRIGGER_CM * 2:
        log("   !! 너무 가깝다 (판정 거리 %.0f cm 의 2배 미만) — 시작하자마자 되돌아간다. BACK_CM 을 더 키울 것" % TRIGGER_CM)
    else:
        log("   OK — 판정 거리 %.0f cm 의 %.1f 배. 걸어가서 다가가야만 발동한다" % (TRIGGER_CM, d / TRIGGER_CM))
# ── 빛기둥: Unlit 반투명 원기둥 (엔진 Cylinder = 지름 100 cm, 높이 100 cm, 중심 피벗)
ML = unreal.MaterialEditingLibrary; TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
mpath = PKG + "/M_InwangBeam"
if EAL.does_asset_exist(mpath): beam_mat = EAL.load_asset(mpath); ML.delete_all_material_expressions(beam_mat)
else: beam_mat = TOOLS.create_asset("M_InwangBeam", PKG, unreal.Material, unreal.MaterialFactoryNew())
beam_mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
beam_mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
beam_mat.set_editor_property("two_sided", True)
col = ML.create_material_expression(beam_mat, unreal.MaterialExpressionConstant3Vector, -400, 0)
col.set_editor_property("constant", unreal.LinearColor(0.95, 0.92, 0.80, 1.0))
op = ML.create_material_expression(beam_mat, unreal.MaterialExpressionConstant, -400, 200); op.set_editor_property("r", BEAM_OPACITY)
o1 = ML.connect_material_property(col, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
o2 = ML.connect_material_property(op, "", unreal.MaterialProperty.MP_OPACITY)
ML.recompile_material(beam_mat); EAL.save_asset(mpath)
log("M_InwangBeam  Emissive %s  Opacity %s" % (o1, o2))
cyl = EAL.load_asset("/Engine/BasicShapes/Cylinder")
if cyl is None: log("!! 엔진 Cylinder 메시 없음")
else:
    bz = fl.z + BEAM_H_M * 100.0 / 2.0 - 50.0
    b = sub.spawn_actor_from_object(cyl, unreal.Vector(fl.x, fl.y, bz), unreal.Rotator(0, 0, 0))
    b.set_actor_scale3d(unreal.Vector(BEAM_D_M, BEAM_D_M, BEAM_H_M))
    b.set_actor_label("Exit_Beam"); b.set_folder_path("Inwang/Exit")
    c = b.get_component_by_class(unreal.StaticMeshComponent)
    for i in range(c.get_num_materials()): c.set_material(i, beam_mat)
    try: c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    except Exception as ex: log("   (참고) 빛기둥 콜리전 끄기 실패: %s" % ex)
    log(">>> 빛기둥 지름 %.0f m, 높이 %.0f m, 중심 z %.0f (액자 z %.0f)" % (BEAM_D_M, BEAM_H_M, bz, fl.z))
log("레벨 저장 %s" % LES.save_current_level())
