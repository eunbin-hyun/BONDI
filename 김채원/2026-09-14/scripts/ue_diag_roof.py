# -*- coding: utf-8 -*-
"""
지붕 반짝임 원인 추적 v1 (2026-09-14)
=====================================
house / house2 를 숨겼는데도 반짝인다 = 겹친 액터가 원인이 아니었다는 뜻.
남은 후보를 한 번에 확인한다.
  A. 레벨의 house_ink 액터가 '고친 메시'를 안 쓰고 있다.
     - 고친 house_ink.glb 는 삼각형 808 / 텍스처 2048x1024.
     - 그런데 직전 로그는 삼각형 455 라고 찍혔다 = 옛날 에셋(455)일 가능성이 큼.
     - 콘텐츠 브라우저에 house_ink 가 두 개(house_ink, house_ink1 …) 있고 액터가 옛 것을 가리키는 경우가 흔함.
  B. house_ink 바운드 안에 아직 다른 '보이는' 액터가 들어앉아 있다 (이름에 house 가 없는 액터).
  C. 위 둘이 아니면 메시 자체의 겹친 면(추녀 획이 지붕 위 3 cm) 문제 → 이건 GLB 를 다시 만들어야 함.

하는 일: 프로젝트 안 house* 스태틱메시를 전부 찍고, 레벨 액터가 쓰는 메시를 표시.
         FIX=True 이면 삼각형이 EXPECT_TRI 인 메시로 액터를 바꿔 끼움.
         그 다음 house_ink 바운드와 겹치는 '보이는' 액터를 전부 나열.

사용법 (L_Inwang 열린 상태, 언리얼 콘솔):
    py "C:/KCW_SSAFY/특화/S15P21C201/김채원/2026-09-12/scripts/ue_diag_roof.py"

확인 지표:
    '>>> A 판정: ...'  ← 여기서 '옛 메시' 면 그게 원인. FIX 가 바꿔 끼운 뒤 다시 VR 로 확인.
    '>>> B 판정: 겹치는 보이는 액터 N개'  ← 0 이어야 정상.
"""
import unreal

FIX = True              # 옛 메시를 쓰고 있으면 삼각형 EXPECT_TRI 짜리로 바꿔 끼움
EXPECT_TRI = 808        # 고친 house_ink.glb 의 면 수
TARGET = "house_ink"
OVERLAP_MIN = 0.25      # 바운드 겹침 비율이 이 이상이면 '겹친다'고 봄

EAL = unreal.EditorAssetLibrary
sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
reg = unreal.AssetRegistryHelpers.get_asset_registry()


def log(m): unreal.log("[INWANG] %s" % m)


def tex_info(mesh):
    """메시가 실제로 참조하는 텍스처 이름·해상도"""
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
                try: sz = "%dx%d" % (t.blueprint_get_size_x(), t.blueprint_get_size_y())
                except Exception: sz = "?"
                out.append("%s(%s)" % (t.get_name(), sz))
    except Exception as ex:
        out.append("읽기실패 %s" % ex)
    return ", ".join(out) if out else "-"


# ── 프로젝트 안 house* 스태틱메시 전부
metas = [a for a in reg.get_assets_by_class(unreal.TopLevelAssetPath("/Script/Engine", "StaticMesh"), True)
         if "house" in str(a.asset_name).lower()]
log("프로젝트 house* 스태틱메시 %d개" % len(metas))
best = None
for m in sorted(metas, key=lambda x: str(x.package_name)):
    path = str(m.package_name)
    o = EAL.load_asset(path)
    if not isinstance(o, unreal.StaticMesh): continue
    tri = o.get_num_triangles(0)
    mark = ""
    if tri == EXPECT_TRI and (best is None): best = o; mark = "  <= 고친 버전"
    log("  %-52s 삼각형 %-6d 텍스처 %s%s" % (path, tri, tex_info(o), mark))

# ── 레벨 액터가 쓰는 메시
acts = [a for a in sub.get_all_level_actors() if a.get_actor_label() == TARGET]
log("레벨의 '%s' 액터 %d개" % (TARGET, len(acts)))
swapped = 0
cur_tri = -1
for a in acts:
    c = a.get_component_by_class(unreal.StaticMeshComponent)
    sm = c.static_mesh if c else None
    if sm is None: log("  !! 스태틱메시 없음"); continue
    cur_tri = sm.get_num_triangles(0)
    log("  쓰는 메시 %s  삼각형 %d  텍스처 %s" % (sm.get_path_name(), cur_tri, tex_info(sm)))
    if cur_tri != EXPECT_TRI and FIX and best is not None:
        c.set_static_mesh(best); swapped += 1
        log("  → 바꿔 끼움: %s (삼각형 %d)" % (best.get_path_name(), best.get_num_triangles(0)))

if cur_tri == EXPECT_TRI:
    log(">>> A 판정: 고친 메시(%d) 사용 중 — 이게 원인이 아님" % EXPECT_TRI)
elif swapped:
    log(">>> A 판정: 옛 메시(%d) 를 쓰고 있었음 → 고친 메시로 %d개 교체. 이게 원인일 확률 높음" % (cur_tri, swapped))
elif best is None:
    log(">>> A 판정: 삼각형 %d 짜리 house_ink 에셋이 프로젝트에 아예 없음 → ue_import_house_ink.py 먼저 실행" % EXPECT_TRI)
else:
    log(">>> A 판정: 옛 메시(%d) 사용 중이지만 FIX=False 라 안 바꿈" % cur_tri)

# ── house_ink 바운드와 겹치는 '보이는' 액터
if acts:
    o0, e0 = acts[0].get_actor_bounds(False)
    lo0 = [o0.x - e0.x, o0.y - e0.y, o0.z - e0.z]; hi0 = [o0.x + e0.x, o0.y + e0.y, o0.z + e0.z]
    v0 = max(1.0, (e0.x * 2) * (e0.y * 2) * (e0.z * 2))
    hits = []
    for a in sub.get_all_level_actors():
        if a in acts: continue
        if a.is_temporarily_hidden_in_editor(): continue
        c = a.get_component_by_class(unreal.StaticMeshComponent)
        if c is None or c.static_mesh is None: continue
        o, e = a.get_actor_bounds(False)
        lo = [o.x - e.x, o.y - e.y, o.z - e.z]; hi = [o.x + e.x, o.y + e.y, o.z + e.z]
        ov = 1.0
        for i in range(3):
            d = min(hi0[i], hi[i]) - max(lo0[i], lo[i])
            if d <= 0: ov = 0.0; break
            ov *= d
        r = ov / v0
        if r >= OVERLAP_MIN:
            hits.append((r, a.get_actor_label(), c.static_mesh.get_name(), c.static_mesh.get_num_triangles(0)))
    hits.sort(reverse=True)
    log(">>> B 판정: house_ink 바운드와 %.0f%% 이상 겹치는 '보이는' 액터 %d개 (0 이어야 정상)" % (OVERLAP_MIN * 100, len(hits)))
    for r, lab, mn, t in hits:
        log("    %-20s 메시 %-22s 삼각형 %-6d 겹침 %.0f%%" % (lab, mn, t, r * 100))
    if not hits and cur_tri == EXPECT_TRI:
        log(">>> C: A·B 둘 다 아님 → 메시 자체의 겹친 면(추녀 획이 지붕 위 3 cm)이 원인. GLB 재생성 필요하다고 알려줄 것")

log("레벨 저장 %s" % LES.save_current_level())
