# 작업 전·후 확인표 (AI 트랙)

> 팀 규칙에서 뽑은 것만 적었다. 출처를 옆에 달아 뒀으니 의심되면 원문을 봐라.
> 갱신: 2026-09-10

---

## 0. 브랜치 — 어디에 올릴 것인가 ★ 제일 먼저

| 브랜치 | 용도 | 올리는 것 |
|---|---|---|
| **dev** | **실제 작업. 협업은 전부 여기서** | 자산 번들 `assets/<artifact-id>/`, 스크립트, 명세·인계 문서, UE 프로젝트 |
| **Study** | **"무엇을 공부했는지" 기록 전용. 협업 없음** | 학습 정리 `.md` + `images/`. 포지션별 협업 방침, LFS 설치법, 명령어 정리 |

- **산출물 파일(.glb/.blend/텍스처)을 Study에 올리지 않는다.** 팀원이 보는 곳이 아니고,
  Study의 `.gitattributes` 는 dev와 달라서 LFS도 안 탄다
- dev 에는 직접 push 하지 않는다. `feat/...` · `docs/...` 브랜치를 따서 MR
- Study 규칙: `김채원/YYYY-MM-DD/` 폴더에 `YYYY-MM-DD.md` + `images/`,
  커밋 메시지 `docs(study): ...`

---
## A. 저장소 — 클론했거나 새 PC에서 처음 만질 때

```bash
git lfs install
git config lfs.https://lab.ssafy.com/s15-ai-image-sub1/S15P21C201.git/info/lfs.locksverify true
```

- `git lfs install` 을 **안 하면 에셋이 포인터 텍스트로 내려와 언리얼에서 안 열린다.**
  ("파일은 있는데 언리얼이 못 읽어요" 증상의 90%가 이거다) — `.gitattributes` 주석
- `locksverify true` 는 **남이 잠근 파일을 내가 덮어쓰고 push 하는 걸 서버가 막아준다.**
  안 켜면 잠금이 '권고'로만 작동한다 — 공세민, 2026-09-09 11:59

LFS 추적 대상 — **dev 브랜치의 `.gitattributes`** (2026-09-08 활성 · 한도 10 GB):

```
*.uasset *.umap                          ← lockable (아래 B 참조)
*.fbx *.glb *.gltf *.obj *.ply *.stl *.psd *.wav *.ttf *.otf
*.png *.jpg *.jpeg *.tga *.exr *.hdr     ← 09-08 추가
```

`git lfs install` 과 `locksverify` 는 **컴퓨터·저장소 설정**이라 브랜치와 무관하다.
그런데 **`.gitattributes` 는 브랜치마다 다른 파일이다.** 위 목록은 dev 것이고,
Study 에는 없다 — 그래서도 산출물은 dev 에만 올린다 (0장).

**내가 내보내는 `.glb` · `.png` 는 dev 에서 전부 LFS로 간다.** 다시 내보낼 때마다
같은 크기의 blob이 새로 쌓이므로, **형상이 굳은 뒤에 커밋한다.** 지형 하나가 14 MB다.

---

## B. 언리얼 — `vr/testproj` 를 열 때

**직접 열어서 바로 작업하지 않는다. 로컬에 따로 복사해 백업본에서 작업하고,
완료된 것만 저장소에 반영한다.** — 공세민, 2026-09-09 13:30

| 항목 | 값 |
|---|---|
| 엔진 | UE **5.8.2** |
| 시작 맵 | `/Game/XRFramework/Levels/L_Museum` |
| 게임모드 · Pawn | `BP_XRGameMode` · `BP_XRPawn` |
| 대상 기기 | Oculus Quest 2 (`D-44`) |

`.uasset` · `.umap` 은 `lockable` 이라 **읽기 전용으로 내려온다.** 편집하려면 먼저 잠근다.

```bash
git lfs lock   vr/testproj/Content/Museum/Blueprints/BP_StageToggle.uasset
git lfs unlock vr/testproj/Content/Museum/Blueprints/BP_StageToggle.uasset
```

- `.uasset` · `.umap` 은 **Git이 병합할 수 없다.** 두 명이 같은 레벨·블루프린트를 동시에 만지면
  한쪽 작업이 통째로 사라진다 — CONTRIBUTING 10절
- 편집 전 팀 채널에 대상 파일을 공지하거나 `git lfs lock` 을 건다
- 충돌이 나면 **병합하지 말고** 어느 쪽을 쓸지 담당자끼리 정한 뒤 한쪽을 다시 적용한다
- 에셋 변경이 포함된 MR에는 **변경 전후 스크린샷이나 짧은 영상**을 첨부한다

### 임포트할 때 걸리는 함정

| 증상 | 원인 | 조치 |
|---|---|---|
| 지형이 1/100 크기 | 언리얼 기본 단위 cm, 우리 자산은 **meter** | Import Uniform Scale = **100** |
| 노멀맵이 이상하게 번들거림 | `TC_Default` + sRGB 켜짐 (미배치 유물 `bon*` 에서 실제로 난 사고) | **sRGB 해제 + Compression = `Normalmap (DXT5, BC5)`** |
| 나무·집이 회색 덩어리 | 정점색 임포트 꺼짐 | Vertex Color Import Option 확인 |
| 먹 농담이 조명에 덮임 | PBR 라이팅 | Shading Model **Unlit** + Emissive |

### 엔진 프로젝트 안에 원본을 두지 않는다

`FR-OPS-004` — `vr/testproj/Content/` 안의 `.obj` `.glb` `.jpg` 원본은 전부
**`assets/<artifact-id>/`** 로 옮겨져 있다. 임포트된 `.uasset` 은 원본 없이도 열린다.
**다시 임포트할 때만** 원본이 필요하다.

---

## C. 자산을 내보낼 때 (매 버전)

1. `python scripts/check_coordinate_contract.py assets --mode scene` — **전부 통과** 확인
   (meter · Z-up · 바닥 중심 pivot · 단계 정합. 명세 19.3)
2. 면 수 확인 — 유물 1점 **≤ 30,000** (명세 20장, W1 실기 측정 전 **임시** 기준)
   - 텍스처 ≤ 2장, 각 변 ≤ 1024 / 머티리얼 ≤ 2
   - **최대 장면 면 수·목표 fps 는 아직 "미확정"** 이다. 장면 합계는 판정 기준이 없다
3. `records/` 가 비어 있지 않은지 — **비면 자산 검사 실패** (명세 19.1)
4. `manifest.json` 의 `limitations[]` 갱신 — **빈 배열 금지** (명세 19.2)
5. 연출용으로 넣은 것(측정값이 아닌 것)은 `provenance.estimated` 에 **반드시** 적는다

---

## D. Jira 작업을 완료로 옮길 때 — CONTRIBUTING 11절

**결과 파일과 검증 자료가 모두 등록돼야 완료다.**

| 구분 | 필요한 검증 자료 |
|---|---|
| **3D 에셋** | 폴리곤 수 · 텍스처 해상도 · **임포트 설정** · **엔진 내 배치 확인** |
| AI 생성 | 입력 사진 · 사용 모델과 버전 · 출력 메시 · 소요 시간 |
| 데이터 | 출처와 라이선스 · 수량 · 전처리 방법 · 저장 경로 |
| VR | 대상 기기와 엔진 버전 · 실행 영상 또는 스크린샷 · 프레임 레이트 |

> 3D 에셋 항목에 **"엔진 내 배치 확인"** 이 들어 있다. 내보내기만으로는 완료가 아니다.

---

## E. 상시 주의

- **원화 이미지(`source/input.jpg`)의 소장기관 표기·이용조건 미확인.**
  확인 전까지 발표자료·대외 공개물·배포물에 넣지 않는다
- **명세에 박힌 구조를 혼자 바꾸지 않는다** (19.1 폴더·파일명). 개정안은 `docs/AMEND-19.md`
- 낡은 문서 3곳 — 명세 22.3 · `assets/README.md` · CONTRIBUTING 10절 (LFS 미활성이라 적혀 있음)
