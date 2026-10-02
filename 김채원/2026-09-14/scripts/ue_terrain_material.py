# -*- coding: utf-8 -*-
"""
지형 머티리얼 한 장으로 통합 (2026-09-14)  ※ ue_apply_evidence.py 를 대체함
============================================================================
지형에 얹는 층이 셋으로 늘어서 스크립트가 서로 덮어쓰는 문제가 있었다. 하나로 합치고 위쪽 스위치로 켜고 끈다.
  1) 원화 텍스처            — 메시 자체 UV(시점 투영)
  2) 근거 여백 (USE_EVIDENCE) — terrain_evidence.png. 정선 시점에서 안 보이던 곳을 종이색으로. 월드 좌표 샘플링
  3) 접지 음영 (USE_AO)      — contact_ao.png. 집·안내판 발밑이 먹처럼 번져 어두워짐. 월드 좌표 샘플링(Clamp)
  4) 조명 (USE_LIT)          — Lit + 월드 법선을 광원 방향으로 고정 → 밝기는 평평, 실시간 그림자만 얹힘
                               (끄면 Unlit + Emissive. 그림자는 안 생기지만 원화 색이 그대로)

좌표 맞추기: 축 대응은 지형 액터 월드 바운드 ↔ 원본 glb 바운드 크기로, 축 부호는 기준 액터 두 개의 좌표 '차이' 부호로
   데이터에서 확정한다. 지형 UV 가 평면 투영이 아니라 시점 투영이라 UV 로는 위치를 못 찾기 때문.

사용법 (L_Inwang 열린 상태, 언리얼 콘솔):
    py "C:/KCW_SSAFY/특화/S15P21C201/김채원/2026-09-12/scripts/ue_terrain_material.py"
    (조명 액터 자체는 ue_setup_shadows.py 가 만든다. USE_LIT=True 로 쓰려면 그 스크립트를 먼저 한 번)
확인 지표: '축 대응 …', '기준점 대조 … 오차 … cm' (몇 십 cm 이내), '연결 N/N', '>>> 적용: 여백 O / 음영 O / 조명 O'
"""
import os, json, math, unreal

USE_EVIDENCE = True
USE_AO = True
USE_LIT = True

PAPER = (186, 170, 150)     # 여백 종이색 (ink_palette.json '종이(85-95%)')
EV_FLOOR = 0.12             # 근거 0 인 곳에 남길 원화 비율
EV_GAMMA = 1.35             # 클수록 여백 경계가 또렷
AO_POWER = 1.0              # 접지 음영 세기 배수 (1 = 구운 그대로, 2 면 두 배 진함)
BASE_GAIN = 1.0             # 전체 밝기 보정

RT = r"C:\Users\SSAFY\Desktop\SSAFY_2학기\02_특화 프로젝트\특화PJT_\landscape_to_3D\Claude outputs\VR_inwangjesaekdo_v0.11\inwangjesaekdo_VR_v0.11\runtime"
RECD = os.path.join(os.path.dirname(RT), "records")
PKG = "/Game/Museum/Inwang"
TARGET = "terrain_jeong"
MAT_NAME = "M_InwangTerrain"

EAL = unreal.EditorAssetLibrary; ML = unreal.MaterialEditingLibrary; TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem); LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


def log(m): unreal.log("[INWANG] %s" % m)


def import_png(name, clamp=False):
    p = "%s/room/%s" % (PKG, name)
    tex = EAL.load_asset(p) if EAL.does_asset_exist(p) else None
    if not isinstance(tex, unreal.Texture2D):
        src = os.path.join(RT, name + ".png")
        if not os.path.exists(src): log("!! %s 없음" % src); return None
        t = unreal.AssetImportTask()
        t.set_editor_property("filename", src); t.set_editor_property("destination_path", PKG + "/room")
        t.set_editor_property("replace_existing", True); t.set_editor_property("automated", True); t.set_editor_property("save", True)
        TOOLS.import_asset_tasks([t]); tex = EAL.load_asset(p)
    if not isinstance(tex, unreal.Texture2D): log("!! %s 임포트 실패" % name); return None
    try:
        tex.set_editor_property("srgb", False)
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
        if clamp:
            tex.set_editor_property("address_x", unreal.TextureAddress.TA_CLAMP)
            tex.set_editor_property("address_y", unreal.TextureAddress.TA_CLAMP)
        EAL.save_loaded_asset(tex)
    except Exception as ex: log("   (참고) %s 텍스처 설정 일부 실패: %s" % (name, ex))
    log("   마스크 %s %dx%d  주소모드 %s" % (name, tex.blueprint_get_size_x(), tex.blueprint_get_size_y(), "Clamp" if clamp else "기본"))
    return tex


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
a = A.get(TARGET)
if a is None: log("!! '%s' 액터 없음 — 현재 레벨이 L_Inwang 인지 확인" % TARGET); raise SystemExit
comp = a.get_component_by_class(unreal.StaticMeshComponent)

# ── 월드 축 대응·부호 (지형 기준) ───────────────────────────────
EVJ = os.path.join(RECD, "terrain_evidence.json")
if not os.path.exists(EVJ): log("!! %s 없음 — build_visibility_mask.py 결과가 필요" % EVJ); raise SystemExit
EV = json.load(open(EVJ, encoding="utf-8"))
g_lo = {"x": EV["x_min_m"], "z": EV["z_min_m"]}; g_hi = {"x": EV["x_max_m"], "z": EV["z_max_m"]}
o, e = a.get_actor_bounds(False)
w_lo = [o.x - e.x, o.y - e.y]; w_hi = [o.x + e.x, o.y + e.y]
w_size = [w_hi[0] - w_lo[0], w_hi[1] - w_lo[1]]
g_size = {k: g_hi[k] - g_lo[k] for k in ("x", "z")}
pair = {i: min(g_size, key=lambda k: abs(w_size[i] / 100.0 - g_size[k])) for i in (0, 1)}
if pair[0] == pair[1]: log("!! 축 대응 겹침 — 수동 확인 필요"); raise SystemExit
log("축 대응: 월드 X ← glb %s (%.0f m vs %.0f m),  월드 Y ← glb %s (%.0f m vs %.0f m)"
    % (pair[0], w_size[0] / 100.0, g_size[pair[0]], pair[1], w_size[1] / 100.0, g_size[pair[1]]))
sign = {0: 1.0, 1: 1.0}
LM = EV.get("landmarks_glb_m", {}); have = [(n, v) for n, v in LM.items() if n in A]
if len(have) >= 2:
    (n1, v1), (n2, v2) = have[0], have[1]
    p1, p2 = A[n1].get_actor_location(), A[n2].get_actor_location()
    dw = [p2.x - p1.x, p2.y - p1.y]; dg = {"x": v2[0] - v1[0], "z": v2[2] - v1[2]}
    for i in (0, 1):
        d = dg[pair[i]]
        if abs(d) < 1.0: log("   (참고) 월드 %s 부호: 기준점 차이 %.1f m 로 작아 + 가정" % ("XY"[i], d)); continue
        sign[i] = 1.0 if (dw[i] * d) > 0 else -1.0
    log("축 부호: %+.0f, %+.0f  (기준점 %s → %s)" % (sign[0], sign[1], n1, n2))
else:
    log("   (참고) 기준 액터 2개 미만 — 부호 + 가정. 여백/음영이 반대쪽이면 알려줄 것")


def kc_for(i, lo_g, hi_g):
    k = (w_hi[i] - w_lo[i]) / ((hi_g - lo_g) if sign[i] > 0 else (lo_g - hi_g))
    return k, w_lo[i] - k * (lo_g if sign[i] > 0 else hi_g)


def world_uv_coeffs(J):
    """이 이미지가 덮는 지형 범위 → (월드좌표 × s + o) 계수 두 쌍"""
    out = []
    for i in (0, 1):
        key = pair[i]
        k, c = kc_for(i, g_lo[key], g_hi[key])                       # 월드 ↔ glb 는 지형 전체로 구함
        lo_i = J["x_min_m"] if key == "x" else J["z_min_m"]
        hi_i = J["x_max_m"] if key == "x" else J["z_max_m"]
        span = hi_i - lo_i
        out.append((1.0 / (k * span), (-c / k - lo_i) / span))
    return out


for n, v in have:
    p = A[n].get_actor_location(); pred = []
    for i in (0, 1):
        key = pair[i]; k, c = kc_for(i, g_lo[key], g_hi[key])
        pred.append(k * (v[0] if key == "x" else v[2]) + c)
    log("기준점 대조 %-18s 예측 (%.0f, %.0f) vs 실제 (%.0f, %.0f)  오차 (%.0f, %.0f) cm"
        % (n, pred[0], pred[1], p.x, p.y, abs(pred[0] - p.x), abs(pred[1] - p.y)))

# ── 머티리얼 ───────────────────────────────────────────────────
art = art_texture(comp)
if art is None: log("!! 원화 텍스처를 못 찾음"); raise SystemExit
ev_tex = import_png("terrain_evidence") if USE_EVIDENCE else None
ao_tex = import_png("contact_ao", clamp=True) if USE_AO else None
if USE_EVIDENCE and ev_tex is None: USE_EVIDENCE = False; log("   → 여백 끔")
if USE_AO and ao_tex is None: USE_AO = False; log("   → 음영 끔")

Lue = (0.057, -0.270, 0.961)
SJ = os.path.join(RECD, "sun_fit.json")
if os.path.exists(SJ):
    Lg = json.load(open(SJ, encoding="utf-8"))["L_glb"]
    v = (Lg[0], Lg[2], Lg[1]); n_ = math.sqrt(sum(t * t for t in v)) or 1.0
    Lue = tuple(t / n_ for t in v)

path = "%s/%s" % (PKG, MAT_NAME)
if EAL.does_asset_exist(path): mat = EAL.load_asset(path); ML.delete_all_material_expressions(mat)
else: mat = TOOLS.create_asset(MAT_NAME, PKG, unreal.Material, unreal.MaterialFactoryNew())
mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_DEFAULT_LIT if USE_LIT else unreal.MaterialShadingModel.MSM_UNLIT)
mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_OPAQUE)
tsn = True
if USE_LIT:
    try: mat.set_editor_property("tangent_space_normal", False); tsn = False
    except Exception as ex: log("   !! tangent_space_normal 설정 실패: %s" % ex)
oks = []


def mk(cls, x, y, **pr):
    ex = ML.create_material_expression(mat, cls, x, y)
    for k, v in pr.items(): ex.set_editor_property(k, v)
    return ex


def L(s_, d_, ins, outs=""):
    r = False
    for i in ([ins] if isinstance(ins, str) else ins):
        for ou in ([outs] if isinstance(outs, str) else outs):
            try:
                if ML.connect_material_expressions(s_, ou, d_, i): r = True; break
            except Exception: pass
        if r: break
    oks.append(r); return r


def world_sampler(tex, J, y, tag):
    """월드 XY 로 텍스처를 샘플하는 작은 묶음 → TextureSample 노드 반환"""
    (su_, ou_), (sv_, ov_) = world_uv_coeffs(J)
    log("   %s 월드→UV: u = X×%.8f + %.5f,  v = Y×%.8f + %.5f" % (tag, su_, ou_, sv_, ov_))
    wp = mk(unreal.MaterialExpressionWorldPosition, -2000, y)
    mx = mk(unreal.MaterialExpressionComponentMask, -1850, y - 40, r=True, g=False, b=False, a=False)
    my = mk(unreal.MaterialExpressionComponentMask, -1850, y + 60, r=False, g=True, b=False, a=False)
    cu = mk(unreal.MaterialExpressionConstant, -1850, y - 120, r=su_); du = mk(unreal.MaterialExpressionConstant, -1700, y - 120, r=ou_)
    cv = mk(unreal.MaterialExpressionConstant, -1850, y + 140, r=sv_); dv = mk(unreal.MaterialExpressionConstant, -1700, y + 140, r=ov_)
    mu = mk(unreal.MaterialExpressionMultiply, -1680, y - 40); au = mk(unreal.MaterialExpressionAdd, -1540, y - 40)
    mv = mk(unreal.MaterialExpressionMultiply, -1680, y + 60); av = mk(unreal.MaterialExpressionAdd, -1540, y + 60)
    ap = mk(unreal.MaterialExpressionAppendVector, -1400, y)
    ts_ = mk(unreal.MaterialExpressionTextureSample, -1250, y, texture=tex)
    L(wp, mx, ["", "Input"]); L(wp, my, ["", "Input"])
    L(mx, mu, "A"); L(cu, mu, "B"); L(mu, au, "A"); L(du, au, "B")
    L(my, mv, "A"); L(cv, mv, "B"); L(mv, av, "A"); L(dv, av, "B")
    L(au, ap, "A"); L(av, ap, "B"); L(ap, ts_, ["UVs", "Coordinates", ""])
    return ts_


ts_art = mk(unreal.MaterialExpressionTextureSample, -1250, -700, texture=art)
color = ts_art
color_out = ["RGB", ""]

if USE_EVIDENCE:
    ts_ev = world_sampler(ev_tex, EV, -200, "근거지도")
    gam = mk(unreal.MaterialExpressionConstant, -1100, -120, r=EV_GAMMA)
    pw = mk(unreal.MaterialExpressionPower, -960, -180)
    fl = mk(unreal.MaterialExpressionConstant, -1100, -40, r=EV_FLOOR)
    one = mk(unreal.MaterialExpressionConstant, -1100, 40, r=1.0)
    sb = mk(unreal.MaterialExpressionSubtract, -960, -20)
    mm = mk(unreal.MaterialExpressionMultiply, -820, -120); ad = mk(unreal.MaterialExpressionAdd, -700, -80)
    paper = mk(unreal.MaterialExpressionConstant3Vector, -820, -400,
               constant=unreal.LinearColor(PAPER[0] / 255.0, PAPER[1] / 255.0, PAPER[2] / 255.0, 1.0))
    lerp = mk(unreal.MaterialExpressionLinearInterpolate, -520, -300)
    L(ts_ev, pw, ["Base", "A"], ["R", "RGB", ""]); L(gam, pw, ["Exp", "B"])
    L(one, sb, "A"); L(fl, sb, "B"); L(pw, mm, "A"); L(sb, mm, "B"); L(mm, ad, "A"); L(fl, ad, "B")
    L(paper, lerp, "A"); L(color, lerp, "B", color_out); L(ad, lerp, "Alpha")
    color, color_out = lerp, ""

if USE_AO:
    AOJ = json.load(open(os.path.join(RECD, "contact_ao.json"), encoding="utf-8"))
    ts_ao = world_sampler(ao_tex, AOJ, 400, "접지음영")
    aop = mk(unreal.MaterialExpressionConstant, -1100, 520, r=AO_POWER)
    pwa = mk(unreal.MaterialExpressionPower, -960, 440)
    mul_ao = mk(unreal.MaterialExpressionMultiply, -380, 0)
    L(ts_ao, pwa, ["Base", "A"], ["R", "RGB", ""]); L(aop, pwa, ["Exp", "B"])
    L(color, mul_ao, "A", color_out); L(pwa, mul_ao, "B")
    color, color_out = mul_ao, ""

gain = mk(unreal.MaterialExpressionConstant, -380, 200, r=BASE_GAIN)
mul_g = mk(unreal.MaterialExpressionMultiply, -220, 60)
L(color, mul_g, "A", color_out); L(gain, mul_g, "B")

if USE_LIT:
    nrm = mk(unreal.MaterialExpressionConstant3Vector, -220, 300, constant=unreal.LinearColor(Lue[0], Lue[1], Lue[2], 0.0))
    rgh = mk(unreal.MaterialExpressionConstant, -220, 420, r=1.0)
    spc = mk(unreal.MaterialExpressionConstant, -220, 500, r=0.0)
    ok1 = ML.connect_material_property(mul_g, "", unreal.MaterialProperty.MP_BASE_COLOR)
    ok2 = ML.connect_material_property(nrm, "", unreal.MaterialProperty.MP_NORMAL)
    ML.connect_material_property(rgh, "", unreal.MaterialProperty.MP_ROUGHNESS)
    ML.connect_material_property(spc, "", unreal.MaterialProperty.MP_SPECULAR)
    log("Lit: BaseColor %s / Normal %s / 탄젠트공간법선 %s (False 여야 법선 고정)  법선벡터 (%.3f, %.3f, %.3f)" % (ok1, ok2, tsn, Lue[0], Lue[1], Lue[2]))
else:
    log("Unlit: Emissive %s" % ML.connect_material_property(mul_g, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR))

ML.recompile_material(mat); EAL.save_asset(path)
for i in range(comp.get_num_materials()): comp.set_material(i, mat)
if USE_LIT:
    try: comp.set_mobility(unreal.ComponentMobility.MOVABLE)
    except Exception: pass
log("노드 연결 %d/%d" % (sum(oks), len(oks)))
log(">>> 적용: 여백 %s / 접지음영 %s / 조명 %s   머티리얼 %s" %
    ("O" if USE_EVIDENCE else "X", "O" if USE_AO else "X", "O" if USE_LIT else "X", comp.get_material(0).get_name()))
log("레벨 저장 %s" % LES.save_current_level())
