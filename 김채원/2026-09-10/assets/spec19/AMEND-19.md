# 명세 19장 개정안 (AMEND-19) — 회화·경관형 유물 대응

- 제안: 김채원 (AI 트랙)
- 날짜: 2026-09-10
- 대상: `docs/PROJECT_MASTER_SPEC.md` **19장 (635~703행)** · `assets/README.md` · `CONTRIBUTING.md` 10절
- 상태: **초안 — 공세민 결정 대기**
- 근거 자산: `assets/inwangjesaekdo/` (v0.10, 저장소 최초의 완성 번들)

---

## 0. 한 줄 요약

**19장은 "손상된 입체 유물을 복원한다"만 전제한다.**
인왕제색도는 손상되지 않았고, 애초에 입체가 아니다.
유물 유형을 둘로 나누고 파일명·기록 요건을 유형별로 둔다.

---

## 1. 무엇이 안 맞는가 — 실물 근거

19.1은 파일명까지 못 박아 놨다.

```text
master/
├── 1-damaged.glb          # ① 손상 상태
├── 2-model-restored.glb   # ② 모델 복원
└── 3-mcp-restored.glb     # ③ MCP 복원
```

| | 19.1이 요구 | `inwangjesaekdo` 실제 |
|---|---|---|
| ① 손상 상태 | 필수 | **존재하지 않음.** 원화가 손상된 게 아니다. 원화에는 3D 형상 자체가 없다 |
| 단계의 의미 | 복원 진행도 | **해석의 축** — 실측 지형 ↔ 정선이 과장한 지형 |
| 단계 수 | 3 (MCP 실패 시 2) | 2 (`terrain_real` / `terrain_jeong`) |
| 파일 구성 | 단계 1개 = 파일 1개 | **유물 1건이 개체 7종으로 분리** — 지형·나무·기와집·운무·화제·받침 |
| `records/` 예시 | `mcp-prompts.md`, `mcp-log.txt`, `snapshots/` | MCP를 쓰지 않음. 대신 정합·추정·기각 기록 9종 |

**19.1은 "파일 1개 = 단계 1개"를 전제해서 개체 분리를 표현할 자리가 없다.**
그런데 개체 분리는 선택이 아니다 — 나무를 지형 텍스처로 두면 VR에서 납작하게 보이고,
운무를 지형에 굽으면 반투명 처리를 못 한다.

---

## 2. 개정안

### 2-1. `manifest.json` 에 `artifactClass` 추가 (필수 필드)

| 값 | 뜻 | 적용 |
|---|---|---|
| `object` | 손상 복원형 입체 유물 | **현행 19.1 그대로.** `ssu022891` 등 |
| `scene` | 회화·경관형 | 아래 2-2·2-3 규칙 |

> `type` 필드가 이미 있으나 전시 분류용 자유 문자열이라 자산 검사의 분기 조건으로 쓸 수 없다.
> 검사가 읽을 열거형 필드가 따로 필요하다.

### 2-2. `scene` 유형의 파일명 규칙

```text
<part>[-<stage>].glb
```

- `part` — 유물을 이루는 개체. 자유 명명, **`parts_master[]` / `parts_runtime[]` 에 열거 필수**
- `stage` — 같은 part의 해석 단계. 단일이면 생략

```text
master/
├── terrain-real.glb       # part=terrain, stage=real
├── terrain-jeong.glb      # part=terrain, stage=jeong
├── trees.glb              # 단계 없음
├── house.glb
├── fog.glb
├── inscription.glb
└── base.glb
```

> 현재 내 파일명은 언더스코어(`terrain_real.glb`)다. 이 안이 통과하면 **하이픈으로 맞추겠다.**
> 19.1 원문이 `2-model-restored.glb` 처럼 하이픈을 쓰므로 그쪽에 통일하는 게 맞다.

### 2-3. `records/` 요건을 "파일 목록" → "재현에 필요한 근거" 로

**현행 문구의 문제.** 19.1은 `records/` 예시로 `model-restore.json` · `mcp-prompts.md` ·
`mcp-log.txt` · `snapshots/` 를 들고, "**`records/`가 비어 있으면 자산 검사 실패다**" 라고 못 박는다.
그런데 그 예시는 전부 **MCP 복원 전용**이다. MCP를 쓰지 않은 `scene` 유물은
**무엇을 넣어야 통과인지 문서만 봐서는 알 수 없다.**

개정: 유형별 최소 요건 표로 바꾼다.

| `artifactClass` | `records/` 최소 요건 |
|---|---|
| `object` | 현행 유지 — 모델 기록 / MCP 프롬프트 전문·호출 로그·전후 스냅샷 |
| `scene` | ① **관측 근거의 출처·좌표계** ② **사람이 채집한 입력** ③ **추정 파라미터와 그 근거** ④ **기각된 가설** |

`inwangjesaekdo` 의 대응 관계:

| 요건 | 파일 |
|---|---|
| ① 출처·좌표계 | `best_fit.json` (EPSG:5179, 시점 위경도·방위·초점거리·정합 오차) |
| ② 사람이 채집한 입력 | `objects_manifest.json` (나무 168·기와집 2·운무선 61점) |
| ③ 추정 파라미터와 근거 | `distortion_curves.json`, `fog_null.json`, `eye_scan2.json`, `micro_relief.json`, `terrain_uv_extent.json` |
| ④ 기각된 가설 | `tree_refit.json` (시점 오류 가설 기각), `tree_height_check.json` (먹 농도 자동 추출 실패, 상관 0.094) |

> **④를 요건에 넣자는 게 이 개정안의 핵심이다.** 성공한 것만 적으면 그건 근거가 아니라 홍보물이다.
> `NFR-REP-002`(재현성)의 취지에도 실패 기록이 있어야 맞다.

### 2-4. `master/` 폴더명 — 선택 사항

- **문제**: 우리는 최종 프로토타입까지 `dev` 만 쓰는데, 폴더명이 `master` 라 **git 브랜치로 오해된다.**
- **안**: `preservation/` — 국가기록원(NARA)·FADGI 디지털화 표준이 보존용 최고품질본을
  *preservation master* 라 부른다. 문화유산 복원 프로젝트라는 성격과도 맞는다.
- **비용**: 경로 변경 1회. **완성 번들이 아직 1건뿐이라 지금이 가장 싸다.**
- **안 해도 무방**: 각주 한 줄("이 `master`는 git 브랜치와 무관하다")로 갈음 가능.

### 2-5. 부수 정정 (사실관계가 이미 어긋난 곳)

| 위치 | 현재 서술 | 사실 |
|---|---|---|
| 명세 22.3 | "Git LFS — `.gitattributes` 주석 해제 필요" | **2026-09-08 활성화 완료** (`75ef44e`), 한도 10 GB 확인 |
| `assets/README.md` | 2단계(`damaged.glb`/`restored.glb`) + `mcp/` 폴더, 장 번호 21·22장, "아직 LFS 미활성" | 전부 낡음. 현행은 3단계 + `master/`·`runtime/`·`records/`, 19·20장 |
| `CONTRIBUTING.md` 10절 | "**확인 필요.** LFS 활성 여부와 용량 한도를 프로젝트 시작 시점에 확인" | 확인 완료 — 활성, 10 GB |

---

## 3. 영향 범위

- **기존 `ssu022891`(object): 영향 없음.** `artifactClass: "object"` 한 줄만 추가하면 현행 그대로 통과
- **자산 검사 스크립트**: `artifactClass` 분기 추가 필요. 좌표·단위 검사(19.3)는 유형과 무관하므로 그대로
- **`inwangjesaekdo`**: 파일명 하이픈화 1회. 좌표·pivot 계약은 바뀌지 않으므로 **VR 쪽 재작업 없음**

---

## 4. 결정이 필요한 것 (공세민)

1. `artifactClass` 도입 여부 — **가장 중요**
2. `scene` 파일명 규칙 (`<part>[-<stage>].glb`)
3. `records/` 요건을 유형별 최소 요건으로 전환 — 특히 **④ 기각된 가설을 요건에 넣을지**
4. `master/` 개명 여부 (선택)
5. 2-5 부수 정정 반영 (사실관계라 이견 없을 것)

## 5. 결정 전까지 AI 트랙이 할 것

- 현행 폴더 구조(`source`/`master`/`runtime`/`records`)는 **그대로 유지한다.** 혼자 바꾸지 않는다
- `manifest.json` 에 `artifactClass: "scene"` 을 **미리 넣어 두되**, 필수로 취급하지 않는다
- 파일명 하이픈화는 **결정 후** 한 번에 한다 (지금 바꾸면 VR 쪽이 경로를 두 번 고쳐야 한다)
