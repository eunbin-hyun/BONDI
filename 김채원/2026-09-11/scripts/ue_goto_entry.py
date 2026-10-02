# -*- coding: utf-8 -*-
"""
인왕제색도 - 액터 원점 정렬 + 축 매핑 자동 측정 + 카메라/PlayerStart 진입점 이동 (v2)
=====================================================================================
사용법 (언리얼 하단 콘솔, Cmd 모드):
    py "C:/KCW_SSAFY/특화/S15P21C201/김채원/2026-09-11/scripts/ue_goto_entry.py"

v2 변경
  - get_all_level_actors_of_class 는 없는 함수였음 → get_all_level_actors + isinstance 로 교체
  - entry_point.json 의 "UE_X=-gZ" 축 변환은 추정치였고 틀렸음. 이제 추정 안 하고 *측정*한다:
      trees 액터의 언리얼 바운딩 박스 vs glTF 바운딩 박스를 축별 크기로 대조해서
      glTF→UE 축 매핑(어느 축이 어느 축으로, 부호 포함)을 자동으로 알아낸 뒤 눈 위치를 변환
  - 7개 액터를 전부 위치(0,0,0)/회전0/스케일1 로 정렬 (드래그로 넣으면 커서 위치에 떨어짐)

작성: 김채원(AI) / 2026-09-11 / 번들 v0.11
"""

import math
import unreal

PARTS = ["terrain_jeong", "terrain_real", "base", "house", "trees", "fog", "inscription"]

# glTF 값 (m). 출처: records/entry_point.json, trees.glb accessor min/max
EYE_G   = (-1.0, 154.33, 1175.0)
FLOOR_G = 152.73
FWD_G   = (0.0, 0.0, -1.0)                    # glTF 전방 -Z
TREES_G_MIN = (-215.51, 152.88,   41.49)
TREES_G_MAX = ( 256.02, 542.67, 1147.19)

# PlayerStart 높이 = 바닥 + 캡슐 반높이(기본 90cm). ← 첫 추정치.
# VR 에서 발이 떠 있으면 줄이고, 파묻히면 늘림. 이 숫자만 고치고 다시 실행.
CAPSULE_HALF = 90.0

# 측정 실패 시 쓰는 기본 매핑 (언리얼 glTF 임포터 표준: UE=(gX, gZ, gY))
FALLBACK = [(0, +1), (2, +1), (1, +1)]


def log(msg):
    unreal.log("[INWANG] %s" % msg)


def close(a, b, tol=1.0):
    return abs(a - b) <= tol


sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors = {}
for a in sub.get_all_level_actors():
    actors.setdefault(a.get_actor_label(), a)

# ── 1) 7개 액터 원점 정렬 ─────────────────────────────────────────
log("=" * 70)
log("1) 액터 원점 정렬  (위치 0,0,0 / 회전 0 / 스케일 1)")
missing = []
for part in PARTS:
    act = actors.get(part)
    if act is None:
        log("   %-14s !! 레벨에 없음" % part)
        missing.append(part)
        continue
    before = act.get_actor_location()
    act.set_actor_location(unreal.Vector(0, 0, 0), False, False)
    act.set_actor_rotation(unreal.Rotator(0, 0, 0), False)
    act.set_actor_scale3d(unreal.Vector(1, 1, 1))
    log("   %-14s 이전 (%.0f, %.0f, %.0f) -> 원점" % (part, before.x, before.y, before.z))

# ── 2) 축 매핑 측정 ──────────────────────────────────────────────
log("=" * 70)
log("2) glTF -> UE 축 매핑 측정 (trees 바운딩 박스 대조)")
mapping = None
trees = actors.get("trees")
if trees is not None:
    origin, ext = trees.get_actor_bounds(False)
    ue_c = [origin.x, origin.y, origin.z]
    ue_e = [ext.x * 2, ext.y * 2, ext.z * 2]                  # 전체 폭 (cm)
    g_c = [(TREES_G_MIN[i] + TREES_G_MAX[i]) / 2 * 100 for i in range(3)]
    g_e = [(TREES_G_MAX[i] - TREES_G_MIN[i]) * 100 for i in range(3)]
    log("   UE   중심 (%.0f, %.0f, %.0f)  폭 (%.0f, %.0f, %.0f)" % tuple(ue_c + ue_e))
    log("   glTF 중심 (%.0f, %.0f, %.0f)  폭 (%.0f, %.0f, %.0f)" % tuple(g_c + g_e))
    m = []
    used = set()
    for i in range(3):
        best = None
        for j in range(3):
            if j in used:
                continue
            err = abs(ue_e[i] - g_e[j]) / g_e[j]
            if err < 0.03 and (best is None or err < best[1]):
                best = (j, err)
        if best is None:
            m = None
            break
        j = best[0]
        used.add(j)
        sign = +1 if (ue_c[i] * g_c[j]) >= 0 else -1
        m.append((j, sign))
    if m:
        mapping = m
        how = "측정"
    else:
        log("   !! 폭이 안 맞아서 매핑 못 정함 (스케일이 100 이 아닌가?)")
if mapping is None:
    mapping = FALLBACK
    how = "추정(기본값)"
names = "XYZ"
log("   매핑 [%s]:  UE_X = %sg%s,  UE_Y = %sg%s,  UE_Z = %sg%s" % (
    how,
    "+" if mapping[0][1] > 0 else "-", names[mapping[0][0]],
    "+" if mapping[1][1] > 0 else "-", names[mapping[1][0]],
    "+" if mapping[2][1] > 0 else "-", names[mapping[2][0]]))


def to_ue(g, scale=100.0):
    return [mapping[i][1] * g[mapping[i][0]] * scale for i in range(3)]


eye = to_ue(EYE_G)
fwd = to_ue(FWD_G, 1.0)
yaw = math.degrees(math.atan2(fwd[1], fwd[0]))
floor_z = to_ue((0.0, FLOOR_G, 0.0))[2] if mapping[2][0] == 1 else eye[2] - 160.0
ROT = unreal.Rotator(roll=0.0, pitch=0.0, yaw=yaw)

# ── 3) 에디터 카메라 ─────────────────────────────────────────────
log("=" * 70)
log("3) 에디터 카메라 -> (%.0f, %.0f, %.0f)  yaw %.0f" % (eye[0], eye[1], eye[2], yaw))
ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
ues.set_level_viewport_camera_info(unreal.Vector(*eye), ROT)
loc, rot = ues.get_level_viewport_camera_info()
cam_ok = close(loc.x, eye[0]) and close(loc.y, eye[1]) and close(loc.z, eye[2]) and close(rot.yaw, yaw)
log("   되읽음: (%.0f, %.0f, %.0f)  yaw %.0f   -> %s"
    % (loc.x, loc.y, loc.z, rot.yaw, "OK" if cam_ok else "!! 다름"))

# ── 4) PlayerStart ───────────────────────────────────────────────
log("=" * 70)
ps_z = floor_z + CAPSULE_HALF
PS = unreal.Vector(eye[0], eye[1], ps_z)
log("4) PlayerStart -> (%.0f, %.0f, %.0f)  yaw %.0f   (바닥 %.0f + 캡슐 %.0f)"
    % (eye[0], eye[1], ps_z, yaw, floor_z, CAPSULE_HALF))
starts = [a for a in sub.get_all_level_actors() if isinstance(a, unreal.PlayerStart)]
if starts:
    ps = starts[0]
    origin_s = "기존 %d개 중 1번째" % len(starts)
    ps.set_actor_location(PS, False, False)
    ps.set_actor_rotation(ROT, False)
else:
    ps = sub.spawn_actor_from_class(unreal.PlayerStart, PS, ROT)
    origin_s = "새로 생성"
ps.set_actor_label("PlayerStart_Inwang")
pl = ps.get_actor_location()
pr = ps.get_actor_rotation()
ps_ok = close(pl.x, eye[0]) and close(pl.y, eye[1]) and close(pl.z, ps_z)
log("   %s   되읽음: (%.0f, %.0f, %.0f)  yaw %.0f   -> %s"
    % (origin_s, pl.x, pl.y, pl.z, pr.yaw, "OK" if ps_ok else "!! 다름"))
if len(starts) > 1:
    log("   !! PlayerStart 가 %d개. 나머지는 안 건드림 - 시작 위치를 언리얼이 임의로 고를 수 있음." % len(starts))

# ── 판정 ─────────────────────────────────────────────────────────
log("-" * 70)
if cam_ok and ps_ok and not missing and how == "측정":
    log(">>> 성공. 뷰포트에 산이 정면. Ctrl+S 저장 후 VR Preview.")
else:
    log(">>> !! 붙은 줄(또는 '추정' 매핑 줄)을 그대로 복사해서 알려주세요.")
log("=" * 70)
