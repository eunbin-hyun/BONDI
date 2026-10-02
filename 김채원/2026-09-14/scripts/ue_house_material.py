# -*- coding: utf-8 -*-
"""
집 머티리얼 — 지붕 밑면 어둡게 + 조명 (2026-09-14)
===================================================
왜: 지붕이 '두께 0 인 한 겹 면' 이라 밑면 전용 면이 따로 없다. 양면(two-sided) 으로 그리기 때문에
    위에서 보든 아래서 보든 아틀라스의 같은 자리를 본다 → 처마 밑이 지붕 위와 똑같은 먹색.
해법: 머티리얼에서 **뒷면(= 밑에서 보는 면) 만** 어둡게 한다. TwoSidedSign 노드가 앞면 +1 / 뒷면 -1 을 주므로
    saturate 하면 앞면 1 · 뒷면 0 인 마스크가 되고, 그걸로 어둡기를 섞는다. 메시는 그대로.

같이 들어 있는 것
  USE_LIT : 집도 '법선 고정 Lit' 으로 바꿔 실제 그림자를 받게 한다 (지형과 같은 방식).
            해 고도가 74° 라 처마가 벽에 드리우는 띠는 40 cm 정도로 얇다 — 깊은 처마 그늘은
            아틀라스에 구운 그라데이션(build_house_ink.py v4) 이 담당한다.

사용법 (L_Inwang 열린 상태, 언리얼 콘솔):
    py "C:/KCW_SSAFY/특화/S15P21C201/김채원/2026-09-12/scripts/ue_house_material.py"
확인 지표: 'TwoSidedSign 연결 True', '연결 N/N', '>>> 적용 액터 N개'. 처마 밑에서 올려다봤을 때 지붕 안쪽이 어두워야 함.
조절: UNDER_DARK(지붕 밑면 어둡기, 1 = 그대로 / 0.4 = 많이 어둡게) · USE_LIT · BASE_GAIN
"""
import os, json, math, unreal

UNDER_DARK = 0.45        # 뒷면(지붕 밑) 밝기 배율. 1 = 변화 없음
USE_LIT = True           # 지형과 같은 '법선 고정 Lit' — 실제 그림자를 받음
BASE_GAIN = 1.0

RT = r"C:\Users\SSAFY\Desktop\SSAFY_2학기\02_특화 프로젝트\특화PJT_\landscape_to_3D\Claude outputs\VR_inwangjesaekdo_v0.11\inwangjesaekdo_VR_v0.11\runtime"
SUN_JSON = os.path.join(os.path.dirname(RT), "records", "sun_fit.json")
PKG = "/Game/Museum/Inwang"
TARGETS = ["house_ink_small", "house_ink_big", "house_ink"]     # 있는 것만 적용
MAT_NAME = "M_InwangHouseInk"

EAL = unreal.EditorAssetLibrary; ML = unreal.MaterialEditingLibrary; TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem); LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


def log(m): unreal.log("[INWANG] %s" % m)


def art_texture(comp):
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


A = {x.get_actor_label(): x for x in sub.get_all_level_actors()}
acts = [A[t] for t in TARGETS if t in A]
if not acts: log("!! 집 액터가 없음 (%s) — 현재 레벨이 L_Inwang 인지 확인" % ", ".join(TARGETS)); raise SystemExit
tex = None
for a in acts:
    c = a.get_component_by_class(unreal.StaticMeshComponent)
    tex = art_texture(c)
    if tex is not None: break
if tex is None: log("!! 집 아틀라스 텍스처를 못 찾음"); raise SystemExit
log("아틀라스 %s %dx%d" % (tex.get_name(), tex.blueprint_get_size_x(), tex.blueprint_get_size_y()))

Lue = (0.057, -0.270, 0.961)
if os.path.exists(SUN_JSON):
    Lg = json.load(open(SUN_JSON, encoding="utf-8"))["L_glb"]
    v = (Lg[0], Lg[2], Lg[1]); n_ = math.sqrt(sum(t * t for t in v)) or 1.0
    Lue = tuple(t / n_ for t in v)

path = "%s/%s" % (PKG, MAT_NAME)
if EAL.does_asset_exist(path): mat = EAL.load_asset(path); ML.delete_all_material_expressions(mat)
else: mat = TOOLS.create_asset(MAT_NAME, PKG, unreal.Material, unreal.MaterialFactoryNew())
mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_DEFAULT_LIT if USE_LIT else unreal.MaterialShadingModel.MSM_UNLIT)
mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_OPAQUE)
mat.set_editor_property("two_sided", True)                        # 지붕이 한 겹 면이라 반드시 양면
tsn = True
if USE_LIT:
    try: mat.set_editor_property("tangent_space_normal", False); tsn = False
    except Exception as ex: log("   !! tangent_space_normal 설정 실패: %s" % ex)
oks = []


def mk(cls, x, y, **pr):
    e = ML.create_material_expression(mat, cls, x, y)
    for k, v in pr.items(): e.set_editor_property(k, v)
    return e


def L(a_, b_, ins, outs=""):
    r = False
    for i in ([ins] if isinstance(ins, str) else ins):
        for o in ([outs] if isinstance(outs, str) else outs):
            try:
                if ML.connect_material_expressions(a_, o, b_, i): r = True; break
            except Exception: pass
        if r: break
    oks.append(r); return r


ts = mk(unreal.MaterialExpressionTextureSample, -900, -200, texture=tex)
try:
    tss = mk(unreal.MaterialExpressionTwoSidedSign, -900, 200)
    have_sign = True
except Exception as ex:
    tss = None; have_sign = False; log("   !! TwoSidedSign 노드를 못 만듦 — 지붕 밑면 어둡게 하기 건너뜀: %s" % ex)
color = ts; color_out = ["RGB", ""]
if have_sign:
    sat = mk(unreal.MaterialExpressionSaturate, -760, 200)         # 앞면 1 / 뒷면 0
    dk = mk(unreal.MaterialExpressionConstant, -760, 320, r=UNDER_DARK)
    one = mk(unreal.MaterialExpressionConstant, -760, 400, r=1.0)
    lp = mk(unreal.MaterialExpressionLinearInterpolate, -600, 260)  # 뒷면 → UNDER_DARK, 앞면 → 1
    mul = mk(unreal.MaterialExpressionMultiply, -440, 0)
    ok_s = L(tss, sat, ["", "Input"])
    L(dk, lp, "A"); L(one, lp, "B"); L(sat, lp, "Alpha")
    L(color, mul, "A", color_out); L(lp, mul, "B")
    color, color_out = mul, ""
    log("TwoSidedSign 연결 %s  → 뒷면 밝기 ×%.2f" % (ok_s, UNDER_DARK))

gain = mk(unreal.MaterialExpressionConstant, -440, 200, r=BASE_GAIN)
mg = mk(unreal.MaterialExpressionMultiply, -280, 60)
L(color, mg, "A", color_out); L(gain, mg, "B")

if USE_LIT:
    nrm = mk(unreal.MaterialExpressionConstant3Vector, -280, 300, constant=unreal.LinearColor(Lue[0], Lue[1], Lue[2], 0.0))
    rgh = mk(unreal.MaterialExpressionConstant, -280, 420, r=1.0)
    spc = mk(unreal.MaterialExpressionConstant, -280, 500, r=0.0)
    ok1 = ML.connect_material_property(mg, "", unreal.MaterialProperty.MP_BASE_COLOR)
    ok2 = ML.connect_material_property(nrm, "", unreal.MaterialProperty.MP_NORMAL)
    ML.connect_material_property(rgh, "", unreal.MaterialProperty.MP_ROUGHNESS)
    ML.connect_material_property(spc, "", unreal.MaterialProperty.MP_SPECULAR)
    log("Lit: BaseColor %s / Normal %s / 탄젠트공간법선 %s (False 여야 법선 고정)" % (ok1, ok2, tsn))
else:
    log("Unlit: Emissive %s" % ML.connect_material_property(mg, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR))

ML.recompile_material(mat); EAL.save_asset(path)
log("노드 연결 %d/%d" % (sum(oks), len(oks)))
n = 0
for a in acts:
    c = a.get_component_by_class(unreal.StaticMeshComponent)
    for i in range(c.get_num_materials()): c.set_material(i, mat)
    try:
        c.set_editor_property("cast_shadow", True)
        if USE_LIT: c.set_mobility(unreal.ComponentMobility.MOVABLE)
    except Exception: pass
    n += 1
    log("  %-18s → %s" % (a.get_actor_label(), c.get_material(0).get_name()))
log(">>> 적용 액터 %d개.  처마 밑에서 올려다보면 지붕 안쪽이 어두워야 함" % n)
log("레벨 저장 %s" % LES.save_current_level())
