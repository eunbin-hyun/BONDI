# -*- coding: utf-8 -*-
"""
새로 만든 GLB 를 임포트하고 레벨 액터에 바로 끼움 (2026-09-14)
================================================================
왜 한 스크립트로 묶었나: 임포터가 destination_path 아래에 폴더를 한 겹 더 만드는 바람에
   house_ink 에셋이 두 벌이 되고 레벨 액터는 옛 것을 계속 가리키는 일이 있었음.
   → 임포트 직후 '방금 만들어진 메시'를 그대로 액터에 꽂아서 그 틈을 없앤다.

이번에 바뀐 것
  house_ink.glb        : 기둥·벽 윗면을 정점마다 바로 위 지붕면까지 늘림 (원래 0.8~2.1 m 떠 있었음) + 2 cm 만 관통
  inscription_board.glb: 안내판 텍스처 2배 해상도(4096×2048) · 먹 진하게 · 본문까지 굵은 글씨

사용법 (L_Inwang 열린 상태, 언리얼 콘솔):
    py "C:/KCW_SSAFY/특화/S15P21C201/김채원/2026-09-12/scripts/ue_reimport_apply.py"
확인 지표: 파트마다 '>>> … 액터에 적용 OK  삼각형 … 텍스처 …' 두 줄. 끝에 '레벨 저장 True'.
그 다음: ue_setup_materials.py  →  ue_setup_motion.py  순서로 한 번씩.
"""
import os, unreal

RT = r"C:\Users\SSAFY\Desktop\SSAFY_2학기\02_특화 프로젝트\특화PJT_\landscape_to_3D\Claude outputs\VR_inwangjesaekdo_v0.11\inwangjesaekdo_VR_v0.11\runtime"
PARTS = [("house_ink", "house_ink"), ("inscription_board", "inscription_board"),
         ("terrain_ink_ext", "terrain_ink_ext")]   # (파일 이름, 레벨 액터 라벨)
PKG = "/Game/Museum/Inwang"

EAL = unreal.EditorAssetLibrary; TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


def log(m): unreal.log("[INWANG] %s" % m)


def tex_of(mesh):
    out = []
    try:
        for sm in mesh.get_editor_property("static_materials"):
            mi = sm.get_editor_property("material_interface")
            if mi is None: continue
            try: tps = mi.get_editor_property("texture_parameter_values")
            except Exception: tps = []
            for tp in tps:
                t = tp.get_editor_property("parameter_value")
                if t is None: continue
                try: out.append("%s(%dx%d)" % (t.get_name(), t.blueprint_get_size_x(), t.blueprint_get_size_y()))
                except Exception: out.append(t.get_name())
    except Exception as ex: out.append("읽기실패 %s" % ex)
    return ", ".join(out) if out else "-"


actors = {a.get_actor_label(): a for a in sub.get_all_level_actors()}
for name, label in PARTS:
    src = os.path.join(RT, name + ".glb")
    if not os.path.exists(src): log("!! 원본 없음: %s" % src); continue
    log("― %s  (%d KB)" % (name, os.path.getsize(src) // 1024))
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", src)
    t.set_editor_property("destination_path", "%s/%s" % (PKG, name))
    t.set_editor_property("replace_existing", True); t.set_editor_property("automated", True); t.set_editor_property("save", True)
    TOOLS.import_asset_tasks([t])
    made = [str(p) for p in t.get_editor_property("imported_object_paths")]
    log("   임포트된 오브젝트 %d개" % len(made))
    mesh = None
    for p in made:                                     # 방금 만들어진 것 중 스태틱메시
        o = EAL.load_asset(p.split(".")[0] if "." in p.rsplit("/", 1)[-1] else p)
        if isinstance(o, unreal.StaticMesh): mesh = o; break
    if mesh is None:                                   # imported_object_paths 가 비면 폴더에서 가장 최근 것
        best = None
        for p in EAL.list_assets("%s/%s" % (PKG, name), recursive=True, include_folder=False):
            o = EAL.load_asset(p)
            if isinstance(o, unreal.StaticMesh) and p.rsplit("/", 1)[-1].split(".")[0].lower() == name:
                best = o                                # 같은 이름이 여럿이면 마지막(가장 깊은 폴더 = 최신 임포트)
        mesh = best
    if mesh is None: log("   !! 임포트된 스태틱메시를 못 찾음"); continue
    a = actors.get(label)
    if a is None: log("   !! 레벨에 '%s' 액터 없음" % label); continue
    c = a.get_component_by_class(unreal.StaticMeshComponent)
    old = c.static_mesh.get_path_name() if (c and c.static_mesh) else "없음"
    c.set_static_mesh(mesh)
    ok = c.static_mesh.get_path_name() == mesh.get_path_name()
    log("   %s\n       → %s" % (old, mesh.get_path_name()))
    log(">>> %-18s 액터에 적용 %s   삼각형 %d   텍스처 %s" % (label, "OK" if ok else "!! 실패", mesh.get_num_triangles(0), tex_of(mesh)))

log("레벨 저장 %s" % LES.save_current_level())
log(">>> 다음: ue_setup_materials.py → ue_setup_motion.py")
