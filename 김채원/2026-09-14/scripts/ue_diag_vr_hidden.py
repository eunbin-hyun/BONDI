# -*- coding: utf-8 -*-
"""
에디터엔 보이는데 VR/게임에선 안 보이는 원인 찾기 (2026-09-14)
=================================================================
에디터 뷰포트와 게임(PIE·VR)은 '보임' 판정 기준이 다르다. 게임에서만 사라지게 만드는 값은 정해져 있음:
    hidden(Actor Hidden In Game) / visible / hidden_in_game / detail_mode / 드로우 거리 컷 / render_in_main_pass
이 스크립트는 문제 액터와 '정상적으로 보이는' 대조군 액터의 같은 값을 나란히 찍어서 어디가 다른지 바로 보이게 한다.
같이: 현재 레벨의 BP_PortalInwang 액터들이 어느 레벨로 가게 설정돼 있는지도 찍음.

사용법 (L_Inwang 열린 상태, 언리얼 콘솔):
    py "C:/KCW_SSAFY/특화/S15P21C201/김채원/2026-09-12/scripts/ue_diag_vr_hidden.py"
확인 지표: 표에서 house_ink 행만 대조군과 값이 다른 칸 → 그 칸이 범인.
          '>>> 포털 …  LevelName = …' 이 L_Room_Inwang 이면 스크립트 쪽은 정상 (남은 건 블루프린트 Open Level 노드).
"""
import unreal

SUSPECT = "house_ink"
CONTROL = ["terrain_jeong", "base", "trees_cards"]      # VR 에서 잘 보이는 액터 (대조군)

sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def log(m): unreal.log("[INWANG] %s" % m)


def gp(obj, name):
    try:
        v = obj.get_editor_property(name)
        return str(v).replace("MaterialShadingModel.", "").replace("DetailMode.", "").replace("ComponentMobility.", "")
    except Exception:
        return "-"


ACT_PROPS = ["hidden", "is_editor_only_actor", "net_dormancy"]
COMP_PROPS = ["visible", "hidden_in_game", "detail_mode", "render_in_main_pass", "render_in_depth_pass",
              "ld_max_draw_distance", "cached_max_draw_distance", "min_draw_distance", "bounds_scale",
              "mobility", "visible_in_scene_capture_only", "cast_shadow", "is_visualization_component"]

A = {a.get_actor_label(): a for a in sub.get_all_level_actors()}
names = [SUSPECT] + [c for c in CONTROL if c in A]
rows = {}
for n in names:
    a = A.get(n)
    if a is None: log("!! 액터 없음: %s" % n); continue
    c = a.get_component_by_class(unreal.StaticMeshComponent)
    d = {}
    d["편집기숨김"] = str(a.is_temporarily_hidden_in_editor())
    for p in ACT_PROPS: d[p] = gp(a, p)
    for p in COMP_PROPS: d[p] = gp(c, p) if c else "-"
    if c and c.static_mesh:
        d["메시"] = c.static_mesh.get_name()
        m0 = c.get_material(0)
        d["머티리얼"] = m0.get_name() if m0 else "없음"
        try: d["나나이트"] = str(c.static_mesh.get_editor_property("nanite_settings").get_editor_property("enabled"))
        except Exception: d["나나이트"] = "-"
    else:
        d["메시"] = d["머티리얼"] = d["나나이트"] = "-"
    o, e = a.get_actor_bounds(False)
    d["바운드반크기"] = "%.0f,%.0f,%.0f" % (e.x, e.y, e.z)
    rows[n] = d

keys = ["메시", "머티리얼", "나나이트", "편집기숨김"] + ACT_PROPS + COMP_PROPS + ["바운드반크기"]
log("―― 게임/VR 가시성 비교 (맨 왼쪽이 문제 액터) ――")
log("%-24s | %s" % ("속성", " | ".join("%-20s" % n for n in names)))
for k in keys:
    vals = [rows.get(n, {}).get(k, "-") for n in names]
    diff = "  <== 다름" if len(set(vals)) > 1 else ""
    log("%-24s | %s%s" % (k, " | ".join("%-20s" % v[:20] for v in vals), diff))

# ── 포털이 어느 레벨로 가게 돼 있나
log("―― 포털 설정 ――")
found = 0
for a in sub.get_all_level_actors():
    lab = a.get_actor_label()
    if "Portal" not in lab: continue
    found += 1
    try: lv = a.get_editor_property("LevelName")
    except Exception as ex: lv = "읽기실패(%s)" % ex
    log(">>> 포털 %-18s LevelName = %s   위치 (%.0f, %.0f, %.0f)" % (lab, lv, a.get_actor_location().x, a.get_actor_location().y, a.get_actor_location().z))
if not found: log("!! 이 레벨에 Portal 액터 없음")
log("―― 끝. 위 표에서 '다름' 붙은 줄이 VR 에서 안 보이는 이유 후보 ――")
