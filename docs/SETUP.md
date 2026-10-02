# 실행 환경과 시작 방법

BONDI는 AI 제작 환경, Unreal Engine VR 프로젝트, 내부 자료 서버로 나뉩니다. 원본 데이터와 모델 가중치는 저장소에 포함하지 않으므로 clone만으로 전체 파이프라인을 실행할 수는 없습니다.

## 공통 준비

```bash
git lfs install
git clone https://github.com/eunbin-hyun/BONDI.git
cd BONDI
git lfs pull
```

Git LFS 없이 clone하면 `.uasset`, `.umap`, 이미지와 3D 파일이 포인터 텍스트로 내려옵니다.

## AI 형상 복원

### 외부 의존성

- Python과 CUDA를 지원하는 PyTorch 환경
- TRELLIS.2 실행 환경
- PoinTr/AdaPoinTr 원본 저장소
- AdaPoinTr ShapeNet-55 사전학습 가중치
- 완형 3D와 원본 사진

저장소에서 제외한 대표 경로:

| 대상 | 기본 위치 또는 변수 |
| --- | --- |
| 실행 중간 산출물 | `ADAPOINTR_WORK` |
| 원본·완형 자료 | `RESTORE_ROOT` |
| TRELLIS.2 설치 | `TRELLIS2_HOME` |
| AI-Hub 211-2 자료 | `AIHUB_211_2_ROOT` |
| 사전학습·파인튜닝 가중치 | `ai/3d-to-3d-shape/completion/ckpts/` |

### 재현 순서

`ai/3d-to-3d-shape/completion/`에서 실행합니다.

```bash
export ADAPOINTR_WORK="<저장소 밖 작업 폴더>/work"

python scan_dataset.py
python make_pairs.py --per-pattern 20
python train_adapointr.py --epochs 40 --patience 6
python run_71489.py --ckpt ckpts/AdaPoinTr_gupdari_v3.pth --runs 8 --tag _v3tta8
python versions.py --build v22 --measure
```

프로젝트는 CUDA 확장 대신 순수 PyTorch 대체 경로를 사용합니다. 정확한 입력 폴더와 산출물 계약은 [`completion/파이프라인.md`](../ai/3d-to-3d-shape/completion/파이프라인.md)를 먼저 확인하세요.

## 색·질감 복원

`ai/3d-to-3d-color/`에서 유물별 입력 메시와 텍스처를 준비합니다. 기능마다 필요한 Python 패키지와 선택 모델이 달라 전체를 하나의 환경으로 고정하지 않았습니다.

주요 진입점:

| 파일 | 역할 |
| --- | --- |
| `color_match.py` | 사진과 메시의 색 분포 정렬 |
| `relief_maps.py` | 높이·노멀맵 생성 |
| `restore_original_colour.py` | 재질별 손상 색 복원 |
| `segment_masks.py` | SAM 2 기반 보조 마스크 |
| `serve_viewer.py` | 복원 전후 뷰어와 수동 마스크 |

유물별 옵션과 검증값은 [`ai/3d-to-3d-color/README.md`](../ai/3d-to-3d-color/README.md)를 따릅니다.

## Unreal Engine VR

### 필요 환경

- Unreal Engine 5.8.2
- Meta Quest 2
- OpenXR
- SteamVR
- ALVR

### 실행

1. `vr/testproj/testproj.uproject`를 Unreal Engine에서 엽니다.
2. `/Game/XRFramework/Levels/L_Museum`을 시작 맵으로 확인합니다.
3. SteamVR과 ALVR을 실행하고 Quest 2를 연결합니다.
4. Unreal Editor의 VR Preview 또는 패키징 빌드를 실행합니다.

성능 평가는 에디터 VR Preview가 아니라 패키징 빌드에서 수행합니다. ALVR 설정은 [`vr-streaming-setup.md`](vr-streaming-setup.md), 프로젝트 세부 내용은 [`vr/testproj/README.md`](../vr/testproj/README.md)를 참고하세요.

### 공개 배포 전 확인

`MalgunGothic.uasset`에는 Windows 시스템 폰트 글리프가 포함돼 있습니다. 공개 빌드 전 Noto Sans KR 또는 Pretendard처럼 재배포 가능한 폰트로 교체해야 합니다.

## 내부 유물 자료 저장소

Python 3.11 이상과 `uv`가 필요합니다.

```bash
cd infra/web/server
uv sync
uv run python dev.py
```

기본 주소는 `http://127.0.0.1:8412/`입니다. 기본 데이터 위치는 사용자 홈의 `c201-assets/`이며 다음 환경변수로 바꿀 수 있습니다.

- `CATALOG_DB`
- `CATALOG_FILES`
- `CATALOG_PREVIEW`

운영 서버 주소는 `infra/web/.env.example`을 `.env`로 복사해 로컬에서만 설정합니다. `.env`, DB, 프리뷰와 원본 자산은 커밋하지 않습니다.

## 저장소에 포함되지 않는 것

- `.pth`, `.pt`, `.ckpt` 모델 가중치
- 원본 촬영 이미지와 대규모 3D 데이터셋
- AI 중간 산출물과 실험용 `work/`
- Unreal Engine 빌드·캐시 폴더
- 자료 서버 DB, 프리뷰와 배포 비밀값

이 파일이 없으면 해당 기능은 제한적으로만 재현할 수 있습니다.
