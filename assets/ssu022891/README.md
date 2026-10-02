# ssu022891 — 빗살무늬토기

첫 번째 전시 유물. 자산 번들 계약은 `docs/PROJECT_MASTER_SPEC.md` 19.1을 따른다.

## 현재 들어 있는 것

| 단계 | 파일 | 크기 | 원래 파일명 |
| --- | --- | --- | --- |
| ① 손상 | `master/1-damaged.obj` | 22 MB | `Pot_1_Damaged.obj` |
| ② 모델 복원 | `master/2-model-restored.glb` | 13 MB | `Pot_2_ModelRestored.glb` |
| ③ MCP 복원 | `master/3-mcp-restored.glb` | 13 MB | `Pot_3_Pristine.glb` |

## 확인이 필요한 것

**단계 매핑** — 위 표는 원본 파일명의 번호(`Pot_1` / `Pot_2` / `Pot_3`)를 그대로 따랐다.
`Pot_3_Pristine`이 실제로 Blender MCP 산출물인지 **AI 직군 확인이 필요하다.**
2026-09-04 학습 정리의 MCP 복원 대상은 고배(`0c08e232`)였고 이 토기가 아니다.
다르면 파일명을 바로잡는다.

**`1-damaged.obj`가 OBJ다** — 19.3 좌표·단위 계약은 교환 포맷을 **glTF 2.0 GLB**로 정했다.
GLB로 다시 내보내야 한다. 또한 이 OBJ는 Y-up·pivot 중앙이라 GLB(Z-up·바닥 pivot)와 어긋난다.
19.3의 "①②③이 같은 좌표·같은 pivot·같은 크기" 조건을 **현재 만족하지 않는다.**
지금은 앱에서 스케일·회전을 보정하고 있는데, 19.3은 보정 대신 자산을 다시 내보내라고 정하고 있다.

## 아직 없는 것

| 항목 | 담당 | 비고 |
| --- | --- | --- |
| `manifest.json` | AI | 19.2 필수 필드. 하나라도 빠지면 유물 목록에 등록되지 않는다 (`FR-AI-007`, `FR-OPS-002`) |
| `records/` | AI | 비어 있으면 자산 검사 실패다. 재현성의 유일한 근거 |
| `runtime/` | VR | `master`를 경량화한 전시용 |
| `source/` | AI | 입력 사진 또는 실측 스캔 |

## 위치에 대해

공유 스토리지(`U-12`)가 아직 없어 원본을 임시로 저장소에 둔다. 스토리지가 정해지면
`master/`·`source/` 원본은 그쪽으로 옮기고 여기에는 경로만 남긴다 (`FR-OPS-004`).
