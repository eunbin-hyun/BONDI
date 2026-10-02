# -*- coding: utf-8 -*-
"""
인왕제색도 — 나무 흔들림 + 안개 흐름 (움직이는 머티리얼) v2.4  (2026-09-14)
=====================================================================
사용법 (언리얼 하단 콘솔, Cmd 모드):
    py "C:/KCW_SSAFY/특화/S15P21C201/김채원/2026-09-12/scripts/ue_setup_motion.py"
되돌리기: 맨 아래 MOTION_ON = False 로 바꿔 다시 실행 (원래 머티리얼로 복귀)

전제: ue_setup_materials.py v7 성공 (M_InwangVertexUnlit, M_InwangFogL0~4, M_InwangTreeCards 존재),
      ue_place_trees.py 로 tree_000… 액터가 Inwang/Trees 에 배치된 상태.
      절차 나무(pine_proc·willow_proc·pine_ai) 는 TEXCOORD_0.x = 흔들림 마스크(밑동 0 → 꼭대기 1, 버드나무 가닥은 +0.3).

만드는 것 (기존 머티리얼은 안 건드림, 새로 만든 것만 액터에 끼움)
  M_InwangTreesSway      : 정점색 → Emissive. WorldPositionOffset = [sin(t·S + x·p) + 0.35·sin(t·2.3S + y·p')] × 진폭 × 마스크(UV0.x)
                           → 밑동은 고정, 꼭대기만 바람에 흔들림. 나무마다 위치가 달라 위상이 어긋남(같이 안 움직임)
  M_InwangTreeCardsSway  : 카드 나무(trees_cards, 선택). 텍스처 RGB→Emissive, A→OpacityMask, 마스크 = 1 − UV0.y (카드 위쪽일수록 큼)
  M_InwangFogDriftL0~4   : 운무 겹마다. 텍스처 RGB→Emissive,
                           v3(2026-09-14) Opacity = Clamp(텍스처A × FOG_GAIN) × Noise(월드좌표 + 시간×바람)[FOG_MIN~1]
                             — v2 는 Clamp 가 맨 뒤라 진한 부분이 1 에 붙어버려 흐름이 안 보였음. Clamp 를 노이즈 앞으로 옮김.
                             — 바람 방향은 PlayerStart 가 보는 방향의 오른쪽 → 시야에서 왼→오른쪽으로 물처럼 흐름
                           WorldPositionOffset 으로 좌우 일렁임 (v3: 진폭 450→70 cm 로 대폭 축소, 주기도 느리게)
확인 지표
  - 로그: 연결 줄마다 '연결 OK', 끝에 '>>> 성공: 머티리얼 N개, 액터 M개 적용'. '!!' 가 있으면 그 줄 복사.
  - 뷰포트: 왼쪽 위 ▾ 메뉴 '실시간'(Ctrl+R) 이 켜져 있어야 Time 노드가 흐름 → 나무 윗부분이 흔들리고 안개 농도가 변함.
    (에디터는 몇 분 지나면 실시간을 자동으로 끄기도 함 — 안 움직이면 Ctrl+R 부터)
  - 나무가 전혀 안 움직이면 NANITE_OFF_FOR_TREES = True 로 재실행 (Nanite 메시에서 WPO 가 막힌 경우. 추측 — 로그로 확인)
조절값: SWAY_AMP(cm)·SWAY_SPEED(rad/s)·SWAY_PHASE(1/cm), FOG_SPEED(cm/s)·FOG_SCALE(1/cm)·FOG_MIN·FOG_WAVE_AMP
주의: 노드·핀 이름은 v1(09-11) 에서 쓴 것과 같은 후보 목록으로 시도하고 성공한 조합을 로그로 남김 — 직접 못 돌려본 부분은 '!!' 로 드러남.
"""
import unreal

PKG = "/Game/Museum/Inwang"
ML = unreal.MaterialEditingLibrary; EAL = unreal.EditorAssetLibrary; TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
SUB = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

MOTION_ON = True                    # False 면 원래 머티리얼로 복귀
SWAY_AMP = (22.0, 14.0, 0.0)        # 꼭대기 최대 변위 cm (X, Y, Z)  — v2.1: 40→22 (폭 줄임)
SWAY_SPEED = 0.8                    # rad/s (0.8 ≈ 8초에 한 번 왕복)
SWAY_PHASE = 0.0015                 # 1/cm — 위치에 따른 위상 차 (0.0015 → 약 42 m 마다 한 주기)
CARD_AMP = (14.0, 9.0, 0.0)         # 카드 나무 진폭  — v2.1: 25→14
# ── 안개 (v3, 2026-09-14) ──────────────────────────────────────────
# v2.4 까지 안 움직여 보였던 이유(진단): 불투명도 = Clamp(노이즈 × 텍스처A × 1.5) 였는데, 진한 부분은 1 에서 잘려
#   노이즈가 아무리 흘러도 값이 계속 1 → 정작 눈에 띄는 곳이 미동도 안 함. v3 은 Clamp 를 노이즈 '앞'으로 옮겨
#   불투명도 = Clamp(텍스처A × GAIN) × 노이즈  로 바꿈 → 진한 곳도 노이즈만큼 옅어졌다 진해진다.
# 흐름 방향은 PlayerStart 가 보는 방향의 '오른쪽'으로 자동 계산 (= 시야에서 왼→오른쪽). 못 읽으면 FOG_DIR_FALLBACK.
FOG_SPEED = 2600.0                  # 흐르는 속도 cm/s (26 m/s) — 물처럼 한 방향으로
FOG_DIR_FALLBACK = (0.0, 1.0, 0.0)  # PlayerStart 를 못 찾을 때 쓸 방향 (월드 +Y)
FOG_SCALE = 1.0 / 2200.0            # 노이즈 덩어리 크기 1/cm (2200 → 약 22 m) — v3: 45→22 m, 작을수록 흐름이 자주 보임
FOG_MIN = 0.12                      # 농도 최소 배율 — v3: 0.35→0.12, 진했다 옅어지는 폭을 크게
FOG_LEVELS = 2                      # 노이즈 옥타브 (많을수록 비쌈)
FOG_GAIN = 1.5                      # 텍스처 알파 배율 (Clamp 로 1 에서 잘림) — v3 부터 노이즈보다 먼저 적용
FOG_WAVE_AMP = 70.0                 # v3: 450→70 — 팔랑거림은 거의 없애고 흐름만 남김
FOG_WAVE_SPEED = 0.30               # v3: 0.55→0.30 (≈ 21초 왕복, 느린 일렁임)
FOG_WAVE_K = 1.0 / 6000.0           # 진행 방향 위치에 따른 위상 1/cm (6000 → 파장 약 380 m)
NANITE_OFF_FOR_TREES = False
FOG_LAYERS = ["fog_l0", "fog_l1", "fog_l2", "fog_l3", "fog_l4"]

def fog_wind():
    """시야에서 왼→오른쪽으로 흐르게: PlayerStart 가 보는 방향의 오른쪽 벡터 × 속도.
    노이즈는 N(p + v·t) 라 무늬가 −v 로 흘러 보이므로 부호를 뒤집어 넣는다."""
    import math
    ps = next((a for a in SUB.get_all_level_actors() if isinstance(a, unreal.PlayerStart)), None)
    if ps is None:
        d = FOG_DIR_FALLBACK; log("   (참고) PlayerStart 없음 — 흐름 방향 기본값 %s" % (d,))
    else:
        yaw = ps.get_actor_rotation().yaw + 90.0                    # 보는 방향의 오른쪽
        d = (math.cos(math.radians(yaw)), math.sin(math.radians(yaw)), 0.0)
        log("   흐름 방향: PlayerStart yaw %.0f° 기준 오른쪽 (%.2f, %.2f, 0) × %.0f cm/s" % (ps.get_actor_rotation().yaw, d[0], d[1], FOG_SPEED))
    return (-d[0] * FOG_SPEED, -d[1] * FOG_SPEED, 0.0)


MP_EMISSIVE = unreal.MaterialProperty.MP_EMISSIVE_COLOR; MP_OPACITY = unreal.MaterialProperty.MP_OPACITY
MP_MASK = unreal.MaterialProperty.MP_OPACITY_MASK; MP_WPO = unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET
OUT = [""]; IN_A, IN_B = ["A"], ["B"]; IN_ANY = ["", "Input", "Position"]
fails = []


def log(m): unreal.log("[INWANG] %s" % m)


class Fail(Exception): pass


def mk(mat, cls, x, y, **props):
    e = ML.create_material_expression(mat, cls, x, y)
    for k, v in props.items():
        try: e.set_editor_property(k, v)
        except Exception as ex: log("   (참고) %s.%s 설정 불가: %s" % (cls.__name__, k, ex))
    return e


def link(src, src_outs, dst, dst_ins, what):
    for o in src_outs:
        for i in dst_ins:
            try:
                if ML.connect_material_expressions(src, o, dst, i): log("   연결 OK  %-38s (out=%r in=%r)" % (what, o, i)); return
            except Exception: pass
    raise Fail("연결 실패 %s (out 후보 %r, in 후보 %r)" % (what, src_outs, dst_ins))


def link_prop(src, src_outs, prop, what):
    for o in src_outs:
        try:
            if ML.connect_material_property(src, o, prop): log("   연결 OK  %-38s (out=%r)" % (what, o)); return
        except Exception: pass
    raise Fail("연결 실패 %s" % what)


def new_material(name, translucent=False, masked=False):
    path = "%s/%s" % (PKG, name)
    if EAL.does_asset_exist(path): mat = EAL.load_asset(path); ML.delete_all_material_expressions(mat)
    else: mat = TOOLS.create_asset(name, PKG, unreal.Material, unreal.MaterialFactoryNew())
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED if masked else (unreal.BlendMode.BLEND_TRANSLUCENT if translucent else unreal.BlendMode.BLEND_OPAQUE))
    mat.set_editor_property("two_sided", bool(translucent or masked))
    try: mat.set_editor_property("used_with_nanite", True)
    except Exception: pass
    return mat, path


def find_texture(part):
    """ue_setup_materials 와 같은 규칙: 메시가 참조하는 텍스처 → 이름 검색"""
    sm = None
    for p in EAL.list_assets(PKG, recursive=True, include_folder=False):
        leaf = p.rsplit("/", 1)[-1].split(".")[0].lower()
        if leaf == part.lower():
            o = EAL.load_asset(p)
            if isinstance(o, unreal.StaticMesh): sm = o; break
    if sm is not None:
        for smm in sm.get_editor_property("static_materials"):
            mi = smm.material_interface
            try:
                for tp in mi.get_editor_property("texture_parameter_values"):
                    if isinstance(tp.parameter_value, unreal.Texture2D): return tp.parameter_value
            except Exception: pass
    for p in EAL.list_assets(PKG, recursive=True, include_folder=False):
        leaf = p.rsplit("/", 1)[-1].split(".")[0].lower()
        if leaf == part.lower() or leaf.startswith(part.lower() + "_"):
            o = EAL.load_asset(p)
            if isinstance(o, unreal.Texture2D): return o
    return None


def sway_wpo(mat, amp, mask_expr, mask_out, x0=-1500, y0=200):
    """WPO = [sin(t·S + x·p) + 0.35·sin(t·2.3S + y·p·1.7)] × amp × mask  → 노드 반환"""
    wpos = mk(mat, unreal.MaterialExpressionWorldPosition, x0, y0)
    mx = mk(mat, unreal.MaterialExpressionComponentMask, x0 + 200, y0, r=True, g=False, b=False, a=False)
    my = mk(mat, unreal.MaterialExpressionComponentMask, x0 + 200, y0 + 120, r=False, g=True, b=False, a=False)
    ph1 = mk(mat, unreal.MaterialExpressionConstant, x0 + 200, y0 + 240, r=SWAY_PHASE)
    ph2 = mk(mat, unreal.MaterialExpressionConstant, x0 + 200, y0 + 300, r=SWAY_PHASE * 1.7)
    time = mk(mat, unreal.MaterialExpressionTime, x0, y0 + 400)
    s1 = mk(mat, unreal.MaterialExpressionConstant, x0 + 200, y0 + 400, r=SWAY_SPEED)
    s2 = mk(mat, unreal.MaterialExpressionConstant, x0 + 200, y0 + 460, r=SWAY_SPEED * 2.3)
    m_xp = mk(mat, unreal.MaterialExpressionMultiply, x0 + 400, y0); m_yp = mk(mat, unreal.MaterialExpressionMultiply, x0 + 400, y0 + 120)
    m_t1 = mk(mat, unreal.MaterialExpressionMultiply, x0 + 400, y0 + 400); m_t2 = mk(mat, unreal.MaterialExpressionMultiply, x0 + 400, y0 + 480)
    a1 = mk(mat, unreal.MaterialExpressionAdd, x0 + 600, y0 + 50); a2 = mk(mat, unreal.MaterialExpressionAdd, x0 + 600, y0 + 250)
    sn1 = mk(mat, unreal.MaterialExpressionSine, x0 + 750, y0 + 50); sn2 = mk(mat, unreal.MaterialExpressionSine, x0 + 750, y0 + 250)
    k2 = mk(mat, unreal.MaterialExpressionConstant, x0 + 750, y0 + 330, r=0.35)
    m_k2 = mk(mat, unreal.MaterialExpressionMultiply, x0 + 900, y0 + 250)
    a3 = mk(mat, unreal.MaterialExpressionAdd, x0 + 1050, y0 + 120)
    ampn = mk(mat, unreal.MaterialExpressionConstant3Vector, x0 + 1050, y0 + 300, constant=unreal.LinearColor(amp[0], amp[1], amp[2], 0.0))
    m_a = mk(mat, unreal.MaterialExpressionMultiply, x0 + 1200, y0 + 150)
    m_m = mk(mat, unreal.MaterialExpressionMultiply, x0 + 1350, y0 + 200)
    link(wpos, OUT, mx, IN_ANY, "WorldPos → Mask(X)"); link(wpos, OUT, my, IN_ANY, "WorldPos → Mask(Y)")
    link(mx, OUT, m_xp, IN_A, "x → Mul.A"); link(ph1, OUT, m_xp, IN_B, "phase → Mul.B")
    link(my, OUT, m_yp, IN_A, "y → Mul.A"); link(ph2, OUT, m_yp, IN_B, "phase2 → Mul.B")
    link(time, OUT, m_t1, IN_A, "Time → Mul.A"); link(s1, OUT, m_t1, IN_B, "speed → Mul.B")
    link(time, OUT, m_t2, IN_A, "Time → Mul2.A"); link(s2, OUT, m_t2, IN_B, "speed2 → Mul2.B")
    link(m_xp, OUT, a1, IN_A, "x·p → Add1.A"); link(m_t1, OUT, a1, IN_B, "t·S → Add1.B")
    link(m_yp, OUT, a2, IN_A, "y·p' → Add2.A"); link(m_t2, OUT, a2, IN_B, "t·2.3S → Add2.B")
    link(a1, OUT, sn1, IN_ANY, "Add1 → Sine1"); link(a2, OUT, sn2, IN_ANY, "Add2 → Sine2")
    link(sn2, OUT, m_k2, IN_A, "Sine2 → Mul.A"); link(k2, OUT, m_k2, IN_B, "0.35 → Mul.B")
    link(sn1, OUT, a3, IN_A, "Sine1 → Add3.A"); link(m_k2, OUT, a3, IN_B, "0.35·Sine2 → Add3.B")
    link(a3, OUT, m_a, IN_A, "파동 → Mul.A"); link(ampn, OUT, m_a, IN_B, "진폭 → Mul.B")
    link(m_a, OUT, m_m, IN_A, "파동×진폭 → Mul.A"); link(mask_expr, mask_out, m_m, IN_B, "마스크 → Mul.B")
    link_prop(m_m, OUT, MP_WPO, "→ WorldPositionOffset")
    return m_m


def build_trees():
    mat, path = new_material("M_InwangTreesSway")
    vc = mk(mat, unreal.MaterialExpressionVertexColor, -600, -300)
    uv = mk(mat, unreal.MaterialExpressionTextureCoordinate, -600, 900, coordinate_index=0)
    mu = mk(mat, unreal.MaterialExpressionComponentMask, -400, 900, r=True, g=False, b=False, a=False)
    link(uv, OUT, mu, IN_ANY, "UV0 → Mask(R)=흔들림 마스크")
    link_prop(vc, ["", "RGB"], MP_EMISSIVE, "VertexColor.RGB → Emissive")
    sway_wpo(mat, SWAY_AMP, mu, OUT)
    ML.recompile_material(mat); EAL.save_asset(path); return mat


def build_cards():
    tex = find_texture("trees_cards")
    if tex is None: raise Fail("trees_cards 텍스처 없음 (카드 나무 안 쓰면 무시)")
    mat, path = new_material("M_InwangTreeCardsSway", masked=True)
    ts = mk(mat, unreal.MaterialExpressionTextureSample, -600, -300, texture=tex)
    uv = mk(mat, unreal.MaterialExpressionTextureCoordinate, -600, 900, coordinate_index=0)
    mv = mk(mat, unreal.MaterialExpressionComponentMask, -400, 900, r=False, g=True, b=False, a=False)
    om = mk(mat, unreal.MaterialExpressionOneMinus, -250, 900)
    link(uv, OUT, mv, IN_ANY, "UV0 → Mask(G)"); link(mv, OUT, om, IN_ANY, "v → 1−v (위쪽일수록 큼)")
    link_prop(ts, ["RGB", ""], MP_EMISSIVE, "Tex.RGB → Emissive"); link_prop(ts, ["A"], MP_MASK, "Tex.A → OpacityMask")
    sway_wpo(mat, CARD_AMP, om, OUT)
    ML.recompile_material(mat); EAL.save_asset(path); return mat


def build_fog(k, part):
    tex = find_texture(part)
    if tex is None: raise Fail("%s 텍스처 없음" % part)
    mat, path = new_material("M_InwangFogDriftL%d" % k, translucent=True)
    ts = mk(mat, unreal.MaterialExpressionTextureSample, -700, -300, texture=tex)
    wpos = mk(mat, unreal.MaterialExpressionWorldPosition, -1500, 200)
    time = mk(mat, unreal.MaterialExpressionTime, -1500, 400)
    f = 1.0 + 0.18 * (k - 2)                                                      # 겹마다 바람 조금 다르게 (l0 느림 … l4 빠름)
    _w = fog_wind()
    wind = mk(mat, unreal.MaterialExpressionConstant3Vector, -1500, 500, constant=unreal.LinearColor(_w[0] * f, _w[1] * f, _w[2], 0.0))
    m_tw = mk(mat, unreal.MaterialExpressionMultiply, -1250, 420); add = mk(mat, unreal.MaterialExpressionAdd, -1050, 250)
    noise = mk(mat, unreal.MaterialExpressionNoise, -850, 250, scale=FOG_SCALE, levels=FOG_LEVELS, output_min=FOG_MIN, output_max=1.0, turbulence=False, quality=1)
    try: noise.set_editor_property("noise_function", unreal.NoiseFunction.NOISE_FAST_GRADIENT)
    except Exception as ex: log("   (참고) noise_function 설정 불가 — 기본값 사용: %s" % ex)
    gain = mk(mat, unreal.MaterialExpressionConstant, -600, 120, r=FOG_GAIN)
    m_g = mk(mat, unreal.MaterialExpressionMultiply, -450, 60)           # v3: 텍스처A × gain 을 먼저
    clamp = mk(mat, unreal.MaterialExpressionClamp, -300, 60)            #      여기서 1 로 자른 뒤
    m_o = mk(mat, unreal.MaterialExpressionMultiply, -150, 30)           #      마지막에 노이즈를 곱한다
    link(time, OUT, m_tw, IN_A, "Time → Mul.A"); link(wind, OUT, m_tw, IN_B, "Wind → Mul.B")
    link(wpos, OUT, add, IN_A, "WorldPos → Add.A"); link(m_tw, OUT, add, IN_B, "Time×Wind → Add.B")
    link(add, OUT, noise, ["Position", ""], "Add → Noise.Position")
    link(ts, ["A"], m_g, IN_A, "Tex.A → Mul.A"); link(gain, OUT, m_g, IN_B, "gain → Mul.B")
    link(m_g, OUT, clamp, ["", "Input"], "A×gain → Clamp(0~1)")
    link(clamp, OUT, m_o, IN_A, "Clamp → Mul.A"); link(noise, OUT, m_o, IN_B, "Noise → Mul.B")
    link_prop(ts, ["RGB", ""], MP_EMISSIVE, "Tex.RGB → Emissive"); link_prop(m_o, OUT, MP_OPACITY, "Clamp×Noise → Opacity")
    # v2.3 좌우 파도: WPO = (0, sin(t·ω + X·k + 겹위상), 0) × 진폭  — 안개 판 자체가 옆으로 천천히 밀렸다 돌아옴
    wx = mk(mat, unreal.MaterialExpressionComponentMask, -1250, 700, r=True, g=False, b=False, a=False)
    kx = mk(mat, unreal.MaterialExpressionConstant, -1250, 800, r=FOG_WAVE_K); m_kx = mk(mat, unreal.MaterialExpressionMultiply, -1050, 720)
    ws = mk(mat, unreal.MaterialExpressionConstant, -1250, 900, r=FOG_WAVE_SPEED); m_ts = mk(mat, unreal.MaterialExpressionMultiply, -1050, 880)
    a_w = mk(mat, unreal.MaterialExpressionAdd, -850, 780); ph = mk(mat, unreal.MaterialExpressionConstant, -850, 900, r=1.2 * k)
    a_w2 = mk(mat, unreal.MaterialExpressionAdd, -700, 820); sn = mk(mat, unreal.MaterialExpressionSine, -550, 820)
    amp = mk(mat, unreal.MaterialExpressionConstant3Vector, -550, 940, constant=unreal.LinearColor(0.0, FOG_WAVE_AMP, 0.0, 0.0))
    m_w = mk(mat, unreal.MaterialExpressionMultiply, -350, 860)
    link(wpos, OUT, wx, IN_ANY, "WorldPos → Mask(X)"); link(wx, OUT, m_kx, IN_A, "X → Mul.A"); link(kx, OUT, m_kx, IN_B, "k → Mul.B")
    link(time, OUT, m_ts, IN_A, "Time → Mul.A"); link(ws, OUT, m_ts, IN_B, "ω → Mul.B")
    link(m_kx, OUT, a_w, IN_A, "X·k → Add.A"); link(m_ts, OUT, a_w, IN_B, "t·ω → Add.B")
    link(a_w, OUT, a_w2, IN_A, "→ Add2.A"); link(ph, OUT, a_w2, IN_B, "겹 위상 → Add2.B"); link(a_w2, OUT, sn, IN_ANY, "→ Sine")
    link(sn, OUT, m_w, IN_A, "Sine → Mul.A"); link(amp, OUT, m_w, IN_B, "파도 진폭(Y) → Mul.B"); link_prop(m_w, OUT, MP_WPO, "파도 → WorldPositionOffset")
    ML.recompile_material(mat); EAL.save_asset(path); return mat


def assign(actor, mat, nanite_off=False):
    comp = actor.get_component_by_class(unreal.StaticMeshComponent)
    if comp is None: return False
    for s in range(comp.get_num_materials()): comp.set_material(s, mat)
    if nanite_off:
        sm = comp.static_mesh; ns = sm.get_editor_property("nanite_settings")
        if ns.get_editor_property("enabled"):
            ns.set_editor_property("enabled", False); sm.set_editor_property("nanite_settings", ns); EAL.save_loaded_asset(sm); log("   %s 메시 Nanite 끔" % sm.get_name())
    got = comp.get_material(0); return got is not None and got.get_name() == mat.get_name()


actors = {a.get_actor_label(): a for a in SUB.get_all_level_actors()}
tree_actors = [a for l, a in actors.items() if l.startswith("tree_")] + ([actors["trees"]] if "trees" in actors else [])
n_mat = 0; n_act = 0
log("=" * 70); log("나무 흔들림 + 안개 흐름 v3   MOTION_ON=%s" % MOTION_ON); log("=" * 70)

if MOTION_ON:
    try:
        log("1) M_InwangTreesSway"); m = build_trees(); n_mat += 1
        ok = [assign(a, m, NANITE_OFF_FOR_TREES) for a in tree_actors]; n_act += sum(ok)
        log("   나무 액터 %d개 중 %d개 적용 (tree_* + trees)" % (len(ok), sum(ok)))
    except Fail as e: fails.append(str(e)); log("   !! " + str(e))
    try:
        log("2) M_InwangTreeCardsSway (선택)"); m = build_cards(); n_mat += 1
        if "trees_cards" in actors: n_act += int(assign(actors["trees_cards"], m)); log("   trees_cards 적용")
    except Fail as e: log("   (건너뜀) " + str(e))
    for k, part in enumerate(FOG_LAYERS):
        try:
            log("3) M_InwangFogDriftL%d" % k); m = build_fog(k, part); n_mat += 1
            if part in actors: n_act += int(assign(actors[part], m)); log("   %s 적용" % part)
            else: log("   (참고) %s 액터 없음 — ue_setup_materials.py 먼저" % part)
        except Fail as e: fails.append(str(e)); log("   !! " + str(e))
else:
    base = EAL.load_asset(PKG + "/M_InwangVertexUnlit"); cards = EAL.load_asset(PKG + "/M_InwangTreeCards")
    for a in tree_actors: n_act += int(assign(a, base))
    if "trees_cards" in actors and cards: n_act += int(assign(actors["trees_cards"], cards))
    for k, part in enumerate(FOG_LAYERS):
        fm = EAL.load_asset("%s/M_InwangFogL%d" % (PKG, k))
        if part in actors and fm: n_act += int(assign(actors[part], fm))
    log("원래 머티리얼로 복귀: 액터 %d개" % n_act)

log("-" * 70)
if fails: log(">>> !! 실패 %d건 — 위 '!!' 줄을 그대로 복사해 주세요" % len(fails))
else: log(">>> 성공: 머티리얼 %d개, 액터 %d개 적용. 뷰포트 '실시간'(Ctrl+R) 켜고 확인. 되돌리려면 MOTION_ON=False" % (n_mat, n_act))
log("=" * 70)
