# -*- coding: utf-8 -*-
"""
음향 배치 — 그림 안팎 + 거리 감쇠 (2026-09-14)
================================================
음원: assets/sounds/inwang_ambience.wav  (원본 inwangjesaekdo.mp3 를 변환)
   - 언리얼은 MP3 를 임포트하지 못한다 → WAV(PCM 16bit) 로 변환해 둠
   - **모노** 로 변환했다. 스테레오 음원은 3D 위치·거리 감쇠가 걸리지 않는다 (엔진 규칙)
   - 원본이 피크 -28.8 dBFS 로 아주 작아 +22.8 dB 올려 피크 -6 dBFS 로 맞춤. 이음매 단차 0.00 % — 그대로 루프 가능

볼륨 단계 (전시실 ↔ 그림 안의 차이를 분명히)
   액자에서 1 m 밖   전체의 10 %      (Amb_RoomBed — 감쇠 없이 전시실 전체에 깔림)
   액자 바로 앞      전체의 30 %      (+ Amb_FromPainting 이 1 m 구간에서 선형으로 0 → 20 % 로 올라옴)
   그림 안(L_Inwang) 100 %            (Amb_Mountain)
   → 10 → 30 % 구간이 그라데이션. 컨트롤러 이동이 붙어도 "가까이 갈수록 스며들고, 들어가면 확 커진다" 가 유지된다.

사용법 (해당 레벨을 연 상태, 언리얼 콘솔):
    py "C:/KCW_SSAFY/특화/S15P21C201/김채원/2026-09-14/scripts/ue_place_sound.py"
   현재 열린 레벨 이름을 보고 알아서 고른다. 강제로 지정하려면 WHERE = "inwang" / "room".
확인 지표: '사운드 임포트 … 길이 124.7 초', 배치마다 '반경 … m → … m 에서 0', '>>> 배치 N개'
조절: PLAN 의 볼륨·반경·감쇠곡선. 단계 차이가 부족하면 바닥(Amb_RoomBed) 볼륨을 낮추는 게 가장 효과적이다.
"""
import os, unreal

WHERE = None            # None = 현재 레벨 보고 자동, "inwang" / "room" 으로 강제 가능
TEST_NO_ATTEN = False   # 감쇠 없이 어디서나 최대 볼륨으로 울리는 Amb_Test 를 하나 더 놓는다.
                        #   이게 들리면 → 감쇠 설정이 원인. 이것도 안 들리면 → 출력장치/음소거 쪽 (엔진 밖)
SND_DIR = r"C:\KCW_SSAFY\특화\S15P21C201\김채원\2026-09-14\assets\sounds"
SND_FILE = "inwang_ambience.wav"
PKG = "/Game/Museum/Inwang"
SND_PKG = PKG + "/sound"

# ── 볼륨 설계 (2026-09-14) ─────────────────────────────────────
#   전시실과 그림 안의 차이가 안 느껴진다는 지적 → 단계를 명확히 벌린다.
#      액자에서 1 m 밖   : 전체의 10 %
#      액자 바로 앞      : 전체의 30 %   (10 → 30 % 는 부드럽게 이어짐)
#      그림 안(L_Inwang): 100 %
#   언리얼 감쇠는 바깥반경에서 반드시 0 이 되므로 "멀어져도 10 % 유지" 를 감쇠 하나로는 못 만든다.
#   → 전시실을 두 겹으로 쌓는다.  바닥(감쇠 없음, 10 %) + 액자 근처(감쇠 있음, +20 %)  = 합쳐서 10~30 %
#   두 겹은 같은 순간에 재생을 시작하므로 파형이 어긋나지 않는다 (그래서 음정도 둘 다 1.00).
#
# (라벨, 기준액터(없으면 원점), 볼륨, 안쪽반경 m, 바깥반경 m, 음정, 감쇠곡선)
#   안쪽반경까지 최대 볼륨 → 바깥반경에서 0.  바깥반경 <= 안쪽반경 이면 감쇠를 안 건다(어디서나 최대).
#   감쇠곡선 "linear" = 거리에 비례해 고르게 줄어듦(짧은 구간의 그라데이션에 적합)
#                "natural" = 로그 곡선(넓은 야외에 적합)
PLAN = {
    # L_Inwang: 소리가 끊겨서 동시 재생을 2개 → 1개로 줄였다 (124초 12 MB 짜리는 디코더 부담이 크다).
    #   집 앞 소리를 다시 쓰려면 아래 주석을 풀 것 (끊김이 없어진 걸 확인한 뒤에).
    "inwang": [("Amb_Mountain", None, 1.00, 300.0, 2000.0, 1.00, "natural")],   # 그림 안 = 100 %
    #           ("Amb_House", "house_ink_big", 0.70, 12.0, 90.0, 0.94, "natural"),
    "room": [
        ("Amb_RoomBed",     "Painting_Inwang", 0.10, 0.0,  0.0, 1.00, "natural"),  # 바닥 10 % — 전시실 어디서나
        ("Amb_FromPainting", "Painting_Inwang", 0.20, 0.15, 1.0, 1.00, "linear"),  # 액자 앞에서 +20 % → 합 30 %
    ],
}

EAL = unreal.EditorAssetLibrary; TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem); LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


def log(m): unreal.log("[INWANG] %s" % m)


lvl = ""
try: lvl = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_name()
except Exception:
    try: lvl = unreal.EditorLevelLibrary.get_editor_world().get_name()
    except Exception as ex: log("   (참고) 레벨 이름을 못 읽음: %s" % ex)
key = WHERE or ("room" if "Room" in lvl else "inwang")
log("현재 레벨 '%s' → 배치안 '%s'" % (lvl, key))

# ── 1) 음원 임포트 ─────────────────────────────────────────────
name = SND_FILE.rsplit(".", 1)[0]
path = "%s/%s" % (SND_PKG, name)
snd = EAL.load_asset(path) if EAL.does_asset_exist(path) else None
if not isinstance(snd, unreal.SoundWave):
    src = os.path.join(SND_DIR, SND_FILE)
    if not os.path.exists(src): log("!! 음원 없음: %s" % src); raise SystemExit
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", src); t.set_editor_property("destination_path", SND_PKG)
    t.set_editor_property("replace_existing", True); t.set_editor_property("automated", True); t.set_editor_property("save", True)
    TOOLS.import_asset_tasks([t]); snd = EAL.load_asset(path)
if not isinstance(snd, unreal.SoundWave): log("!! 사운드 임포트 실패 (%s)" % path); raise SystemExit
try:
    dur = snd.get_editor_property("duration"); ch = snd.get_editor_property("num_channels")
except Exception: dur, ch = -1, -1
try:
    snd.set_editor_property("looping", True)
except Exception as ex: log("   (참고) 루프 설정 실패 — 사운드 에셋에서 Looping 체크: %s" % ex)
# 끊김 대책: 긴 사운드가 디스크에서 스트리밍되면 프레임이 튈 때마다 버퍼가 비어 뚝뚝 끊긴다.
#   메모리에 올려두고(RetainOnLoad) 스트리밍을 끄면 그 원인이 사라진다. 12 MB 정도는 메모리에 두어도 문제없다.
_lb = "-"
for nm, val in (("loading_behavior", "RETAIN_ON_LOAD"),):
    try:
        snd.set_editor_property(nm, getattr(unreal.SoundWaveLoadingBehavior, val)); _lb = val
    except Exception as ex: log("   (참고) %s 설정 실패: %s" % (nm, ex))
for nm in ("streaming", "is_streaming", "use_streaming"):
    try: snd.set_editor_property(nm, False); break
    except Exception: pass
EAL.save_loaded_asset(snd)
log("끊김 대책: 로딩방식 %s, 스트리밍 끔" % _lb)
log("사운드 임포트 %s  길이 %.1f 초  채널 %d (1 이어야 거리 감쇠가 걸림)" % (snd.get_name(), dur, ch))
if ch != 1: log("   !! 채널이 1 이 아님 — 스테레오는 3D 감쇠가 안 걸린다")

# ── 2) 배치 ───────────────────────────────────────────────────
A = {x.get_actor_label(): x for x in sub.get_all_level_actors()}
for lab in list(A):
    if lab.startswith("Amb_"): sub.destroy_actor(A[lab]); log("  기존 %s 제거" % lab)

plan = list(PLAN[key])
if TEST_NO_ATTEN: plan.append(("Amb_Test", None, 1.00, 0.0, 0.0, 1.00, "natural"))   # r_out <= r_in 이면 감쇠를 안 건다
n = 0
for label, anchor, vol, r_in, r_out, pitch, curve in plan:
    if anchor and anchor in A:
        o, e = A[anchor].get_actor_bounds(False); loc = unreal.Vector(o.x, o.y, o.z)
    elif anchor:
        log("  (참고) 기준 액터 %s 없음 — 원점에 배치" % anchor); loc = unreal.Vector(0, 0, 0)
    else:
        ps = next((x for x in sub.get_all_level_actors() if isinstance(x, unreal.PlayerStart)), None)
        loc = ps.get_actor_location() if ps else unreal.Vector(0, 0, 0)
    a = sub.spawn_actor_from_class(unreal.AmbientSound, loc, unreal.Rotator(0, 0, 0))
    a.set_actor_label(label); a.set_folder_path("Inwang/Sound")
    comp = a.get_component_by_class(unreal.AudioComponent)
    comp.set_editor_property("sound", snd)
    comp.set_editor_property("volume_multiplier", vol)
    try: comp.set_editor_property("pitch_multiplier", pitch)
    except Exception as ex: log("   (참고) 음정 설정 실패: %s" % ex)
    try: comp.set_editor_property("auto_activate", True)
    except Exception: pass
    if r_out <= r_in:                                   # 감쇠 없음 = 거리와 무관하게 최대 볼륨
        n += 1
        log("  %-18s (%.0f, %.0f, %.0f)  볼륨 %.2f (= 전체의 %.0f %%)  **감쇠 없음** — 이 레벨 어디서나 같은 크기"
            % (label, loc.x, loc.y, loc.z, vol, vol * 100))
        continue
    # 감쇠: 속성 이름이 엔진 버전마다 달라 하나씩 따로 넣고 성공 여부를 찍는다.
    #   (5.8 에서 enable_spatialization 이 없어 통째로 실패했던 문제 — 한 개가 없어도 나머지는 들어가게)
    s = unreal.SoundAttenuationSettings()
    done = []

    def setp(names, value, tag):
        for nm in ([names] if isinstance(names, str) else names):
            try:
                s.set_editor_property(nm, value); done.append("%s=%s" % (tag, nm)); return True
            except Exception: pass
        done.append("%s=없음" % tag); return False

    setp("attenuation_shape", unreal.AttenuationShape.SPHERE, "모양")
    setp("attenuation_shape_extents", unreal.Vector(r_in * 100.0, 0.0, 0.0), "안쪽반경")
    setp("falloff_distance", (r_out - r_in) * 100.0, "감쇠거리")
    _curve = unreal.AttenuationDistanceModel.LINEAR if curve == "linear" else unreal.AttenuationDistanceModel.NATURAL_SOUND
    setp(["distance_algorithm", "attenuation_function"], _curve, "감쇠곡선(%s)" % curve)
    setp(["spatialize", "enable_spatialization", "b_spatialize"], True, "3D화")
    ok_att = False
    try:
        comp.set_editor_property("attenuation_overrides", s)
        comp.set_editor_property("override_attenuation", True)
        got = comp.get_editor_property("attenuation_overrides")
        ext = got.get_editor_property("attenuation_shape_extents")
        fall = got.get_editor_property("falloff_distance")
        ok_att = abs(ext.x - r_in * 100.0) < 1.0 and abs(fall - (r_out - r_in) * 100.0) < 1.0
        log("   감쇠 속성 [%s]  → 컴포넌트에 적용 후 되읽기: 안쪽 %.0f m / 감쇠 %.0f m  일치 %s"
            % (", ".join(done), ext.x / 100.0, fall / 100.0, ok_att))
    except Exception as ex: log("   !! %s 감쇠 적용 실패: %s" % (label, ex))
    n += 1
    log("  %-18s (%.0f, %.0f, %.0f)  볼륨 %.2f  반경 %.0f m 까지 최대 → %.0f m 에서 0   감쇠설정 %s"
        % (label, loc.x, loc.y, loc.z, vol, r_in, r_out, ok_att))
    log("      음정 %.2f · 곡선 %s" % (pitch, curve))

if key == "room":
    _bed = sum(v for (_l, _a, v, ri, ro, _p, _c) in plan if ro <= ri)
    _near = sum(v for (_l, _a, v, ri, ro, _p, _c) in plan if ro > ri)
    log(">>> 전시실 볼륨 설계:  1 m 밖 %.0f %%  →  액자 앞 %.0f %%   (그림 안은 100 %%)" % (_bed * 100, (_bed + _near) * 100))
log(">>> 배치 %d개.  플레이해서 확인 — 액자로 다가갈수록 커지고, 그림 안으로 들어가면 확 커져야 함" % n)
log("   아직도 끊기면 프레임 문제다. 플레이 중 콘솔에 'stat unit' 을 치고 Frame 이 VR 목표(90fps = 11.1 ms)를 넘는지 볼 것")
if TEST_NO_ATTEN:
    log("   [판정] Amb_Test 가 들린다 → 감쇠 설정 문제.  Amb_Test 도 안 들린다 → 엔진 밖(출력장치·음소거·VR 헤드셋)")
    log("   확인 끝나면 TEST_NO_ATTEN = False 로 두고 다시 실행해 Amb_Test 를 없앨 것")
log("레벨 저장 %s" % LES.save_current_level())
