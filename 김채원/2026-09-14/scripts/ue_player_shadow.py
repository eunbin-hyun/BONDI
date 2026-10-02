# -*- coding: utf-8 -*-
"""
사용자 발밑 먹 그림자 — 머티리얼 만들기 + 미리보기 배치 (2026-09-14)
=====================================================================
VR 폰은 보통 몸 메시가 없어서 그림자를 던질 게 없다. 그래서 '발밑 먹 얼룩' 을 따로 둔다.
BP_XRPawn(김신정 담당) 은 건드리지 않고, 카메라를 매 틱 따라다니는 **우리 전용 액터**를 쓴다.

이 스크립트가 하는 일 (파이썬으로 가능한 부분 전부):
  1) M_InwangShadowBlob 생성 — Unlit·반투명·양면. 가운데가 진하고 가장자리로 사라지는 원형 먹 얼룩.
     (반투명 평면이라 Quest 2 모바일 렌더러에서도 확실히 나온다. 디퍼드 데칼은 모바일에서 안 나올 수 있어 피함)
  2) 엔진 Plane 메시로 미리보기 액터 ShadowBlob_Preview 배치 — 크기·진하기를 눈으로 맞추는 용도
  3) BP_ShadowBlob 이 이미 있으면 그 배치까지 (없으면 아래 순서표대로 5분)

블루프린트 순서표 — BP_ShadowBlob (한 번만)
  1. 콘텐츠 브라우저 /Game/Museum/Inwang 우클릭 → 블루프린트 클래스 → 부모 Actor → 이름 BP_ShadowBlob
  2. 컴포넌트 + 추가 → Static Mesh.  디테일:
       Static Mesh = Plane (엔진 기본),  Material = M_InwangShadowBlob
       Scale = (BLOB_M, BLOB_M, 1) — 아래 로그에 나오는 값
       Collision Presets = NoCollision   ← 안 끄면 자기 자신을 바닥으로 감지한다
       Cast Shadow 체크 해제
  3. 이벤트 그래프:
       Event Tick
       → Get Player Camera Manager (Player Index 0) → Get Camera Location
       → Break Vector 로 X, Y 를 빼고, Z 는 그대로 씀
       → Line Trace By Channel
            Start  = Make Vector (X, Y, Z)                 ← 카메라 위치 그대로
            End    = Make Vector (X, Y, Z - TRACE_DOWN_CM) ← 아래로 이만큼
            Trace Channel = Visibility,  Draw Debug Type = None
       → Branch (Return Value)
            True → Break Hit Result 의 Location 에 Z 만 + LIFT_CM 더해서 → Set Actor Location
  4. 컴파일 → 저장.  레벨에 하나 끌어다 놓으면 끝 (이 스크립트를 다시 돌려도 자동 배치됨)
  확인: 플레이 중 걸어다니면 얼룩이 발밑을 따라옴. 안 따라오면 Line Trace 가 바닥을 못 맞힌 것 —
        2번의 Collision Presets 가 NoCollision 인지, 지형에 콜리전이 있는지 확인.

사용법 (L_Inwang 열린 상태, 언리얼 콘솔):
    py "C:/KCW_SSAFY/특화/S15P21C201/김채원/2026-09-12/scripts/ue_player_shadow.py"
확인 지표: 'M_InwangShadowBlob 연결 N/N Emissive True Opacity True', '>>> 미리보기 배치 …'
조절: BLOB_M(지름 m) · BLOB_OPACITY(진하기) · BLOB_EDGE(가장자리 부드럽기) · INK(먹색)
"""
import unreal

BLOB_M = 1.6              # 얼룩 지름 (m). 엔진 Plane 이 1 m 라 스케일 값이 그대로 지름
BLOB_OPACITY = 0.38       # 한가운데 진하기
BLOB_EDGE = 2.2           # 클수록 가운데만 진하고 가장자리가 빨리 사라짐
INK = (0.10, 0.09, 0.09)  # 먹색 (진묵)
TRACE_DOWN_CM = 400.0     # 블루프린트에서 쓸 값 — 카메라 아래로 이만큼 훑어 바닥을 찾음
LIFT_CM = 3.0             # 바닥에서 살짝 띄움 (Z-파이팅 방지)
PKG = "/Game/Museum/Inwang"
MAT = "M_InwangShadowBlob"

EAL = unreal.EditorAssetLibrary; ML = unreal.MaterialEditingLibrary; TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem); LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
reg = unreal.AssetRegistryHelpers.get_asset_registry()


def log(m): unreal.log("[INWANG] %s" % m)


# ── 1) 먹 얼룩 머티리얼 ────────────────────────────────────────
path = "%s/%s" % (PKG, MAT)
if EAL.does_asset_exist(path): mat = EAL.load_asset(path); ML.delete_all_material_expressions(mat)
else: mat = TOOLS.create_asset(MAT, PKG, unreal.Material, unreal.MaterialFactoryNew())
mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
mat.set_editor_property("two_sided", True)
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


# 불투명도 = (1 - 중심에서의 거리/0.5)^EDGE × OPACITY   → 가운데 진하고 가장자리 0
tc = mk(unreal.MaterialExpressionTextureCoordinate, -1100, 100)
half = mk(unreal.MaterialExpressionConstant2Vector, -1100, 240, constant=unreal.LinearColor(0.5, 0.5, 0, 0))
sb = mk(unreal.MaterialExpressionSubtract, -940, 150)
ln = mk(unreal.MaterialExpressionDistance, -800, 150)          # |UV - 0.5|
zero = mk(unreal.MaterialExpressionConstant2Vector, -940, 300, constant=unreal.LinearColor(0, 0, 0, 0))
inv = mk(unreal.MaterialExpressionConstant, -800, 300, r=2.0)  # /0.5 = ×2
mm = mk(unreal.MaterialExpressionMultiply, -650, 190)
sat = mk(unreal.MaterialExpressionSaturate, -520, 190)
om = mk(unreal.MaterialExpressionOneMinus, -400, 190)
ed = mk(unreal.MaterialExpressionConstant, -400, 320, r=BLOB_EDGE)
pw = mk(unreal.MaterialExpressionPower, -270, 220)
op = mk(unreal.MaterialExpressionConstant, -270, 350, r=BLOB_OPACITY)
mo = mk(unreal.MaterialExpressionMultiply, -140, 260)
col = mk(unreal.MaterialExpressionConstant3Vector, -270, -60, constant=unreal.LinearColor(INK[0], INK[1], INK[2], 1.0))

L(tc, sb, "A"); L(half, sb, "B")
L(sb, ln, "A"); L(zero, ln, "B")
L(ln, mm, "A"); L(inv, mm, "B"); L(mm, sat, ["", "Input"]); L(sat, om, ["", "Input"])
L(om, pw, ["Base", "A"]); L(ed, pw, ["Exp", "B"])
L(pw, mo, "A"); L(op, mo, "B")
ok_e = ML.connect_material_property(col, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
ok_o = ML.connect_material_property(mo, "", unreal.MaterialProperty.MP_OPACITY)
ML.recompile_material(mat); EAL.save_asset(path)
log("%s 연결 %d/%d  Emissive %s  Opacity %s   (지름 %.1f m · 진하기 %.2f · 가장자리 %.1f)"
    % (MAT, sum(oks), len(oks), ok_e, ok_o, BLOB_M, BLOB_OPACITY, BLOB_EDGE))

# ── 2) 미리보기 배치 (PlayerStart 발밑) ─────────────────────────
A = {x.get_actor_label(): x for x in sub.get_all_level_actors()}
for lab in ("ShadowBlob_Preview", "PlayerShadow_Inwang"):
    if lab in A: sub.destroy_actor(A[lab]); log("  기존 %s 제거" % lab)
ps = next((x for x in sub.get_all_level_actors() if isinstance(x, unreal.PlayerStart)), None)
plane = EAL.load_asset("/Engine/BasicShapes/Plane")
if ps is None or plane is None:
    log("!! PlayerStart 또는 엔진 Plane 메시 없음 — 미리보기 배치 건너뜀")
else:
    p = ps.get_actor_location()
    a = sub.spawn_actor_from_object(plane, unreal.Vector(p.x, p.y, p.z - 90.0 + LIFT_CM), unreal.Rotator(0, 0, 0))
    a.set_actor_scale3d(unreal.Vector(BLOB_M, BLOB_M, 1.0))
    a.set_actor_label("ShadowBlob_Preview"); a.set_folder_path("Lighting")
    c = a.get_component_by_class(unreal.StaticMeshComponent)
    for i in range(c.get_num_materials()): c.set_material(i, mat)
    try:
        c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        c.set_editor_property("cast_shadow", False)
    except Exception as ex: log("   (참고) 미리보기 콜리전/그림자 설정 실패: %s" % ex)
    log(">>> 미리보기 배치 ShadowBlob_Preview (%.0f, %.0f, %.0f)  크기 %.1f m — 진하기·크기를 여기서 눈으로 맞출 것"
        % (p.x, p.y, p.z - 90.0 + LIFT_CM, BLOB_M))

# ── 3) BP_ShadowBlob 이 있으면 레벨에 배치 ─────────────────────
hits = [str(x.package_name) for x in reg.get_assets_by_class(unreal.TopLevelAssetPath("/Script/Engine", "Blueprint"), True)
        if str(x.asset_name) == "BP_ShadowBlob"]
if not hits:
    log("BP_ShadowBlob 없음 — 파일 맨 위 '블루프린트 순서표' 대로 만들면 다음 실행 때 자동 배치됨")
    log("   순서표에 쓸 값: Scale %.1f / Line Trace 아래로 %.0f cm / 바닥에서 %.0f cm 띄움" % (BLOB_M, TRACE_DOWN_CM, LIFT_CM))
else:
    cls = EAL.load_blueprint_class(hits[0])
    loc = ps.get_actor_location() if ps else unreal.Vector(0, 0, 0)
    b = sub.spawn_actor_from_class(cls, loc, unreal.Rotator(0, 0, 0))
    b.set_actor_label("PlayerShadow_Inwang"); b.set_folder_path("Lighting")
    log(">>> BP_ShadowBlob 배치 완료 (%s)" % hits[0])
log("레벨 저장 %s" % LES.save_current_level())
