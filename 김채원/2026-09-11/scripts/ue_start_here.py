# -*- coding: utf-8 -*-
"""
인왕제색도 - 지금 뷰포트 카메라 자리를 VR 시작점(PlayerStart_Inwang)으로
=======================================================================
사용법: PC 뷰포트에서 카메라를 원하는 자리·방향으로 맞춘 뒤 콘솔(Cmd)에
    py "C:/KCW_SSAFY/특화/S15P21C201/김채원/2026-09-11/scripts/ue_start_here.py"

카메라 XY·방향(yaw)은 그대로, Z 는 카메라가 눈높이라고 보고 160 cm 내려 바닥으로 잡는다.
VR 에서 발이 떠 있으면 FLOOR_OFFSET_CM 을 줄이고, 파묻히면 늘린다.

작성: 김채원(AI) / 2026-09-11
"""

import unreal

EYE_HEIGHT_CM   = 160.0    # 에디터 카메라를 눈높이로 가정
FLOOR_OFFSET_CM = 90.0     # ue_goto_entry.py 에서 쓰던 값. 발이 떠 있으면 0 으로.


def log(msg):
    unreal.log("[INWANG] %s" % msg)


ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
cam, rot = ues.get_level_viewport_camera_info()
target = unreal.Vector(cam.x, cam.y, cam.z - EYE_HEIGHT_CM + FLOOR_OFFSET_CM)
yaw = unreal.Rotator(roll=0.0, pitch=0.0, yaw=rot.yaw)

sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
ps = None
for a in sub.get_all_level_actors():
    if isinstance(a, unreal.PlayerStart):
        if a.get_actor_label() == "PlayerStart_Inwang" or ps is None:
            ps = a
if ps is None:
    ps = sub.spawn_actor_from_class(unreal.PlayerStart, target, yaw)
    ps.set_actor_label("PlayerStart_Inwang")
    how = "새로 생성"
else:
    ps.set_actor_location(target, False, False)
    ps.set_actor_rotation(yaw, False)
    how = "이동"

p = ps.get_actor_location()
r = ps.get_actor_rotation()
ok = abs(p.x - target.x) < 1 and abs(p.y - target.y) < 1 and abs(p.z - target.z) < 1
log("=" * 70)
log("카메라      (%.0f, %.0f, %.0f)  yaw %.0f" % (cam.x, cam.y, cam.z, rot.yaw))
log("PlayerStart (%.0f, %.0f, %.0f)  yaw %.0f   %s  -> %s" % (p.x, p.y, p.z, r.yaw, how, "OK" if ok else "!! 다름"))
log(">>> %s" % ("Ctrl+S 저장 후 VR 프리뷰. 이 자리에서 시작." if ok else "!! 위 줄 복사해서 알려주세요."))
log("=" * 70)
