# -*- coding: utf-8 -*-
"""
금빛 반짝임 끄기 (2026-09-14)
==============================
반짝임 머티리얼(M_InwangBoardShine / M_InwangInkShine)을 원래 머티리얼로 되돌린다.
기본은 안내판(inscription_board)만 끔. 화제(inscription)까지 끄려면 TARGETS 에 "inscription" 을 추가.

사용법 (L_Inwang 열린 상태, 언리얼 콘솔):
    py "C:/KCW_SSAFY/특화/S15P21C201/김채원/2026-09-12/scripts/ue_shine_off.py"
확인 지표: '>>> inscription_board 꺼짐 (M_InwangBoard)'  — 괄호 안이 Shine 이 아니면 성공.
다시 켜려면: ue_toggle_shine.py (TARGET 을 원하는 것으로)
"""
import unreal

TARGETS = ["inscription_board"]            # ["inscription_board", "inscription"] 처럼 여러 개 가능
PKG = "/Game/Museum/Inwang"
PLAIN = {"inscription_board": "M_InwangBoard", "inscription": "M_InwangInk"}

EAL = unreal.EditorAssetLibrary
sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


def log(m): unreal.log("[INWANG] %s" % m)


A = {x.get_actor_label(): x for x in sub.get_all_level_actors()}
n = 0
for t in TARGETS:
    a = A.get(t)
    if a is None: log("!! '%s' 액터 없음 — 현재 레벨이 L_Inwang 인지 확인" % t); continue
    comp = a.get_component_by_class(unreal.StaticMeshComponent)
    if comp is None: log("!! %s 에 메시 컴포넌트 없음" % t); continue
    cur = comp.get_material(0); cur_name = cur.get_name() if cur else "없음"
    m = EAL.load_asset("%s/%s" % (PKG, PLAIN[t]))
    if m is None: log("!! %s 머티리얼이 없음 — ue_setup_materials.py 먼저" % PLAIN[t]); continue
    for i in range(comp.get_num_materials()): comp.set_material(i, m)
    got = comp.get_material(0).get_name(); n += 1
    log(">>> %-18s 꺼짐 (%s)   [이전 %s]" % (t, got, cur_name))
log("바꾼 액터 %d개.  레벨 저장 %s" % (n, LES.save_current_level()))
