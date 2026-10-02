# -*- coding: utf-8 -*-
"""
인왕제색도 런타임 자산 - 언리얼 머티리얼 자동 설정 (v3: 카드 나무 trees_cards 추가, Masked)
=========================================================
사용법 (언리얼 하단 콘솔, Cmd 모드):
    py "C:/KCW_SSAFY/특화/S15P21C201/김채원/2026-09-11/scripts/ue_setup_materials.py"

v2 변경
  - VertexColor 노드의 RGB 출력 이름은 "" (빈 문자열). "RGB"는 텍스처 노드용.   ← v1 False 원인
  - 레벨에 없는 파트는 스태틱 메시 에셋에서 찾아 (0,0,0)에 자동 배치           ← base 못 찾음 해결
  - 머티리얼은 지우지 않고 재사용(노드만 비움). 몇 번 돌려도 안전.

작성: 김채원(AI) / 2026-09-11 / 번들 v0.11
"""

import unreal

PKG   = "/Game/Museum/Inwang"      # 임포트한 폴더. 다르면 이 줄만 고치면 됨
ML    = unreal.MaterialEditingLibrary
EAL   = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()

MP_EMISSIVE = unreal.MaterialProperty.MP_EMISSIVE_COLOR
MP_OPACITY  = unreal.MaterialProperty.MP_OPACITY

PARTS = ["terrain_jeong", "terrain_real", "base", "house", "trees", "fog", "inscription", "trees_cards"]
OPTIONAL = {"trees_cards"}   # 없어도 실패로 안 침 (카드 나무는 선택)

report = []


def log(msg):
    unreal.log("[INWANG] %s" % msg)


def connect(expr, out_names, prop):
    """여러 출력 이름을 순서대로 시도. 성공한 이름을 돌려준다."""
    for n in out_names:
        try:
            if ML.connect_material_property(expr, n, prop):
                return n if n else '""'
        except Exception:
            pass
    return None


def get_or_make_material(name, translucent=False, masked=False):
    path = "%s/%s" % (PKG, name)
    if EAL.does_asset_exist(path):
        mat = EAL.load_asset(path)
        ML.delete_all_material_expressions(mat)
        how = "재사용"
    else:
        mat = TOOLS.create_asset(name, PKG, unreal.Material, unreal.MaterialFactoryNew())
        how = "생성"
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    bm = unreal.BlendMode.BLEND_MASKED if masked else (unreal.BlendMode.BLEND_TRANSLUCENT if translucent else unreal.BlendMode.BLEND_OPAQUE)
    mat.set_editor_property("blend_mode", bm)
    mat.set_editor_property("two_sided", bool(translucent or masked))
    return mat, path, how


def build_vertex_material(name, translucent):
    mat, path, how = get_or_make_material(name, translucent)
    vc = ML.create_material_expression(mat, unreal.MaterialExpressionVertexColor, -350, 0)
    ok_rgb = connect(vc, ["", "RGB"], MP_EMISSIVE)
    ok_a = "-"
    if translucent:
        ok_a = connect(vc, ["A"], MP_OPACITY)
    ML.recompile_material(mat)
    EAL.save_asset(path)
    report.append((name, how, "VertexColor", ok_rgb, ok_a))
    return mat


def find_asset(part, cls):
    """PKG 아래에서 part 이름의 cls 타입 에셋을 찾는다 (폴더 깊이 무관)."""
    for p in EAL.list_assets(PKG, recursive=True, include_folder=False):
        leaf = p.rsplit("/", 1)[-1].split(".")[0].lower()
        if part.lower() == leaf or ("%s_texture" % part.lower()) in leaf:
            obj = EAL.load_asset(p)
            if isinstance(obj, cls):
                return obj
    return None


def build_texture_material(name, part, translucent, masked=False):
    tex = find_asset(part, unreal.Texture2D)
    if tex is None:
        report.append((name, "건너뜀", "!! %s 텍스처 없음" % part, None, None))
        return None
    mat, path, how = get_or_make_material(name, translucent, masked)
    ts = ML.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -400, 0)
    ts.set_editor_property("texture", tex)
    ok_rgb = connect(ts, ["RGB", ""], MP_EMISSIVE)
    ok_a = "-"
    if masked:
        ok_a = connect(ts, ["A"], unreal.MaterialProperty.MP_OPACITY_MASK)
    elif translucent:
        ok_a = connect(ts, ["A"], MP_OPACITY)
    ML.recompile_material(mat)
    EAL.save_asset(path)
    report.append((name, how, tex.get_name(), ok_rgb, ok_a))
    return mat


# ── 1) 머티리얼 ──────────────────────────────────────────────────
log("=" * 70)
log("1) 머티리얼   (대상 폴더: %s)" % PKG)

m_vertex = build_vertex_material("M_InwangVertexUnlit", translucent=False)
m_fog    = build_vertex_material("M_InwangFogUnlit",    translucent=True)
m_jeong  = build_texture_material("M_InwangTerrainJeong", "terrain_jeong", translucent=False)
m_real   = build_texture_material("M_InwangTerrainReal",  "terrain_real",  translucent=False)
m_ink    = build_texture_material("M_InwangInk",          "inscription",   translucent=True)
m_cards  = build_texture_material("M_InwangTreeCards",    "trees_cards",   translucent=False, masked=True)   # 카드 나무 (선택)

log("-" * 70)
log("%-22s %-6s %-24s %-10s %s" % ("머티리얼", "처리", "입력", "RGB->이미시브", "A->오파시티"))
log("-" * 70)
mat_fail = 0
for name, how, src, rgb, a in report:
    rgb_s = "OK(%s)" % rgb if rgb else "!! 실패"
    if rgb is None and not src.startswith("!!"):
        mat_fail += 1
    log("%-22s %-6s %-24s %-10s %s" % (name, how, src, rgb_s, a))

# ── 2) 액터 배치 + 배정 ──────────────────────────────────────────
WANT = {
    "base":          m_vertex,
    "house":         m_vertex,
    "trees":         m_vertex,
    "fog":           m_fog,
    "terrain_jeong": m_jeong,
    "terrain_real":  m_real,
    "inscription":   m_ink,
    "trees_cards":   m_cards,
}

sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
existing = {}
for actor in sub.get_all_level_actors():
    existing.setdefault(actor.get_actor_label(), actor)

log("=" * 70)
log("2) 액터")
log("%-16s %-8s %-26s %s" % ("파트", "출처", "머티리얼", "판정"))
log("-" * 70)
ok_count = 0
for part in PARTS:
    mat = WANT.get(part)
    actor = existing.get(part)
    origin = "기존"
    if actor is None:
        sm = find_asset(part, unreal.StaticMesh)
        if sm is None:
            if part in OPTIONAL:
                log("%-16s %-8s %-26s %s" % (part, "-", "-", "(선택 파트, 임포트 안 됨 — 건너뜀)")); continue
            log("%-16s %-8s %-26s %s" % (part, "-", "-", "!! 스태틱 메시 에셋도 없음 (임포트 안 됨?)"))
            continue
        actor = sub.spawn_actor_from_object(sm, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
        actor.set_actor_label(part)
        origin = "자동배치"
    comp = actor.get_component_by_class(unreal.StaticMeshComponent)
    if comp is None or mat is None:
        log("%-16s %-8s %-26s %s" % (part, origin, "-", "!! 컴포넌트 또는 머티리얼 없음"))
        continue
    comp.set_material(0, mat)
    cur = comp.get_material(0)
    got = cur.get_name() if cur else "None"
    ok = (got == mat.get_name())
    ok_count += 1 if ok else 0
    log("%-16s %-8s %-26s %s" % (part, origin, got, "OK" if ok else "!! 다름"))

log("-" * 70)
need = len([p for p in PARTS if p not in OPTIONAL or find_asset(p, unreal.StaticMesh) is not None])
log("액터 %d / %d 적용,  머티리얼 연결 실패 %d" % (ok_count, need, mat_fail))
log("")
if ok_count == need and mat_fail == 0:
    log(">>> 성공. Ctrl+S 로 레벨 저장하고 뷰포트 확인.")
else:
    log(">>> !! 붙은 줄을 그대로 복사해서 알려주세요.")
log("=" * 70)
