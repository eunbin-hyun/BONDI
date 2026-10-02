# BONDI 문서

이 폴더는 최종 구현을 이해하고 재현하는 데 필요한 문서를 먼저 보여 주고, 초기 기획과 연구 과정은 별도로 보존합니다.

## 현행 문서

| 문서 | 내용 | 기준 |
| --- | --- | --- |
| [ARCHITECTURE.md](ARCHITECTURE.md) | 전체 AI·VR·자료 저장소 구성과 데이터 흐름 | 최종 구현 |
| [AI_RESTORATION.md](AI_RESTORATION.md) | 형상·색·질감 복원 방법과 현은빈의 구현 범위 | 최종 코드와 실험 기록 |
| [VR_EXPERIENCE.md](VR_EXPERIENCE.md) | 박물관 공간, Quest 2 연결, 인터랙션과 최적화 | 최종 UE 프로젝트 |
| [VALIDATION.md](VALIDATION.md) | 평가 정의, 결과, 실패 사례와 한계 | 발표 자료 + 최종 검증 |
| [SETUP.md](SETUP.md) | Git LFS, AI, VR, 자료 서버의 최소 실행 절차 | 저장소 현재 상태 |
| [DECISIONS.md](DECISIONS.md) | 프로젝트 진행 중 내린 설계 결정의 시간순 기록 | 역사 기록 |

세부 구현은 다음 문서를 함께 봅니다.

- [`ai/3d-to-3d-shape/README.md`](../ai/3d-to-3d-shape/README.md): 현행 형상 복원 경로와 세 접근의 비교
- [`ai/3d-to-3d-shape/completion/파이프라인.md`](../ai/3d-to-3d-shape/completion/파이프라인.md): 학습, 추론, 메시화 재현 순서
- [`ai/3d-to-3d-color/README.md`](../ai/3d-to-3d-color/README.md): 색·질감 복원과 평가
- [`vr/testproj/README.md`](../vr/testproj/README.md): Unreal Engine 프로젝트 구조와 실기 문제 해결
- [`infra/README.md`](../infra/README.md): 유물 자료 저장소와 배포 구조

## 자료별 우선순위

서로 다른 시점의 수치나 설명이 충돌하면 다음 순서로 판단합니다.

1. `master`의 실행 코드와 구성 파일
2. 각 구현 폴더의 최신 README와 결과 문서
3. 최종 발표 자료
4. `PROJECT_MASTER_SPEC.md`와 `DECISIONS.md`의 초기 계획
5. `Study` 브랜치의 연구 노트

발표 자료는 최종 서비스의 문제 정의와 사용자 경험을 설명하는 기준입니다. 구현 수치와 현재 실행 경로는 발표 이후 갱신된 `master` 문서를 우선합니다.

## Study 브랜치

팀원별 조사와 실험 과정은 제품 코드와 섞지 않고 `Study` 브랜치에 보존합니다. 현은빈의 원본 연구 기록은 [Study/현은빈](https://github.com/eunbin-hyun/BONDI/tree/Study/%ED%98%84%EC%9D%80%EB%B9%88)에서 확인할 수 있습니다.

다음 문서가 현재 형상 복원 경로의 배경이 됐습니다.

- `복원-일반화-로드맵.md`
- `[AI] trellis2-복원-파이프라인-재구성.md`
- `[AI] 2026-09-15-AdaPoinTr-완형검증.md`
- `[수학] 회전대칭-메시-직접-복원.md`
- `[수학] 투창-n-fold-판정.md`
- `[수학] 채움면-매끄럽게-만들기.md`

초기 결론 중 일부는 이후 실험으로 바뀌었습니다. 최종 판단은 [AI_RESTORATION.md](AI_RESTORATION.md)와 `master`의 결과 문서를 기준으로 합니다.

## 초기 기획과 보관 문서

| 문서 | 상태 |
| --- | --- |
| [PROJECT_MASTER_SPEC.md](PROJECT_MASTER_SPEC.md) | 초기 제품 명세. 계획과 요구사항의 변화를 확인하는 역사 자료 |
| [archive/v1.0-unity-PROJECT_MASTER_SPEC.md](archive/v1.0-unity-PROJECT_MASTER_SPEC.md) | Unity·Quest 3 기준으로 작성했다가 폐기한 v1 명세 |
| [proposal_outdoor-architecture-gounsa.md](proposal_outdoor-architecture-gounsa.md) | 고운사 연수전 공간 복원 제안 기록 |

초기 문서의 미확정 항목과 목표 수치는 최종 성과로 인용하지 않습니다.
