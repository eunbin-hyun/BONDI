# -*- coding: utf-8 -*-
"""
집 겹침 정리 — house_ink 하나만 남기고 나머지 집 액터 숨김 (2026-09-14)
======================================================================
증상: 지붕 아래쪽이 반짝이며 깨져 보임 = Z-파이팅(같은 자리에 두 면이 겹침).
원인 후보: house / house2 / house_giwa 등 옛 집 액터가 house_ink 와 같은 자리에 함께 보이는 상태.
하는 일: 라벨에 'house' 가 들어간 액터를 전부 찾아 위치·바운드·표시 상태를 찍고, KEEP 만 남기고 나머지는 숨김.
사용법 (L_Inwang 열린 상태, 언리얼 콘솔):
    py "C:/KCW_SSAFY/특화/S15P21C201/김채원/2026-09-12/scripts/ue_fix_house_overlap.py"
확인 지표: 목록에서 house_ink 만 '표시', 나머지 '숨김'. 그 뒤에도 반짝이면 house_ink 자체가 두 개인지 확인.
"""
import unreal

KEEP = "house_ink"
sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem); LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


def log(m): unreal.log("[INWANG] %s" % m)


hits = [a for a in sub.get_all_level_actors() if "house" in a.get_actor_label().lower()]
log("집 관련 액터 %d개" % len(hits))
n_hide = 0
for a in hits:
    lab = a.get_actor_label(); o, e = a.get_actor_bounds(False)
    keep = (lab == KEEP)
    if not keep:
        a.set_is_temporarily_hidden_in_editor(True); a.set_actor_hidden_in_game(True); n_hide += 1
    else:
        a.set_is_temporarily_hidden_in_editor(False); a.set_actor_hidden_in_game(False)
    comp = a.get_component_by_class(unreal.StaticMeshComponent)
    tri = comp.static_mesh.get_num_triangles(0) if (comp and comp.static_mesh) else -1
    log("  %-14s %s  중심 (%.0f, %.0f, %.0f)  크기 %.0f×%.0f×%.0f  삼각형 %d" % (lab, "표시" if keep else "숨김", o.x, o.y, o.z, e.x * 2, e.y * 2, e.z * 2, tri))
same = [a.get_actor_label() for a in hits if a.get_actor_label() == KEEP]
log(">>> %d개 숨김. '%s' 액터 개수 %d (1 이어야 함 — 2 이상이면 그게 반짝임 원인)" % (n_hide, KEEP, len(same)))
log("레벨 저장 %s" % LES.save_current_level())
