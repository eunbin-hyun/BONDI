# -*- coding: utf-8 -*-
"""
인왕제색도 - 안개 흐름 + 나무 흔들림 (움직이는 머티리얼)
========================================================
사용법 (언리얼 하단 콘솔, Cmd 모드):
    py "C:/KCW_SSAFY/특화/S15P21C201/김채원/2026-09-11/scripts/ue_setup_motion.py"

전제: ue_setup_materials.py 가 성공한 상태 (7 액터에 Unlit 머티리얼).
      trees.glb 는 v4b (TEXCOORD_0.x = 나무 내 높이 비율 0~1) — 09-11 오후 파일.
      (마스크를 정점 알파 대신 UV 에 둔 이유: 알파 해석이 도구마다 달라서. '알파 때문에 정점색이 사라진다'는 09-11 오후 진단은 틀렸었음)

하는 일 (기존 머티리얼은 안 건드림. 새 머티리얼 2개를 만들고, 노드 연결이 전부 성공했을 때만 바꿔 낌)
  M_InwangFogDrift  : 정점색 → Emissive,  Opacity = 정점알파 × Noise(월드좌표 + 시간×바람)   → 안개가 천천히 흐름
  M_InwangTreesSway : 정점색 → Emissive,  WorldPositionOffset = sin(시간) × 진폭 × UV0.x(마스크)  → 꼭대기만 흔들림

확인 지표: 뷰포트 왼쪽 위 ▾ → '실시간' 체크(단축키 Ctrl+R) 상태에서 안개 농도가 천천히 변하고 나무 윗부분이 흔들림.
           안 움직이면 로그의 '!!' 줄 또는 아래 NANITE 항목 참고.

조절값: WIND (안개 흐름 cm/s), FOG_SCALE (덩어리 크기), SWAY_AMP (나무 진폭 cm), SWAY_SPEED

작성: 김채원(AI) / 2026-09-11
"""

import unreal

PKG = "/Game/Museum/Inwang"
ML  = unreal.MaterialEditingLibrary
EAL = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()

WIND       = (120.0, 40.0, 0.0)   # 안개 흐름 속도 cm/s (X,Y,Z)
FOG_SCALE  = 1.0 / 6000.0         # 노이즈 덩어리 크기: 1/cm  (6000 → 약 60 m 덩어리)
FOG_MIN    = 0.45                 # 농도 최소 배율 (0 이면 구멍이 뚫림)
SWAY_AMP   = (35.0, 20.0, 0.0)    # 나무 꼭대기 최대 변위 cm
SWAY_SPEED = 0.9                  # 흔들림 주기 (rad/s)
NANITE_OFF_FOR_TREES = False      # 나무가 안 흔들리면 True 로 바꿔 다시 실행 (Nanite 에서 WPO 가 막힌 경우)

log_lines = []


def log(msg):
    unreal.log("[INWANG] %s" % msg)


class Fail(Exception):
    pass


def mk(mat, cls, x, y, **props):
    e = ML.create_material_expression(mat, cls, x, y)
    for k, v in props.items():
        e.set_editor_property(k, v)
    return e


def link(src, src_outs, dst, dst_ins, what):
    """출력 이름·입력 이름 후보를 순서대로 시도. 성공한 조합을 로그. 실패면 Fail."""
    for o in src_outs:
        for i in dst_ins:
            try:
                if ML.connect_material_expressions(src, o, dst, i):
                    log("   연결 OK  %-34s (out=%r in=%r)" % (what, o, i))
                    return
            except Exception:
                pass
    raise Fail("연결 실패 %s  (out 후보 %r, in 후보 %r)" % (what, src_outs, dst_ins))


def link_prop(src, src_outs, prop, what):
    for o in src_outs:
        try:
            if ML.connect_material_property(src, o, prop):
                log("   연결 OK  %-34s (out=%r)" % (what, o))
                return
        except Exception:
            pass
    raise Fail("연결 실패 %s" % what)


def new_material(name, translucent):
    path = "%s/%s" % (PKG, name)
    if EAL.does_asset_exist(path):
        mat = EAL.load_asset(path)
        ML.delete_all_material_expressions(mat)
    else:
        mat = TOOLS.create_asset(name, PKG, unreal.Material, unreal.MaterialFactoryNew())
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT if translucent else unreal.BlendMode.BLEND_OPAQUE)
    mat.set_editor_property("two_sided", bool(translucent))
    for flag in ("used_with_nanite",):
        try:
            mat.set_editor_property(flag, True)
        except Exception:
            log("   (참고) %s 플래그 설정 불가 — 무시" % flag)
    return mat, path


MP_EMISSIVE = unreal.MaterialProperty.MP_EMISSIVE_COLOR
MP_OPACITY  = unreal.MaterialProperty.MP_OPACITY
MP_WPO      = unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET
IN_A, IN_B = ["A"], ["B"]
OUT = [""]            # 대부분 노드의 첫 출력
IN_ANY = ["", "Input", "Position"]


def build_fog():
    mat, path = new_material("M_InwangFogDrift", translucent=True)
    vc   = mk(mat, unreal.MaterialExpressionVertexColor, -900, -200)
    wpos = mk(mat, unreal.MaterialExpressionWorldPosition, -1400, 100)
    time = mk(mat, unreal.MaterialExpressionTime, -1400, 300)
    wind = mk(mat, unreal.MaterialExpressionConstant3Vector, -1400, 420,
              constant=unreal.LinearColor(WIND[0], WIND[1], WIND[2], 0.0))
    mul_tw = mk(mat, unreal.MaterialExpressionMultiply, -1150, 320)
    add    = mk(mat, unreal.MaterialExpressionAdd, -950, 150)
    noise  = mk(mat, unreal.MaterialExpressionNoise, -700, 150,
                scale=FOG_SCALE, output_min=FOG_MIN, output_max=1.0, turbulence=False)
    mul_o  = mk(mat, unreal.MaterialExpressionMultiply, -400, 0)

    link(time, OUT, mul_tw, IN_A, "Time → Mul.A")
    link(wind, OUT, mul_tw, IN_B, "Wind → Mul.B")
    link(wpos, OUT, add, IN_A, "WorldPos → Add.A")
    link(mul_tw, OUT, add, IN_B, "Time*Wind → Add.B")
    link(add, OUT, noise, ["Position", ""], "Add → Noise.Position")
    link(noise, OUT, mul_o, IN_A, "Noise → Mul.A")
    link(vc, ["A"], mul_o, IN_B, "VertexColor.A → Mul.B")
    link_prop(vc, ["", "RGB"], MP_EMISSIVE, "VertexColor.RGB → Emissive")
    link_prop(mul_o, OUT, MP_OPACITY, "Noise*A → Opacity")
    ML.recompile_material(mat)
    EAL.save_asset(path)
    return mat


def build_trees():
    mat, path = new_material("M_InwangTreesSway", translucent=False)
    vc    = mk(mat, unreal.MaterialExpressionVertexColor, -900, -200)
    wpos  = mk(mat, unreal.MaterialExpressionWorldPosition, -1600, 200)
    maskx = mk(mat, unreal.MaterialExpressionComponentMask, -1400, 200, r=True, g=False, b=False, a=False)
    phase = mk(mat, unreal.MaterialExpressionConstant, -1400, 320, r=0.002)
    mul_p = mk(mat, unreal.MaterialExpressionMultiply, -1200, 250)
    time  = mk(mat, unreal.MaterialExpressionTime, -1400, 450)
    spd   = mk(mat, unreal.MaterialExpressionConstant, -1400, 550, r=SWAY_SPEED)
    mul_t = mk(mat, unreal.MaterialExpressionMultiply, -1200, 480)
    add   = mk(mat, unreal.MaterialExpressionAdd, -1000, 350)
    sine  = mk(mat, unreal.MaterialExpressionSine, -800, 350)
    amp   = mk(mat, unreal.MaterialExpressionConstant3Vector, -800, 500,
               constant=unreal.LinearColor(SWAY_AMP[0], SWAY_AMP[1], SWAY_AMP[2], 0.0))
    mul_a = mk(mat, unreal.MaterialExpressionMultiply, -600, 400)
    mul_m = mk(mat, unreal.MaterialExpressionMultiply, -400, 300)
    uv    = mk(mat, unreal.MaterialExpressionTextureCoordinate, -900, 600, coordinate_index=0)
    masku = mk(mat, unreal.MaterialExpressionComponentMask, -700, 600, r=True, g=False, b=False, a=False)

    link(wpos, OUT, maskx, IN_ANY, "WorldPos → Mask(R)")
    link(maskx, OUT, mul_p, IN_A, "Mask → Mul.A")
    link(phase, OUT, mul_p, IN_B, "phase → Mul.B")
    link(time, OUT, mul_t, IN_A, "Time → Mul.A")
    link(spd, OUT, mul_t, IN_B, "speed → Mul.B")
    link(mul_p, OUT, add, IN_A, "phase*x → Add.A")
    link(mul_t, OUT, add, IN_B, "time*speed → Add.B")
    link(add, OUT, sine, IN_ANY, "Add → Sine")
    link(sine, OUT, mul_a, IN_A, "Sine → Mul.A")
    link(amp, OUT, mul_a, IN_B, "amp → Mul.B")
    link(mul_a, OUT, mul_m, IN_A, "Sine*amp → Mul.A")
    link(uv, OUT, masku, IN_ANY, "UV0 → Mask(R)")
    link(masku, OUT, mul_m, IN_B, "UV0.x(마스크) → Mul.B")
    link_prop(vc, ["", "RGB"], MP_EMISSIVE, "VertexColor.RGB → Emissive")
    link_prop(mul_m, OUT, MP_WPO, "→ WorldPositionOffset")
    ML.recompile_material(mat)
    EAL.save_asset(path)
    return mat


def assign(part, mat):
    sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in sub.get_all_level_actors():
        if a.get_actor_label() == part:
            comp = a.get_component_by_class(unreal.StaticMeshComponent)
            comp.set_material(0, mat)
            got = comp.get_material(0)
            ok = got is not None and got.get_name() == mat.get_name()
            log("   액터 %-8s ← %-20s %s" % (part, mat.get_name(), "OK" if ok else "!! 다름"))
            if NANITE_OFF_FOR_TREES and part == "trees":
                sm = comp.static_mesh
                ns = sm.get_editor_property("nanite_settings")
                ns.set_editor_property("enabled", False)
                sm.set_editor_property("nanite_settings", ns)
                EAL.save_loaded_asset(sm)
                log("   trees 스태틱 메시 Nanite 끔 (WPO 용)")
            return ok
    log("   !! 액터 %s 없음" % part)
    return False


results = {}
for name, fn, part in (("안개 흐름", build_fog, "fog"), ("나무 흔들림", build_trees, "trees")):
    log("=" * 70)
    log(name)
    try:
        mat = fn()
        results[part] = assign(part, mat)
    except Fail as e:
        log("   !! %s  → 이 파트는 기존 머티리얼 그대로 둠" % e)
        results[part] = False
    except Exception as e:
        log("   !! 예외: %r  → 이 파트는 기존 머티리얼 그대로 둠" % (e,))
        results[part] = False

log("-" * 70)
if all(results.values()):
    log(">>> 성공. 뷰포트 '실시간'(Ctrl+R) 켜고 안개 농도 변화·나무 윗부분 흔들림 확인. Ctrl+S.")
else:
    log(">>> !! %s 실패. '!!' 줄을 그대로 복사해서 알려주세요. (성공한 쪽은 적용됨)"
        % ", ".join(k for k, v in results.items() if not v))
log("=" * 70)
