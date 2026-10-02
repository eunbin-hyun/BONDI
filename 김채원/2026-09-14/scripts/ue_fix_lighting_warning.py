# -*- coding: utf-8 -*-
"""
뷰포트 주황색 경고 없애기 (2026-09-14)
=========================================
두 가지를 같이 처리한다.
  A) '여러 디렉셔널 라이트가 … 경쟁' — 레벨에 디렉셔널 라이트가 2개 이상이면 뜬다.
     우리 Sun_Inwang 만 남기고 나머지는 끈다(지우지 않고 숨김 + 꺼짐 — 되돌릴 수 있게).
  B) 'LIGHTING NEEDS TO BE REBUILT' — 정적 메시 + 라이트 조합.
왜 뜨나: 레벨에 라이트가 있는데 일부 메시가 **Static(정적)** 이면 언리얼은 라이트맵을 구워야 한다고 본다.
         우리는 라이트맵을 안 굽고 전부 **동적 그림자**로 가므로 구울 필요가 없다 → 메시를 Movable 로 바꾸면 경고가 사라진다.
         (Movable 로 바꿔도 화면은 그대로. 정적 조명을 안 쓰니 성능 차이도 사실상 없다)

하는 일: 레벨의 StaticMeshActor·라이트를 전부 Movable 로. 바꾼 개수와 남은 Static 개수를 찍는다.
사용법 (레벨을 연 상태, 언리얼 콘솔):
    py "C:/KCW_SSAFY/특화/S15P21C201/김채원/2026-09-14/scripts/ue_fix_lighting_warning.py"
확인 지표: '>>> Movable 로 바꿈 N개,  남은 Static 0개'  — 0 이면 경고가 사라진다.
경고가 그래도 남으면: 뷰포트 좌상단 글자를 그대로 알려줄 것 (다른 경고일 수 있음).
"""
import unreal

sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


def log(m): unreal.log("[INWANG] %s" % m)


# ── A) 디렉셔널 라이트 하나만 ─────────────────────────────────
KEEP_SUN = "Sun_Inwang"
suns = [a for a in sub.get_all_level_actors() if a.get_component_by_class(unreal.DirectionalLightComponent) is not None]
log("디렉셔널 라이트 %d개: %s" % (len(suns), ", ".join(a.get_actor_label() for a in suns)))
keep = next((a for a in suns if a.get_actor_label() == KEEP_SUN), None)
if keep is None and suns: keep = suns[0]; log("   (참고) %s 가 없어 '%s' 를 남김" % (KEEP_SUN, keep.get_actor_label()))
n_off = 0
for a in suns:
    c = a.get_component_by_class(unreal.DirectionalLightComponent)
    on = (a is keep)
    try:
        c.set_visibility(on, True)
        c.set_editor_property("affects_world", on)
    except Exception as ex: log("   (참고) %s 끄기 실패: %s" % (a.get_actor_label(), ex))
    if not on:
        a.set_is_temporarily_hidden_in_editor(True); n_off += 1
    log("   %-22s %s" % (a.get_actor_label(), "남김(켜짐)" if on else "끔"))
log(">>> 디렉셔널 라이트 %d개 끔 — 1개만 남으면 '경쟁' 경고가 사라진다" % n_off)

# ── B) 정적 메시 → Movable ────────────────────────────────────
n_move = 0; left = []
for a in sub.get_all_level_actors():
    for cls in (unreal.StaticMeshComponent, unreal.LightComponent):
        c = a.get_component_by_class(cls)
        if c is None: continue
        try:
            if c.get_editor_property("mobility") != unreal.ComponentMobility.MOVABLE:
                c.set_mobility(unreal.ComponentMobility.MOVABLE); n_move += 1
        except Exception as ex:
            left.append("%s (%s)" % (a.get_actor_label(), ex))
        break

still = 0
for a in sub.get_all_level_actors():
    c = a.get_component_by_class(unreal.StaticMeshComponent)
    if c is None: continue
    try:
        if c.get_editor_property("mobility") != unreal.ComponentMobility.MOVABLE: still += 1
    except Exception: pass

log(">>> Movable 로 바꿈 %d개,  남은 Static %d개  (0 이면 주황 경고가 사라진다)" % (n_move, still))
if left: log("   못 바꾼 것 %d개: %s" % (len(left), ", ".join(left[:8])))
log("레벨 저장 %s" % LES.save_current_level())
