# 인프라 트랙 전달 — 유물 자산 번들 1호 (인왕제색도 v0.10)

- 전달: 김채원 (AI) → 권영호 (인프라)
- 날짜: 2026-09-10
- **이 전달의 목적은 "언리얼에 넣어 보세요"가 아니다.** 그건 VR 트랙(`HANDOVER_VR.md`)이다.
  인프라에게 필요한 건 **유물 1건이 저장소에 들어가는 표준 형태가 이걸로 확정돼도 되는지**다.

---

## 1. 이게 뭔가

명세 19.1이 말한 디렉터리 계약을 **처음으로 실제 파일로 채운 것**이다.
지금까지 저장소에 `manifest.json`을 가진 유물이 하나도 없었다. 이게 1호다.

```
assets/inwangjesaekdo/
├── source/     원본 입력 1개          4.40 MB
├── master/     감면 전 원본 메시 7개  34.65 MB
├── runtime/    VR 투입용 8개           7.45 MB
├── records/    판단 근거 JSON 9개      0.06 MB
└── manifest.json                      0.01 MB
                                 합계  46.58 MB
```

앞으로 유물이 N건 늘어나면 이 구조가 N번 반복된다. **그래서 지금 확정해야 한다.**

---

## 2. 결정해 줬으면 하는 것 (우선순위)

### 2-1. `master/`를 git에 넣을 것인가 ★ 가장 급함

- `master/`는 감면 전 원본이라 **VR 런타임에는 안 쓴다.** 그런데 전체 용량의 74%다.
- 재현성·재감면을 위해 보관은 해야 하는데, git LFS에 넣으면 **수정할 때마다 새 blob이 통째로 쌓인다.**
  오늘 하루만 해도 지형을 4번 다시 내보냈다. 그때마다 28 MB씩이다.
- LFS 할당량은 `.gitattributes` 커밋(`75ef44e`, 2026-09-08)에서 10 GB로 확인했다.
  단순 나눗셈으로는 유물 214건이지만, **버전 누적 때문에 실제로는 훨씬 빨리 찬다.**

제안(셋 중 골라 주세요):

| 안 | 내용 | 장점 | 단점 |
|---|---|---|---|
| A | master도 LFS에 그냥 넣는다 | 단순 | 할당량이 버전 수에 비례해 녹는다 |
| B | **git에는 `runtime/` + `records/` + `manifest.json`만.** master는 릴리스 아티팩트나 별도 스토리지 | 저장소가 가볍다 (건당 7.5 MB) | 스토리지가 하나 더 생긴다 |
| C | master는 확정본 1개만 태그 시점에 커밋 | 절충 | 규칙을 사람이 지켜야 한다 |

나는 **B**가 맞다고 보는데, 스토리지 비용·구성은 인프라 판단이라 결정을 넘긴다.

### 2-2. `manifest.json` 스키마 확정

지금 최상위 키는 이렇게 넣어 뒀다. **필수/선택을 갈라 주면 그대로 맞추겠다.**

```
artifactId, version, title, description, period, type,
source{kind, credit, license, url, terrain},
stages[{id,label,method,human_in_loop,ai_generated}],
provenance{observed[], ai_inferred[], estimated[]},
limitations[],
runtime{triangles, textures, master_textures, note, budget_spec20},
review{by, at, decision},
coordinate_contract{spec, unit, up_axis, pivot, format, stages_aligned, pivot_offset_...},
parts_master[], parts_runtime[]
```

특히 물어보고 싶은 것:

- `artifactId` — 지금은 작업용 문자열 `inwangjesaekdo`다. **기관 공식 유물 ID 체계를 쓸 건지**, 쓴다면 언제 배정되는지. 지금 폴더명이 곧 ID라서, 나중에 바뀌면 경로가 전부 바뀐다.
- `review.decision` — 지금 `pending`이다. 이 값을 **누가 무엇으로 바꾸는지**(사람 승인 UI인지, PR 승인인지) 정해지면 파이프라인에 반영하겠다.
- `provenance` / `limitations` — AI가 만든 부분과 추정한 부분을 여기 적고 있다. 이게 **화면에 노출되는 값인지 내부 기록인지**에 따라 문장 톤을 바꿔야 한다.

### 2-3. 좌표 계약 검사를 CI에 넣기 (FR-OPS-002)

`scripts/check_coordinate_contract.py` 를 같이 넣었다. 휴리스틱 없이 네 가지만 본다.

```
python check_coordinate_contract.py assets --mode scene
```

- A 포맷 — glTF 2.0 GLB인가
- B 단계 정합 — `terrain_real` ↔ `terrain_jeong` 이 같은 bbox·pivot인가
- C 단위 사고 — 같은 이름 파트의 크기 비가 10배 넘게 벌어지는가 (m/cm 혼동 탐지)
- D pivot — 원점이 bbox 바닥 중심인가

현재 이 번들은 **전부 통과**다. 자산 커밋 시 자동으로 돌게 붙여 주면,
"임포트할 때 스케일이 안 맞더라" 류의 문제가 자산 단계에서 걸린다.

### 2-4. `MeshScale` · `MeshRollFix` 제거 — 인프라·백엔드 동의가 필요

이건 VR 쪽 코드에만 있는 게 아니라 **업로드 경로/데이터 모델에 남는 필드**라 인프라 사안이다.
위 검사가 통과한다는 건 이 두 값이 항상 `1.0` / `0`이라는 뜻이다.
제거 3단계 제안은 현은빈에게 따로 보내고, 스키마 변경 여부는 여기서 합의했으면 한다.

---

## 3. 넣지 않은 것과 그 이유

- **`.blend` 는 안 넣었다.** 작업 파일이라 인프라 저장소에 들어갈 물건이 아니다 (13.2 MB).
  필요하면 `김채원/2026-09-09/assets/inwang_recon_v2.blend` 에 있다.
- **`master/` 는 이 zip에서 뺐다.** 지형 2개가 28 MB라 전달 한도를 넘는다.
  (이게 바로 2-1을 지금 정해야 하는 이유다.) 파일별 크기는 아래와 같다.

  | master 파일 | 크기 |
  |---|---:|
  | terrain_jeong.glb | 14.02 MB |
  | terrain_real.glb | 14.02 MB |
  | inscription.glb | 1.00 MB |
  | trees.glb | 0.48 MB |
  | base.glb | 0.06 MB |
  | fog.glb | 0.05 MB |
  | house.glb | 0.00 MB |

  필요하면 개별로 보내겠다. `manifest.json` 의 `parts_master` 에 면 수·크기가 다 들어 있다.

## 4. 명세 대조 결과 (원문 확인함)

`origin/dev:docs/PROJECT_MASTER_SPEC.md` 19장(635~703행)·20장 원문과 대조했다.

**맞는 것**

| 항목 | 명세 20장 | 이 번들 |
|---|---|---|
| 유물 1점 면 수 | ≤ 30,000 (**W1 실기 측정 전 임시 기준**) | 24,116 ✓ |
| 텍스처 | ≤ 2장, 각 변 ≤ 1024 | 2장 / 1024 ✓ |
| 머티리얼 | ≤ 2 | 2 ✓ |

- **최대 장면 면 수·목표 fps 는 20장에 "미확정"** 으로 남아 있다. 위 24,116은 *유물 1점* 기준이라
  통과지만, **장면 전체 기준이 없어서 나무·운무·받침까지 합친 값이 괜찮은지는 판정할 근거가 없다.**
  실기 측정 때 이 값을 같이 채웠으면 한다.
- 드로우콜 수치는 20장에 없다 (D-29의 "측정할 것" 목록에만 존재).

**안 맞는 것 — 별도 개정안으로 올린다**

19.1은 `master/`·`runtime/` 파일명을 `1-damaged.glb` / `2-model-restored.glb` /
`3-mcp-restored.glb` 로 못 박는다. **인왕제색도에는 "손상 상태"가 없다.**
`records/` 예시도 전부 MCP 복원 전용이라, MCP를 안 쓴 이 번들이 자산 검사를 통과하는지
문서만 봐서는 알 수 없다. → **개정안 초안: `docs/AMEND-19.md`** (공세민 결정 대기)

이 번들의 `manifest.json` 에는 개정안을 선반영해 `artifactClass: "scene"` 을 넣어 뒀다.
**개정 전까지는 선택 필드로 취급**하면 된다. 폴더 구조와 파일명은 **현행 그대로 유지**한다.
- 원화 이미지의 **소장기관 표기·이용조건이 미확인**이다. `source/input.jpg` 가 그 이미지다.
  **확인 전에는 대외 공개물·배포물에 넣지 말 것.** manifest의 `source.license` 에도 그렇게 적어 뒀다.
