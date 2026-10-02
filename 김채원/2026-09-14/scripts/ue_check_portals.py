# -*- coding: utf-8 -*-
"""
포털 점검 — 어느 레벨로 가게 돼 있나 (2026-09-14)
====================================================
증상: 액자로 들어가면 엉뚱한 레벨(로비)로 간다.
원인 후보는 하나뿐: BP_PortalInwang 의 **Open Level (by Name) 노드에 글자를 직접 타이핑**해 두면
   액터마다 넣어둔 LevelName 변수는 무시되고 모든 포털이 그 글자로 간다.
이 스크립트는 (1) 프로젝트의 실제 레벨 이름 (2) 이 레벨의 포털 액터들이 들고 있는 LevelName 을 찍는다.
   둘이 맞는데도 엉뚱한 데로 간다면 원인은 100 % 블루프린트 쪽 타이핑이다.

사용법 (아무 레벨에서나, 언리얼 콘솔):
    py "C:/KCW_SSAFY/특화/S15P21C201/김채원/2026-09-14/scripts/ue_check_portals.py"
확인 지표: '레벨 목록' 에 L_Inwang / L_Room_Inwang 이 정확히 그 철자로 있는지,
          '포털 … LevelName = …' 이 가려던 레벨과 같은지.
"""
import unreal

sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
EAL = unreal.EditorAssetLibrary
reg = unreal.AssetRegistryHelpers.get_asset_registry()


def log(m): unreal.log("[INWANG] %s" % m)


lvl = ""
try: lvl = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_name()
except Exception: pass
log("현재 레벨: %s" % lvl)

log("― 프로젝트의 레벨 목록 (Open Level 에 넣을 수 있는 이름) ―")
lv = sorted(str(a.package_name) for a in reg.get_assets_by_class(unreal.TopLevelAssetPath("/Script/Engine", "World"), True))
for p in lv: log("   %-28s  ← 이름만 쓰면 '%s'" % (p, p.rsplit("/", 1)[-1]))
if not lv: log("   !! 레벨을 못 찾음")

log("― 이 레벨의 포털 액터 ―")
n = 0
for a in sub.get_all_level_actors():
    lab = a.get_actor_label()
    if "Portal" not in lab: continue
    n += 1
    try: v = a.get_editor_property("LevelName")
    except Exception as ex: v = "읽기실패(%s)" % ex
    p = a.get_actor_location()
    log("   %-20s LevelName = %-20s  위치 (%.0f, %.0f, %.0f)  클래스 %s" % (lab, v, p.x, p.y, p.z, a.get_class().get_name()))
if n == 0: log("   (이 레벨엔 Portal 액터가 없음)")
log("―― 위 LevelName 이 맞는데도 엉뚱한 레벨로 간다면 → BP_PortalInwang 의 Open Level 노드에 타이핑된 글자가 원인 ――")
