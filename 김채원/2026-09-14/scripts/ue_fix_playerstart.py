# -*- coding: utf-8 -*-
"""
PlayerStart 를 방 안 제자리로 (2026-09-14)
==========================================
MODE = "inside" : 포털 박스 한가운데에 놓음 → 플레이하자마자 즉시 발동 (포털 자체가 되는지 확인용)
MODE = "front"  : 포털 앞 FRONT_CM 에 놓고 그림을 바라봄 (걸어 들어가는 정상 동작 확인용)
둘 다 방 안(X < 500)으로 강제 — 벽을 뚫고 나가지 않음.
사용법: L_Room_Inwang 열린 상태, 언리얼 콘솔
    py "C:/KCW_SSAFY/특화/S15P21C201/김채원/2026-09-12/scripts/ue_fix_playerstart.py"
확인 지표: '>>> PlayerStart (x, y, z) yaw 0  — 방 안 True / 박스 안 True'
"""
import unreal

MODE = "inside"          # "inside" 또는 "front"
FRONT_CM = 200.0         # front 모드에서 박스 앞 거리
FLOOR_Z = 92.0           # 바닥 위 눈높이 캡슐 중심
WALL_X = 500.0

sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem); LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


def log(m): unreal.log("[INWANG] %s" % m)


A = {a.get_actor_label(): a for a in sub.get_all_level_actors()}
portal = A.get("Portal_To_Inwang"); ps = next((a for a in A.values() if isinstance(a, unreal.PlayerStart)), None)
if portal is None: log("!! Portal_To_Inwang 없음")
elif ps is None: log("!! PlayerStart 없음")
else:
    box = portal.get_component_by_class(unreal.BoxComponent)
    c = portal.get_actor_location(); e = box.get_scaled_box_extent() if box else unreal.Vector(30, 100, 60)
    z = max(FLOOR_Z, c.z - e.z + 20)                       # 박스 Z 범위 안이면서 바닥 위
    x = c.x if MODE == "inside" else c.x - e.x - FRONT_CM
    x = min(x, WALL_X - 40)                                 # 벽 안쪽 보장
    ps.set_actor_location(unreal.Vector(x, c.y, z), False, False)
    ps.set_actor_rotation(unreal.Rotator(0, 0, 0), False)   # +X = 그림 쪽
    in_room = x < WALL_X
    in_box = (abs(x - c.x) <= e.x) and (abs(z - c.z) <= e.z)
    log("포털 중심 (%.0f, %.0f, %.0f) 반크기 (%.0f, %.0f, %.0f)" % (c.x, c.y, c.z, e.x, e.y, e.z))
    log(">>> PlayerStart (%.0f, %.0f, %.0f) yaw 0  — 방 안 %s / 박스 안 %s  [MODE=%s]" % (x, c.y, z, in_room, in_box, MODE))
    log("레벨 저장 %s" % LES.save_current_level())
