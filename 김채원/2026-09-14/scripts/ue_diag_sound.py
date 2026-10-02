# -*- coding: utf-8 -*-
"""
소리가 안 날 때 원인 찾기 (2026-09-14)
=======================================
소리는 '에셋 → 액터 → 감쇠 → 거리 → 출력장치' 순서 중 하나만 어긋나도 안 들린다.
이 스크립트는 **엔진 안에서 확인 가능한 앞의 네 단계**를 전부 찍는다. 마지막 출력장치만 눈으로 봐야 한다.

사용법 (소리가 안 나는 레벨을 연 상태, 언리얼 콘솔):
    py "C:/KCW_SSAFY/특화/S15P21C201/김채원/2026-09-14/scripts/ue_diag_sound.py"
확인 지표: 아래 '판정' 줄들. '!!' 가 붙은 게 원인 후보.
"""
import unreal

SND_PATH = "/Game/Museum/Inwang/sound/inwang_ambience"
sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
EAL = unreal.EditorAssetLibrary


def log(m): unreal.log("[INWANG] %s" % m)


def gp(o, n, d="-"):
    try: return o.get_editor_property(n)
    except Exception: return d


lvl = ""
try: lvl = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_name()
except Exception: pass
log("현재 레벨: %s" % lvl)

# ── 1) 사운드 에셋
snd = EAL.load_asset(SND_PATH) if EAL.does_asset_exist(SND_PATH) else None
if not isinstance(snd, unreal.SoundWave):
    log("!! 1단계 사운드 에셋 없음: %s  → ue_place_sound.py 를 먼저" % SND_PATH)
else:
    log("1단계 에셋 %s  길이 %.1f초  채널 %s  루프 %s  볼륨 %s" %
        (snd.get_name(), gp(snd, "duration", -1), gp(snd, "num_channels"), gp(snd, "looping"), gp(snd, "volume", "-")))
    if gp(snd, "looping") is not True:
        log("   !! 루프가 꺼져 있음 — 한 번 재생하고 끝난다. 사운드 에셋 열어 Looping 체크")
    if gp(snd, "num_channels") != 1:
        log("   !! 모노가 아님 — 거리 감쇠가 안 걸린다")

# ── 2) 액터
ps = next((x for x in sub.get_all_level_actors() if isinstance(x, unreal.PlayerStart)), None)
amb = [a for a in sub.get_all_level_actors() if a.get_actor_label().startswith("Amb_")]
log("2단계 소리 액터 %d개%s" % (len(amb), "" if amb else "   !! 이 레벨엔 없음 → 이 레벨을 연 채로 ue_place_sound.py 실행"))
for a in amb:
    c = a.get_component_by_class(unreal.AudioComponent)
    if c is None: log("   !! %s 오디오 컴포넌트 없음" % a.get_actor_label()); continue
    s_ = gp(c, "sound")
    vol = gp(c, "volume_multiplier", -1); pit = gp(c, "pitch_multiplier", -1)
    auto = gp(c, "auto_activate"); ovr = gp(c, "override_attenuation")
    p = a.get_actor_location()
    d = (((p.x - ps.get_actor_location().x) ** 2 + (p.y - ps.get_actor_location().y) ** 2 +
          (p.z - ps.get_actor_location().z) ** 2) ** 0.5 / 100.0) if ps else -1
    log("   %-18s 사운드 %s  볼륨 %.2f  음정 %.2f  자동재생 %s  감쇠override %s  PlayerStart 에서 %.1f m"
        % (a.get_actor_label(), s_.get_name() if s_ else "!! 없음", vol, pit, auto, ovr, d))
    if s_ is None: log("      !! 사운드가 안 꽂힘")
    if auto is not True: log("      !! 자동재생 꺼짐 — 플레이해도 안 울림")
    if ovr:
        at = gp(c, "attenuation_overrides")
        try:
            ext = at.get_editor_property("attenuation_shape_extents"); fall = at.get_editor_property("falloff_distance")
            r_in, r_out = ext.x / 100.0, ext.x / 100.0 + fall / 100.0
            log("      감쇠: %.1f m 까지 최대 → %.1f m 에서 0" % (r_in, r_out))
            if d >= 0 and d > r_out: log("      !! PlayerStart 가 감쇠 바깥(%.1f m > %.1f m) — 시작 지점에선 안 들림" % (d, r_out))
        except Exception as ex: log("      (감쇠 값 읽기 실패 %s)" % ex)
    else:
        log("      감쇠 override 꺼짐 — 기본 감쇠 사용(보통 거리와 무관하게 들림)")

log("―― 여기까지 '!!' 가 없으면 엔진 설정은 정상. 남은 건 출력 쪽 ――")
log("  · 에디터 상단 툴바나 뷰포트 ▾ 메뉴의 오디오 음소거가 켜져 있는지")
log("  · 플레이 방식: VR 프리뷰면 소리가 헤드셋으로 나간다. 헤드셋을 쓰고 있는지, 윈도우 기본 출력장치가 맞는지")
log("  · 에디터 환경설정 → 레벨 에디터 > 플레이 에 '사운드 비활성화' 류 옵션이 켜져 있는지")
log("  · 콘솔에 'au.Debug.Sounds 1' 을 치면 화면에 지금 재생 중인 소리 목록이 뜬다 (끄려면 0)")
