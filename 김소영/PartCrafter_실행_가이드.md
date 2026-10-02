# PartCrafter 설정 및 실행

## 사용 목적

PartCrafter는 사진 한 장에서 여러 파트로 분리된 3D 메쉬 후보를 생성한다. TRELLIS가 만든 전체 형상과 비교하고, 유물의 파트 구조 가설을 검토하기 위해 사용한다.

기존 TRELLIS 메쉬를 분할하거나 결손부를 정답대로 복원하는 모델은 아니다. 생성된 파트의 위치와 형태는 별도로 검증해야 한다.

## 1. 요구 환경 확인

- Windows
- NVIDIA GPU VRAM 8GB 노트북에서 시험한 설정 (모든 입력·옵션의 실행을 보장하지 않음)
- Git
- uv

PowerShell에서 GPU를 확인한다.

```powershell
nvidia-smi
```

Git 또는 uv가 없다면 설치한다.

```powershell
winget install --id Git.Git -e
winget install --id astral-sh.uv -e
```

## 2. 소스 코드 받기

```powershell
cd C:\SSAFY\AI-PJ
git clone https://github.com/wgsxm/PartCrafter.git partcrafter
cd .\partcrafter
git checkout 3d773bf02fad51c7ab31a5615573fec93b287b30
```

`C:\SSAFY\AI-PJ\partcrafter`가 이미 있으면 `git clone`은 생략한다.

## 3. Python 환경 구성

```powershell
uv python install 3.11
uv venv --python 3.11 --python-preference only-managed .venv
```

PyTorch CUDA 버전을 설치한다.

```powershell
uv pip install --python .venv\Scripts\python.exe `
  torch==2.5.1 torchvision==0.20.1 `
  --index-url https://download.pytorch.org/whl/cu124
```

추론에 필요한 패키지를 설치한다.

```powershell
uv pip install --python .venv\Scripts\python.exe `
  diffusers==0.33.1 transformers==4.51.3 peft==0.15.2 `
  accelerate einops trimesh omegaconf scikit-image `
  numpy==1.26.4 "opencv-python<4.12" pillow "huggingface-hub<1" scipy
```

CUDA 연결을 확인한다.

```powershell
.\.venv\Scripts\python.exe -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
```

`True`와 GPU 이름이 출력되어야 한다.

## 4. Windows 추론용 파일 확인

수정본은 공식 저장소에 게시된 커밋이 아니라 로컬 변경이다. 이 문서와 함께 제공하는 [Windows 저메모리 추론 패치](patches/partcrafter-windows-laptop.patch)를 사용한다. 기준 공식 커밋은 `3d773bf02fad51c7ab31a5615573fec93b287b30`이다.

패치는 실행 스크립트 추가, 추론 시 불필요한 의존성 로딩 조정, 메시 추출 오류 출력 및 dtype 처리 변경을 포함한다. 기존 작업 폴더가 아닌 위에서 새로 복제한 폴더에 적용한다.

패치 파일을 저장한 실제 경로로 다음 변수를 바꾼다.

```powershell
$patchPath = "C:\SSAFY\RecoverRelic\김소영\patches\partcrafter-windows-laptop.patch"
git apply --check $patchPath
git apply $patchPath
```

이미 수정된 로컬 프로젝트에는 중복 적용하지 않는다. 스터디에 올릴 때 이 문서와 `patches/` 폴더를 함께 올린다. 패치 적용 확인은 추론 품질 보증과 별개다.

## 5. 입력 이미지 준비

71489 시험 이미지는 아래 위치에 둔다.

```text
C:\SSAFY\AI-PJ\partcrafter\inputs\71489_composite.png
```

파일이 없다면 원본을 복사한다.

```powershell
New-Item -ItemType Directory -Force .\inputs
Copy-Item -LiteralPath "원본_이미지_경로" -Destination ".\inputs\71489_composite.png"
```

현재 시험 스크립트의 크롭 좌표는 확인된 1280×480 합성 이미지 전용이다.

## 6. 실행

### 기본 실행

```powershell
cd C:\SSAFY\AI-PJ\partcrafter

$env:HF_HUB_DISABLE_XET = "1"
$env:HF_HUB_DOWNLOAD_TIMEOUT = "300"

.\.venv\Scripts\python.exe .\scripts\test_laptop.py `
  --source ".\inputs\71489_composite.png" `
  --output "results\71489_p2_d8" `
  --num-parts 2 `
  --num-tokens 512 `
  --dense-depth 8 `
  --hierarchical-depth 9
```

첫 두 줄은 실행 위치와 가중치 다운로드 방식을 설정한다.

- `cd`: PartCrafter 프로젝트 폴더로 이동한다.
- `HF_HUB_DISABLE_XET=1`: Hugging Face 가중치를 일반 HTTP 방식으로 받는다.
- `HF_HUB_DOWNLOAD_TIMEOUT=300`: 파일 응답 제한 시간을 300초로 설정한다.

가중치가 없으면 최초 실행에서 자동으로 다운로드한다. 이후에는 받은 파일을 재사용한다.

### 실행 옵션

| 옵션 | 의미 |
|---|---|
| `--source` | 입력 이미지 경로. 현재 스크립트는 1280×480 합성 이미지에서 71489 사진 영역을 자동으로 자른다. |
| `--output` | 결과를 저장할 폴더. 프로젝트 폴더를 기준으로 생성된다. |
| `--num-parts 2` | 생성할 파트 수를 2개로 지정한다. 모델이 파트 수를 자동 판정하는 값이 아니다. |
| `--num-tokens 512` | 파트 하나의 형상 표현에 사용하는 토큰 수다. 높이면 표현 용량과 메모리 사용량이 증가하지만 형상 품질이나 올바른 파트 분할이 보장되지는 않는다. |
| `--steps 50` | 노이즈에서 형상을 생성하는 반복 횟수다. 기본값이 50이라 명령에서 생략했다. |
| `--seed 0` | 난수 초기값이다. 같은 입력과 설정에서 결과를 재현할 때 사용하며 기본값은 0이다. |
| `--dense-depth 8` | 초기 표면 탐색 해상도다. 축당 약 256개 지점에서 표면 후보를 찾는다. |
| `--hierarchical-depth 9` | 표면 주변을 한 단계 더 세밀하게 추출한다. 높이면 메쉬가 세밀해지지만 메모리 사용량이 증가한다. |

### 실행 과정

스크립트는 다음 순서로 동작한다.

1. 합성 이미지에서 71489 원본 사진만 자른다.
2. RMBG 모델로 배경을 제거하고 `input.png`를 만든다.
3. 이미지를 특징 벡터로 변환한다.
4. PartCrafter가 지정된 파트 수만큼 3D 잠재 형상을 생성한다.
5. 잠재 형상을 옥트리로 탐색해 메쉬로 변환한다.
6. 파트별 GLB와 모든 파트를 포함한 `object.glb`를 저장한다.
7. 설정·실행시간·최대 VRAM·오류를 `manifest.json`에 기록한다.

모델은 실행 중 자동으로 CPU 오프로딩과 FP16을 사용한다. 사용자가 별도 옵션을 줄 필요는 없다.

### 설정을 바꿔 실행하기

파트 수를 3개로 시험할 때는 기존 결과를 덮어쓰지 않도록 출력 폴더도 바꾼다.

```powershell
.\.venv\Scripts\python.exe .\scripts\test_laptop.py `
  --source ".\inputs\71489_composite.png" `
  --output "results\71489_p3_d8" `
  --num-parts 3 `
  --num-tokens 512 `
  --dense-depth 8 `
  --hierarchical-depth 9
```

같은 설정에서 다른 생성 후보를 만들려면 `--seed`와 출력 폴더를 함께 바꾼다.

```powershell
.\.venv\Scripts\python.exe .\scripts\test_laptop.py `
  --source ".\inputs\71489_composite.png" `
  --output "results\71489_p2_seed1" `
  --num-parts 2 `
  --num-tokens 512 `
  --seed 1 `
  --dense-depth 8 `
  --hierarchical-depth 9
```

`--num-parts`는 정답 부위 수가 아니라 생성 가설이다. 우선 2파트로 실행하고, 필요한 경우 3파트 결과와 비교한다.

## 7. 성공 여부 확인

```powershell
Get-Content .\results\71489_p2_d8\manifest.json
Get-ChildItem .\results\71489_p2_d8\*.glb
```

결과 폴더의 파일은 다음과 같다.

| 파일 | 내용 |
|---|---|
| `photo_crop.png` | 합성 이미지에서 잘라낸 원본 사진 |
| `input.png` | 배경 제거 후 모델에 입력된 이미지 |
| `part_00.glb`, `part_01.glb` | 각각 생성된 파트 메쉬 |
| `object.glb` | 생성된 파트를 같은 좌표에 배치한 통합 파일 |
| `manifest.json` | 입력·설정·상태·실행시간·VRAM·오류 기록 |

성공 조건은 다음과 같다.

- `manifest.json`의 `status`가 `complete`
- `part_00.glb`, `part_01.glb`, `object.glb`가 존재

`status`가 `failed`이면 콘솔의 `Mesh extraction failed` 메시지와 `manifest.json`의 `error`를 확인한다.

## 8. Blender 확인

1. Blender에서 `File > Import > glTF 2.0`을 선택한다.
2. `C:\SSAFY\AI-PJ\partcrafter\results\71489_p2_d8\object.glb`를 연다.
3. Outliner에서 `part_00`, `part_01`을 번갈아 숨겨 파트 분리 상태를 확인한다.

`object.glb`가 없으면 메쉬 생성에 실패한 것이다.

## 메모리 부족 시

`CUDA out of memory` 오류가 발생할 때만 `--num-tokens 512`를 `384`로 낮춘다. 첫 시험의 최대 VRAM 사용량은 약 3.1GB였다.

