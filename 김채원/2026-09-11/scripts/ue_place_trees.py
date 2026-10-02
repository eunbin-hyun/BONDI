# -*- coding: utf-8 -*-
"""
인왕제색도 - 나무 메시를 밑동 위치 168곳에 심기  (v2: AI 생성 소나무 2종 기본)
===============================================================================
사용법 (언리얼 하단 콘솔, Cmd 모드):
    py "C:/KCW_SSAFY/특화/S15P21C201/김채원/2026-09-11/scripts/ue_place_trees.py"

전제
  1) runtime/pine_ai_1.glb · pine_ai_2.glb 를 콘텐츠 브라우저 Museum/Inwang 폴더에 임포트해 둠
     → 에셋 경로가 /Game/Museum/Inwang/pine_ai_1/StaticMeshes/pine_ai_1 (임포트 규칙: <이름>/StaticMeshes/<이름>)
     다른 폴더에 넣었으면 아래 PINE_MESHES 경로를 고침 (에셋 우클릭 → 레퍼런스 복사)
  2) 레벨에 'trees' 액터(절차 생성 나무)가 있음 — 축 매핑 측정 기준으로만 쓰고, 심은 뒤 숨김

하는 일
  - records/tree_positions.json 의 밑동 168곳 (glTF 좌표) → 측정한 축 매핑으로 언리얼 좌표 변환
  - 나무마다 StaticMeshActor 스폰. 소나무는 PINE_MESHES 를 번갈아 씀. 높이는 json 의 h_m (메시는 높이 1 m 로 정규화돼 있어 스케일 = h_m)
  - 회전 무작위, 아웃라이너 폴더 Inwang/Trees. 다시 실행하면 이전 것 지우고 다시 심음
  - 머티리얼: MATERIAL_MODE
      "vertex"  → M_InwangVertexUnlit (검증됨). pine_ai_*.glb 는 먹 팔레트가 정점색으로 이미 구워져 있어 이걸로 충분
      "inkwash" → M_InwangInkWash 를 새로 만들어 덮음 (진묵↔담묵 + 거리 바램). 노드 15개, 미검증. Fab 등 외부 메시용
      "none"    → 메시 원래 머티리얼

확인 지표: 로그 '심음 168 / 168', 아웃라이너 Inwang/Trees 폴더에 tree_000~, 나무들이 먹색으로 옛 자리에 서 있음

작성: 김채원(AI) / 2026-09-11
"""

import json, math, random
import unreal

PINE_MESHES = ["/Game/Museum/Inwang/pine_ai_1/StaticMeshes/pine_ai_1",
               "/Game/Museum/Inwang/pine_ai_2/StaticMeshes/pine_ai_2"]
WILLOW_MESH = ""                               # 없으면 비워둠 → 절차 생성 버드나무는 'trees' 액터에 남아 있으므로 그냥 건너뜀
POS_JSON    = "C:/KCW_SSAFY/특화/S15P21C201/김채원/2026-09-11/assets/spec19/records/tree_positions.json"
MATERIAL_MODE = "vertex"                       # "vertex" | "inkwash" | "none"
MESH_HEIGHT_NORMALIZED = True                  # pine_ai_*.glb 는 높이 1 m. Fab 메시면 False (실제 높이를 재서 나눔)
FOLDER = "Inwang/Trees"
PKG = "/Game/Museum/Inwang"

TREES_G_MIN = None; TREES_G_MAX = None         # json 의 meta 에서 읽음


def log(m):
    unreal.log("[INWANG] %s" % m)


def srgb_to_linear(c):
    x = c / 255.0
    return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4


data = json.load(open(POS_JSON, encoding="utf-8"))
meta = data["meta"]; trees = data["trees"]
TREES_G_MIN = meta["trees_glb_bounds_min"]; TREES_G_MAX = meta["trees_glb_bounds_max"]

sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
EAL = unreal.EditorAssetLibrary

# ── 0) 에셋 확인
pines = []
for p in PINE_MESHES:
    if EAL.does_asset_exist(p):
        pines.append(EAL.load_asset(p))
    else:
        log("!! 소나무 메시 없음: %s" % p)
if not pines:
    log("!! 소나무 메시가 하나도 없음 → PINE_MESHES 경로 확인 (임포트했는지, 폴더가 맞는지)")
    raise SystemExit
willow = EAL.load_asset(WILLOW_MESH) if (WILLOW_MESH and EAL.does_asset_exist(WILLOW_MESH)) else None


def asset_height_cm(sm):
    if MESH_HEIGHT_NORMALIZED:
        return 100.0
    b = sm.get_bounds()
    return float(b.box_extent.z * 2.0)


log("소나무 메시 %d종 (높이 %s)" % (len(pines), "정규화 1 m" if MESH_HEIGHT_NORMALIZED else "실측"))

# ── 1) 축 매핑 측정 (ue_goto_entry.py 와 같은 방법: trees 액터 바운딩 박스 vs glTF)
actors = {a.get_actor_label(): a for a in sub.get_all_level_actors()}
ref = actors.get("trees")
if ref is None:
    log("!! 'trees' 액터가 없어 축 매핑을 잴 수 없음"); raise SystemExit
origin, ext = ref.get_actor_bounds(False)
ue_c = [origin.x, origin.y, origin.z]; ue_e = [ext.x * 2, ext.y * 2, ext.z * 2]
g_c = [(TREES_G_MIN[i] + TREES_G_MAX[i]) / 2 * 100 for i in range(3)]
g_e = [(TREES_G_MAX[i] - TREES_G_MIN[i]) * 100 for i in range(3)]
mapping = []; used = set()
for i in range(3):
    best = None
    for j in range(3):
        if j in used: continue
        err = abs(ue_e[i] - g_e[j]) / g_e[j]
        if err < 0.03 and (best is None or err < best[1]): best = (j, err)
    if best is None:
        log("!! 축 매핑 실패  UE 폭 %s  glTF 폭 %s" % ([round(v) for v in ue_e], [round(v) for v in g_e])); raise SystemExit
    used.add(best[0]); mapping.append((best[0], 1 if ue_c[i] * g_c[best[0]] >= 0 else -1))
log("매핑 [측정]: " + ", ".join("UE_%s = %sg%s" % ("XYZ"[i], "+" if s > 0 else "-", "XYZ"[j]) for i, (j, s) in enumerate(mapping)))
ref_loc = ref.get_actor_location()


def to_ue(g):
    return unreal.Vector(*[ref_loc.x * 0 + mapping[i][1] * g[mapping[i][0]] * 100.0 for i in range(3)])


# ── 2) 수묵 머티리얼 (원화 팔레트: records/ink_palette.json 과 같은 값)
#    색 = lerp(진묵, 담묵, 면이 위를 보는 정도)  → 위쪽은 담묵으로 번지고 옆·아래는 진묵 (먹 덩어리 느낌)
#    거리 = 150 m 부터 1 km 에 걸쳐 종이색 쪽으로 62% 까지 바램  (절차 나무의 ink_color(d) 와 같은 식)
#    노드 연결이 하나라도 실패하면 진묵 단색으로 대체 (그래도 심기는 진행)
PAL = {"진묵": (56, 52, 52), "담묵": (108, 101, 96), "종이": (186, 170, 150)}
ink_mat = None
if MATERIAL_MODE == "vertex":
    ink_mat = EAL.load_asset(PKG + "/M_InwangVertexUnlit")
    log("머티리얼: M_InwangVertexUnlit %s" % ("OK" if ink_mat else "!! 없음 → ue_setup_materials.py 먼저"))
elif MATERIAL_MODE == "inkwash":
    ML = unreal.MaterialEditingLibrary
    path = PKG + "/M_InwangInkWash"
    if EAL.does_asset_exist(path):
        ink_mat = EAL.load_asset(path); ML.delete_all_material_expressions(ink_mat)
    else:
        ink_mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset("M_InwangInkWash", PKG, unreal.Material, unreal.MaterialFactoryNew())
    ink_mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    ink_mat.set_editor_property("two_sided", True)

    def col(name, x, y):
        e = ML.create_material_expression(ink_mat, unreal.MaterialExpressionConstant3Vector, x, y)
        e.set_editor_property("constant", unreal.LinearColor(*[srgb_to_linear(v) for v in PAL[name]], 1.0)); return e

    def const(v, x, y):
        e = ML.create_material_expression(ink_mat, unreal.MaterialExpressionConstant, x, y); e.set_editor_property("r", v); return e

    def node(cls, x, y, **p):
        e = ML.create_material_expression(ink_mat, cls, x, y)
        for k, v in p.items(): e.set_editor_property(k, v)
        return e

    def L(a, ao, b, bi, what):
        for o_ in ao:
            for i_ in bi:
                try:
                    if ML.connect_material_expressions(a, o_, b, i_):
                        return True
                except Exception:
                    pass
        log("   !! 연결 실패 %s" % what); return False

    ok = True
    jin, dam, paper = col("진묵", -1400, -200), col("담묵", -1400, -80), col("종이", -800, 200)
    nrm = node(unreal.MaterialExpressionVertexNormalWS, -1400, 60)
    up = node(unreal.MaterialExpressionComponentMask, -1250, 60, r=False, g=False, b=True, a=False)
    sat1 = node(unreal.MaterialExpressionSaturate, -1100, 60)
    lerp1 = node(unreal.MaterialExpressionLinearInterpolate, -950, -100)
    depth = node(unreal.MaterialExpressionPixelDepth, -1400, 300)
    sub = node(unreal.MaterialExpressionSubtract, -1250, 300); c150 = const(15000.0, -1400, 380)
    div = node(unreal.MaterialExpressionDivide, -1100, 300);   c1k = const(100000.0, -1250, 380)
    sat2 = node(unreal.MaterialExpressionSaturate, -950, 300)
    pw = node(unreal.MaterialExpressionPower, -800, 300);      c075 = const(0.75, -950, 380)
    mul = node(unreal.MaterialExpressionMultiply, -650, 300);  c062 = const(0.62, -800, 380)
    lerp2 = node(unreal.MaterialExpressionLinearInterpolate, -450, 0)
    ANY = ["", "Input"]
    ok &= L(nrm, [""], up, ANY, "Normal→Mask")
    ok &= L(up, [""], sat1, ANY, "Mask→Saturate")
    ok &= L(jin, [""], lerp1, ["A"], "진묵→Lerp.A"); ok &= L(dam, [""], lerp1, ["B"], "담묵→Lerp.B"); ok &= L(sat1, [""], lerp1, ["Alpha"], "up→Lerp.Alpha")
    ok &= L(depth, [""], sub, ["A"], "Depth→Sub.A"); ok &= L(c150, [""], sub, ["B"], "150m→Sub.B")
    ok &= L(sub, [""], div, ["A"], "Sub→Div.A"); ok &= L(c1k, [""], div, ["B"], "1km→Div.B")
    ok &= L(div, [""], sat2, ANY, "Div→Saturate")
    ok &= L(sat2, [""], pw, ["Base", ""], "Sat→Power.Base"); ok &= L(c075, [""], pw, ["Exp", "Exponent"], "0.75→Power.Exp")
    ok &= L(pw, [""], mul, ["A"], "Pow→Mul.A"); ok &= L(c062, [""], mul, ["B"], "0.62→Mul.B")
    ok &= L(lerp1, [""], lerp2, ["A"], "먹→Lerp2.A"); ok &= L(paper, [""], lerp2, ["B"], "종이→Lerp2.B"); ok &= L(mul, [""], lerp2, ["Alpha"], "거리→Lerp2.Alpha")
    if ok:
        ok = ML.connect_material_property(lerp2, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    if not ok:
        ML.delete_all_material_expressions(ink_mat)
        c = col("진묵", -300, 0)
        ML.connect_material_property(c, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        log("   수묵 노드 실패 → 진묵 단색으로 대체")
    ML.recompile_material(ink_mat); EAL.save_asset(path)
    log("M_InwangInkWash %s" % ("OK (진묵↔담묵 + 거리 바램)" if ok else "단색 대체"))

# ── 3) 이전 것 정리 후 심기
old = [a for a in sub.get_all_level_actors() if a.get_actor_label().startswith("tree_")]
for a in old:
    sub.destroy_actor(a)
if old:
    log("이전 나무 %d개 제거" % len(old))

rng = random.Random(7)
placed = 0; skipped = 0
for i, t in enumerate(trees):
    if t["species"] == "willow":
        if willow is None:
            skipped += 1; continue
        sm = willow
    else:
        sm = pines[i % len(pines)]
    h_asset = asset_height_cm(sm)
    loc = to_ue((t["x"], t["y"], t["z"]))
    rot = unreal.Rotator(roll=0.0, pitch=0.0, yaw=rng.uniform(0, 360))
    a = sub.spawn_actor_from_object(sm, loc, rot)
    if a is None:
        continue
    s = (t["h_m"] * 100.0) / max(h_asset, 1.0)
    a.set_actor_scale3d(unreal.Vector(s, s, s))
    a.set_actor_label("tree_%03d" % i)
    a.set_folder_path(FOLDER)
    if ink_mat is not None:
        comp = a.get_component_by_class(unreal.StaticMeshComponent)
        for k in range(comp.get_num_materials()):
            comp.set_material(k, ink_mat)
    placed += 1

# 절차 생성 나무 숨김 (지우진 않음 — 축 매핑 기준으로 계속 필요)
ref.set_is_temporarily_hidden_in_editor(True)
ref.set_actor_hidden_in_game(True)

log("-" * 70)
log("심음 %d / %d   (버드나무 %d 건너뜀 — 메시 없음, 절차 나무 'trees' 액터는 숨김)" % (placed, len(trees), skipped))
log(">>> %s" % ("성공. Ctrl+S. 아웃라이너 %s 폴더 확인." % FOLDER if placed + skipped == len(trees) else "!! 일부 실패 — 위 로그 복사"))
