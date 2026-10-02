# -*- coding: utf-8 -*-
"""
인왕제색도 런타임 자산 - 언리얼 머티리얼 자동 설정 (v7.7: 소유권 분리 — 전용 스크립트가 맡은 파트는 안 건드림 · v7.5: inscription 숨김 취소 · v7.3: 화제 안내판 inscription_board · v7.2: 메시가 참조하는 텍스처 우선 · 찾기 완화 + house_ink 양면(two_sided) — 면 방향 안전판. v6: 운무 v3 5겹 fog_l0~4, 수묵 지붕 house_ink)
=========================================================
사용법 (언리얼 하단 콘솔, Cmd 모드):
    py "C:/KCW_SSAFY/특화/S15P21C201/김채원/2026-09-12/scripts/ue_setup_materials.py"

v7.3 변경 (2026-09-13)
  - inscription_board (선택): 큰 채 앞 관람 안내판 → M_InwangBoard (텍스처 Unlit). inscription(원화의 화제·인장 공중 판)과는 별개 자산이므로 둘 다 유지. (v7.5)
v7.2 변경 (2026-09-13)
  - 텍스처는 먼저 '임포트된 스태틱 메시의 머티리얼 인스턴스가 실제로 참조하는 것'을 쓰고, 못 읽을 때만 이름 검색. 폴더에 예전 임포트 텍스처가 남아 있어 옛 것을 집던 문제 대응(추측 — '텍스처 연결:' 로그의 [출처] 로 확인).
  - 텍스처 에셋 찾기 완화: 'house_ink' 뿐 아니라 'house_ink_…' 로 시작하는 Texture2D 도 인정 (임포터가 붙이는 이름 대응). 어떤 에셋을 썼는지 '텍스처 연결:' 줄로 로그.
  - M_InwangHouseInk 를 two_sided=True 로. house_ink.glb 도 면 방향(winding)을 바깥으로 통일해 다시 내보냈으므로 둘 중 하나만으로도 '깨짐'은 사라짐.
    로그 확인: '1) 머티리얼' 표에서 M_InwangHouseInk 줄, 그리고 마지막에 'M_InwangHouseInk two_sided True'.
v5 변경 (2026-09-13)
  - fog_l0~fog_l4 (선택): 운무 v3 5겹. 겹마다 텍스처 머티리얼 M_InwangFogL0~4. 있으면 예전 'fog' 액터는 숨김. 폴더 Inwang/Fog
  - house_ink (선택): 집 전체 먹 wash 아틀라스(지붕·벽·기둥·기단·획). 슬롯 1개 = M_InwangHouseInk. 처음엔 숨김 → ue_toggle_house.py 로 전환
    (v5 의 house_giwa 는 09-13 결정으로 폐기 — 에셋이 남아 있어도 이 스크립트는 건드리지 않음)
v4 변경 (2026-09-12)
  - fog: v2 는 텍스처(RGBA) 메시 → M_InwangFogSoft (텍스처 RGB→Emissive, A→Opacity, Translucent).
         fog 텍스처가 없으면(v1 메시) 예전 M_InwangFogUnlit(정점색) 로 자동 대체
  - terrain_ink_ext (선택): 원화 없는 산면 먹 덧칠 층 → M_InwangInkExt (Translucent). 아웃라이너 눈 아이콘으로 토글

v2 변경
  - VertexColor 노드의 RGB 출력 이름은 "" (빈 문자열). "RGB"는 텍스처 노드용.   ← v1 False 원인
  - 레벨에 없는 파트는 스태틱 메시 에셋에서 찾아 (0,0,0)에 자동 배치           ← base 못 찾음 해결
  - 머티리얼은 지우지 않고 재사용(노드만 비움). 몇 번 돌려도 안전.

작성: 김채원(AI) / 2026-09-11, v6·v7 2026-09-13 / 번들 v0.12
"""

import unreal

PKG   = "/Game/Museum/Inwang"      # 임포트한 폴더. 다르면 이 줄만 고치면 됨
ML    = unreal.MaterialEditingLibrary
EAL   = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()

MP_EMISSIVE = unreal.MaterialProperty.MP_EMISSIVE_COLOR
MP_OPACITY  = unreal.MaterialProperty.MP_OPACITY

FOG_LAYERS = ["fog_l%d" % i for i in range(5)]
PARTS = ["terrain_jeong", "terrain_real", "base", "house", "trees", "fog", "inscription", "trees_cards", "terrain_ink_ext", "house_ink", "inscription_board"] + FOG_LAYERS
OPTIONAL = {"trees_cards", "terrain_ink_ext", "house_ink", "inscription_board"} | set(FOG_LAYERS)   # 없어도 실패로 안 침 (선택 파트)

# ── v7.7 (2026-09-14): 소유권 분리 ──────────────────────────────
#   이 스크립트가 모든 파트의 머티리얼을 다시 만들어 덮어쓰는 바람에, 나중에 만든 설정이 매번 날아갔다.
#   (지형 여백·AO·조명 / 지붕 밑면 어둡게 / 화제 금빛 / 나무·안개 움직임)
#   아래 파트는 각자 전용 스크립트가 주인이다. SKIP_OWNED=True 면 이 스크립트는 손대지 않는다.
SKIP_OWNED = True
OWNED = {
    "terrain_jeong":     "ue_terrain_material.py",
    "house_ink":         "ue_house_material.py",
    "inscription":       "ue_toggle_shine.py",
    "trees_cards":       "ue_setup_motion.py",
    "fog_l0": "ue_setup_motion.py", "fog_l1": "ue_setup_motion.py", "fog_l2": "ue_setup_motion.py",
    "fog_l3": "ue_setup_motion.py", "fog_l4": "ue_setup_motion.py",
}

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


def get_or_make_material(name, translucent=False, masked=False, two_sided=None):
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
    mat.set_editor_property("two_sided", bool(translucent or masked) if two_sided is None else bool(two_sided))
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
    """PKG 아래에서 part 이름의 cls 타입 에셋을 찾는다 (폴더 깊이 무관).
    v7.1: 이름이 정확히 같거나(house_ink), 'part_…' 로 시작하는 것도 허용(house_ink_material_0_basecolor 같은 임포터 작명).
          단 더 긴 다른 파트 이름으로 시작하면 제외 (fog 가 fog_l0_… 텍스처를 집지 않게)."""
    part_l = part.lower(); longer = [q.lower() for q in PARTS if len(q) > len(part) and q.lower().startswith(part_l)]
    exact, loose = None, None
    for p in EAL.list_assets(PKG, recursive=True, include_folder=False):
        leaf = p.rsplit("/", 1)[-1].split(".")[0].lower()
        if any(leaf == q or leaf.startswith(q + "_") for q in longer):
            continue
        if leaf == part_l or ("%s_texture" % part_l) in leaf:
            obj = EAL.load_asset(p)
            if isinstance(obj, cls): exact = obj; break
        elif loose is None and leaf.startswith(part_l + "_"):
            obj = EAL.load_asset(p)
            if isinstance(obj, cls): loose = obj
    return exact if exact is not None else loose


def texture_from_mesh(part):
    """임포트된 스태틱 메시가 실제로 참조하는 베이스컬러 텍스처 (임포터 머티리얼 인스턴스의 텍스처 파라미터). 못 찾으면 None.
    v7.2: 같은 폴더에 예전 임포트 텍스처가 남아 있어도 메시가 쓰는 최신 것을 고르기 위함."""
    sm = find_asset(part, unreal.StaticMesh)
    if sm is None:
        return None, "메시 없음"
    try:
        mats = list(sm.get_editor_property("static_materials"))
    except Exception as e:
        return None, "static_materials 읽기 실패 %s" % e
    for sm_mat in mats:
        mi = sm_mat.material_interface
        if mi is None:
            continue
        chain = [mi]
        try:
            par = mi.get_editor_property("parent")
            while par is not None and len(chain) < 5:
                chain.append(par); par = par.get_editor_property("parent") if hasattr(par, "get_editor_property") else None
        except Exception:
            pass
        for m_ in chain:
            try:
                for tp in m_.get_editor_property("texture_parameter_values"):
                    t = tp.parameter_value
                    if isinstance(t, unreal.Texture2D):
                        return t, "메시 머티리얼 %s 의 파라미터 %s" % (mi.get_name(), tp.parameter_info.name)
            except Exception:
                continue
    return None, "메시 머티리얼에서 텍스처 파라미터 못 읽음 (%s)" % ", ".join(str(x.material_interface.get_name()) if x.material_interface else "None" for x in mats)


def build_texture_material(name, part, translucent, masked=False, two_sided=None):
    tex, src = texture_from_mesh(part)
    if tex is None:
        tex = find_asset(part, unreal.Texture2D); src = "이름 검색 (%s)" % src
    if tex is None:
        report.append((name, "건너뜀", "!! %s 텍스처 없음" % part, None, None))
        return None
    mat, path, how = get_or_make_material(name, translucent, masked, two_sided)
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
    log("텍스처 연결: %-22s ← %s   [%s]" % (name, tex.get_path_name(), src))
    return mat


# ── 1) 머티리얼 ──────────────────────────────────────────────────
log("=" * 70)
log("1) 머티리얼   (대상 폴더: %s)" % PKG)

m_vertex = build_vertex_material("M_InwangVertexUnlit", translucent=False)
try:
    m_vertex.set_editor_property("two_sided", True); ML.recompile_material(m_vertex); EAL.save_asset(PKG + "/M_InwangVertexUnlit")
    log("M_InwangVertexUnlit two_sided True  (v7.4: house/trees 면 방향 대비)")
except Exception as _e: log("!! M_InwangVertexUnlit 양면 설정 실패: %s" % _e)
m_fog    = build_texture_material("M_InwangFogSoft",      "fog",           translucent=True)                # 운무 v2 (텍스처)
if m_fog is None:
    m_fog = build_vertex_material("M_InwangFogUnlit", translucent=True)                                        # 운무 v1 (정점색) 대체
m_inkext = build_texture_material("M_InwangInkExt",       "terrain_ink_ext", translucent=True)                # 먹산 덧칠 (선택)
m_hink   = build_texture_material("M_InwangHouseInk",     "house_ink",     translucent=False, two_sided=True)   # 수묵 집 (선택) — v7: 양면
m_board  = build_texture_material("M_InwangBoard",        "inscription_board", translucent=False)           # 화제 안내판 (선택) — v7.3
m_fogl   = {p: build_texture_material("M_InwangFogL%d" % i, p, translucent=True) for i, p in enumerate(FOG_LAYERS)}   # 운무 v3 (선택)
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
    "terrain_ink_ext": m_inkext,
    "house_ink":     m_hink,
    "inscription_board": m_board,
}
WANT.update(m_fogl)

sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
existing = {}
for actor in sub.get_all_level_actors():
    existing.setdefault(actor.get_actor_label(), actor)

log("=" * 70)
log("2) 액터")
log("%-16s %-8s %-26s %s" % ("파트", "출처", "머티리얼", "판정"))
log("-" * 70)
ok_count = 0
n_skip = 0
for part in PARTS:
    if SKIP_OWNED and part in OWNED:
        a_ = existing.get(part)
        cur_ = a_.get_component_by_class(unreal.StaticMeshComponent).get_material(0) if a_ else None
        log("%-16s %-8s %-26s %s" % (part, "보호", cur_.get_name() if cur_ else "-", "→ %s 가 담당 (건드리지 않음)" % OWNED[part]))
        n_skip += 1; continue
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
    if part == "house_ink":                                    # v2 는 아틀라스 1장 = 슬롯 1개. (슬롯이 2개면 옛 판 → 슬롯 1 정점색)
        if comp.get_num_materials() > 1:
            comp.set_material(1, m_vertex)
        log("%-16s %-8s %-26s %s" % ("", "", "슬롯 수 %d (v2 아틀라스면 1)" % comp.get_num_materials(), ""))
        # v7.6: 예전엔 여기서 house_ink 를 숨겼음(ue_toggle_house.py 로 전환하던 시절). 지금은 house_ink 가 본편이라 숨기지 않는다.
        actor.set_folder_path("Inwang/House")
        actor.set_is_temporarily_hidden_in_editor(False); actor.set_actor_hidden_in_game(False)
        try: actor.set_editor_property("hidden", False)
        except Exception: pass
    if part in FOG_LAYERS:
        actor.set_folder_path("Inwang/Fog")
    cur = comp.get_material(0)
    got = cur.get_name() if cur else "None"
    ok = (got == mat.get_name())
    ok_count += 1 if ok else 0
    log("%-16s %-8s %-26s %s" % (part, origin, got, "OK" if ok else "!! 다름"))

# 운무 v3 겹이 하나라도 있으면 예전 단일 fog 는 숨김
if any(existing.get(p) or find_asset(p, unreal.StaticMesh) for p in FOG_LAYERS):
    old_fog = {a.get_actor_label(): a for a in sub.get_all_level_actors()}.get("fog")
    if old_fog is not None:
        old_fog.set_is_temporarily_hidden_in_editor(True); old_fog.set_actor_hidden_in_game(True)
        log("%-16s %-8s %-26s %s" % ("fog", "기존", "-", "숨김 (fog_l* 사용)"))
# v7.5: inscription(원화의 화제·인장 픽셀을 분리한 공중 판)과 inscription_board(관람 안내판)는 별개 자산.
#       v7.3 에서 안내판이 있으면 inscription 을 숨겼던 건 잘못된 판단 → 숨기지 않고 둘 다 유지.
log("-" * 70)
need = len([p for p in PARTS if p not in OPTIONAL or find_asset(p, unreal.StaticMesh) is not None])
log("액터 %d / %d 적용,  보호(건드리지 않음) %d,  머티리얼 연결 실패 %d" % (ok_count, need, n_skip, mat_fail))
if SKIP_OWNED: log("   보호된 파트는 전용 스크립트로 — 한 번에 되돌리려면 ue_restore_state.py")
if m_hink is not None:
    log("M_InwangHouseInk two_sided %s  (v7: True 여야 함)" % m_hink.get_editor_property("two_sided"))
log("")
if ok_count == need and mat_fail == 0:
    log(">>> 성공. Ctrl+S 로 레벨 저장하고 뷰포트 확인.")
else:
    log(">>> !! 붙은 줄을 그대로 복사해서 알려주세요.")
log("=" * 70)
