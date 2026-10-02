# 유물 정보 패널 데이터화 설계

- 작성자: 현은빈 (VR)
- 상태: **제안** — 팀 합의 전
- 관련 명세: 19.1 자산 번들 계약 · 19.2 manifest 필수 필드 · `FR-UI-003~005` · `NFR-ETH-003` · `N-05`
- 관련 직군: **FE**(위젯) · **AI**(유물 데이터) · **Infra**(변환·검사) · **VR**(액터·전환)

## 0. 한 줄 요약

지금 유물 설명 문구가 **위젯 안에 직접 박혀 있다.** 유물이 늘면 위젯을 복제해야 하고,
UI 담당이 유물 데이터까지 관리하게 된다. **문구를 데이터로 빼고 위젯은 하나만 둔다.**

---

## 1. 지금 구조

### 1.1 파일

```text
Content/Museum/UI/
├── WBP_ArtifactInfo.uasset            ← 복원 상태용
└── WBP_ArtifactInfo_Damaged.uasset    ← 손상 상태용
```

두 위젯은 **레이아웃이 완전히 같다.** 다른 것은 안에 적힌 글자뿐이다.

### 1.2 문구가 저장된 위치

위젯의 `TextBlock` 위젯에 직접 입력돼 있다.

| 위젯 | `Text_Title` | `Text_Stage` | `Text_Disclaimer` |
| --- | --- | --- | --- |
| `WBP_ArtifactInfo_Damaged` | 빗살무늬토기 — 손상 상태 | 근거 : 실측 3D 스캔 (관측) | (면책 문구 없음) |
| `WBP_ArtifactInfo` | 빗살무늬토기 — 복원 상태 | 근거 : AI 복원 결과 (추정) | AI 기반 복원 가설입니다… |

### 1.3 무엇이 문제인가

**① 유물이 늘면 위젯이 배수로 늘어난다**

| 유물 수 | 단계 수 | 필요한 위젯 |
| ---: | ---: | ---: |
| 1 (현재) | 2 | 2 |
| 3 (`N-05` MUST) | 3 (`FR-UI-003`) | **9** |

레이아웃을 한 번 고치면 9개를 전부 고쳐야 한다.

**② 직군 경계가 어긋난다**

위젯 안에 든 내용은 UI가 아니라 **유물 데이터**다.

```text
자료 : ssu022891 원본 스캔
상태 : 접합 완형. 파단선과 표면 마모가 남아 있음
크기 : 262 × 383 × 268 mm
알려진 한계 : 외부 문화유산 전문가 검토 없음
```

명세 6.2는 FE를 *"사용자에게 무엇이 보이는가에 대한 책임"* 으로 정의한다.
출처·한계·치수는 AI 직군이 유물을 만들며 기록하는 정보다.
지금 구조로는 **FE가 유물 데이터를 관리**하게 된다.

**③ 명세를 절반만 지키고 있다**

> **`NFR-ETH-003`** 관측과 AI 추정을 **데이터와 UI 양쪽에서** 구분해야 한다

현재는 UI에만 있고 데이터에는 없다. 관측/추정 구분이 사람이 문구를 어느 위젯에 쓰느냐로 결정된다.
유물이 늘면 **잘못 붙일 위험**이 생긴다.

**④ 바이너리 충돌 위험**

`.uasset`은 Git이 병합하지 못한다. 유물 데이터가 위젯 파일 안에 있으면
AI 직군의 내용 수정과 FE의 레이아웃 수정이 **같은 파일에서 충돌**한다.

---

## 2. 바꿀 구조

```text
assets/<artifact-id>/manifest.json     ← AI 직군이 작성 (권위 있는 원본, 명세 19.2)
        │
        ▼  tools/ 변환 스크립트 (Infra, FR-OPS-001)
   ArtifactInfo.csv
        │
        ▼  임포트
   DT_ArtifactInfo  (DataTable)
        │
        ▼  행 조회
   WBP_ArtifactInfo  (위젯 1개)        ← FE: 레이아웃·폰트·대비만
        ▲
        │  SetInfo(행) 호출
   유물 액터                            ← VR: ArtifactId + 현재 단계만 보유
```

**데이터는 아래에서 위로 흐르고, 위젯은 표현만 한다.**

---

## 3. 구조체 `F_ArtifactInfo`

명세 19.2의 manifest 필드를 그대로 옮긴다.

| 필드 | 타입 | 명세 19.2 대응 | 예시 (손상 상태) |
| --- | --- | --- | --- |
| `ArtifactId` | Name | `artifactId` | `ssu022891` |
| `Stage` | Name | `stages[]` | `damaged` |
| `Title` | Text | `title` | 빗살무늬토기 |
| `StageLabel` | Text | — | 손상 상태 |
| **`IsAIInferred`** | **bool** | **`provenance`** | `false` |
| `EvidenceKind` | Text | — | 실측 3D 스캔 (관측) |
| `Description` | Text | `description` | 접합 완형. 파단선과 표면 마모가 남아 있음 |
| `Source` | Text | `source.credit` · `source.license` | ssu022891 원본 스캔 |
| `Limitations` | Text | `limitations[]` | 외부 문화유산 전문가 검토 없음 |
| `Dimensions` | Text | — | 262 × 383 × 268 mm |
| `MeshPath` | SoftObjectPath | — | `/Game/Museum/Artifacts/Pot_Damaged` |
| `MeshScale` | float | — | `0.1` |
| `MeshRollFix` | float | 19.3 좌표 계약 | `90.0` |

### 3.1 `IsAIInferred` 가 핵심이다

관측/추정 구분이 **문구가 아니라 데이터**가 된다.

```text
IsAIInferred = false  →  면책 문구를 Collapsed 로 숨긴다
IsAIInferred = true   →  "AI 기반 복원 가설입니다…" 를 표시한다
```

사람이 매번 판단하지 않으므로 유물이 늘어도 틀릴 수 없다.
`NFR-ETH-003`이 요구하는 **데이터 쪽 구분**이 이것으로 충족된다.

> 우리 빗살무늬토기는 손상 상태가 **실측 스캔**이라 진짜 `observed`다.
> 명세 3장은 ①단계도 생성 모델 결과로 전제하는데, 우리 구성이 근거가 더 강하다.

### 3.2 메시 정보를 함께 넣는 이유

`MeshScale`·`MeshRollFix`는 UI 정보가 아니지만 같이 둔다.
2026-09-03 작업에서 **같은 유물의 GLB와 OBJ가 상하 축·pivot·단위가 전부 달랐다.**

| | 복원후 (GLB) | 복원전 (OBJ) |
| --- | --- | --- |
| 상하 축 | Z-up | **Y-up** |
| pivot | 바닥 | **중앙** |
| 필요한 보정 | 스케일 0.001 | **Roll 90 + 스케일 0.1** |

이 보정값이 지금 블루프린트 안에 하드코딩돼 있다.
유물마다 다르므로 **데이터에 두는 것이 맞다.**

> 명세 19.3이 좌표 계약을 요구하는 이유가 이것이다.
> AI 직군이 내보내기 규약을 통일하면 이 필드는 전부 같은 값이 되고, 나중에 지울 수 있다.

---

## 4. DataTable `DT_ArtifactInfo`

행 키는 `<ArtifactId>_<Stage>` 로 한다.

| Row Name | Title | StageLabel | IsAIInferred | EvidenceKind |
| --- | --- | --- | :---: | --- |
| `ssu022891_damaged` | 빗살무늬토기 | 손상 상태 | `false` | 실측 3D 스캔 (관측) |
| `ssu022891_restored` | 빗살무늬토기 | 복원 상태 | `true` | AI 복원 결과 (추정) |

유물이 3점 3단계가 되면 **행 9개**가 된다. 위젯은 여전히 1개다.

---

## 5. 위젯 변경 — `WBP_ArtifactInfo`

레이아웃은 그대로 두고 **함수 하나만 추가**한다.

```text
SetInfo(Info : F_ArtifactInfo)
    Text_Title       ← Info.Title + " — " + Info.StageLabel
    Text_Stage       ← "근거 : " + Info.EvidenceKind
    Text_Description ← 자료/상태/크기 를 Info 에서 조합
    Text_Limitations ← "알려진 한계 : " + Info.Limitations
    Text_Disclaimer  ← Info.IsAIInferred 이면 Visible, 아니면 Collapsed
```

`WBP_ArtifactInfo_Damaged` 는 **동작 확인 후 삭제**한다.

---

## 6. 액터·전환 로직 변경

### 6.1 유물 액터

```text
변수 : ArtifactId (Name)     ← 예: ssu022891
       CurrentStage (Name)   ← damaged / restored
```

유물별 문구를 들고 있지 않는다. **식별자만** 갖는다.

### 6.2 `BP_StageToggle`

```text
버튼이 눌리면:
    CurrentStage 를 전환한다
    DT_ArtifactInfo 에서 "<ArtifactId>_<CurrentStage>" 행을 찾는다
    ArtifactMesh 에 행의 MeshPath / MeshScale / MeshRollFix 를 적용한다
    패널의 SetInfo(행) 을 호출한다
```

현재 로직과 흐름은 같다. **하드코딩된 값이 행 조회로 바뀔 뿐이다.**

#### 변경 전후

```text
[변경 전]
  if 복원상태:
      SetStaticMesh("/Game/.../Pot_3_Pristine")     ← 경로 하드코딩
      SetRelativeScale3D(0.001)                     ← 값 하드코딩
      SetRelativeRotation(Roll 0)                   ← 값 하드코딩
      Stage_Restored 태그 액터 표시 / Stage_Damaged 숨김
  else:
      SetStaticMesh("/Game/.../Pot_Damaged")
      SetRelativeScale3D(0.1)
      SetRelativeRotation(Roll 90)
      ...

[변경 후]
  Row = DT_ArtifactInfo["<ArtifactId>_<CurrentStage>"]
  SetStaticMesh(Row.MeshPath)
  SetRelativeScale3D(Row.MeshScale)
  SetRelativeRotation(MakeRotator(Row.MeshRollFix, 0, 0))
  Panel.SetInfo(Row)
```

분기가 사라지고 **유물이 늘어도 로직은 그대로**다.

---

## 7. 무엇이 바뀌지 않는가

**화면과 동작은 지금과 동일하다.** 이 변경은 내부 구조만 바꾼다.

| 항목 | 상태 |
| --- | --- |
| 버튼 근접 16cm 전환 | 동일 |
| 손상(회갈색·파단선) ↔ 복원(태토색) | 동일 |
| 잡고 돌린 방향 유지 | 동일 |
| 패널에 보이는 문구 | 동일 |
| 쿨다운 0.8초 | 동일 |

동작이 달라지면 그건 버그다. 작업 후 이 표를 그대로 확인 항목으로 쓴다.

---

## 8. 담당 분리

변경 뒤에는 **아무도 남의 파일을 열지 않는다.**

| 직군 | 소유 파일 | 유물 3점이 되면 |
| --- | --- | --- |
| **AI** | `assets/<id>/manifest.json` | 파일 2개 추가 |
| **Infra** | `tools/` 변환·검사 스크립트 | 변경 없음 |
| **FE (공세민)** | `WBP_ArtifactInfo` **1개** | **변경 없음** |
| **VR (현은빈)** | 유물 액터, `BP_StageToggle`, `DT_ArtifactInfo` 임포트 | 액터 2개 추가 |

`.uasset`은 병합이 안 되므로 **파일 단위 소유가 곧 충돌 방지**다.

---

## 9. 작업 순서

```text
1. F_ArtifactInfo 구조체 생성
2. DT_ArtifactInfo 생성 + 현재 유물 2행 입력
3. WBP_ArtifactInfo 에 SetInfo 함수 추가
4. 유물 액터에 ArtifactId 변수 추가
5. BP_StageToggle 을 행 조회 방식으로 수정
6. VR 에서 7장 확인 항목 전부 점검
7. 통과하면 WBP_ArtifactInfo_Damaged 삭제
```

7번은 **반드시 마지막**에. 되돌릴 여지를 남긴다.

### 예상 작업량

반나절. 새 기능이 없고 기존 값을 옮기는 작업이다.

### 시점

**2점째 유물을 올리기 전에 해야 한다.**

지금은 유물 1점이라 하드코딩이 문제가 안 된다. 그러나 2점째를 하드코딩으로 올리면
그때 만든 것을 버리고 다시 해야 한다. `U-06`(복원 대상 선정)이 정해지면 곧바로 2점째가 들어온다.

---

## 10. 확인이 필요한 것

| 항목 | 확인 대상 | 내용 |
| --- | --- | --- |
| manifest 작성 시점·담당 | **AI 직군** | 명세 19.2 필드를 누가 언제 채우는가 |
| 변환 스크립트 | **Infra** | `manifest.json → CSV → DataTable` 경로를 만들 것인가 |
| 위젯 레이아웃 확정 | **FE** | `SetInfo` 가 채울 `TextBlock` 구성을 먼저 확정해야 함 |
| MCP 구조체 생성 가능 여부 | VR | 안 되면 에디터에서 직접 생성 (5분) |
| 좌표 계약 | **AI + VR** | 19.3 을 실제 값으로 채우면 `MeshScale`·`MeshRollFix` 필드를 없앨 수 있음 |

### 대안 — DataTable 대신 JSON 직접 읽기

언리얼이 `manifest.json` 을 런타임에 직접 파싱하는 방법도 있다.
중간 변환이 없어 원본과 어긋날 일이 없다는 장점이 있지만,

- 에디터에서 내용을 확인·수정하기 어렵다
- 파싱 실패를 런타임에야 알게 된다
- `FR-OPS-002`(검사 실패 자산 차단)를 빌드 전에 걸기 어렵다

**DataTable 쪽을 권한다.** 임포트 시점에 형식 오류가 드러나고, 에디터에서 눈으로 확인된다.

---

## 참고

| 대상 | 위치 |
| --- | --- |
| 작업 배경 | `현은빈/2026-09-03.md` |
| 자산 번들 계약 · manifest 필드 | `docs/PROJECT_MASTER_SPEC.md` 19.1 · 19.2 |
| 좌표·단위 계약 | `docs/PROJECT_MASTER_SPEC.md` 19.3 |
| 바이너리 충돌 방지 | `CONTRIBUTING.md` 10절 |
| 직군 책임 범위 | `docs/PROJECT_MASTER_SPEC.md` 6.2 · 6.3 |
