# -*- coding: utf-8 -*-
"""
그림자 A — 조명·그림자 설정 (2026-09-14)  ※ 머티리얼은 ue_terrain_material.py 담당
=====================================================================================
문제: 전부 Unlit + Emissive 라 빛 계산이 없어 그림자가 생길 곳이 없다. 공간이 붕 뜬 느낌.
      그렇다고 그냥 Lit 으로 바꾸면 원화가 이미 그려놓은 먹 명암 위에 엔진 음영이 또 얹혀 이중 음영이 된다.
해법: (이 스크립트) 원화에서 역산한 방향으로 태양·하늘빛을 세우고, 무엇이 그림자를 던질지 정한다.
      (ue_terrain_material.py) 지형을 Lit 으로 바꾸되 월드 법선을 광원 방향으로 고정 → 밝기는 평평, 남는 변화는 그림자뿐.

광원 방향: records/sun_fit.json — 원화 투영 텍스처의 밝기와 지형 법선의 N·L 상관을 최대화해 구한 값.
      (방위 12° · 고도 74°, 상관 +0.38 — 비 갠 직후라 강한 방향광이 없어 상관이 약하다. 그래서 짧고 바짝 붙은 그림자가 맞다)

사용법 (L_Inwang 열린 상태, 언리얼 콘솔):
    py "C:/KCW_SSAFY/특화/S15P21C201/김채원/2026-09-12/scripts/ue_setup_shadows.py"
실행할 때마다 끔 ↔ 켬 토글 (기준 = Sun_Inwang 액터가 있는지). MODE = 0/1 로 직접 지정 가능.

확인 지표:
  '태양 각도: pitch … yaw …'  / '그림자 던지는 액터 N개, 끈 액터 M개' / '>>> 지금: 켜짐'
  밝기가 Unlit 때와 다르면 LIGHT_LUX/SKY_LUX 또는 ue_terrain_material.py 의 BASE_GAIN 을 조절 — 토글로 껐다 켜며 비교할 것.
조절: LIGHT_LUX(해 세기) · SKY_LUX(하늘빛 = 그림자 속 밝기) · SUN_SOFT_DEG(그림자 가장자리 번짐)
"""
import os, json, math, unreal

MODE = None                 # None = 토글, 0 끔(조명 제거) / 1 켬
LIGHT_LUX = 3.2             # 해 세기. 램버트 확산이 1/π 를 먹으므로 π 근처가 '원래 밝기'에 가깝다 (눈으로 맞출 것)
SKY_LUX = 1.0               # 하늘빛. 이 값이 그림자 속 밝기를 정한다 (0 이면 그림자가 새까맣게)
SUN_SOFT_DEG = 3.0          # 해의 겉보기 크기(도). 클수록 그림자 가장자리가 부드러움 (실제 해는 0.53°)
SHADOW_DIST_CM = 120000.0   # 동적 그림자 유효 거리
CAST_ON = ["house_ink_small", "house_ink_big", "house_ink", "inscription_board", "trees_cards"]
CAST_OFF = ["fog_l0", "fog_l1", "fog_l2", "fog_l3", "fog_l4", "inscription", "SM_SkySphere", "Exit_Beam"]

RT = r"C:\Users\SSAFY\Desktop\SSAFY_2학기\02_특화 프로젝트\특화PJT_\landscape_to_3D\Claude outputs\VR_inwangjesaekdo_v0.11\inwangjesaekdo_VR_v0.11\runtime"
SUN_JSON = os.path.join(os.path.dirname(RT), "records", "sun_fit.json")
PKG = "/Game/Museum/Inwang"

EAL = unreal.EditorAssetLibrary; ML = unreal.MaterialEditingLibrary; TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem); LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


def log(m): unreal.log("[INWANG] %s" % m)


A = {x.get_actor_label(): x for x in sub.get_all_level_actors()}
nxt = MODE if MODE is not None else (0 if "Sun_Inwang" in A else 1)

# ── 끄기: 원래 Unlit 머티리얼로, 조명 액터 제거 ─────────────────
if nxt == 0:
    for lab in ("Sun_Inwang", "Sky_Inwang"):
        if lab in A: sub.destroy_actor(A[lab]); log("  %s 제거" % lab)
    log(">>> 지금: 꺼짐 (조명 액터 제거). 지형을 Unlit 으로 되돌리려면 ue_terrain_material.py 를 USE_LIT=False 로 실행")
    log("레벨 저장 %s" % LES.save_current_level()); raise SystemExit

# ── 1) 태양 방향 ───────────────────────────────────────────────
if os.path.exists(SUN_JSON):
    S = json.load(open(SUN_JSON, encoding="utf-8")); Lg = S["L_glb"]
    log("광원 근거: %s (방위 %s° · 고도 %s° · 상관 %s)" % (os.path.basename(SUN_JSON), S["방위_deg"], S["고도_deg"], S["상관"]))
else:
    Lg = [0.057, 0.961, -0.270]; log("   (참고) sun_fit.json 없음 — 기본값 사용 %s" % Lg)
# glb → 언리얼 월드: UE_X = gX, UE_Y = gZ, UE_Z = gY  (house_ink 중심 좌표 대조로 확인된 대응)
Lue = (Lg[0], Lg[2], Lg[1])                       # 빛이 '오는' 쪽
n = math.sqrt(sum(v * v for v in Lue)) or 1.0
Lue = tuple(v / n for v in Lue)
fwd = tuple(-v for v in Lue)                      # 빛이 '가는' 쪽 = 라이트의 정면
pitch = math.degrees(math.asin(max(-1.0, min(1.0, fwd[2]))))
yaw = math.degrees(math.atan2(fwd[1], fwd[0]))
log("태양 각도: pitch %.1f° yaw %.1f°   (빛이 오는 방향 벡터 %.3f, %.3f, %.3f)" % (pitch, yaw, Lue[0], Lue[1], Lue[2]))

for lab in ("Sun_Inwang", "Sky_Inwang"):
    if lab in A: sub.destroy_actor(A[lab])
sun = sub.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 50000), unreal.Rotator(0, pitch, yaw))
sun.set_actor_label("Sun_Inwang"); sun.set_folder_path("Lighting")
sc = sun.get_component_by_class(unreal.DirectionalLightComponent)
try:
    sc.set_mobility(unreal.ComponentMobility.MOVABLE)
    sc.set_editor_property("intensity", LIGHT_LUX)
    sc.set_editor_property("cast_shadows", True)
    sc.set_editor_property("dynamic_shadow_distance_movable_light", SHADOW_DIST_CM)
    sc.set_editor_property("light_source_angle", SUN_SOFT_DEG)
except Exception as ex: log("   (참고) 태양 속성 일부 설정 실패: %s" % ex)
sky = sub.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 50000), unreal.Rotator(0, 0, 0))
sky.set_actor_label("Sky_Inwang"); sky.set_folder_path("Lighting")
kc = sky.get_component_by_class(unreal.SkyLightComponent)
try:
    kc.set_mobility(unreal.ComponentMobility.MOVABLE)
    kc.set_editor_property("intensity", SKY_LUX)
    kc.set_editor_property("real_time_capture", True)
    kc.set_editor_property("cast_shadows", False)
except Exception as ex: log("   (참고) 하늘빛 속성 일부 설정 실패: %s" % ex)
log("태양 %.2f lux (겉보기 %.1f°) · 하늘빛 %.2f lux — 하늘빛이 그림자 속 밝기를 정함" % (LIGHT_LUX, SUN_SOFT_DEG, SKY_LUX))

# ── 2) 그림자 던지기 on/off ────────────────────────────────────
n_on = n_off = 0
for lab, want in [(l, True) for l in CAST_ON] + [(l, False) for l in CAST_OFF]:
    a = A.get(lab)
    if a is None: continue
    c = a.get_component_by_class(unreal.StaticMeshComponent)
    if c is None: continue
    try:
        c.set_editor_property("cast_shadow", want)
        if want: c.set_mobility(unreal.ComponentMobility.MOVABLE)      # 정적 조명 굽기 없이 동적 그림자
        n_on += int(want); n_off += int(not want)
    except Exception as ex: log("   (참고) %s cast_shadow 설정 실패: %s" % (lab, ex))
log("그림자 던지는 액터 %d개, 끈 액터 %d개 (안개·하늘·빛기둥은 꺼야 화면이 탁해지지 않음)" % (n_on, n_off))


log(">>> 지금: 켜짐 — 조명·그림자 설정 완료.")
log("    지형이 그림자를 '받으려면' ue_terrain_material.py 를 USE_LIT=True 로 한 번 실행해야 한다 (Unlit 은 그림자를 못 받음)")
log("    밝기가 예전과 다르면 LIGHT_LUX / SKY_LUX, 또는 ue_terrain_material.py 의 BASE_GAIN 을 조절")
log("레벨 저장 %s" % LES.save_current_level())
