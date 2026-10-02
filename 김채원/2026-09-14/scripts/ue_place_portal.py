# -*- coding: utf-8 -*-
"""
액자 → 인왕제색도 3D 공간 진입 포털 v3  (2026-09-13)
=====================================================
알게 된 것 (Portal_To_Hall 의 T3D): 팀 BP_Portal 은 변수 TargetLoc / TargetRot 로 **같은 레벨 안에서 순간이동**하는 액터.
  플레인 메시는 NoCollision, 겉모습은 M_Portal 머티리얼(PortalColor). 다른 레벨(L_Inwang)로 넘어가는 기능은 없음.
→ 우리 전용 BP_PortalInwang (박스 트리거 → 페이드 → Open Level) 을 쓴다. 만드는 법은 아래 '블루프린트 순서표'. 팀 에셋은 안 건드림.
이 스크립트: L_Room_Inwang 의 그림 앞에 BP_PortalInwang 을 놓고, 박스 크기를 그림 크기에 맞추고, LevelName 변수에 L_Inwang 을 넣음.
             예전에 놓았던 BP_Portal(Portal_To_Inwang) 은 지움.
사용법 (언리얼 하단 콘솔, Cmd 모드, L_Room_Inwang 이 열린 상태, BP_PortalInwang 을 만든 뒤):
    py "C:/KCW_SSAFY/특화/S15P21C201/김채원/2026-09-12/scripts/ue_place_portal.py"
확인 지표: 로그 'BP_PortalInwang 로드 OK', '박스 크기 …', 'LevelName = L_Inwang', '>>> 포털 배치 …', 레벨 저장 True.
          플레이 → 액자로 걸어 들어가면 화면이 어두워졌다가 L_Inwang 정선 시점에서 시작.

블루프린트 순서표 (BP_PortalInwang, 한 번만 만들면 됨 — 5분)
  1. 콘텐츠 브라우저 /Game/Museum/Inwang 에서 우클릭 → 블루프린트 클래스 → 부모 Actor → 이름 BP_PortalInwang
  2. 컴포넌트 패널: + 추가 → Box Collision. 디테일: 콜리전 프리셋 OverlapAllDynamic, 'Generate Overlap Events' 체크. (크기는 스크립트가 맞춤)
  3. 내 블루프린트 → 변수 + : 이름 LevelName, 타입 Name, '인스턴스 편집 가능' 체크, 기본값 L_Inwang   (컴파일 후 기본값 입력 가능)
  4. 이벤트 그래프 — Box 컴포넌트 선택 → 디테일 아래 '이벤트' → On Component Begin Overlap 클릭해서 노드 생성. 그 뒤로 순서대로 연결:
       On Component Begin Overlap (Other Actor)
       → [Other Actor] Cast To Pawn  (실패 핀은 비움: 손·물체가 스쳐도 무시)
       → Do Once
       → Get Player Camera Manager → Start Camera Fade (From 0, To 1, Duration 0.5, Hold When Finished 체크)
       → Delay 0.5
       → Open Level (by Name)  Level Name ← 변수 LevelName (Get)
     컴파일 → 오류 0, 저장.
  확인: 컴파일 버튼이 초록 체크. (Pawn 캐스트 대신 'Other Actor == Get Player Pawn' 도 됨)
돌아오는 길: 같은 BP 를 L_Inwang 에 놓고 LevelName 만 L_Room_Inwang(또는 L_Museum) 으로 — 나중에.
"""
import unreal

OUR_BP = "/Game/Museum/Inwang/BP_PortalInwang"
DEST_LEVEL_NAME = "L_Inwang"
PAINT_LABEL = "Painting_Inwang"
STANDOFF_CM = 10.0                  # 그림 앞면에서 방 쪽으로 이만큼 앞에 박스 중심 (박스 두께 = 2×DEPTH_HALF)
DEPTH_HALF = 15.0                   # 박스 반두께 cm (앞뒤 판정 폭 60 cm)
MARGIN = 1.05                       # 그림보다 5 % 크게
FOLDER = "InwangRoom/Exhibit"

sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem); EAL = unreal.EditorAssetLibrary; LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
fails = []


def log(m): unreal.log("[INWANG] %s" % m)


def bad(m): fails.append(m); log("!! " + m)


actors = {a.get_actor_label(): a for a in sub.get_all_level_actors()}
paint = actors.get(PAINT_LABEL)
if paint is None: bad("%s 액터 없음 — 현재 레벨이 L_Room_Inwang 인지 확인" % PAINT_LABEL)
cls = None
bp_path = OUR_BP if EAL.does_asset_exist(OUR_BP) else None
if bp_path is None:                                                          # v3.1: 어느 폴더에 있든 이름으로 찾기
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    hits = [str(a.package_name) for a in reg.get_assets_by_class(unreal.TopLevelAssetPath("/Script/Engine", "Blueprint"), True) if str(a.asset_name) == "BP_PortalInwang"]
    if hits: bp_path = hits[0]; log("BP_PortalInwang 을 다른 폴더에서 찾음: %s" % bp_path)
if bp_path:
    try: cls = EAL.load_blueprint_class(bp_path); log("BP_PortalInwang 로드 OK (%s)" % bp_path)
    except Exception as ex: bad("BP_PortalInwang 로드 실패: %s" % ex)
else:
    bad("BP_PortalInwang 이 프로젝트 어디에도 없음 — 이름이 정확히 BP_PortalInwang 인지, 저장했는지 확인")

# 예전 BP_Portal 배치 제거 (같은 레벨 안 순간이동용이라 우리 용도엔 안 맞음)
for a in list(actors.values()):
    if a.get_actor_label().startswith("Portal_To_Inwang"): sub.destroy_actor(a); log("기존 Portal_To_Inwang 제거")

if not fails:
    o, e = paint.get_actor_bounds(False)
    loc = unreal.Vector(o.x - e.x - STANDOFF_CM, o.y, o.z)
    portal = sub.spawn_actor_from_class(cls, loc, unreal.Rotator(0, 0, 0))
    portal.set_actor_label("Portal_To_Inwang"); portal.set_folder_path(FOLDER)
    box = portal.get_component_by_class(unreal.BoxComponent)
    if box is None: bad("BP_PortalInwang 에 Box Collision 컴포넌트가 없음 — 순서표 2번")
    else:
        box.set_box_extent(unreal.Vector(DEPTH_HALF, e.y * MARGIN, e.z * MARGIN), True)
        try: box.set_collision_profile_name("OverlapAllDynamic"); box.set_generate_overlap_events(True)
        except Exception as ex: log("   (참고) 콜리전 설정 실패 — BP 안에서 확인: %s" % ex)
        be = box.get_scaled_box_extent(); log("박스 크기 %.0f×%.0f×%.0f cm (그림 %.0f×%.0f)" % (be.x * 2, be.y * 2, be.z * 2, e.y * 2, e.z * 2))
    try:
        portal.set_editor_property("LevelName", unreal.Name(DEST_LEVEL_NAME)); log("LevelName = %s" % portal.get_editor_property("LevelName"))
    except Exception as ex: bad("변수 LevelName 설정 실패 (순서표 3번: Name 타입, 인스턴스 편집 가능): %s" % ex)
    log(">>> 포털 배치 (%.0f, %.0f, %.0f) — 그림 앞 %.0f cm, 판정 두께 %.0f cm" % (loc.x, loc.y, loc.z, STANDOFF_CM, DEPTH_HALF * 2))
    saved = LES.save_current_level(); log("레벨 저장 %s" % saved)
if fails: log(">>> !! %s" % " | ".join(fails))
