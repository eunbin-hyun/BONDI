# vr — BONDI VR 박물관

Unreal Engine 5에서 박물관 공간, 포털 이동, 유물 전시, 정보 UI와 유물 인터랙션을 구현합니다.

## 현재 구성

| 항목 | 값 |
| --- | --- |
| 프로젝트 | [`testproj/testproj.uproject`](testproj/testproj.uproject) |
| 엔진 | Unreal Engine 5.8.2 |
| 시작 맵 | `/Game/XRFramework/Levels/L_Museum` |
| 대상 기기 | Meta Quest 2 |
| XR | OpenXR |
| PC VR | SteamVR + ALVR |
| 입력 | 컨트롤러 기본, 손 추적 지원 |

## 주요 기능

- 실제 크기를 반영한 유물 전시
- 포털 기반 테마 공간 이동
- 유물 잡기, 회전, 복귀
- 손상 상태와 복원 상태 전환
- 거리 기반 정보 패널
- VR 미러 화면과 시연용 안내

## 실행 전

```bash
git lfs install
git lfs pull
```

`.uasset`과 `.umap`은 Git LFS로 관리합니다. LFS 파일이 포인터 상태이면 Unreal Engine에서 프로젝트가 정상적으로 열리지 않습니다.

자세한 시작 방법은 [`../docs/SETUP.md`](../docs/SETUP.md), 체험 구성과 성능 개선은 [`../docs/VR_EXPERIENCE.md`](../docs/VR_EXPERIENCE.md), 프로젝트 내부 기록은 [`testproj/README.md`](testproj/README.md)를 참고합니다.

## 저장소에서 제외하는 것

- `Binaries/`, `Intermediate/`, `Saved/`, `DerivedDataCache/`
- APK와 패키징 결과
- 다시 생성 가능한 캐시와 로그
- 원본 촬영 자료와 미사용 대형 자산

## 공개 배포 주의

프로젝트에 임베드된 맑은 고딕 글리프는 외부 재배포 전에 Noto Sans KR 또는 Pretendard 같은 OFL 폰트로 교체해야 합니다.
