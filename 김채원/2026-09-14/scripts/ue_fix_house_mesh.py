# -*- coding: utf-8 -*-
"""
house_ink 액터를 '최신 임포트 에셋'으로 바꿔 끼움 (2026-09-14)
===============================================================
문제: 프로젝트에 house_ink 스태틱메시가 두 개 있고, 레벨 액터가 옛것(텍스처 1024x512)을 쓰고 있었음.
      새 임포트는 /Game/Museum/Inwang/house_ink/house_ink/... 에 한 겹 더 들어가 있어서 아무도 안 쓰는 상태.
하는 일: house_ink 스태틱메시를 전부 찾아 '참조 텍스처 가로폭이 가장 큰' 것을 최신으로 보고 액터에 끼움.
         옛 에셋은 삭제하지 않고 이름만 로그에 남김 (되돌릴 수 있게).
사용법 (L_Inwang 열린 상태, 언리얼 콘솔):
    py "C:/KCW_SSAFY/특화/S15P21C201/김채원/2026-09-12/scripts/ue_fix_house_mesh.py"
확인 지표: '>>> 교체 완료 … 텍스처 2048x1024'.  그 뒤 ue_setup_materials.py 를 한 번 더 돌려야 머티리얼이 새 텍스처를 잡음.
"""
import unreal

TARGET = "house_ink"

EAL = unreal.EditorAssetLibrary
sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
reg = unreal.AssetRegistryHelpers.get_asset_registry()


def log(m): unreal.log("[INWANG] %s" % m)


def tex_w(mesh):
    """메시가 참조하는 텍스처 중 가장 큰 가로폭 (없으면 0)"""
    w = 0; names = []
    try:
        for sm in mesh.get_editor_property("static_materials"):
            mi = sm.get_editor_property("material_interface")
            if mi is None: continue
            try: tps = mi.get_editor_property("texture_parameter_values")
            except Exception: tps = []
            for tp in tps:
                t = tp.get_editor_property("parameter_value")
                if t is None: continue
                try:
                    x, y = t.blueprint_get_size_x(), t.blueprint_get_size_y()
                    names.append("%s(%dx%d)" % (t.get_name(), x, y)); w = max(w, x)
                except Exception: pass
    except Exception as ex: log("   텍스처 읽기 실패 %s" % ex)
    return w, (", ".join(names) if names else "-")


cands = []
for a in reg.get_assets_by_class(unreal.TopLevelAssetPath("/Script/Engine", "StaticMesh"), True):
    if str(a.asset_name).lower() != TARGET: continue
    o = EAL.load_asset(str(a.package_name))
    if not isinstance(o, unreal.StaticMesh): continue
    w, nm = tex_w(o)
    cands.append((w, str(a.package_name), o, nm))

if not cands:
    log("!! house_ink 스태틱메시를 못 찾음 — ue_import_house_ink.py 먼저")
else:
    cands.sort(reverse=True)
    for w, p, o, nm in cands:
        log("  후보 %-56s 삼각형 %-5d 텍스처 %s%s" % (p, o.get_num_triangles(0), nm, "   <= 최신" if (w, p) == (cands[0][0], cands[0][1]) else ""))
    bw, bp, bmesh, bnm = cands[0]
    acts = [a for a in sub.get_all_level_actors() if a.get_actor_label() == TARGET]
    log("레벨의 '%s' 액터 %d개" % (TARGET, len(acts)))
    done = 0
    for a in acts:
        c = a.get_component_by_class(unreal.StaticMeshComponent)
        if c is None: continue
        old = c.static_mesh.get_path_name() if c.static_mesh else "없음"
        if c.static_mesh is bmesh:
            log("  이미 최신 메시 사용 중 — 바꿀 것 없음"); continue
        c.set_static_mesh(bmesh); done += 1
        log("  %s\n      → %s" % (old, bp))
    if done:
        log(">>> 교체 완료 %d개 — 새 메시 텍스처 %s" % (done, bnm))
        log(">>> 다음: py \".../ue_setup_materials.py\" 를 한 번 더 돌려야 M_InwangHouseInk 가 새 텍스처(%s)를 잡음" % bnm)
    else:
        log(">>> 바뀐 것 없음 (이미 최신이거나 액터 없음)")
    log("레벨 저장 %s" % LES.save_current_level())
