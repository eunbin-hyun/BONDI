# -*- coding: utf-8 -*-
"""
인왕제색도 - 텔레포트용 NavMesh 설정
====================================
사용법 (언리얼 하단 콘솔, Cmd 모드):
    py "C:/KCW_SSAFY/특화/S15P21C201/김채원/2026-09-11/scripts/ue_setup_navmesh.py"

전제: 배치 액터 패널에서 `Nav Mesh Bounds Volume` 을 레벨에 하나 드래그해 둔 상태.
      (Python 으로 볼륨을 직접 생성하면 브러시가 비어서 동작 안 함 — 그래서 이 한 번만 손으로)

하는 일
  1) NavMeshBoundsVolume 을 PlayerStart_Inwang 중심, 300 m x 300 m, 바닥 ±50 m 로 이동·크기 조정
  2) 바닥 메시(base / terrain_real / terrain_jeong) 충돌을 '복잡한 형태 그대로(Complex as Simple)' 로
     → 임포트 지형은 단순 충돌이 없어 텔레포트 포물선이 땅을 못 맞추는 경우가 흔함
  3) RebuildNavigation 콘솔 명령
  4) 되읽어서 표로 출력

확인 지표: 뷰포트에서 P 키 → 바닥에 초록색 영역. VR 에서 오른손 스틱 앞으로 → 포물선.

작성: 김채원(AI) / 2026-09-11
"""

import unreal

PKG = "/Game/Museum/Inwang"
GROUND_PARTS = ["base", "terrain_real", "terrain_jeong"]
SIZE_XY_CM = 30000.0        # 300 m
SIZE_Z_CM  = 10000.0        # ±50 m
CAPSULE_HALF = 90.0         # ue_goto_entry.py 와 같은 값


def log(msg):
    unreal.log("[INWANG] %s" % msg)


sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors = sub.get_all_level_actors()
labels = {}
for a in actors:
    labels.setdefault(a.get_actor_label(), a)

fail = 0

# ── 1) NavMeshBoundsVolume ───────────────────────────────────────
log("=" * 70)
log("1) NavMeshBoundsVolume")
vols = [a for a in actors if isinstance(a, unreal.NavMeshBoundsVolume)]
if not vols:
    log("   !! 레벨에 NavMeshBoundsVolume 없음. 배치 액터 → 'Nav Mesh Bounds Volume' 드래그 후 다시 실행.")
    fail += 1
else:
    vol = vols[0]
    ps = labels.get("PlayerStart_Inwang")
    if ps is None:
        log("   !! PlayerStart_Inwang 없음. ue_goto_entry.py 먼저 실행.")
        fail += 1
    else:
        p = ps.get_actor_location()
        floor_z = p.z - CAPSULE_HALF
        # 현재 브러시 크기를 재서 목표 크기가 되도록 스케일 계산 (기본 크기 가정 안 함)
        vol.set_actor_scale3d(unreal.Vector(1, 1, 1))
        _, ext = vol.get_actor_bounds(False)
        cur = [ext.x * 2, ext.y * 2, ext.z * 2]
        if min(cur) <= 0:
            log("   !! 볼륨 크기가 0 (브러시 없음). 볼륨 지우고 배치 액터에서 다시 드래그.")
            fail += 1
        else:
            sc = unreal.Vector(SIZE_XY_CM / cur[0], SIZE_XY_CM / cur[1], SIZE_Z_CM / cur[2])
            vol.set_actor_location(unreal.Vector(p.x, p.y, floor_z), False, False)
            vol.set_actor_scale3d(sc)
            o, e = vol.get_actor_bounds(False)
            log("   중심 (%.0f, %.0f, %.0f)  크기 %.0f x %.0f x %.0f m   (볼륨 %d개 중 1번째)"
                % (o.x, o.y, o.z, e.x * 2 / 100, e.y * 2 / 100, e.z * 2 / 100, len(vols)))
            ok = abs(e.x * 2 - SIZE_XY_CM) < 100 and abs(e.z * 2 - SIZE_Z_CM) < 100
            log("   판정: %s" % ("OK" if ok else "!! 크기 다름"))
            fail += 0 if ok else 1

# ── 2) 바닥 메시 충돌 ────────────────────────────────────────────
log("=" * 70)
log("2) 바닥 메시 충돌 → Complex as Simple")
EAL = unreal.EditorAssetLibrary
for part in GROUND_PARTS:
    act = labels.get(part)
    if act is None:
        log("   %-14s !! 액터 없음" % part)
        fail += 1
        continue
    comp = act.get_component_by_class(unreal.StaticMeshComponent)
    sm = comp.static_mesh if comp else None
    if sm is None:
        log("   %-14s !! 스태틱 메시 없음" % part)
        fail += 1
        continue
    bs = sm.get_editor_property("body_setup")
    if bs is None:
        log("   %-14s !! body_setup 없음" % part)
        fail += 1
        continue
    before = bs.get_editor_property("collision_trace_flag")
    bs.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    after = bs.get_editor_property("collision_trace_flag")
    EAL.save_loaded_asset(sm)
    comp.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
    log("   %-14s %s -> %s   저장" % (part, before, after))

# ── 3) NavMesh 재생성 ───────────────────────────────────────────
log("=" * 70)
log("3) RebuildNavigation")
try:
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.SystemLibrary.execute_console_command(world, "RebuildNavigation")
    log("   명령 보냄. 생성은 비동기라 몇 초 걸림.")
except Exception as e:
    log("   !! 실패: %s  → 콘솔에 직접 RebuildNavigation 입력" % e)

log("-" * 70)
if fail == 0:
    log(">>> 설정 완료. 뷰포트 클릭 후 P 키 → 바닥에 초록색이 보이면 성공. Ctrl+S.")
else:
    log(">>> !! 붙은 줄 %d개. 그대로 복사해서 알려주세요." % fail)
log("=" * 70)
