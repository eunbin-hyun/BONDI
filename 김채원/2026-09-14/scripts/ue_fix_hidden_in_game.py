# -*- coding: utf-8 -*-
"""
'게임에서 숨김'(Actor Hidden In Game) 잘못 켜진 액터 되살리기 (2026-09-14)
==========================================================================
증상: 에디터 뷰포트엔 보이는데 PIE·VR 에서만 안 보임.
원인: 액터의 hidden(= Actor Hidden In Game) 이 True. 에디터 뷰포트는 이 값을 무시해서 티가 안 남.
하는 일: SHOW 에 적힌 액터는 hidden=False + 편집기 숨김 해제,
         HIDE 에 적힌 액터는 hidden=True + 편집기 숨김 (겹친 옛 집은 계속 숨긴 채로 유지).
         그리고 레벨 전체를 훑어 '에디터엔 보이는데 게임에선 숨김'인 액터를 전부 경고로 찍는다.
사용법 (L_Inwang 열린 상태, 언리얼 콘솔):
    py "C:/KCW_SSAFY/특화/S15P21C201/김채원/2026-09-14/scripts/ue_fix_hidden_in_game.py"
확인 지표: '>>> house_ink  hidden False / 편집기숨김 False' 와 '>>> 불일치 남은 액터 0개'.
이 파일이 **보임/숨김의 유일한 기준**이다. 다른 스크립트가 상태를 흔들면 이걸 다시 돌리면 된다 (ue_restore_state.py 가 이걸 포함).
"""
import unreal

# inscription(원화의 화제·인장을 분리한 공중 판)은 inscription_board(관람 안내판)와 별개 자산 → 되살림
SHOW = ["house_ink", "house_ink_small", "house_ink_big", "inscription_board", "inscription",
        "terrain_ink_ext", "trees_cards"]
# 아래는 '새 버전으로 대체된 옛 액터'만. 이 판단이 틀렸으면 줄에서 빼면 됨
HIDE = ["house", "house2",      # → house_ink (분리본 house_ink_small/big 사용)
        "fog",                  # → fog_l0~l4 (운무 v3 5겹)
        "trees"]                # 절차적 나무 168그루 — 삼각형 예산 초과라 안 씀 (대신 trees_cards 를 씀)
# terrain_ink_ext 는 2026-09-14 부터 SHOW — 조명 켠 상태에서 산 뒷면을 채워주는 게 낫다는 판단

sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


def log(m): unreal.log("[INWANG] %s" % m)


def set_vis(a, show):
    try: a.set_editor_property("hidden", not show)
    except Exception as ex: log("   !! hidden 설정 실패 %s: %s" % (a.get_actor_label(), ex))
    try: a.set_actor_hidden_in_game(not show)
    except Exception: pass
    a.set_is_temporarily_hidden_in_editor(not show)


A = {a.get_actor_label(): a for a in sub.get_all_level_actors()}
for n in SHOW:
    a = A.get(n)
    if a is None: log("!! 액터 없음: %s" % n); continue
    set_vis(a, True)
    log(">>> %-18s hidden %s / 편집기숨김 %s  (보여야 함)" % (n, a.get_editor_property("hidden"), a.is_temporarily_hidden_in_editor()))
for n in HIDE:
    a = A.get(n)
    if a is None: continue
    set_vis(a, False)
    log("    %-18s hidden %s / 편집기숨김 %s  (숨김 유지)" % (n, a.get_editor_property("hidden"), a.is_temporarily_hidden_in_editor()))

# ── 레벨 전체 점검: 에디터엔 보이는데 게임에선 숨김인 액터 (같은 함정이 또 있는지)
bad = []
for a in sub.get_all_level_actors():
    c = a.get_component_by_class(unreal.StaticMeshComponent)
    if c is None or c.static_mesh is None: continue
    try: h = a.get_editor_property("hidden")
    except Exception: continue
    if h and not a.is_temporarily_hidden_in_editor(): bad.append(a.get_actor_label())
log(">>> 불일치(에디터엔 보임 · 게임선 숨김) 남은 액터 %d개%s" % (len(bad), (": " + ", ".join(bad[:20])) if bad else ""))
log("레벨 저장 %s" % LES.save_current_level())
