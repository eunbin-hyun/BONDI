# -*- coding: utf-8 -*-
"""
지금까지 만든 상태를 한 번에 되돌리기 (2026-09-14)
===================================================
왜: 스크립트를 하나 돌릴 때마다 다른 설정이 날아가는 일이 반복됐다.
    원인은 ue_setup_materials.py 가 **모든 파트의 머티리얼을 다시 만들어 덮어썼기** 때문 —
    지형 여백·AO·조명, 지붕 밑면 어둡게, 화제 금빛, 나무·안개 움직임이 전부 거기서 풀렸다.
    (v7.7 부터는 그 스크립트가 전용 스크립트 담당 파트를 건드리지 않는다. 이 파일은 그래도 뭔가 어긋났을 때의 복구용)

하는 일: 아래 STEPS 를 순서대로 실행한다. 각 스크립트의 스위치를 '원하는 값' 으로 **강제로 바꿔서** 돌리므로
    토글 스크립트가 반대로 뒤집히는 일이 없다. 바꾼 줄과 결과를 전부 로그에 찍는다.

사용법 (L_Inwang 열린 상태, 언리얼 콘솔):
    py "C:/KCW_SSAFY/특화/S15P21C201/김채원/2026-09-14/scripts/ue_restore_state.py"
    (L_Room_Inwang 은 소리만 해당 — 그 레벨을 열고 ue_place_sound.py 를 따로 한 번)
확인 지표: 단계마다 '── [n/N] 파일 … 덮어쓴 값 …' 과 '   → 끝' 또는 '   !! 실패'. 마지막에 '>>> 완료 n/N'.
빼고 싶은 단계는 아래 STEPS 에서 첫 칸을 False 로.
"""
import os, re, unreal

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in dir() else \
    r"C:\KCW_SSAFY\특화\S15P21C201\김채원\2026-09-14\scripts"

# (실행할지, 파일, {상수이름: 강제할 값(파이썬 표현식 문자열)})
STEPS = [
    (True,  "ue_setup_materials.py", {"SKIP_OWNED": "True"}),                      # 주인 없는 파트만 채움
    (True,  "ue_fix_hidden_in_game.py", {}),                                       # 보임/숨김 정리
    (True,  "ue_setup_shadows.py", {"MODE": "1"}),                                 # 해·하늘빛 + 그림자 던지기
    (True,  "ue_terrain_material.py", {"USE_EVIDENCE": "True", "USE_AO": "True", "USE_LIT": "True"}),
    (True,  "ue_house_material.py", {"USE_LIT": "True"}),                          # 지붕 밑면 어둡게 + Lit
    (True,  "ue_setup_motion.py", {"MOTION_ON": "True"}),                          # 나무 흔들림 · 안개 흐름
    (True,  "ue_toggle_shine.py", {"MODE": "1", "TARGET": '"inscription"'}),       # 화제 금빛
    (False, "ue_place_sound.py", {}),                                              # 소리 (레벨마다 따로 돌리는 게 나아 기본 꺼둠)
]


def log(m): unreal.log("[INWANG] %s" % m)


def force(src, name, value):
    """모듈 맨 위의 '이름 = …' 한 줄을 원하는 값으로 바꾼다. 못 찾으면 None"""
    pat = re.compile(r"^(%s)\s*=\s*[^\n]*$" % re.escape(name), re.M)
    if not pat.search(src): return None
    return pat.sub("%s = %s" % (name, value), src, count=1)


log("=" * 70)
log("상태 복구 — %d 단계" % sum(1 for e, _, _ in STEPS if e))
log("경로: %s" % HERE)
log("=" * 70)
done = 0; total = sum(1 for e, _, _ in STEPS if e); i = 0
for enabled, fname, overrides in STEPS:
    if not enabled: continue
    i += 1
    path = os.path.join(HERE, fname)
    if not os.path.exists(path):
        log("── [%d/%d] %-26s !! 파일 없음 (%s)" % (i, total, fname, path)); continue
    src = open(path, encoding="utf-8").read()
    applied = []
    for k, v in overrides.items():
        out = force(src, k, v)
        if out is None: applied.append("%s=못찾음" % k)
        else: src = out; applied.append("%s=%s" % (k, v))
    log("── [%d/%d] %-26s 덮어쓴 값: %s" % (i, total, fname, ", ".join(applied) if applied else "(없음)"))
    g = {"__name__": "__main__", "__file__": path}
    try:
        exec(compile(src, path, "exec"), g)
        done += 1; log("   → 끝")
    except SystemExit:
        done += 1; log("   → 끝 (스크립트가 스스로 중단 — 위 '!!' 줄 확인)")
    except Exception as ex:
        log("   !! 실패: %s: %s" % (type(ex).__name__, ex))

log("=" * 70)
log(">>> 완료 %d/%d 단계" % (done, total))
log("   이제 이 파일 하나만 돌리면 지금 상태가 그대로 복구된다.")
log("   소리는 레벨마다 따로: 각 레벨을 열고 ue_place_sound.py")
log("=" * 70)
