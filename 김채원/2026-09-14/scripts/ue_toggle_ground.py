# -*- coding: utf-8 -*-
"""
땅 텍스처 토글 — 원화 ↔ 흙 ↔ 풀  v2 (2026-09-14)
==================================================
v2: 지형 전체를 덮지 않는다. **평평한 곳(바닥)에만** 흙/풀을 섞고 경사면(산)은 원화 텍스처 그대로.
    면 기울기(월드 법선 Z)로 가르며, SLOPE_FLAT 이상이면 흙/풀, SLOPE_STEEP 이하면 원화, 사이는 부드럽게 섞임.
L_Inwang 의 terrain_jeong 머티리얼을 돌려가며 바꾼다. 실행할 때마다 다음 단계로 순환.
  0 원화(M_InwangTerrainJeong) → 1 흙(M_InwangGroundSoil) → 2 풀(M_InwangGroundGrass) → 0 …
텍스처는 runtime/ground_soil.png · ground_grass.png 를 경로 지정 임포트(없으면 자동).
UV 는 월드 좌표 XY 기준 GROUND_TILE_CM 마다 반복 → 지형 크기와 무관하게 결 크기 일정.
사용법 (L_Inwang 열린 상태, 언리얼 콘솔):
    py "C:/KCW_SSAFY/특화/S15P21C201/김채원/2026-09-12/scripts/ue_toggle_ground.py"
확인 지표: '>>> 지금: 흙' / '풀' / '원화'  + 뷰포트 지형 색 변화. MODE 를 0/1/2 로 직접 지정도 가능.
"""
import os, unreal

MODE = None                 # None = 순환, 0 원화 / 1 흙 / 2 풀 로 직접 지정 가능
GROUND_TILE_CM = 800.0      # 텍스처 1장이 덮는 실제 길이 (작을수록 촘촘)
SLOPE_STEEP, SLOPE_FLAT = 0.80, 0.95   # 법선 Z: 이하면 원화(경사·산), 이상이면 흙/풀(평지). 사이는 혼합
RT = r"C:\Users\SSAFY\Desktop\SSAFY_2학기\02_특화 프로젝트\특화PJT_\landscape_to_3D\Claude outputs\VR_inwangjesaekdo_v0.11\inwangjesaekdo_VR_v0.11\runtime"
PKG = "/Game/Museum/Inwang"
TARGET = "terrain_jeong"

EAL = unreal.EditorAssetLibrary; ML = unreal.MaterialEditingLibrary; TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem); LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


def log(m): unreal.log("[INWANG] %s" % m)


def import_png(name):
    p = "%s/room/%s" % (PKG, name)
    if EAL.does_asset_exist(p):
        t = EAL.load_asset(p)
        if isinstance(t, unreal.Texture2D): return t
    src = os.path.join(RT, name + ".png")
    if not os.path.exists(src): log("!! %s 없음" % src); return None
    t = unreal.AssetImportTask(); t.set_editor_property("filename", src); t.set_editor_property("destination_path", PKG + "/room")
    t.set_editor_property("replace_existing", True); t.set_editor_property("automated", True); t.set_editor_property("save", True)
    TOOLS.import_asset_tasks([t]); tex = EAL.load_asset(p)
    log("텍스처 임포트 %s %s" % (name, "OK" if isinstance(tex, unreal.Texture2D) else "!! 실패"))
    return tex if isinstance(tex, unreal.Texture2D) else None


def ground_material(name, tex):
    """Unlit. UV = 월드 XY / 타일. 평지에만 흙·풀, 경사면은 원화 텍스처(terrain_jeong 자체 UV)."""
    path = "%s/%s" % (PKG, name)
    if EAL.does_asset_exist(path): mat = EAL.load_asset(path); ML.delete_all_material_expressions(mat)
    else: mat = TOOLS.create_asset(name, PKG, unreal.Material, unreal.MaterialFactoryNew())
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_OPAQUE)
    def mk(cls, x, y, **pr):
        e = ML.create_material_expression(mat, cls, x, y)
        for k, v in pr.items(): e.set_editor_property(k, v)
        return e
    oks = []
    def L(a, b, bi, ao=""):
        r = False
        for i in ([bi] if isinstance(bi, str) else bi):
            for o in ([ao] if isinstance(ao, str) else ao):
                try:
                    if ML.connect_material_expressions(a, o, b, i): r = True; break
                except Exception: pass
            if r: break
        oks.append(r)
    # 흙/풀: 월드 XY 투영
    wp = mk(unreal.MaterialExpressionWorldPosition, -1500, 0)
    mx = mk(unreal.MaterialExpressionComponentMask, -1300, -60, r=True, g=False, b=False, a=False)
    my = mk(unreal.MaterialExpressionComponentMask, -1300, 60, r=False, g=True, b=False, a=False)
    k = mk(unreal.MaterialExpressionConstant, -1300, 200, r=1.0 / GROUND_TILE_CM)
    mu = mk(unreal.MaterialExpressionMultiply, -1100, -60); mv = mk(unreal.MaterialExpressionMultiply, -1100, 60)
    ap = mk(unreal.MaterialExpressionAppendVector, -900, 0)
    ts = mk(unreal.MaterialExpressionTextureSample, -700, 0, texture=tex)
    L(wp, mx, ["", "Input"]); L(wp, my, ["", "Input"])
    L(mx, mu, "A"); L(k, mu, "B"); L(my, mv, "A"); L(k, mv, "B")
    L(mu, ap, "A"); L(mv, ap, "B"); L(ap, ts, ["UVs", "Coordinates", ""])
    # 원화: terrain_jeong 자체 UV + 원화 텍스처
    art = find_terrain_texture()
    ts2 = mk(unreal.MaterialExpressionTextureSample, -700, 400, texture=art) if art is not None else None
    # 기울기 마스크: 월드 법선 Z → SmoothStep(STEEP, FLAT)
    vn = mk(unreal.MaterialExpressionVertexNormalWS, -1500, 700)
    mz = mk(unreal.MaterialExpressionComponentMask, -1300, 700, r=False, g=False, b=True, a=False)
    ss = mk(unreal.MaterialExpressionSmoothStep, -1100, 700)
    try: ss.set_editor_property("const_min", SLOPE_STEEP); ss.set_editor_property("const_max", SLOPE_FLAT)
    except Exception as ex: log("   (참고) SmoothStep 범위 설정 불가: %s" % ex)
    L(vn, mz, ["", "Input"]); L(mz, ss, ["Value", "", "Input"])
    if ts2 is not None:
        lp = mk(unreal.MaterialExpressionLinearInterpolate, -450, 200)
        L(ts2, lp, "A", ["RGB", ""]); L(ts, lp, "B", ["RGB", ""]); L(ss, lp, "Alpha")
        ok = ML.connect_material_property(lp, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        log("   원화 텍스처 %s 와 기울기 혼합 (경사 %.2f~%.2f)" % (art.get_name(), SLOPE_STEEP, SLOPE_FLAT))
    else:
        ok = ML.connect_material_property(ts, "RGB", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        log("   !! terrain_jeong 텍스처를 못 찾아 지형 전체를 덮음 (경사 혼합 없음)")
    ML.recompile_material(mat); EAL.save_asset(path)
    log("머티리얼 %-24s 노드연결 %d/%d  Emissive %s" % (name, sum(oks), len(oks), ok))
    return mat


def find_terrain_texture():
    """terrain_jeong 메시가 참조하는 원화 텍스처 (ue_setup_materials 와 같은 규칙)"""
    for p in EAL.list_assets(PKG, recursive=True, include_folder=False):
        leaf = p.rsplit("/", 1)[-1].split(".")[0].lower()
        if leaf.startswith("terrain_jeong"):
            o = EAL.load_asset(p)
            if isinstance(o, unreal.Texture2D): return o
    return None


a = {x.get_actor_label(): x for x in sub.get_all_level_actors()}.get(TARGET)
if a is None: log("!! %s 액터 없음 — 현재 레벨이 L_Inwang 인지 확인" % TARGET)
else:
    comp = a.get_component_by_class(unreal.StaticMeshComponent)
    cur = comp.get_material(0); cur_name = cur.get_name() if cur else ""
    order = ["M_InwangTerrainJeong", "M_InwangGroundSoil", "M_InwangGroundGrass"]
    idx = order.index(cur_name) if cur_name in order else 0
    nxt = MODE if MODE is not None else (idx + 1) % 3
    if nxt == 0:
        m = EAL.load_asset(PKG + "/M_InwangTerrainJeong")
        if m is None: log("!! M_InwangTerrainJeong 없음 — ue_setup_materials.py 먼저")
    elif nxt == 1:
        t = import_png("ground_soil"); m = ground_material("M_InwangGroundSoil", t) if t else None
    else:
        t = import_png("ground_grass"); m = ground_material("M_InwangGroundGrass", t) if t else None
    if m is not None:
        for i in range(comp.get_num_materials()): comp.set_material(i, m)
        got = comp.get_material(0).get_name()
        log(">>> 지금: %s  (머티리얼 %s)  [이전 %s]" % (["원화", "흙", "풀"][nxt], got, cur_name or "없음"))
        log("레벨 저장 %s" % LES.save_current_level())
