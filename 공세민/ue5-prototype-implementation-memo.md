# [기록] 2026-09-01 UE5 실험 프로젝트 구현 메모

> ⚠️ **이 문서가 설명하는 프로젝트는 이미 삭제됐다.**
>
> UE5·Unreal MCP 학습을 위한 폐기용 실험 프로젝트의
> 구현 기록이다. 저장소에 올리지 않았고 프로젝트 파일도 정리했다.
> **실제 VR 프로젝트는 별도로 새로 만든다. 이 문서를 그 폴더의 설명서로 읽지 않는다.**
>
> 같은 폴더의 아래 두 문서가 정리본이다. 먼저 그쪽을 본다.
>
> | 문서 | 용도 |
> | --- | --- |
> | `ue5-project-setup.md` | 새 프로젝트 시작 전 확인 사항 |
> | `2026-09-01.md` | 학습 정리 |
>
> 이 파일은 **더 자세한 값이 필요할 때만** 본다 — 좌대 치수, 노드 타입 ID,
> 프로퍼티 이름, PIE 검증 결과 등.

---

| 항목 | 값 |
| --- | --- |
| 프로젝트 | `vr/UE5/TestProject` (삭제됨) |
| 엔진 | UE 5.8 (부록 A 기준 엔진) |
| 템플릿 | VR Template |
| XR 플러그인 | OpenXR, OpenXRHandTracking, OpenXREyeTracker, PICOController |
| 상태 | **폐기.** 실기 검증 안 됨 |

> 이 문서는 구현 메모다. 제품 결정은 `docs/DECISIONS.md`,
> 요구사항은 `docs/PROJECT_MASTER_SPEC.md`가 권위다.

## 1. 만들어진 것 — N-07, N-08 프로토타입

FE 직군 담당분(정보 패널, 복원 3단계 토글)의 뼈대다. 전부 Unreal MCP로 생성했다.

### `/Game/Heritage/UI/WBP_ArtifactPanel`

3D 공간에 띄우는 유물 정보 패널. VR에서는 스크린 스페이스 UI를 못 쓰므로
`WidgetComponent`로 월드에 배치한다.

루트는 `Root_Size` (SizeBox, **600×760 고정**) 다. `WidgetComponent` 의 `drawSize` 와
같은 값이라 디자이너에서 보이는 크기가 헤드셋에서 보이는 크기와 일치한다.
고정하지 않으면 디자이너 캔버스(기본 Fill Screen) 전체로 퍼져 정렬이 깨져 보인다.

| 위젯 | 내용 | 요구사항 |
| --- | --- | --- |
| `Txt_Name` | 유물 명칭 | FR-UI-004 |
| `Txt_Stage` | 현재 복원 단계 (①②③) | FR-UI-003 |
| `Txt_Desc` | 설명 | FR-UI-004 |
| `Txt_Source` | 출처 | FR-UI-004 |
| `Txt_Method` | 단계별 생성 방식 | FR-UI-004 |
| `Txt_Limit` | 한계 | FR-UI-004 |
| `Txt_Disclaimer` | "AI 기반 복원 가설" 고지 | FR-UI-005 |
| `Btn_Prev` / `Btn_Next` | 단계 전환 버튼 | FR-UI-003 |

- 문구는 전부 한국어다 (FR-UI-007).
- 본문 20~38pt, 흰색/앰버 대비 배경 위 — 미러링 가독성(FR-UI-006) 초안이다.
  **실기 측정 전이므로 확정값이 아니다.**
- 함수 `UpdatePanel(InName, InStage, InDesc, InSource, InMethod, InLimit)` — 여섯 칸을 한 번에 채운다.

### `/Game/Heritage/Blueprints/BP_ArtifactPedestal`

유물 전시대.

| 컴포넌트 | 역할 |
| --- | --- |
| `PedestalMesh` | 받침대 (임시 원기둥) |
| `ArtifactMesh` | 유물 — 단계별로 스왑된다 (임시 큐브) |
| `InfoPanel` | `WidgetComponent`, World space, 600×760 |
| `ProximityTrigger` | 반경 200cm 구체 (FR-UI-001) |

| 변수 | 용도 |
| --- | --- |
| `CurrentStage` | 0=손상, 1=모델 복원, 2=MCP 복원 |
| `StageMeshes` | 단계별 유물 메시 3개. **AI 직군이 채운다** |
| `StageLabels` / `StageMethods` / `StageLimits` | 단계별 표시 문구 3쌍 |
| `ArtifactName` / `Description` / `Source` | 유물 공통 정보 |

`ApplyStage()` 함수가 `CurrentStage`에 맞는 메시로 교체한다.

작업 레벨 `/Game/Heritage/Maps/L_Museum` 의 `Heritage` 폴더에 3개 배치돼 있다 (N-05 유물 3점).

### 전시 공간 `/Game/Heritage/Maps/L_Museum`

VR Template 레벨 `L_XRTemplate` 을 복제한 뒤 **템플릿 데모 소품 27개를 제거**했다.
권총, 집기용 큐브, 공, 장애물 큐브, 모닥불, 안내판, 본관 한가운데 있던 BSP 블록.
박물관에 필요 없고 전시대와 겹쳤다.

| 남긴 것 | 왜 |
| --- | --- |
| 바닥 2개 · 벽 6개 | 방 구조 |
| 조명 · 스카이 · 리플렉션 | 조명 환경 |
| `PlayerStart` | 시작 위치 (-100, 0) |
| NavMesh 볼륨 · `NavModifier_NoTeleport` | 텔레포트 이동에 필요 |
| `BP_VRSpectator` | **미러링 화면 (FR-UI-006)** |
| `BP_Passthrough_C_1` | XR 패스스루 기능 |

**공간 구조**

```
        y=+500 ┌───────────────────────┐
               │        [전시대3]       │
               │                       │  뒷방
     (시작)──▶ │        [전시대2]    문 │  (천장 400)
    (-100,0)   │                       │
               │        [전시대1]       │
        y=-500 └───────────────────────┘
             x=-500      x=300      x=500
```

전시대는 `x=300` 선상에 `y = -420 / 0 / +420` 으로 놓았다.
간격 420cm — 근접 트리거(반경 200cm)가 서로 겹치지 않는 최소 거리다.
FR-UI-002(패널 겹침 방지)가 아직 미구현이라 간격으로 회피하고 있다.
각 전시대는 정보 패널이 시작 지점을 향하도록 회전돼 있다 (yaw 43.6 / 90 / 136.4).

> **템플릿 레벨 `L_XRTemplate` 은 원본 그대로 두었다.** 되돌릴 기준이 필요하다.
> **템플릿 레벨은 직접 건드리지 않는다.** 템플릿을 수정하면 되돌릴 기준이 없어진다.

## 1-1. 조명 — 확인된 문제

### 🔴 렌더링 경로가 어긋나 있다 (가장 중요)

`Config/DefaultEngine.ini` 에 두 가지 경로가 섞여 있다.

| 설정 | 값 | 무엇을 위한 것인가 |
| --- | --- | --- |
| `r.ForwardShading` | True | 모바일 VR |
| `r.MobileHDR` | False | 모바일 VR |
| `vr.MobileMultiView` | True | 모바일 VR |
| `r.AntiAliasingMethod` | 3 (MSAA) | 모바일 VR — 맞다 |
| **`r.DynamicGlobalIlluminationMethod`** | **1 = Lumen** | **PC 전용** |
| **`r.ReflectionMethod`** | **1 = Lumen** | **PC 전용** |

**Lumen은 Quest 2에서 동작하지 않는다.** 지금 에디터에서 보이는 조명은
Lumen이 실시간으로 계산한 것이고, 헤드셋에서는 그 계산이 통째로 빠진다.

→ **지금 화면을 보고 조명을 판단하면 안 된다.** 실기와 다르다.
→ G1 빌드 전에 렌더링 경로를 정해야 한다. 팀 결정 사항이다.

### 🟠 L_Museum 에 라이팅 빌드 데이터가 없다

레벨을 복제할 때 `_BuiltData` 파일이 따라오지 않았다.

```
L_XRTemplate.umap          + L_XRTemplate_BuiltData.uasset (3.3MB)  ← 있음
L_Museum.umap              + (없음)                                 ← 없음
```

모바일 VR은 **라이트맵(정적 라이팅)이 사실상 필수**다. 동적 조명은 Quest 2에서 비싸다.
`Build > Build Lighting Only` 를 한 번 돌려야 하는데, **렌더링 경로를 정한 뒤에** 한다.
지금 구우면 Lumen 기준으로 구워져서 다시 해야 한다.

### 🟡 전시장에 조명이 없다

포인트라이트 2개가 모두 **뒷방**에 있다. 본관(전시장)에는 방향광과 스카이라이트뿐이다.

| 조명 | Mobility | 위치 | 색 |
| --- | --- | --- | --- |
| `DirectionalLight_0` | Stationary | 본관 상공 | 흰색, 세기 2 |
| `PointLight4_0` | **Static** | (1000, 0, 60) — **뒷방** | 주황 (255,181,84) |
| `PointLight5_0` | **Static** | (1447, 0, 102) — **뒷방 끝** | 주황, 세기 0.5 |
| `SkyLightPC2_0` | Static | 원점 | 흰색 |

주황색은 템플릿 모닥불 조명이다. 모닥불 메시는 지웠는데 조명만 남았다.
박물관 전시 조명으로 쓸 색이 아니다.

### 🟡 전시대가 정적 조명을 못 받는다

전시대의 모든 컴포넌트가 **Movable** 이다 (블루프린트 기본값).

- `Static` 라이트는 Movable 오브젝트를 **직접 비추지 않는다.** 라이트맵을 통해서만 비춘다.
- 지금 전시대를 비추는 것은 **Stationary 방향광 하나뿐**이다.
- 유물이 단일 방향광만 받아 입체감이 약하다. 전시물로는 부족하다.

> 유물 메시를 `Static` 으로 바꾸면 라이트맵을 받을 수 있지만,
> **복원 단계별로 메시를 교체하므로 Static 으로 둘 수 없다.**
> 단계 전환이 이 프로젝트의 핵심 기능이라 이 제약은 계속 간다.
> → 전시 조명은 `Stationary` 또는 `Movable` 스포트라이트로 해결해야 한다.

### ✅ 적용한 것 (테스트 단계 실험)

**렌더링 경로를 모바일 VR 기준으로 통일** — `Config/DefaultEngine.ini`

| 설정 | 전 | 후 | 왜 |
| --- | --- | --- | --- |
| `r.DynamicGlobalIlluminationMethod` | 1 (Lumen) | **0 (None)** | Quest 2 미지원 |
| `r.ReflectionMethod` | 1 (Lumen) | **0 (None)** | Quest 2 미지원 |
| `r.RayTracing` | True | **False** | PC 전용, 오버헤드 |
| `r.Lumen.HardwareRayTracing` | True | **False** | 위와 동일 |

Virtual Shadow Maps 는 손대지 않았다. Forward Shading 이 켜져 있으면
엔진이 자동으로 일반 Shadow Maps 로 내린다.

> ⚠️ **`DefaultEngine.ini` 는 팀 공유 파일이다.** 지금은 테스트라 바꿨지만,
> 커밋 전에 팀 합의가 필요하다. G1 게이트와 직결된다.

> ⚠️ **에디터를 다시 켜야 완전히 반영된다.** 셰이더가 다시 컴파일된다.

**전시 조명 3개 추가** — `ExhibitSpot_01 ~ 03`

| 항목 | 값 | 이유 |
| --- | --- | --- |
| Mobility | Stationary | Movable 인 유물도 비출 수 있다 |
| 위치 | (230, −420 / 0 / +420, 360) | 각 전시대 앞 위쪽 |
| 각도 | pitch −74° | 관람객 쪽에서 유물로 내리쬔다 |
| 세기 | 2600 cd | 거리 2.5m 기준. **실기 확인 전 임시값** |
| 콘 | 내부 16° / 외부 30° | 전시물만 좁게 |
| 색온도 | 4000K | 박물관 전시 조명 통상값 |

**모닥불 잔존 조명 중성화** — `PointLight4_0`, `PointLight5_0` 의
주황색(255,181,84)을 4500K 중성으로 변경. 뒷방에 있어 전시장에 직접 영향은 없지만
문틈으로 주황빛이 새어나왔다.

**아웃라이너 정리** — 조명을 `Lighting` 폴더로, 전시대를 `Heritage` 폴더로.

### 남은 것

1. **라이팅 빌드** — `Build > Build Lighting Only`. 이제 렌더링 경로가 정해졌으니
   구워도 된다. `L_Museum_BuiltData.uasset` 이 생긴다.
2. **조명 세기 실기 확인** — 2600cd 는 PC 모니터 기준 추정값이다.
   Quest 2 화면은 밝기 특성이 달라 반드시 다시 맞춰야 한다.
3. **동적 조명 개수 예산** — Stationary 스포트 3개 + 방향광 1개.
   모바일 포워드에서 이게 감당되는지 실기 측정 필요 (NFR-PERF).

## 1-2. 폰트 — 확인된 제약

기본 폰트는 `/Engine/EngineFonts/Roboto` 다. 한글 글리프가 없고,
합성 폰트의 fallback(`DroidSansFallback`)이 대신 그린다. **한글은 정상 표시된다.**

문제는 fallback 타입페이스에 **Regular 하나뿐이라는 것**이다.

| 설정 | 라틴 문자 | 한글 |
| --- | --- | --- |
| Bold | 굵어짐 | **안 굵어짐** (fallback에 Bold가 없음) |
| Italic / Light | 적용됨 | 안 됨 |
| 크기 · 색상 | 적용됨 | 적용됨 |

→ **한글 UI에서 굵기로 위계를 만들 수 없다.** 현재 패널은 크기(38/30/24/20)와
색상(흰색 / 앰버 / 회색)으로만 위계를 준다. 의도한 설계다.

→ 굵기가 필요하면 **한국어 폰트를 직접 임포트해야 한다** (Noto Sans KR, Pretendard 등).
  Font Face 에셋으로 넣고 Composite Font 를 새로 만든다. 라이선스 기록 필요 (FR-OPS).

> **미검증.** fallback 폰트가 Android 패키징에 포함되는지 확인 안 했다.
> 누락되면 헤드셋에서 한글이 전부 네모로 나온다. **G1 빌드 때 반드시 확인한다.**

## 1-3. 근접 표시 — 왜 Overlap 이 아닌가

**`BP_XRPawn` 에는 충돌 컴포넌트가 하나도 없다.** 캡슐도 바디도 없다.
컴포넌트는 VROrigin / Camera / 손 메시 / 모션컨트롤러 / 위젯인터랙션뿐이다.

→ 전시대에 트리거 구체를 달아도 **Overlap 이벤트가 영원히 발생하지 않는다.**
  처음에 `EventActorBeginOverlap` 으로 짰다가 PIE 에서 확인하고 발견했다.

### 대신 쓰는 방식 — 거리 측정

`CheckProximity` 함수가 **0.2초 타이머**로 돌면서:

```
플레이어 카메라 위치  ←  Game|GetPlayerCameraManager → Camera|GetCameraLocation
     ↓  거리 계산
전시대 위치 (GetActorLocation)
     ↓
거리 < ShowDistance  →  ShowPanel
그 외                →  HidePanel
```

- **매 프레임(Tick)이 아니라 0.2초 타이머**다. Quest 2 프레임 비용을 아끼기 위함.
- **카메라(머리) 기준**이라 VR 에서 더 자연스럽다. 몸이 아니라 시선이 기준이 된다.
- `ShowDistance` 는 인스턴스별로 조정 가능하다 (Instance Editable). 기본 250cm.
- `ProximityTrigger` 구체는 **에디터에서 범위를 눈으로 보기 위해** 남겨뒀다.
  이벤트는 걸려 있지 않다. 반경을 `ShowDistance` 와 같은 250 으로 맞춰뒀다.

### 실측 검증 (PIE)

| 폰 위치 | Pedestal_01 | Pedestal_02 | Pedestal_03 |
| --- | --- | --- | --- |
| (150, 0) | 숨김 (570cm) | **표시 (150cm)** | 숨김 (570cm) |
| (150, 420) | 숨김 (570cm) | 숨김 (445cm) | **표시 (150cm)** |

FR-UI-001 통과. 전시대 간격이 420cm 라 한 번에 하나만 뜬다 (FR-UI-002 는 여전히 미구현이지만 현재 배치에서는 문제되지 않는다).

## 1-4. 컨트롤러로 버튼 누르기 — 정정

**앞서 "`WidgetInteractionComponent` 가 없어 버튼을 누를 수 없다" 고 적었는데 틀렸다.**
`BP_XRPawn` 에는 이미 양손에 붙어 있다.

| 컴포넌트 | 사거리 | 트레이스 채널 |
| --- | --- | --- |
| `WidgetInteractionLeft` | 500cm | `ECC_GameTraceChannel1` = **3DWidget** |
| `WidgetInteractionRight` | 500cm | 동일 |

문제는 다른 곳이었다. 우리 `InfoPanel` 이 **`UI` 충돌 프로파일**을 쓰고 있었는데,
`3DWidget` 채널의 기본 응답이 `ECR_Ignore` 라 **레이저가 패널을 통과해버린다.**

템플릿의 `BP_Menu` 를 열어보니 답이 있었다.

```
collisionProfileName : Custom
모든 기본 채널        : ECR_Ignore
3DWidget             : ECR_Block      ← 이것
```

`InfoPanel` 을 같은 설정으로 맞췄다.

> ⚠️ **실기 미검증.** 설정은 템플릿 메뉴와 동일하게 맞췄지만,
> 컨트롤러로 실제로 눌러본 것은 아니다. 헤드셋 연결 후 확인해야 한다.

## 1-5. 현대 미술관 룩 — 적용 내역

프로토타입 회색 격자 상태에서 화이트 큐브 갤러리로 바꿨다.

### 머티리얼 4종 `/Game/Heritage/Materials/`

부모는 모두 `M_FlatCol` (Base Color / Metallic / Roughness 만 있는 단순 머티리얼).
모바일에서 저렴하고, 텍스처가 없어 메모리도 안 먹는다.

| 에셋 | Base Color | Roughness | 쓰임 |
| --- | --- | --- | --- |
| `MI_MuseumWall` | 0.86 회백색 | 0.92 | 벽 7면 |
| `MI_MuseumFloor` | 0.34 진회색 | 0.38 | 바닥 — 폴리시드 콘크리트 |
| `MI_MuseumCeiling` | 0.90 백색 | 0.95 | 천장 |
| `MI_Plinth` | 0.93 백색 | 0.70 | 유물 좌대 |

기존 `MI_Grid_Default` (프로토타입 격자) 를 전부 교체했다.

### 천장 추가

본관은 원래 **하늘이 뚫려 있었다.** 실외처럼 보이는 원인이었다.
`MuseumCeiling` 액터를 z=400~450 에 덮어 밀폐했다 (x −500~525, y −550~550).

밀폐하면서 생긴 결과:

- `DirectionalLight_0` (태양) 이 실내에 도달하지 않는다 → 세기 2 → **0.6** 으로 낮춤
- `SkyLightPC2_0` 도 차폐된다 → 실내 조명을 따로 넣어야 한다

### 좌대 형태 변경

| | 전 | 후 |
| --- | --- | --- |
| 메시 | 원기둥 | **정육면체** |
| 크기 | Ø60 × 90cm | **40 × 40 × 100cm** |
| 재질 | 템플릿 회색 | **흰색 `MI_Plinth`** |
| 유물 높이 | z=105 (좌대에 반쯤 묻힘) | **z=113** (좌대 위) |
| 정보 패널 | z=130 | **z=150** — 관람객 눈높이(165) 근방 |

현대 미술관 플린스는 원기둥이 아니라 흰 사각 좌대다.

### 조명 — Static / Stationary 를 나눠 쓴다

| 조명 | 개수 | Mobility | 왜 이 Mobility 인가 |
| --- | --- | --- | --- |
| `GalleryFill_01~04` | 4 | **Static** | 런타임 비용 **0**. 라이트맵으로만 기여. 방 전체를 공짜로 밝힌다 |
| `ExhibitSpot_01~03` | 3 | **Stationary** | 유물이 Movable 이라 **동적으로 비춰야** 한다 |
| `DirectionalLight_0` | 1 | Stationary | 실내엔 무의미. 0.6 으로 낮춤 |

- 전반 조명 `GalleryFill` — 천장 z=350, 3200 루멘, 4200K, 반경 850cm
- 전시 조명 `ExhibitSpot` — 2600 칸델라, 4000K, 콘 16°/30°

> **왜 전반 조명을 Static 으로 했나.** Static 라이트는 굽고 나면 런타임 비용이 0이다.
> Movable 인 유물도 volumetric lightmap 을 통해 간접광은 받는다.
> Quest 2 에서 방을 공짜로 밝히는 유일한 방법이다.
> 유물에 직접 닿는 빛만 Stationary 스포트 3개로 감당한다.

### 노출 고정 — 밝기 문제의 진짜 원인

레벨에 **`PostProcessVolume` 이 없었다.** 그래서 UE 기본 자동 노출이 돌고 있었고,
범위가 **EV100 −10 ~ 20** 이었다. 흰 벽으로 둘러싸인 방에서 자동 노출이
밝기를 계속 끌어올려 화면이 날아갔다.

`PP_Gallery` 를 추가해 노출을 고정했다.

| 설정 | 값 | 이유 |
| --- | --- | --- |
| `bUnbound` | true | 레벨 전체에 적용 (Infinite Extent) |
| `AutoExposureMinBrightness` | **10.0** | Min = Max → **노출 고정** |
| `AutoExposureMaxBrightness` | **10.0** | 같은 값 |
| `AutoExposureBias` | 0.0 | 미세 조정용 손잡이 |
| `BloomIntensity` | 0.675 → **0.25** | 흰 벽에서 블룸이 글레어를 만든다. 모바일에서 비싸기도 하다 |

> **VR 에서 자동 노출은 쓰지 않는다.** 고개를 돌릴 때 화면 밝기가 출렁여
> 멀미를 유발하고, 미러링 화면(FR-UI-006)도 매번 다르게 찍힌다.
> 고정 노출이 정석이다.

> **이제 밝기 조정이 예측 가능해졌다.** 자동 노출이 걸려 있으면 조명을 낮춰도
> 노출이 보상해버려서 아무 변화가 없다. 고정한 뒤에야 조명 값이 화면에 직결된다.

### 밝기 하향 (2차 조정)

| 대상 | 전 | 후 |
| --- | --- | --- |
| `GalleryFill_01~04` | 3200 lm | **1500 lm** |
| `ExhibitSpot_01~03` | 2600 cd | **1800 cd** |
| `DirectionalLight_0` | 0.6 | **0.15** |
| `SkyLightPC2_0` | 1.0 | **0.2** |
| 벽 알베도 | 0.86 | **0.75** |
| 천장 알베도 | 0.90 | **0.78** |
| 좌대 알베도 | 0.93 | **0.84** |

알베도를 낮춘 이유: **흰 방은 빛을 여러 번 반사시킨다.** 벽이 0.86 이면
직접광보다 반사광이 더 밝아진다. 0.75 는 여전히 흰색으로 읽히면서 버운징을 줄인다.

> 이 값들은 **실기 미검증 추정값이다.** Quest 2 화면 밝기 특성이 달라
> 헤드셋에서 반드시 다시 맞춰야 한다.

### 확정된 노출 값

| 설정 | 확정값 |
| --- | --- |
| `AutoExposureMinBrightness` = `MaxBrightness` | 10.0 (고정) |
| **`AutoExposureBias` (Exposure Compensation)** | **3.96** ← 실사용자 확인 |
| 유효 노출 | EV100 **6.04** |
| 노출 배율 | **0.0127** |

### ⚠️ 고정 노출과 월드 UI는 서로 얽혀 있다

노출을 고정하자 **정보 패널이 어두워졌다.** 월드 공간 위젯도 씬과 똑같이
톤매핑·노출을 타기 때문이다.

```
흰 글자 0.95  ×  노출배율 0.0127  =  0.012   →  거의 검정
```

`InfoPanel` 의 `TintColorAndOpacity` 를 **70** 으로 올려 보정했다.

```
0.95 × 70 × 0.0127 = 0.84   →  밝은 흰색
0.04 × 70 × 0.0127 = 0.035  →  어두운 배경 (대비 유지)
```

틴트는 **곱셈**이라 색끼리의 대비 비율은 그대로다. 절대 밝기만 올라간다.

> **노출을 바꾸면 UI 틴트도 같이 바꿔야 한다.** 둘은 연동된다.
>
> `틴트 = 70 / 2^(Bias − 4)`  — Bias 가 1 오르면 틴트는 절반

| Exposure Compensation | 필요한 Tint |
| --- | --- |
| 2 | 275 |
| 3 | 137 |
| **4** | **70** ← 현재 |
| 5 | 34 |
| 6 | 17 |

### 패널 투명도 — Transparent 로 확정

| 설정 | 값 | 비고 |
| --- | --- | --- |
| `InfoPanel.BlendMode` | **Transparent** | 실제 알파 블렌딩 |
| `Panel_Root.BrushColor` 알파 | **0.72** | 28% 투과 |
| `TintColorAndOpacity` | 70 (알파 1.0) | 노출 보정용. 알파는 건드리지 않는다 |

투과율을 조정하려면 **`Panel_Root` 의 Brush Color 알파**만 바꾼다.
틴트 알파가 아니다.

| 알파 | 느낌 |
| --- | --- |
| 0.9 | 거의 불투명 |
| **0.72** | 스모크 글라스 ← 현재 |
| 0.5 | 많이 비침. 뒷 배경이 밝으면 글자 가독성이 떨어진다 |

> ⚠️ **모바일 비용.** 반투명은 Masked 보다 비싸다. 오버드로가 생기고
> 정렬(sorting) 문제가 날 수 있다. 전시대 3개가 한 화면에 겹쳐 보이면
> 확인이 필요하다. **실기 측정 항목이다.**

> 충돌 설정(`3DWidget` = Block)은 BlendMode 와 무관하다. 변경 후 확인했다.

### 밝기를 더 조정하려면

손잡이는 하나만 쓴다. **`PP_Gallery` → `Exposure` → `Exposure Compensation`**

| 원하는 것 | 값 |
| --- | --- |
| 더 어둡게 | −0.5, −1.0, −1.5 … |
| 더 밝게 | +0.5, +1.0 … |

조명을 하나하나 만지지 말고 이걸 먼저 움직인다. **라이팅 리빌드도 필요 없다.**
조명 값을 바꾸면 Static/Stationary 라서 매번 다시 구워야 한다.

### 라이팅 빌드 완료

```
Lightmass: 4.85 sec
Lights with unbuilt interactions: 0
Primitives with unbuilt interactions: 0
```

`L_Museum_BuiltData.uasset` (1.8MB) 생성. **"LIGHTING NEEDS TO BE REBUILT" 경고 해소.**

> ⚠️ **다음 경우 다시 구워야 한다.** 정적 액터를 옮기거나 추가·삭제했을 때,
> Static/Stationary 조명을 바꿨을 때, 렌더링 경로를 바꿨을 때.
> 단축키 `Ctrl+Shift+;` 또는 `Build > Build Lighting Only`.

> ⚠️ **`_BuiltData` 는 1.8MB 바이너리다.** LFS 대상이고, 리빌드마다 새로 커밋된다.
> 히스토리가 빠르게 늘어난다. 커밋 빈도를 팀에서 정해야 한다.

## 2. 아직 안 된 것

프로토타입을 완성으로 읽지 않기 위해 명시한다.

| 항목 | 왜 안 됐나 |
| --- | --- |
| 유물 실제 메시 | AI 직군 산출물 대기 (N-01, N-02). 현재는 큐브·원기둥·구 임시 배치 |
| 컨트롤러로 버튼 누르기 | 설정은 맞췄으나 **실기 미검증.** 1-4절 참조 |
| FR-UI-002 (패널 겹침 방지) | 미구현. 전시대 여러 개가 겹치면 패널이 동시에 뜬다 |
| FR-UI-008 (복원 영역 분리 표시) | 미구현 (SHOULD) |
| 실기 성능 | 측정 안 함. 폰트 크기·조명 세기·드로우콜 전부 추정값 |

| 한글 폰트 패키징 | **미검증.** 1-2절 참조 |
| Quest 2 빌드 | **G1 게이트 미통과.** 최우선 과제 |

## 3. 동작 방식 — 배선 완료

전부 MCP로 작성했다. 에디터에서 손으로 연결한 것은 없다.

### 전시대 `BP_ArtifactPedestal`

| 그래프 | 하는 일 |
| --- | --- |
| `EventBeginPlay` | 단계를 ①로 초기화 → 패널에 자기 참조 전달 → 패널 숨김 → `ApplyStage` |
| `ApplyStage` | `StageMeshes[CurrentStage]` 로 메시 교체 + 패널 여섯 칸 갱신 |
| `NextStage` / `PrevStage` | `(CurrentStage + 1 또는 + 2) % 3` → `ApplyStage` |
| `ShowPanel` / `HidePanel` | `InfoPanel` 의 Hidden in Game 토글 |
| `EventActorBeginOverlap` | `ShowPanel` (FR-UI-001) |
| `EventActorEndOverlap` | `HidePanel` |

### 패널 `WBP_ArtifactPanel`

| 그래프 | 하는 일 |
| --- | --- |
| `UpdatePanel(6개 인자)` | 텍스트 블록 여섯 개를 한 번에 설정 |
| `SetOwner(NewOwner)` | 전시대 참조를 받아 저장 |
| `OnClicked(Btn_Next)` | `OwnerPedestal → NextStage` |
| `OnClicked(Btn_Prev)` | `OwnerPedestal → PrevStage` |

> **`SetOwner` 가 왜 필요한가.** 블루프린트는 다른 오브젝트의 변수를
> 직접 설정할 수 없다. 세터 함수를 거쳐야 한다.

> **순환 참조.** 전시대가 패널 클래스를, 패널이 전시대 클래스를 참조한다.
> UE는 허용하지만 블루프린트 인터페이스로 바꾸면 없앨 수 있다.

## 4. Unreal MCP 사용 기록

### 되는 것 (이 프로토타입은 전부 MCP로 만들었다)

- 위젯 트리 생성·배치·프로퍼티 설정 (`UMGToolSet`)
- 블루프린트 에셋 생성, 컴포넌트 추가, 변수 추가 (`BlueprintTools`, `ActorTools`)
- 함수 그래프 · 이벤트 그래프 · 버튼 바인드 이벤트를 DSL로 작성 (`write_graph_dsl`)
- 블루프린트 클래스로의 Cast, 배열 인덱싱, 다른 BP 함수 호출
- 레벨에 액터 배치, 아웃라이너 정리, 레벨 복제·전환 (`SceneTools`, `AssetTools`)
- 에디터 화면 조작 — 에셋 에디터 열기, 액터 선택·포커스, 콘텐츠 브라우저 이동
- 출력 로그 읽기 (`LogsToolset`) — 컴파일 에러 확인에 쓴다
- 머티리얼 인스턴스 생성·파라미터 설정 (`MaterialInstanceTools`)
- PIE 실행·정지와 런타임 상태 검사 (`EditorAppToolset`) — **기능 검증에 결정적이다**
- **에디터 메뉴 클릭** (`SlateInspectorToolset`) — 아래 참조
- 여러 호출을 파이썬 한 스크립트로 묶기 (`ProgrammaticToolset`) — 왕복이 크게 준다

### MCP에 없는 기능은 에디터 UI를 클릭해서 해결한다

라이팅 빌드는 전용 툴이 없다. `SlateInspectorToolset` 으로 메뉴를 직접 눌렀다.

```
1. Windows(list)                    → 메인 창 ref = w1
2. Observe(w1, maxDepth=40)         → 하위 위젯에 ref 부여 (필수)
3. Snapshot(w1) 에서 "Build" 검색   → button ref = b40
4. Click(b40)                       → 메뉴 열림
5. Snapshot 에서 "Build Lighting Only" 검색 → ref = g6
6. Click(g6)                        → 빌드 실행
7. LogsToolset 으로 결과 확인
8. Unobserve(observer_N)            → 100ms 폴링 중단
```

> **`Observe` 를 먼저 부르지 않으면 안 된다.** 기본 옵저버는 최상위 창만 훑어서
> Snapshot 이 10줄밖에 안 나온다. Observe 후에는 162줄이 나왔다.

> **스냅샷은 스크립트 안에서 걸러라.** 전체를 그대로 받으면 컨텍스트를 낭비한다.
> `ProgrammaticToolset` 안에서 정규식으로 필요한 줄만 뽑는다.

이 방식으로 **메뉴에 있는 거의 모든 기능**을 MCP에서 실행할 수 있다.

### ⚠️ 에디터 언어는 반드시 English 로 둔다

**노드 타입 ID가 에디터 UI 언어를 그대로 따라간다.**

| | 한국어 에디터 | English 에디터 |
| --- | --- | --- |
| BeginPlay | `이벤트추가\|이벤트BeginPlay` | `AddEvent\|EventBeginPlay` |
| 메시 교체 | `컴포넌트\|스태틱메시\|SetStaticMesh` | `Components\|StaticMesh\|SetStaticMesh` |

DSL은 `AddEvent|` 접두사를 하드코딩하고 있어서, **한국어 에디터에서는 이벤트 노드와
블루프린트 클래스 Cast 노드를 아예 만들지 못한다.** 처음에 이 프로젝트가 한국어라
막혔고, English 로 바꾸자 전부 풀렸다.

→ **DSL 스크립트는 언어 간 호환되지 않는다.** 팀원 전원이 English 로 맞춘다.

### 안 되는 것 — 확인된 제약

1. **커스텀 이벤트를 만들 수 없다.** `(event MyEvent)` 는 `AddEvent|MyEvent` 를 찾는데
   그런 타입이 없다. → 대신 **함수 그래프**를 쓴다. 이 프로토타입의
   `NextStage` / `PrevStage` / `ShowPanel` / `HidePanel` 이 그래서 전부 함수다.

2. **버튼 바인드 이벤트는 먼저 만들어 둬야 DSL이 참조할 수 있다.**
   `UMGToolSet.BindToEventProperty` 로 노드를 만들면 타입 ID `AddEvent|OnClicked(Btn_Next)`
   가 생기고, 그때부터 `(event OnClicked(Btn_Next) ...)` 로 쓸 수 있다.

3. **오브젝트 타입 함수 인자는 전용 툴을 쓴다.** `add_function_param` 은 원시 타입만
   받는다. 오브젝트는 `add_object_function_param`.

4. **블루프린트 인터페이스 에셋을 만들 수 없다.** `BlueprintTools.create` 가
   `/Script/Engine.Interface` 를 거부한다.

5. **디자이너 캔버스 크기(Fill Screen / Custom)를 못 바꾼다.**
   → 루트를 SizeBox로 고정하면 우회된다. 1절 참조.

6. **에디터 언어 설정을 못 바꾼다.** 커스텀 위젯이라 `ConfigSettingsToolset` 에
   노출되지 않는다. Editor Preferences 에서 손으로 바꾼다.

7. **뷰포트 스크린샷은 실용적이지 않다.** base64 PNG로 돌아와서 에이전트 컨텍스트를
   통째로 먹는다. 화면 확인은 사람이 한다.

8. 패키징·실기 배포·C++ 빌드는 범위 밖이다. **G1 게이트에 MCP는 도움이 안 된다.**

### 자주 틀린 것 — 값 이름

| 쓴 값 | 맞는 값 |
| --- | --- |
| `sizeRule: "Auto"` | `"Automatic"` (VerticalBoxSlot) |
| `%` 연산자 (int) | `Math\|Integer\|%(Integer)` 노드 |
| `widgetSpace`, `bTwoSided` | `space`, `bIsTwoSided` (WidgetComponent) |
| 배열 Get 의 `TargetArray` | `Array` + `"Dimension 1"` |

> 프로퍼티 이름을 추측하지 말고 `ObjectTools.list_properties` 로 먼저 확인한다.
> 틀리면 조용히 실패하는 게 아니라 에러가 정확한 이름을 알려준다 — 그걸 읽는 게 빠르다.


### 설정

- `.mcp.json` (저장소 루트) — `http://127.0.0.1:8000/mcp`
- `.uproject` 에서 `ModelContextProtocol` 은 `SupportedTargetPlatforms: ["Win64"]` 로
  제한돼 있다. Android 패키징에 실험적 플러그인이 딸려 들어가지 않게 하기 위함이다.
- `AllToolsets` 는 `EditorOnly: true` 라 별도 제한이 필요 없다.

> UE 5.8 의 Unreal MCP 는 **Experimental** 이다. G1 게이트 판단 근거로 삼지 않는다.
