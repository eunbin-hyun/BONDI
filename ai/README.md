# ai — BONDI AI 복원 파이프라인

사진과 3D 유물 자료에서 VR 전시용 손상·복원 자산을 만드는 코드와 검증 기록입니다.

## 구성

| 폴더 | 역할 |
| --- | --- |
| [`2d-to-3d/`](2d-to-3d/) | 단일 이미지 3D 생성 모델 비교와 평가 |
| [`3d-to-3d-shape/`](3d-to-3d-shape/) | AdaPoinTr, 회전대칭, 형상 사전을 이용한 결손 형상 복원 |
| [`3d-to-3d-color/`](3d-to-3d-color/) | 색 분포 정렬, 재질 복원, 손상 마스크와 비교 뷰어 |
| `3d-to-3d-yh/` | 별도 형상·재질 복원 실험 |

현행 형상 경로는 `3d-to-3d-shape/completion/`의 AdaPoinTr v3와 v22 메시화입니다. 회전대칭 경로는 대조군과 빈 영역 보완에 사용합니다.

## 전체 흐름

```text
2D 사진
  → TRELLIS.2 손상 상태 3D
  → AdaPoinTr 점군 완성 + 회전 TTA
  → 관측부와 AI 추정부를 나눈 메시
  → 색상·재질 복원
  → assets/ 전시 번들
```

## 저장소에 포함하는 것

- 학습·추론·메시화·평가 스크립트
- 설정과 메타데이터
- 대표 비교 이미지와 측정 결과
- 실패 원인과 적용 범위를 설명하는 문서

## 저장소에서 제외하는 것

| 대상 | 관리 방식 |
| --- | --- |
| 모델 가중치 | 외부 저장소, `.gitignore` |
| 원본 사진·대규모 3D 데이터셋 | 외부 저장소 |
| 학습 쌍과 중간 점군·메시 | `ADAPOINTR_WORK` 등 저장소 밖 작업 폴더 |
| 최종 전시 자산 | 선별해 `assets/<artifact-id>/`에서 관리 |

## 읽는 순서

1. [`../docs/AI_RESTORATION.md`](../docs/AI_RESTORATION.md)
2. [`3d-to-3d-shape/README.md`](3d-to-3d-shape/README.md)
3. [`3d-to-3d-shape/completion/파이프라인.md`](3d-to-3d-shape/completion/파이프라인.md)
4. [`3d-to-3d-shape/completion/결과.md`](3d-to-3d-shape/completion/결과.md)
5. [`3d-to-3d-color/README.md`](3d-to-3d-color/README.md)

실행 환경과 외부 의존성은 [`../docs/SETUP.md`](../docs/SETUP.md), 평가 정의는 [`../docs/VALIDATION.md`](../docs/VALIDATION.md)를 참고합니다.
