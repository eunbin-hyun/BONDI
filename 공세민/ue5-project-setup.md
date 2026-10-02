# UE5 프로젝트 시작 전 확인 사항

이 문서는 **실제 VR 프로젝트를 새로 만들 때** 미리 알고 시작하기 위한 것이다.
2026-09-01에 폐기용 실험 프로젝트로 전시대·정보 패널 프로토타입을 끝까지 관통시켜 보며
확인한 내용을 정리했다. 실험 프로젝트 자체는 저장소에 올리지 않았다.

> **여기 적힌 것은 대부분 "겪어보고 알아낸 함정"이다.**
> 순서대로 읽고 시작하면 같은 곳에서 다시 막히지 않는다.
> 밝기·성능 관련 수치는 **PC 에디터 기준 추정값**이며 실기 미검증이다.

관련 문서 (모두 `dev` 브랜치): `docs/PROJECT_MASTER_SPEC.md` · `docs/DECISIONS.md` · `CONTRIBUTING.md`

---

## 1. 프로젝트 생성 직후 (순서대로)

### 1-1. 에디터 언어를 English로 바꾼다 — 최우선

```
Edit > Editor Preferences > General > Region & Language > Editor Language → English
```

재시작이 필요하다. **이걸 먼저 하지 않으면 뒤의 작업이 막힌다.**

한국어 에디터에서는 블루프린트 노드 타입 ID가 한글로 나온다.

| | 한국어 에디터 | English |
| --- | --- | --- |
| BeginPlay | `이벤트추가\|이벤트BeginPlay` | `AddEvent\|EventBeginPlay` |
| 메시 교체 | `컴포넌트\|스태틱메시\|SetStaticMesh` | `Components\|StaticMesh\|SetStaticMesh` |
| 유효성 검사 | `유틸리티\|IsValid` | `Utilities\|IsValid` |

**한국어 상태에서 막힌 것**

- Unreal MCP의 블루프린트 DSL이 이벤트 노드를 만들지 못한다 (`AddEvent|` 접두사 하드코딩)
- 블루프린트 클래스로의 Cast 노드도 만들지 못한다
- 작성한 DSL 스크립트가 영어 에디터와 호환되지 않는다

영어로 바꾸자 셋 다 해결됐다. **팀원 전원이 English로 맞춘다.**

### 1-2. 렌더링 경로를 하나로 통일한다

VR Template은 모바일 VR 설정과 PC 전용 설정이 **섞인 채로** 생성된다.
Quest 2 스탠드얼론이 목표라면(D-41) PC 전용 기능을 끈다.

| 설정 | 템플릿 기본값 | Quest 2 기준 |
| --- | --- | --- |
| `r.ForwardShading` | True | 유지 |
| `r.MobileHDR` | False | 유지 |
| `vr.MobileMultiView` | True | 유지 |
| `r.AntiAliasingMethod` | 3 (MSAA) | 유지 — VR에 맞다 |
| **`r.DynamicGlobalIlluminationMethod`** | **1 (Lumen)** | **0 (None)** |
| **`r.ReflectionMethod`** | **1 (Lumen)** | **0 (None)** |
| **`r.RayTracing`** | **True** | **False** |
| `r.AllowStaticLighting` | True | 유지 — 라이트맵을 쓴다 |

**Lumen은 Quest 2에서 동작하지 않는다.** 켜둔 채로 작업하면
**에디터에서 보는 조명과 헤드셋에서 보는 조명이 다르다.** 조명을 맞추는 작업이 전부 헛일이 된다.

Virtual Shadow Maps는 건드리지 않아도 된다. Forward Shading이 켜져 있으면
엔진이 자동으로 일반 Shadow Maps로 내린다.

> ⚠️ `Config/DefaultEngine.ini`는 **팀 공유 파일**이다. 바꾸기 전에 합의한다.
> PC VR 시연(N-09)에도 영향을 준다.

### 1-3. PostProcessVolume을 만들고 노출을 고정한다

**템플릿에는 PostProcessVolume이 없다.** 그래서 자동 노출이 EV100 −10 ~ 20 범위로 돌아간다.

| 설정 | 값 |
| --- | --- |
| `bUnbound` | true (Infinite Extent) |
| `AutoExposureMinBrightness` | Max와 **같은 값** = 노출 고정 |
| `AutoExposureMaxBrightness` | Min과 같은 값 |
| `AutoExposureBias` | 밝기 조정 손잡이 |
| `BloomIntensity` | 0.675 → 0.25 정도 (흰 벽에서 글레어, 모바일에서 비쌈) |

**VR에서 자동 노출은 쓰지 않는다.** 고개를 돌릴 때 밝기가 출렁여 멀미를 유발하고,
미러링 화면(FR-UI-006)이 매번 다르게 찍힌다.

> **자동 노출을 켜둔 채로는 조명 튜닝이 불가능하다.** 조명을 낮춰도
> 노출이 보상해버려 화면이 변하지 않는다. 노출을 먼저 고정하고 조명을 맞춘다.

---

## 2. VR Template의 함정

### 2-1. `BP_XRPawn`에는 충돌 컴포넌트가 없다

캡슐도 바디도 없다. 컴포넌트는 VROrigin / Camera / 손 메시 / 모션컨트롤러 /
위젯인터랙션뿐이다.

→ **트리거 볼륨에 Overlap 이벤트가 발생하지 않는다.**
  `EventActorBeginOverlap`으로 근접 감지를 짜면 아무 일도 일어나지 않는다.

**대안: 거리 측정**

```
Game|GetPlayerCameraManager → Camera|GetCameraLocation
     ↓ 거리 계산 (Math|Vector|Distance)
GetActorLocation
     ↓
거리 < 임계값 → 표시 / 그 외 → 숨김
```

- **매 프레임(Tick)이 아니라 타이머(0.2초)** 로 돈다. Quest 2 프레임 비용 절약
- **카메라(머리) 기준**이 VR에서 더 자연스럽다. 몸이 아니라 시선이 기준
- `SetTimerByFunctionName`은 **함수 그래프**를 부를 수 있다 (커스텀 이벤트는 DSL로 못 만든다)

### 2-2. 컨트롤러로 3D UI를 누르려면 충돌 채널을 맞춰야 한다

`BP_XRPawn`에는 **이미 `WidgetInteractionLeft/Right`가 붙어 있다** (사거리 500cm).
따로 추가할 필요가 없다.

문제는 위젯 쪽이다. 레이저는 커스텀 채널 `ECC_GameTraceChannel1` = **`3DWidget`** 으로
추적하는데, 이 채널의 기본 응답이 `ECR_Ignore`다.
`WidgetComponent`의 기본 프로파일 `UI`는 이 채널을 명시하지 않아 **레이저가 통과해버린다.**

템플릿의 `BP_Menu`가 쓰는 설정을 그대로 쓴다.

```
collisionProfileName : Custom
collisionEnabled     : QueryOnly
모든 기본 채널        : ECR_Ignore
3DWidget             : ECR_Block      ← 이것
```

### 2-3. 템플릿 레벨을 직접 쓰지 않는다

`L_XRTemplate`은 복제해서 쓴다. 원본은 복원 기준으로 남긴다.

**복제할 때 `_BuiltData`가 따라오지 않는다.** 라이팅 빌드 데이터가 없는 상태가 되고
`LIGHTING NEEDS TO BE REBUILT` 경고가 뜬다. 복제 후 한 번 구워야 한다.

템플릿 레벨에는 데모 소품이 많다 — 권총, 집기용 큐브, 장애물, 모닥불, 안내판.
전시 공간으로 쓰려면 정리해야 한다. 다만 **다음은 남긴다.**

| 남길 것 | 이유 |
| --- | --- |
| 바닥 · 벽 | 방 구조 |
| 조명 · 스카이 · 리플렉션 캡처 | 조명 환경 |
| `PlayerStart` | 시작 위치 |
| NavMesh 볼륨 · `NavModifier_NoTeleport` | 텔레포트 이동에 필요 |
| **`BP_VRSpectator`** | **미러링 화면 (FR-UI-006)** |
| `BP_Passthrough` | XR 패스스루 |

> 본관은 **천장이 없다.** 실내로 만들려면 천장을 덮어야 한다.
> 덮으면 방향광·스카이라이트가 차단되므로 실내 조명을 따로 넣어야 한다.

> 데모 에셋을 지울 때는 **참조를 먼저 확인한다.** `BP_Pistol`이 `SM_Pistol`을 참조하고
> 템플릿 레벨이 `BP_Pistol`을 참조하는 식으로 얽혀 있다. 에디터의 Reference Viewer
> 또는 MCP의 `AssetTools.get_referencers`로 확인한다.

---

## 3. 3D 공간 UI (FE 직군)

### 3-1. 스크린 스페이스 UI는 VR에서 못 쓴다

`WidgetComponent`를 `World` 스페이스로 놓는다.

### 3-2. 루트를 SizeBox로 고정한다

위젯 루트가 크기 없이 Fill이면 **디자이너 캔버스(기본 Fill Screen) 전체로 퍼진다.**
정렬과 폰트 크기가 다 어긋나 보인다.

루트를 `SizeBox`로 감싸고 **`WidgetComponent.DrawSize`와 같은 값**으로 고정한다.
그러면 디자이너에서 보는 크기가 헤드셋에서 보는 크기와 일치한다.

### 3-3. 한글은 굵기로 위계를 만들 수 없다

기본 폰트 `/Engine/EngineFonts/Roboto`에는 한글 글리프가 없다.
합성 폰트의 fallback(`DroidSansFallback`)이 대신 그린다. **한글은 정상 표시된다.**

문제는 fallback에 **Regular 하나뿐**이라는 것이다.

| 설정 | 라틴 문자 | 한글 |
| --- | --- | --- |
| **Bold** | 굵어짐 | **안 굵어짐** |
| Italic / Light | 적용됨 | 안 됨 |
| 크기 · 색상 | 적용됨 | 적용됨 |

→ 한글 UI는 **크기와 색상으로만** 위계를 준다.
→ 굵기가 필요하면 한국어 폰트를 직접 임포트한다 (Noto Sans KR, Pretendard 등).
  Font Face 에셋 + Composite Font. **라이선스 기록 필요** (FR-OPS).

> ⚠️ **미검증.** fallback 폰트가 Android 패키징에 포함되는지 확인하지 않았다.
> 누락되면 헤드셋에서 한글이 전부 네모로 나온다. **G1 빌드에서 반드시 확인한다.**

### 3-4. 고정 노출과 월드 UI는 연동된다

노출을 고정하면 **월드 공간 UI도 같이 눌린다.** 월드 위젯도 씬과 똑같이 톤매핑을 탄다.

```
흰 글자 0.95  ×  노출배율  =  거의 검정
```

`WidgetComponent.TintColorAndOpacity`의 **RGB**를 올려 보정한다 (알파는 1.0 유지).
틴트는 곱셈이라 색끼리의 대비 비율은 유지되고 절대 밝기만 올라간다.

```
노출배율 = 1 / (1.2 × 2^(EV100 − Bias))
필요한 틴트 ≈ 0.85 / (0.95 × 노출배율)
```

**Bias가 1 오르면 틴트는 절반.** 노출을 바꿀 때마다 틴트도 같이 바꿔야 한다.

### 3-5. 패널 투명도

`WidgetComponent.BlendMode`가 `Masked`면 알파가 이진 마스크가 되어
**반투명이 되지 않는다** (완전 불투명). 반투명을 원하면 `Transparent`로 바꾼다.

투과율은 배경 위젯(Border 등)의 **Brush Color 알파**로 조정한다. 틴트 알파가 아니다.

> ⚠️ 반투명은 Masked보다 비싸다. 오버드로와 정렬 문제가 생긴다.
> 프레임이 부족하면 되돌릴 1순위 후보다. **실기 측정 항목.**
> 패널 뒤가 흰 벽이면 알파를 너무 낮추면 흰 글자가 안 읽힌다.

---

## 4. 조명

### 4-1. Mobility를 용도별로 나눈다

| 용도 | Mobility | 런타임 비용 | 비고 |
| --- | --- | --- | --- |
| 공간 전반 조명 | **Static** | **0** | 라이트맵으로만 기여. 움직이는 물체도 volumetric lightmap으로 간접광은 받는다 |
| 전시물 조명 | **Stationary** | 있음 | **Movable 오브젝트를 직접 비출 수 있는 유일한 선택** |
| 태양 | Stationary | 있음 | 실내라면 거의 무의미 |

**Static 라이트는 Movable 오브젝트를 직접 비추지 않는다.**
이걸 모르면 "조명을 넣었는데 유물이 어둡다"에서 막힌다.

### 4-2. 복원 단계 토글이 Mobility를 제약한다

유물 메시를 `Static`으로 두면 라이트맵을 받아 품질이 좋아진다.
그런데 **복원 3단계(FR-UI-003)는 메시를 런타임에 교체한다.** Static으로 둘 수 없다.

→ 유물은 항상 Movable이다. 전시 조명은 Stationary로 해결한다.
→ 이 제약은 프로젝트 내내 유지된다.

### 4-3. 흰 방은 생각보다 밝다

벽 알베도가 높으면 빛이 여러 번 반사되어 **직접광보다 반사광이 더 밝아진다.**
"너무 밝다"의 원인이 조명 세기가 아니라 알베도일 수 있다.

미술관 흰 벽은 0.75 정도가 흰색으로 읽히면서 버운징이 과하지 않다.

### 4-4. 라이팅 빌드

`Build > Build Lighting Only` 또는 `Ctrl+Shift+;`

다음을 바꿨으면 다시 굽는다 — 정적 액터 이동·추가·삭제, Static/Stationary 조명 변경,
머티리얼 알베도 변경, 렌더링 경로 변경.

로그에서 확인한다.

```
Lights with unbuilt interactions: 0
Primitives with unbuilt interactions: 0
```

> ⚠️ `_BuiltData`는 수 MB짜리 바이너리다. **리빌드마다 새 버전이 통째로 쌓인다.**
> LFS 용량이 빠르게 늘어난다. 커밋 빈도를 팀에서 정한다.

---

## 5. Git / LFS

- GitLab 인스턴스의 **LFS 사용 가능은 확인됨** (2026-09-01)
- `.gitattributes`의 LFS 줄 주석을 풀고 **그 파일을 먼저 커밋·푸시**한 뒤 바이너리를 추가한다
- 각자 최초 1회 `git lfs install`. 안 하면 바이너리가 포인터 텍스트로만 받아진다
- 확인: `git lfs ls-files`로 실제 변환 여부, `git check-attr filter -- <경로>`로 규칙 적용 여부

**UE 프로젝트에서 커밋하지 않는 것** — `Binaries/` `Intermediate/` `Saved/` `DerivedDataCache/`
(현재 `.gitignore`에 반영됨)

**바이너리 에셋 동시 편집 금지** — `.uasset` `.umap`은 병합이 불가능하다.
CONTRIBUTING 10절의 잠금 규칙을 따른다.

---

## 6. Unreal MCP

UE 5.8에 내장돼 있다 (**Experimental**). `Edit > Plugins`에서 `Unreal MCP` + `All Toolsets` 활성화.

```
ModelContextProtocol.GenerateClientConfig ClaudeCode   → .mcp.json 생성
ModelContextProtocol.StartServer 8000
```

`.uproject`에서 플랫폼을 제한한다. **실험적 플러그인이 Android 패키징에 딸려가면 빌드가 깨질 수 있다.**

```json
{ "Name": "ModelContextProtocol", "Enabled": true, "SupportedTargetPlatforms": ["Win64"] }
```

`AllToolsets`는 `EditorOnly: true`라 별도 제한이 필요 없다.

### 되는 것

위젯 트리 생성·프로퍼티 설정 / 블루프린트 에셋·컴포넌트·변수 생성 /
**함수·이벤트 그래프를 DSL로 작성** / 머티리얼 인스턴스 / 레벨 액터 배치 /
PIE 실행과 런타임 상태 검사 / 출력 로그 읽기 / **에디터 메뉴 클릭**(`SlateInspectorToolset`)

### 안 되는 것

- **커스텀 이벤트를 만들 수 없다** → 함수 그래프로 대체한다
- 버튼 바인드 이벤트는 `UMGToolSet.BindToEventProperty`로 먼저 만들어야 DSL이 참조할 수 있다
- 오브젝트 타입 함수 인자는 `add_object_function_param`을 쓴다 (일반 `add_function_param`은 원시 타입만)
- 블루프린트 인터페이스 에셋 생성 불가
- 디자이너 캔버스 크기 변경 불가 → SizeBox로 우회
- 에디터 언어 설정 변경 불가 (커스텀 위젯)
- 패키징·실기 배포·C++ 빌드는 범위 밖 → **G1 게이트에 MCP는 도움이 안 된다**

### 실무 팁

- **MCP를 쓰기만 하면 학습이 되지 않는다** (명세 4부 원칙). 시킨 뒤 에디터에서 결과를 열어보고
  손으로 한 번 재현한 다음 맡긴다
- 프로퍼티 이름은 추측하지 말고 `ObjectTools.list_properties`로 먼저 확인한다.
  틀리면 에러가 정확한 이름을 알려준다
- 여러 호출은 `ProgrammaticToolset`의 파이썬 스크립트로 묶는다. 왕복이 크게 준다
- 뷰포트 스크린샷은 base64로 돌아와 실용적이지 않다. **화면 확인은 사람이 한다**
- **PIE로 실제 검증한다.** 근접 감지가 동작하지 않는 것을 이 방법으로 발견했다

### 자주 틀린 값 이름

| 틀린 것 | 맞는 것 |
| --- | --- |
| `sizeRule: "Auto"` | `"Automatic"` (VerticalBoxSlot) |
| `%` 연산자 (int) | `Math\|Integer\|%(Integer)` 노드 |
| `widgetSpace` / `bTwoSided` | `space` / `bIsTwoSided` (WidgetComponent) |
| 배열 Get의 `TargetArray` | `Array` + `"Dimension 1"` |

---

## 7. 남은 미검증 항목

**전부 헤드셋이 있어야 확인된다.** 추정으로 진행하지 않는다.

| 항목 | 왜 미검증인가 |
| --- | --- |
| **한글 폰트 Android 패키징** | 누락되면 헤드셋에서 한글이 전부 네모 |
| 컨트롤러 버튼 클릭 | 충돌 설정은 맞췄으나 실제로 눌러보지 않음 |
| 조명 세기 | PC 모니터 기준 추정값. Quest 2는 밝기 특성이 다르다 |
| 폰트 크기 · 미러링 가독성 | FR-UI-006. 실기 캡처로 판정해야 한다 |
| 동적 조명 개수 예산 | Stationary 스포트 몇 개까지 감당되는지 (NFR-PERF) |
| 반투명 UI 비용 | 오버드로가 프레임에 미치는 영향 |
| **Quest 2 빌드 자체** | **G1 게이트.** 실패 시 Unity 전환 |
