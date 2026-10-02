# -*- coding: utf-8 -*-
"""
디오라마 조각들 트랜스폼 맞추기 (2026-09-14)
=============================================
모형은 지형·집·안내판·나무 4덩어리가 **같은 원점**에 겹쳐 있어야 한 덩어리로 보인다.
하나를 옮기거나 크기를 바꾸면 나머지가 어긋나므로, 기준 하나에 전부 맞춘다.
표석(DioMark_*)은 같은 트랜스폼이 아니라 **모형 위 제자리**여야 하므로,
   records/diorama.json 의 모형 좌표를 기준 액터의 회전·크기·위치로 변환해 다시 놓는다.

사용법 (L_Inwang 열린 상태, 언리얼 콘솔):
    py "C:/KCW_SSAFY/특화/S15P21C201/김채원/2026-09-14/scripts/ue_sync_diorama.py"
확인 지표: '기준 … 위치/회전/크기', 조각마다 '맞춤', 표석마다 '모형 위 (…)'.
           마지막 '>>> 조각 N개 일치, 표석 M개 재배치'.
쓰는 법: 에디터에서 기준(REF) 하나만 마음대로 옮기고/돌리고/키운 다음 이 스크립트를 돌리면 나머지가 따라온다.
"""
import os, json, unreal

REF = "Diorama_dio_terrain"      # 이 액터의 트랜스폼을 기준으로 삼는다
MOVE_MARKS = True                # 표석도 다시 놓을지
RECD = os.path.join(r"C:\Users\SSAFY\Desktop\SSAFY_2학기\02_특화 프로젝트\특화PJT_\landscape_to_3D\Claude outputs\VR_inwangjesaekdo_v0.11\inwangjesaekdo_VR_v0.11", "records")

sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


def log(m): unreal.log("[INWANG] %s" % m)


A = {x.get_actor_label(): x for x in sub.get_all_level_actors()}
ref = A.get(REF)
if ref is None:
    log("!! 기준 액터 '%s' 없음 — 현재 레벨이 L_Inwang 인지, ue_place_diorama.py 를 돌렸는지 확인" % REF)
    raise SystemExit
loc = ref.get_actor_location(); rot = ref.get_actor_rotation(); sc = ref.get_actor_scale3d()
log("기준 %s   위치 (%.1f, %.1f, %.1f)  회전 (P %.1f, Y %.1f, R %.1f)  크기 (%.3f, %.3f, %.3f)"
    % (REF, loc.x, loc.y, loc.z, rot.pitch, rot.yaw, rot.roll, sc.x, sc.y, sc.z))

# ── 1) 조각 4개를 기준과 동일하게
n = 0
for lab, a in sorted(A.items()):
    if not lab.startswith("Diorama_") or lab == REF: continue
    a.set_actor_location(loc, False, False)
    a.set_actor_rotation(rot, False)
    a.set_actor_scale3d(sc)
    p = a.get_actor_location(); r = a.get_actor_rotation(); s = a.get_actor_scale3d()
    same = (abs(p.x - loc.x) < 0.1 and abs(p.y - loc.y) < 0.1 and abs(p.z - loc.z) < 0.1
            and abs(r.yaw - rot.yaw) < 0.01 and abs(s.x - sc.x) < 1e-4)
    n += int(same)
    log("  %-24s 맞춤 %s" % (lab, "OK" if same else "!! 값이 안 들어감"))

# ── 2) 표석은 '모형 위 제자리' 로 다시
m = 0
if MOVE_MARKS:
    DJ_PATH = os.path.join(RECD, "diorama.json")
    if not os.path.exists(DJ_PATH):
        log("   (참고) %s 없음 — 표석은 그대로 둠" % DJ_PATH)
    else:
        DJ = json.load(open(DJ_PATH, encoding="utf-8"))
        t = ref.get_actor_transform()
        for mk in DJ["표석"]:
            lab = "DioMark_%s" % mk["name"]
            a = A.get(lab)
            if a is None: log("   (참고) %s 없음" % lab); continue
            mx, my, mz = mk["모형_xyz_m"]                       # glb(m) → 언리얼 로컬(cm): (x, z, y)
            local = unreal.Vector(mx * 100.0, mz * 100.0, my * 100.0)
            try: w = unreal.MathLibrary.transform_location(t, local)
            except Exception:
                w = unreal.Vector(loc.x + sc.x * local.x, loc.y + sc.y * local.y, loc.z + sc.z * local.z)
                log("      (참고) 회전 반영 못함 — 위치·크기만 적용")
            a.set_actor_location(w, False, False)
            a.set_actor_rotation(rot, False)
            m += 1
            log("  %-24s 모형 위 (%.1f, %.1f, %.1f)" % (lab, w.x, w.y, w.z))

log(">>> 조각 %d개 일치, 표석 %d개 재배치" % (n, m))
log("레벨 저장 %s" % LES.save_current_level())
