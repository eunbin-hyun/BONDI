# TRELLIS.2 2D to 3D 세팅 — 사진 한 장으로 3D 만들기 (Windows, 8GB 노트북 기준)

- 작성자: 현은빈
- 확인일: 2026-09-04
- 학습 주제: 단일 이미지 → 3D 생성 모델의 VRAM 요구사항 조사, 8GB 노트북에서 돌아가는 경로 선정, TRELLIS.2 Windows 설치 및 첫 실행 오류 해결
- 기준 PC: SAMSUNG 960XGL · RTX 4070 Laptop (8GB) · RAM 64GB · Windows 11
- 상태: **TRELLIS.2 파이프라인 로딩까지 성공, 실제 생성은 미검증**

관련 문서: [2026-09-04 SAM 3D Objects 검토](%5BAI%5D%202026-09-04-SAM3D-8GB-%EA%B2%80%ED%86%A0.md) · [TRELLIS.2 모델 구조 학습 정리](%5BAI%5D%20trellis2-%EB%AA%A8%EB%8D%B8-%EA%B5%AC%EC%A1%B0.md) · [2026-09-03 복원 유물 반입 — GLB 스케일/축 문제](%5BVR%5D%202026-09-03-Quest2-%EC%97%B0%EA%B2%B0%EA%B3%BC-%EB%B3%B5%EC%9B%90%ED%86%A0%EA%B8%80.md)

## 0. 결론 요약

전시실에 올릴 복원 유물 3D를 사진에서 뽑을 수 있는지 알아봤다. TRELLIS 계열 두 버전을 VRAM 8GB 기준으로 비교한 결론은 아래와 같다.

| 모델 | 공식 요구 VRAM | 8GB에서 | 판단 |
| --- | --- | --- | --- |
| TRELLIS v1 (Microsoft) | 16GB (fp32) | Windows 포크 fp16 모드로 가능 | 2순위 |
| **TRELLIS.2** (Microsoft) | 24GB | Windows 포크 v22가 **8GB 명시 지원** | **1순위, 설치 완료** |

핵심 수확 세 가지.

1. **"fp16이면 8GB로는 안 되지 않나"는 거꾸로 이해한 것이었다.** 16GB 요구는 fp32 기준이고, fp16이 바로 8GB에 들어가게 만드는 수단이다.
2. **8GB 카드의 OOM 보고 중 일부는 VRAM 부족이 아니라 빌드 버그였다.** 오류 메시지만 보고 원인을 단정하면 틀린다.
3. **첫 실행 오류도 메시지가 가리킨 곳이 원인이 아니었다.** opencv-contrib를 깔라고 했지만 실제 원인은 opencv 5.0 빌드에 OpenEXR이 빠진 것이었다.

---

## 팀원용 — TRELLIS.2 웹 UI 환경 설정 (Windows, NVIDIA 8GB 이상)

각자 노트북에서 브라우저로 사진 → 3D GLB를 뽑을 수 있게 하는 절차다. CUDA 툴킷, Visual Studio, 관리자 권한 전부 필요 없다.

### 링크

| 용도 | 링크 |
| --- | --- |
| **설치 zip (v22, 736MB)** | https://github.com/IgorAherne/TRELLIS.2-stableprojectorz/releases/tag/latest |
| 포크 저장소 (README, 이슈) | https://github.com/IgorAherne/TRELLIS.2-stableprojectorz |
| TRELLIS.2 원본 (Microsoft, MIT) | https://github.com/microsoft/TRELLIS.2 |
| TRELLIS.2-4B 가중치 (자동 다운로드됨) | https://huggingface.co/microsoft/TRELLIS.2-4B |
| GPU가 더 작거나 v22가 안 될 때 — TRELLIS v1 포크 (fp16, 311MB) | https://github.com/IgorAherne/trellis-stable-projectorz/releases/tag/latest |

### 절차

1. 위 릴리스 페이지에서 `trellis2-stableprojectorz_v22.zip`을 받아 **한글과 공백이 없는 경로**에 푼다. 예: `C:\ai\trellis2`. 파이썬 도구가 한글 경로에서 자주 깨진다.
2. **첫 실행 전에** `code\install.py`를 메모장으로 열어 284행 근처의 `"opencv-python-headless",`를 아래처럼 바꾼다. 안 바꾸면 4.3에서 설명한 EXR 로딩 오류가 그대로 난다.

   ```python
   "opencv-python-headless==4.11.0.86",
   ```

   이미 실행해서 오류를 봤다면 압축 푼 폴더에서 아래 한 줄로 고칠 수 있다.

   ```text
   code\venv\Scripts\python.exe -m pip install --no-cache-dir "opencv-python-headless==4.11.0.86"
   ```

3. Quest Link, Unreal 에디터, GPU 가속 브라우저 탭을 닫는다. 작업 관리자 > 성능 > GPU에서 전용 GPU 메모리가 1GB 이하인지 확인.
4. `run-gradio.bat` 더블클릭. 첫 실행은 의존성 설치와 4B 가중치 다운로드로 **20~30분**, 디스크 약 20GB. 콘솔의 Triton 오류는 무시해도 된다고 작성자가 명시했다.
5. 콘솔에 `Running on local URL: http://127.0.0.1:7860`이 뜨면 브라우저로 연다.
6. 배경 제거된 단일 오브젝트 PNG를 올리고, 해상도 512로 먼저 성공을 확인한 뒤 1024로 올린다.
7. GLB로 내보내 UE5 콘텐츠 브라우저에 드래그. 스케일과 축(Y-up / Z-up)은 [09-03 문서](%5BVR%5D%202026-09-03-Quest2-%EC%97%B0%EA%B2%B0%EA%B3%BC-%EB%B3%B5%EC%9B%90%ED%86%A0%EA%B8%80.md)의 3.2, 3.3 참고.

### 주의

- `update.bat`은 설치를 깨뜨린다는 보고가 있어 작성자가 주의하라고 했다. **누르지 말 것.**
- 다중 이미지 입력은 8GB에서 OOM 보고가 있다. 1장씩만.
- 설치가 꼬이면 `code\trellis2_init_done.txt`와 `code\venv` 폴더를 지우고 다시 `run-gradio.bat`을 실행하면 처음부터 재설치된다. 이때 2번의 install.py 수정이 되어 있어야 한다.
- GPU가 RTX 20 시리즈 이하거나 VRAM이 6GB면 v22가 안 될 수 있다. 그때는 표의 TRELLIS v1 포크를 받아 `run-gradio-fp16.bat`으로 실행.

---

## 1. 이 노트북 사양

| 항목 | 값 |
| --- | --- |
| GPU | NVIDIA RTX 4070 Laptop, **VRAM 8GB** (드라이버 591.74) |
| iGPU | Intel Arc Graphics |
| CPU | Intel Core Ultra 9 185H (16코어 / 22스레드) |
| RAM | 64GB |
| 디스크 여유 | 약 480GB |
| OS | Windows 11 |

VRAM 8GB가 유일한 병목이다. 나머지는 전부 여유가 있다.

한 가지 더. **Meta Quest Link 드라이버(Meta Virtual Monitor)가 항상 VRAM을 점유한다.** 생성 모델을 돌릴 때는 Quest 관련 앱을 끄고 시작해야 한다.

---

## 2. TRELLIS v1 — fp16이 8GB를 만드는 이유

### 2.1 공식 요구사항

[microsoft/TRELLIS](https://github.com/microsoft/TRELLIS) README 기준 VRAM 16GB 이상, Linux 검증. Windows는 "완전히 테스트되지 않음".

### 2.2 Windows 포크 — trellis-stable-projectorz

[IgorAherne/trellis-stable-projectorz](https://github.com/IgorAherne/trellis-stable-projectorz). StableProjectorz라는 AI 텍스처링 툴에 붙이려고 만든 포크인데 단독으로 쓸 수 있다.

- Windows 원클릭 설치기. Python 3.11, PyTorch 2.7, CUDA 12.8을 통째로 묶어서 CUDA 툴킷, Visual Studio, 관리자 권한이 필요 없다.
- `float32 → float16`, `int64 → int32` 변경으로 **"8GB 카드에 전체 알고리즘이 들어간다"**고 명시.
- `run-gradio-fp16.bat`으로 실행.

### 2.3 fp16이 왜 8GB를 만드는가

처음에는 "8GB인데 fp16이면 안 되지 않나"라고 생각했다. 반대였다.

| 항목 | fp32 (원본) | fp16 (포크) |
| --- | --- | --- |
| TRELLIS-image-large 가중치 (1.2B) | 약 4.8GB | 약 2.4GB |
| DINOv2-L 이미지 인코더 (약 0.3B) | 약 1.2GB | 약 0.6GB |
| SLAT 디코딩 인덱스 텐서 | int64 | int32 (절반) |
| 활성값 + 렌더러 작업 메모리 | 수 GB | 대략 절반 |

fp32는 가중치만 6GB를 먹고 여기에 디코딩 활성값이 얹히니 16GB가 필요했다. 가중치를 반으로, 인덱스를 반으로 줄이면 피크가 8GB 근처로 내려온다. 그래서 **16GB 요구 = fp32 기준, fp16 = 8GB에 넣는 수단**이다.

### 2.4 8GB OOM 보고는 VRAM 부족이 아니었다

포크 [이슈 #2](https://github.com/IgorAherne/trellis-stable-projectorz/issues/2)에서 RTX 2070 Super(8GB), 2080 Ti(11GB) 사용자들이 "1849GiB 할당 시도" 같은 오류를 봤다. 숫자부터 말이 안 된다.

원인은 **가우시안 래스터라이저 CUDA 휠이 RTX 20 시리즈 아키텍처(sm_75) 없이 컴파일된 빌드 버그**였다. 작성자가 아키텍처를 추가해 v18에서 고쳤다. 실패자가 전부 RTX 2000 시리즈였던 것이 단서였다.

RTX 4070 Laptop은 Ada(sm_89)라 이 문제와 무관하다.

### 2.5 8GB에서 붙는 조건

- **이미지 1장만.** [이슈 #33](https://github.com/IgorAherne/trellis-stable-projectorz/issues/33)에서 단일 이미지는 성공, 다중 이미지 컨디셔닝은 OOM.
- **배경 제거된 단일 오브젝트 PNG.** 배경이 남으면 복셀 수가 폭증한다. 자동 배경 제거가 있지만 미리 투명 PNG로 주는 게 안전하다.
- **Windows 오버헤드 0.5~1GB.** 데스크톱 합성과 Quest Link 드라이버가 항상 점유해서 실제 가용은 7GB 정도다. 대신 NVIDIA Windows 드라이버는 VRAM이 넘치면 시스템 RAM으로 넘겨서(sysmem fallback) 크래시 대신 느려진다. 경계선에서 "죽지 않고 오래 걸리는" 쪽으로 빠진다.
- **메시 추출(GLB)이 가장 무거운 단계.** 가우시안 PLY만 뽑으면 훨씬 가볍다.

---

## 3. TRELLIS.2 — 최종 선택

v1 포크 릴리스 노트 끝에 "더 좋은 Trellis.2 설치기가 있다"고 적혀 있어서 그쪽으로 갔다.

### 3.1 TRELLIS.2 공식

[microsoft/TRELLIS.2](https://github.com/microsoft/TRELLIS.2). 4B 파라미터, O-Voxel 표현, 512³~1536³ 해상도, **PBR 텍스처 메시(base color / roughness / metallic / opacity) GLB 출력**. MIT 라이선스.

- 공식 요구 VRAM 24GB, A100/H100 검증, Linux 전용.
- H100 기준 512³ 약 3초, 1024³ 약 17초.

모델 구조는 [학습 정리 문서](%5BAI%5D%20trellis2-%EB%AA%A8%EB%8D%B8-%EA%B5%AC%EC%A1%B0.md)에 따로 정리했다.

### 3.2 Windows 포크 — TRELLIS.2-stableprojectorz v22

[IgorAherne/TRELLIS.2-stableprojectorz](https://github.com/IgorAherne/TRELLIS.2-stableprojectorz/releases/tag/latest). 2026-04-06 릴리스.

> A simple installer for TRELLIS 2, that works on windows and **8GB nvidia gpus**.

README: "8GB GPU에 맞게 최적화, **1024³ 복셀에서도**".

- zip 736MB. Python 3.11, PyTorch 2.8.0, CUDA 12.8 번들.
- `run-gradio.bat` 하나로 설치 + 실행. 첫 실행에 의존성 설치와 TRELLIS.2-4B 가중치 다운로드.
- `update.bat`은 설치를 깨뜨린다는 보고가 있어 작성자가 주의하라고 명시. **누르지 말 것.**
- 콘솔의 Triton 오류는 무시하라고 명시.

v1 대신 이걸 고른 이유: 8GB를 이름이 아니라 릴리스 노트에서 명시했고, 결과물이 PBR 텍스처 메시라 언리얼에 바로 쓸 수 있고, MIT 라이선스다.

---

## 4. 설치와 첫 실행 오류 — EXR 로딩 실패

### 4.1 증상

`run-gradio.bat` 첫 실행. 의존성 설치, DINOv3와 RMBG-2.0 로컬 모델 로딩, TRELLIS.2 파이프라인 로딩까지 통과한 뒤 환경맵 로딩에서 죽었다.

```text
[WORKER] Pipeline loaded, loading environment maps...
RuntimeError: Failed to load '...\code\assets\hdri\forest.exr'. File exists: True.
OpenCV may lack OpenEXR support — try: pip install opencv-contrib-python
```

### 4.2 진단

오류 메시지는 opencv-contrib 설치를 권했다. 코드를 먼저 봤다.

```python
# code/pipeline_worker.py
os.environ['OPENCV_IO_ENABLE_OPENEXR'] = '1'   # 86행 — 이미 켜져 있다
...
raw = cv2.imread(exr_path, cv2.IMREAD_UNCHANGED)   # 118행
```

OpenCV는 보안상 EXR 읽기를 기본 비활성화하는데, 이 코드는 이미 환경변수로 켜고 있었다. 그러면 남은 가능성은 빌드 자체에 OpenEXR이 없는 것.

```text
$ pip list | grep opencv
opencv-python-headless  5.0.0.93

$ python -c "import cv2; print(cv2.getBuildInformation())" | grep OpenEXR
OpenEXR:                     NO
```

**원인은 opencv-python-headless 5.0.0.93 빌드에 OpenEXR이 빠진 것.** `code/install.py` 284행이 버전을 고정하지 않아 pip이 최신 5.0을 받아왔다. 4.x 계열 휠은 OpenEXR을 포함한다.

### 4.3 해결

```text
venv\Scripts\python.exe -m pip install --no-cache-dir "opencv-python-headless==4.11.0.86"
```

교체 후 확인.

```text
4.11.0
forest.exr loaded: True (512, 1024, 3)
OpenEXR:                     build (ver ...)
```

재초기화 시 반복되지 않도록 `code/install.py` 284행도 고정했다. 원본은 `install.py.bak`.

```python
"imageio", "imageio-ffmpeg", "tqdm", "easydict", "opencv-python-headless==4.11.0.86",
```

### 4.4 배운 것

오류 메시지가 제시하는 해결책은 **작성자가 예상한 원인**이다. 실제 원인이 다르면 그대로 따라 해도 안 된다. 메시지가 가리킨 코드 줄부터 읽고, 그 코드가 전제하는 조건(환경변수, 빌드 옵션)을 하나씩 확인하는 쪽이 빨랐다.

---

## 5. 실행 전 체크리스트

1. Meta Quest Link, Meta Virtual Monitor, Unreal 에디터, GPU 가속 브라우저 탭 종료.
2. 작업 관리자 > 성능 > GPU에서 "전용 GPU 메모리" 1GB 이하 확인.
3. `run-gradio.bat` 실행 → `http://127.0.0.1:7860`.
4. 입력은 배경 제거된 단일 오브젝트 투명 PNG.
5. 첫 시도는 해상도 512로 성공 확인 후 1024로 올린다. OOM이 나면 512로 내리는 것이 유일한 조정 손잡이.
6. GLB로 내보내 UE5 콘텐츠 브라우저에 드래그. 09-03에 겪은 **스케일 1000배 / Y-up vs Z-up 문제**를 임포트 옵션에서 미리 확인.

---

## 6. 다음 할 일

- [ ] 실제 생성 1회 성공 여부 확인, 512와 1024 각각 VRAM 피크와 소요 시간 기록
- [ ] 복원 유물 사진(배경 제거)으로 생성 → 전시실 반입 → 기존 GLB 자산과 품질 비교
- [ ] 실패 시 TRELLIS v1 포크 `run-gradio-fp16.bat`으로 내려가서 재시도

---

## 7. 참고 링크

- TRELLIS v1: [microsoft/TRELLIS](https://github.com/microsoft/TRELLIS) · [Windows 포크](https://github.com/IgorAherne/trellis-stable-projectorz) · [이슈 #2 빌드 버그](https://github.com/IgorAherne/trellis-stable-projectorz/issues/2)
- TRELLIS.2: [microsoft/TRELLIS.2](https://github.com/microsoft/TRELLIS.2) · [Windows 포크 v22](https://github.com/IgorAherne/TRELLIS.2-stableprojectorz/releases/tag/latest) · [TRELLIS.2-4B 모델](https://huggingface.co/microsoft/TRELLIS.2-4B)
