# -*- coding: utf-8 -*-
"""
화제 글씨 금빛 반짝임 토글 (2026-09-14)
========================================
대상: inscription — 원화의 화제·인장을 떼어내 공중에 세운 판 (약 20 × 35 m, 시점에서 400 m).
글씨 획 위로 금빛 띠가 위 → 아래로 반복해서 지나간다. 실행할 때마다 끔 ↔ 켬 이 번갈아 바뀐다.
  꺼짐: M_InwangInk       (지금까지 쓰던 것 — 텍스처 RGB→Emissive, A→Opacity, 반투명)
  켜짐: M_InwangInkShine  (같은 텍스처 + 금빛 띠. 반투명·알파 처리 그대로)

어떻게 획에만 얹히나: inscription 텍스처의 **알파가 곧 먹 획의 진하기**다 (원화에서 화제를 떼어낼 때 만든 값).
   종이 부분은 알파 0 이라 애초에 안 보이고, 금빛도 안 올라간다. 새로 만들 에셋 없음 — 머티리얼만 바뀜.
띠의 위치는 UV 가 아니라 **월드 높이(Z)** 로 정하므로 '위에서 아래로' 방향이 뒤집힐 일이 없다.

사용법 (L_Inwang 열린 상태, 언리얼 콘솔):
    py "C:/KCW_SSAFY/특화/S15P21C201/김채원/2026-09-12/scripts/ue_toggle_shine.py"
확인 지표: '>>> 지금: 켜짐 / 꺼짐' + '노드 연결 N/N' (앞뒤 숫자가 같아야 함).
          뷰포트는 '실시간'(Ctrl+R) 이 켜져 있어야 움직인다.
조절: SHINE_WAVE_CM(띠 간격) · SHINE_PERIOD(한 칸 내려가는 초) · SHINE_SHARP(띠 좁기) · SHINE_GAIN(밝기)
참고: TARGET 을 "inscription_board" 로 바꾸면 안내판에도 같은 효과가 붙는다 (그쪽은 알파가 글자 마스크).
"""
import unreal

MODE = None              # None = 토글, 0 꺼짐 / 1 켜짐 으로 직접 지정 가능
TARGET = "inscription"   # "inscription" (원화 화제) 또는 "inscription_board" (관람 안내판)
SHINE_WAVE_CM = 6000.0   # 금빛 띠가 반복되는 간격 (cm). 화제 판 높이가 약 3,500 cm 라 한 줄기씩 쓸고 지나감
SHINE_PERIOD = 3.2       # 한 칸(=SHINE_WAVE_CM) 내려가는 데 걸리는 초
SHINE_SHARP = 5.0        # 띠 좁기 (클수록 가는 띠)
SHINE_GAIN = 2.2         # 금빛 밝기
GOLD = (1.00, 0.80, 0.34)

PKG = "/Game/Museum/Inwang"
# 대상별: (꺼짐 머티리얼, 켜짐 머티리얼, 반투명 여부)
PRESET = {"inscription": ("M_InwangInk", "M_InwangInkShine", True),
          "inscription_board": ("M_InwangBoard", "M_InwangBoardShine", False)}
OFF_MAT, ON_MAT, TRANSLUCENT = PRESET[TARGET]
EAL = unreal.EditorAssetLibrary; ML = unreal.MaterialEditingLibrary; TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem); LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


def log(m): unreal.log("[INWANG] %s" % m)


def mesh_texture(comp):
    """대상 메시가 실제로 참조하는 텍스처"""
    sm = comp.static_mesh
    try: mats = list(sm.get_editor_property("static_materials"))
    except Exception: return None
    for s in mats:
        mi = s.get_editor_property("material_interface")
        if mi is None: continue
        try: tps = mi.get_editor_property("texture_parameter_values")
        except Exception: tps = []
        for tp in tps:
            t = tp.get_editor_property("parameter_value")
            if isinstance(t, unreal.Texture2D): return t
    return None


def build_shine(tex):
    path = "%s/%s" % (PKG, ON_MAT)
    if EAL.does_asset_exist(path): mat = EAL.load_asset(path); ML.delete_all_material_expressions(mat)
    else: mat = TOOLS.create_asset(ON_MAT, PKG, unreal.Material, unreal.MaterialFactoryNew())
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT if TRANSLUCENT else unreal.BlendMode.BLEND_OPAQUE)
    mat.set_editor_property("two_sided", bool(TRANSLUCENT))
    oks = []

    def mk(cls, x, y, **pr):
        e = ML.create_material_expression(mat, cls, x, y)
        for k, v in pr.items(): e.set_editor_property(k, v)
        return e

    def L(a, b, ins, outs=""):
        r = False
        for i in ([ins] if isinstance(ins, str) else ins):
            for o in ([outs] if isinstance(outs, str) else outs):
                try:
                    if ML.connect_material_expressions(a, o, b, i): r = True; break
                except Exception: pass
            if r: break
        oks.append(r)
        return r

    ts = mk(unreal.MaterialExpressionTextureSample, -1500, -300, texture=tex)
    # 띠 위치 = frac(월드Z / 간격 + 시간 / 주기)  → 시간이 흐르면 같은 값의 높이가 내려간다 (위 → 아래)
    wp = mk(unreal.MaterialExpressionWorldPosition, -1500, 200)
    mz = mk(unreal.MaterialExpressionComponentMask, -1300, 200, r=False, g=False, b=True, a=False)
    kz = mk(unreal.MaterialExpressionConstant, -1300, 320, r=1.0 / SHINE_WAVE_CM)
    m_z = mk(unreal.MaterialExpressionMultiply, -1100, 240)
    tm = mk(unreal.MaterialExpressionTime, -1300, 440)
    ks = mk(unreal.MaterialExpressionConstant, -1300, 560, r=1.0 / max(SHINE_PERIOD, 1e-3))
    m_t = mk(unreal.MaterialExpressionMultiply, -1100, 480)
    ad = mk(unreal.MaterialExpressionAdd, -950, 360)
    fr = mk(unreal.MaterialExpressionFrac, -820, 360)
    # 삼각 띠: 1 - |2·frac - 1|  → 0~1, 가운데가 1
    two = mk(unreal.MaterialExpressionConstant, -820, 500, r=2.0)
    m2 = mk(unreal.MaterialExpressionMultiply, -700, 400)
    one = mk(unreal.MaterialExpressionConstant, -700, 520, r=1.0)
    sb = mk(unreal.MaterialExpressionSubtract, -580, 420)
    ab = mk(unreal.MaterialExpressionAbs, -470, 420)
    om = mk(unreal.MaterialExpressionOneMinus, -370, 420)
    shp = mk(unreal.MaterialExpressionConstant, -370, 540, r=SHINE_SHARP)
    pw = mk(unreal.MaterialExpressionPower, -250, 440)
    # 글자 마스크(텍스처 알파) × 띠 × 금색 × 밝기
    m_bm = mk(unreal.MaterialExpressionMultiply, -120, 300)
    gold = mk(unreal.MaterialExpressionConstant3Vector, -250, 120,
              constant=unreal.LinearColor(GOLD[0] * SHINE_GAIN, GOLD[1] * SHINE_GAIN, GOLD[2] * SHINE_GAIN, 1.0))
    m_g = mk(unreal.MaterialExpressionMultiply, 20, 200)
    em = mk(unreal.MaterialExpressionAdd, 160, 0)

    L(wp, mz, ["", "Input"]); L(mz, m_z, "A"); L(kz, m_z, "B")
    L(tm, m_t, "A"); L(ks, m_t, "B")
    L(m_z, ad, "A"); L(m_t, ad, "B"); L(ad, fr, ["", "Input"])
    L(fr, m2, "A"); L(two, m2, "B"); L(m2, sb, "A"); L(one, sb, "B")
    L(sb, ab, ["", "Input"]); L(ab, om, ["", "Input"])
    L(om, pw, ["Base", "A"]); L(shp, pw, ["Exp", "B"])
    L(pw, m_bm, "A"); L(ts, m_bm, "B", ["A"])
    L(gold, m_g, "A"); L(m_bm, m_g, "B")
    L(ts, em, "A", ["RGB", ""]); L(m_g, em, "B")
    ok = ML.connect_material_property(em, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    ok_a = "-"
    if TRANSLUCENT:                                            # 원래 M_InwangInk 와 같게 알파 → 불투명도
        ok_a = ML.connect_material_property(ts, "A", unreal.MaterialProperty.MP_OPACITY)
    ML.recompile_material(mat); EAL.save_asset(path)
    log("%s  노드 연결 %d/%d   Emissive %s   Opacity %s" % (ON_MAT, sum(oks), len(oks), ok, ok_a))
    return mat


a = {x.get_actor_label(): x for x in sub.get_all_level_actors()}.get(TARGET)
if a is None:
    log("!! '%s' 액터 없음 — 현재 레벨이 L_Inwang 인지, 그 액터가 숨김이 아닌지 확인" % TARGET)
else:
    comp = a.get_component_by_class(unreal.StaticMeshComponent)
    cur = comp.get_material(0); cur_name = cur.get_name() if cur else ""
    nxt = MODE if MODE is not None else (0 if cur_name == ON_MAT else 1)
    if nxt == 0:
        m = EAL.load_asset("%s/%s" % (PKG, OFF_MAT))
        if m is None: log("!! %s 없음 — ue_setup_materials.py 먼저" % OFF_MAT)
    else:
        tex = mesh_texture(comp)
        if tex is None:
            log("!! %s 텍스처를 못 찾음" % TARGET); m = None
        else:
            try:
                if bool(tex.get_editor_property("compression_no_alpha")):
                    tex.set_editor_property("compression_no_alpha", False); EAL.save_loaded_asset(tex); log("   텍스처 알파 유지 옵션을 켬")
            except Exception as ex: log("   (참고) compression_no_alpha 확인 불가: %s" % ex)
            try: has_a = not bool(tex.get_editor_property("compression_no_alpha"))
            except Exception: has_a = None
            log("텍스처 %s  %dx%d  알파 유지 %s" % (tex.get_name(), tex.blueprint_get_size_x(), tex.blueprint_get_size_y(), has_a))
            log("   (마스크는 알파 채널 = 먹 획의 진하기. 판 전체가 번쩍이면 알파가 없는 텍스처를 물고 있는 것)")
            m = build_shine(tex)
    if m is not None:
        for i in range(comp.get_num_materials()): comp.set_material(i, m)
        got = comp.get_material(0).get_name()
        log(">>> 지금: %s   (머티리얼 %s, 이전 %s)" % ("켜짐" if nxt else "꺼짐", got, cur_name or "없음"))
        log("    띠 간격 %.0f cm · 한 칸 %.1f 초 · 띠 좁기 %.1f · 밝기 %.1f   뷰포트 '실시간'(Ctrl+R) 켜야 움직임" % (SHINE_WAVE_CM, SHINE_PERIOD, SHINE_SHARP, SHINE_GAIN))
        log("레벨 저장 %s" % LES.save_current_level())
