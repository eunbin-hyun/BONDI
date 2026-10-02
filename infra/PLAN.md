# 유물 자료 서버 구축 계획서

| 항목 | 내용 |
| --- | --- |
| 문서 ID | AS-PLAN-001 |
| 버전 | v1.1 (계획서 / 개발 가이드 분리) |
| 기준일 | 2026-09-03 |
| 작성 근거 | 2026-09-03 권영호 결정 사항 (2장) |
| 관련 프로젝트 | S15P21C201 문화유산 AI 복원 · VR 박물관 |
| 담당 직군 | Infra (권영호) |
| 대상 서버 | `$SERVER_HOST` (`infra/web/.env`) |
| 짝 문서 | **[DEV_GUIDE.md](DEV_GUIDE.md)** — 개발 순서와 구현 가이드 (AS-GUIDE-001) |
| 상태 | 계획 확정, 착수 대기 |

## 0. 문서 사용 규칙

- 이 프로젝트의 문서는 두 개다. **이 문서(계획서)는 무엇을 왜 만드는지**, **[DEV_GUIDE.md](DEV_GUIDE.md)는 어떻게 어떤 순서로 만드는지**를 담는다.
  - 설계 계약(디렉터리 구조·URL·DB 스키마·파일명 규칙·완료 기준)은 **계획서가 권위**다. 가이드는 이를 구현한다.
  - 명령·설정 파일·스크립트·단계별 검증은 **가이드가 권위**다. 계획서는 요약만 한다.
  - 두 문서가 충돌하면 계획서를 먼저 고치고 가이드를 따라 맞춘다.
- 이 서버는 **팀 내부 도구**다. 제품 명세(`docs/PROJECT_MASTER_SPEC.md`)의 산출물이 아니다.
- 수치와 명령은 설명보다 우선한다. 실제 환경과 다르면 문서를 고친다.
- **확인하지 않은 것은 "확인 필요"로 표시한다.** 특히 EC2 디스크 용량과 OS 버전은 착수 전 실측한다.
- 이 문서의 결정 번호는 `AS-nn`, 수용시험은 `AS-AT-nn`을 쓴다. 제품 명세의 `D-nn`, `U-nn`, `AT-nn`과 혼동하지 않기 위해서다.

---

# 1부. 배경과 목표

## 1. 배경

### 1.1 지금 겪는 문제

팀의 3D 자료는 Google Drive `데이터샘플` 폴더에 zip으로 모여 있다. 이 방식의 문제는 다음과 같다.

| 문제 | 구체적인 상황 |
| --- | --- |
| **뭐가 들었는지 모른다** | `bon004740_restored.zip` 185MB를 통째로 받아 풀어야 안에 OBJ가 있는지 PLY가 있는지 안다 |
| **하나만 필요해도 전부 받는다** | PLY 하나가 필요한데 OBJ·8K 텍스처·STL까지 받는다 |
| **누가 어떻게 만들었는지 없다** | `_restored`가 장서진의 CIELAB 규칙 기반인지, 다른 방식인지 파일명만으로는 알 수 없다 |
| **비교가 번거롭다** | 원본과 복원본을 비교하려면 zip 두 개를 받아 각각 풀어 각각 연다 |
| **원본 누락을 눈치채지 못한다** | `duk003312_restored.zip`은 있는데 `duk003312.zip`(원본)이 없다. 지금까지 아무도 발견하지 못했다 |

### 1.2 목적

> **팀원이 링크 하나로 들어가서, 필요한 유물을 찾고, 브라우저에서 3D로 확인하고, 필요한 파일 하나만 바로 받는다.** zip을 받을 일이 없다.

### 1.3 제품 명세와의 관계

이 도구는 신규 범위 추가가 아니라 **명세의 MUST 하나를 이행하는 것**이다.

| 명세 항목 | 내용 | 이 도구 |
| --- | --- | --- |
| `FR-OPS-005` (MUST) | 3D 데이터와 자료를 한곳에 정리. 팀원이 원본·중간 산출물을 **찾을 수 있는** 보관 위치와 목록 | 이 서버가 그 위치와 목록 |
| `U-12` | 공유 스토리지 위치 — 결정 시점 W1 | 이 계획이 U-12의 답. 확정 시 `DECISIONS.md`·명세 22.3 갱신 (12장) |
| 명세 6.2 Infra | "3D 데이터와 자료 정리 — 원본을 모아 저장하고 팀이 찾을 수 있게 한다" | 담당 업무 그 자체 |
| 명세 19.1 `runtime/` | 전시용 경량 모델 | 이 도구의 프리뷰 GLB 생성 스크립트(가이드 1장)가 같은 작업. VR 직군이 출발점으로 재사용 가능 |

**범위 경계 (반드시 지킨다)**

- 명세 5.3은 "웹 프론트엔드·API 서버"를 **MAY**로, D-26/D-37은 "현재 범위 아님"으로 둔다.
  → 이 서버는 **제품이 아니다.** 발표 산출물·시연에 넣지 않는다. 코드는 제품 저장소의 `infra/web/`에 둔다 — **자료(유물 파일·프리뷰·DB)는 넣지 않고 코드·설정·가이드만** (2026-09-10 결정 변경, 이전: 별도 폴더로 분리).
- 4주 일정에서 **W1 게이트(G1~G4)보다 우선하지 않는다.** 타임박스 2일.
- 명세 D-49가 CI/CD를 폐기했다. 이 도구도 CI·Docker 없이 로컬 빌드 + 수동 배포로 간다.

## 2. 확정 사항

2026-09-03 결정. 이 문서와 가이드의 모든 설계는 아래에서 파생된다.

| ID | 결정 | 파생되는 것 |
| --- | --- | --- |
| **AS-01** | **Google Drive는 그대로 둔다. 연동하지 않는다.** 서버는 별도 사본을 갖는다 | Drive API·서비스 계정·동기화 코드 전부 불필요. Drive가 사실상 콜드 백업 역할 |
| **AS-02** | **압축을 풀어 개별 파일에 직접 접근**할 수 있게 제공한다. "찾아주는 것"이 아니라 "바로 쓰는 것" | zip이 아닌 파일 트리로 저장. 파일마다 고정 URL |
| **AS-03** | **브라우저에서 3D 미리보기**를 제공한다 | 유물마다 경량 GLB 프리뷰와 썸네일 생성 |
| **AS-04** | **인증 없음.** 링크를 가진 사람은 모두 사용 가능. 파일 보안은 고려하지 않는다 | Basic 인증·토큰·로그인 없음. 디렉터리 목록(autoindex)도 켠다 |
| **AS-05** | **EC2는 서빙만 한다.** 무거운 변환(데시메이션·썸네일·다운샘플)은 로컬 PC(RTX 4070)에서 미리 한다 | EC2에 GPU·대용량 메모리 불필요. 로컬에 프리뷰 생성 파이프라인 |
| **AS-06** | Docker·CI/CD를 쓰지 않는다 | systemd + Nginx 직접 구성 |
| **AS-07** | 파일 투입은 **Infra(권영호)가 scp/rsync로** 한다. 웹 업로드는 만들지 않는다 | 프리뷰 생성이 로컬 GPU에서 이뤄져야 하므로 한 사람 손을 거치는 게 자연스럽다 |
| **AS-08** | AIHub CSV는 LAS의 텍스트 사본이므로 **서버에 올리지 않는다** | 후보9선 번들 용량 절반 절감 (근거: 김채원 2026-08-28 노트 "CSV는 LAS와 동일한 XYZ+RGB를 담은 텍스트 사본이므로 사용하지 않았다") |
| **AS-09** | 폴더명·파일명은 **영문으로 정규화**해서 저장한다 | URL 복사·CLI 도구 호환. 한글 원명은 DB에 보존 |

---

# 2부. 현황

## 3. 현황 조사

### 3.1 서버

| 항목 | 값 | 상태 |
| --- | --- | --- |
| 호스트 | `$SERVER_HOST` | DNS 확인됨 |
| IP | 저장소에 두지 않는다 (AWS ap-northeast-2) | 확인됨 |
| 접속 | `ssh c201` | pem 존재 확인 (`C:\Users\SSAFY\Desktop\J15C201T.pem`) |
| 방화벽 | ufw 활성, **22/tcp만 열림** (SSAFY 기본) | 바탕화면 `ufw 포트 설정하기.txt` 기준 |
| OS | Ubuntu (버전 미확인) | **확인 필요** |
| 디스크 | 미확인 (SSAFY 표준은 보통 30GB 안팎) | **확인 필요 — 착수 전 필수** |
| CPU / 메모리 | 미확인 | 확인 필요 |
| Python | 미확인 (Ubuntu 22.04는 3.10, 24.04는 3.12) | `uv`가 3.11을 별도로 받으므로 무관 |

### 3.2 로컬 PC (변환·투입 담당)

| 도구 | 상태 | 경로 |
| --- | --- | --- |
| Python | 3.11.15 | `C:\Users\SSAFY\AppData\Local\hermes\hermes-agent\venv\Scripts\python` |
| uv | 있음 | `C:\Users\SSAFY\AppData\Local\hermes\bin\uv` |
| Blender | **5.2.1 LTS** | `C:\Program Files\Blender Foundation\Blender 5.2\blender.exe` |
| ssh / scp | 있음 (Git Bash) | `/usr/bin/ssh`, `/usr/bin/scp` |
| **rsync** | **없음** | 대안: `scp -r` 또는 `tar \| ssh` 파이프. 증분 동기화가 필요해지면 WSL 설치 (`wsl --install`) 후 WSL의 rsync 사용 |
| WSL | 없음 | 선택 사항 |
| node | 22.23.2 | 필요 없음 (화면은 빌드 없는 정적 HTML) |
| GPU | RTX 4070 Laptop | Blender 렌더·데시메이션에 사용 |

### 3.3 Google Drive 인벤토리

폴더 `데이터샘플` (`1BoImuEunFExU9Gsw2q3-t7ePEdpSgl8f`). 2026-09-03 로그인 없이 열람한 목록이다. 33개 항목 + 하위 폴더 `zip`.

**국립박물관 소장품 — 원본/복원 페어**

| ID | 원본 zip | `_restored` zip | 비고 |
| --- | ---: | ---: | --- |
| `bon002074` | 6.5MB | 6.5MB | |
| `bon002789` | 58.2MB | 79.9MB | |
| `bon004740` | 135MB | 185.7MB | |
| `bon009435` | 63.5MB | 82.2MB | |
| `don000498` | 127.7MB | 148.7MB | |
| `duk003312` | **없음** | 51.7MB | **원본 누락** |
| `duk006294` | 25MB | 42MB | |
| `gae000001` | 60MB | 75.2MB | |
| `lkh000002` | 108.7MB | 151.8MB | 로컬 바탕화면에 해제본 존재 (138MB) |
| `ssu003094` | 38.8MB | 79.5MB | |
| `ssu022891` | 66.8MB | 78.7MB | 현은빈 U-Net 실험 대상(`ssu022891-001-30000_Step3.stl`) |
| **소계** | **690MB** | **982MB** | 원본 10 + 복원 11 |

접두어는 국립중앙박물관 소장품 번호 체계로 추정된다 (`bon`=본관, `duk`=덕수, `don`=동원, `ssu`=신수, `lkh`=이건희 기증, `gae`=?). **추정이며 확인 필요.** `_restored`는 장서진 2026-08-27~28 작업(CIELAB 규칙 기반 색 복원, 10유물)의 산출물로 보인다 — 업로드 날짜(8/31)와 유물 수가 일치한다. 확인 후 `method`에 기록한다.

**AIHub 문화유산 3D (LAS)**

| 파일 | 크기 | 만든 사람(추정) | 내용 |
| --- | ---: | --- | --- |
| `RR_07_01_EA_028.las` | 6.2MB | AIHub 원본 | 원형 토기편 (부록 A.4의 "토기 항아리") |
| `RR_07_01_EA_028_pointr_raw_raw.las` | 288KB | 장서진 | PoinTr fine 출력, 원자세 |
| `RR_07_01_EA_028_pointr_raw_yup.las` | 288KB | 장서진 | PoinTr fine 출력, Y-up |
| `RR_07_01_EA_028_pointr_restored.las` | 6.2MB | 장서진 | 원본 + 보충점(class 12) |
| `RR_07_01_PA_033.las` | 51.1MB | AIHub 원본 | 소형 석등 |
| `RR_07_01_PA_033_pointr_raw_output.las` | 288KB | 장서진 | PoinTr 출력 |
| `RR_07_01_PA_033_pointr_restored.las` | 51.2MB | 장서진 | |
| `RR_07_01_PA_033_symmetry_restored.las` | 52.9MB | 장서진 | 육각 회전대칭 창살 복원 |
| `RR_07_01_EA_022_복원_공유.zip` | 574KB | 미상 | 흑색 항아리 |
| **소계** | **169MB** | | |

**대형 번들**

| 파일 | 크기 | 판단 |
| --- | ---: | --- |
| `유물복원_자료.zip` | 880.1MB | 내용 미확인. 위 개별 파일의 묶음일 가능성 |
| `VR_유적지_복원_전시_후보_9선.zip` | 498.3MB | 바탕화면 동명 폴더와 같은 구성으로 추정 — 9개 유물의 LAS/CSV/JSON/PNG. **CSV 제외 시 LAS만 약 450MB** |
| 폴더 `zip` | 크기 불명 | **내용 확인 필요** |

**합계: 압축 상태 약 3.2GB** (`zip` 폴더 제외).

### 3.4 zip 내부 구조 (실측)

바탕화면 `lkh000002/` — `lkh000002.zip`(108.7MB)의 해제본, 138MB. **압축비 약 1.27배.**

```text
lkh000002/
├── 디지털콘텐츠_OBJ/
│   ├── lkh000002-000-30000.obj        # 메시
│   ├── lkh000002-000-30000.mtl        # 재질
│   ├── lkh000002-000-30000.jpg        # 디퓨즈 텍스처 (8K)
│   └── lkh000002-000-30000_nor.jpg    # 노멀맵
├── 스캔_PLY/
│   └── lkh000002-000-30000_step3.ply  # 스캔 점군/메시
└── 프린트_STL/
    └── lkh000002-000-30000_step3.stl  # 프린트용 메시
```

장서진 2026-08-27 노트가 지적한 품질 이슈가 그대로 있을 것으로 본다: MTL 절대경로, OBJ-MTL 재질명 불일치, mm/m 단위 혼재, 변형 바이너리 STL, 스캔 PLY 정점색 더미(전부 흰색). **프리뷰 생성 시 MTL 경로는 반드시 상대경로로 고쳐야 한다** (가이드 1.4).

### 3.5 용량 추정

| 묶음 | 압축 | 해제 후 (×1.27) |
| --- | ---: | ---: |
| 국립박물관 페어 21개 | 1.67GB | **2.1GB** |
| AIHub LAS 8종 + EA_022 | 169MB | 0.2GB |
| 프리뷰 GLB + 썸네일 + `.gz` 사전압축 (신규) | — | **0.8GB** (추정) |
| **소계 — 번들 제외** | | **약 3.1GB** |
| 후보9선 (CSV 제외, LAS만) | — | +0.45GB |
| `유물복원_자료.zip` 해제 | — | +1.1GB (중복이면 0) |
| `zip` 폴더 | ? | ? |

→ **번들을 중복 제거하면 3.5GB 안쪽**이다. EC2 여유가 10GB 이상이면 문제없다. **여유가 8GB 미만이면 가이드 Phase 0에서 계획을 재검토한다.**

### 3.6 발견된 문제 (착수 시 처리)

| # | 문제 | 처리 |
| --- | --- | --- |
| 1 | `duk003312` 원본 누락 | 만든 사람에게 원본 요청. 없으면 `restored`만 등록하고 `note`에 기록 |
| 2 | 번들 2개가 개별 파일과 중복 가능 | 해제 후 SHA-256 비교. 중복이면 번들은 적재 안 함 |
| 3 | `zip` 하위 폴더 내용 불명 | Phase 0에서 열어 인벤토리에 추가 |
| 4 | 파일에 담당자·방법·라이선스 정보 없음 | DB `variants.owner/method`, `artifacts.license`로 보완. 팀원이 웹에서 직접 채움 |
| 5 | 파일명 한글 (`복원_공유`, 폴더명) | AS-09에 따라 영문 정규화, 원명은 DB에 보존 |

---

# 3부. 설계

## 4. 목표 정의와 완료 기준

### 4.1 "바로 사용 가능"의 세 단계

| 단계 | 상태 | 팀원이 할 수 있는 것 | 우선순위 |
| --- | --- | --- | --- |
| **A. 개별 파일 직접 접근** | 압축 해제 상태로 보관, 파일마다 고정 URL | `/files/bon004740/source/scan_ply/xxx.ply` 를 바로 받는다. Blender·Unreal 임포트에 곧장 쓴다 | **MUST** |
| **B. 브라우저 미리보기** | 유물·변형마다 경량 GLB | 받기 **전에** 3D로 돌려보고 확인한다. 원본과 복원본을 나란히 비교한다 | **MUST** |
| **C. 검색·필터** | 메타데이터 DB + 검색 화면 | 유물 ID·출처·담당자·방법으로 좁힌다. 파일 설명을 읽고 직접 고친다 | **MUST** |
| D. 디렉터리 브라우징 | Nginx autoindex | 화면 없이도 `/files/`를 폴더처럼 훑는다 | SHOULD (설정 한 줄) |
| E. 원본 zip 재다운로드 | — | 하지 않는다. Drive에 있다 | 범위 밖 |

### 4.2 완료 기준 (수용 시험)

| ID | Given | When | Then |
| --- | --- | --- | --- |
| **AS-AT-01** | 링크만 아는 팀원, 로그인 없음 | 링크를 연다 | 검색 화면이 뜬다. 인증 요구 없음 |
| **AS-AT-02** | 검색창 | `RR_07_01_EA_028` 입력 | 해당 유물의 변형 4개(source·pointr_raw_raw·pointr_raw_yup·pointr_restored)와 각 파일이 한 화면에 나온다 |
| **AS-AT-03** | 유물 `bon004740` 상세 | 파일 목록에서 `scan_ply/*.ply` 클릭 | 그 파일 하나만 다운로드된다. zip이 아니다 |
| **AS-AT-04** | 유물 `bon004740` 상세 | 3D 뷰어 영역 | source 프리뷰가 3초 안에 뜨고 마우스로 회전·확대된다 |
| **AS-AT-05** | 유물 `bon004740` 상세 | "비교" 클릭 | source와 restored가 나란히(또는 토글로) 표시되고 카메라가 동기화된다 |
| **AS-AT-06** | 유물 상세의 메타 필드 | `owner`를 "장서진"으로 수정·저장 | 새로고침 후 유지된다. DB에 반영된다 |
| **AS-AT-07** | `/files/` URL 직접 접근 | 브라우저로 연다 | 디렉터리 목록이 보인다 (autoindex) |
| **AS-AT-08** | 62MB OBJ 파일 | 다운로드 | 전송량이 원본의 1/3 이하다 (gzip_static 동작 확인, 개발자도구 Network) |
| **AS-AT-09** | 서버 재부팅 | 부팅 완료 후 | 앱이 자동으로 떠 있다 (systemd enable) |
| **AS-AT-10** | 새 유물 zip 1개 | 가이드 6.1 투입 절차 실행 | 15분 안에 검색에 나오고 프리뷰가 보인다 |

**10개 모두 통과하면 완료다.** 썸네일·통계·zip 내부 목록 등은 완료 기준이 아니다.

## 5. 아키텍처

### 5.1 전체 구조

```text
┌──────────────── 로컬 PC (RTX 4070) ─────────────────┐
│  Drive 다운로드 → 압축 해제 → 이름 정규화            │
│     → make_preview.py                                │
│         ├ 메시: Blender headless → 감축 GLB + 썸네일 │
│         ├ 점군: laspy → 다운샘플 → GLB               │
│         └ 텍스트 포맷 .gz 사전 압축                   │
│     → staging/ 트리 완성                              │
└───────────────────────┬──────────────────────────────┘
                        │ scp / tar|ssh  (AS-07)
                        ▼
┌──────────── EC2 $SERVER_HOST ───────────────────────┐
│  /srv/catalog/                                        │
│    files/     ← 원본 트리 (Nginx 직접 서빙)           │
│    preview/   ← GLB·PNG (Nginx 직접 서빙)             │
│    catalog.db ← SQLite                                │
│    app/       ← FastAPI (uvicorn, systemd, :8000)     │
│    web/       ← index.html + viewer.js (정적)         │
│                                                       │
│  Nginx :80                                            │
│    /          → web/                                  │
│    /api/*     → 127.0.0.1:8000                        │
│    /files/*   → files/   (sendfile, gzip_static,      │
│                           autoindex on)               │
│    /preview/* → preview/ (gzip_static, 7d cache)      │
└───────────────────────┬──────────────────────────────┘
                        │ HTTP, 인증 없음 (AS-04)
                        ▼
              팀원 브라우저 / Blender / Unreal
```

### 5.2 컴포넌트

| 컴포넌트 | 위치 | 역할 | 기술 | 상세 |
| --- | --- | --- | --- | --- |
| `make_preview.py` | 로컬 | zip 해제, 이름 정규화, 프리뷰 GLB·썸네일 생성, `.gz` 생성, `_meta.json` 기록 | Python 3.11, Blender 5.2 headless, laspy, Open3D, trimesh | 가이드 1장 |
| `scan.py` | EC2 | `files/`·`preview/` 스캔 → SQLite 갱신. `_meta.json` 읽어 삼각형·점 수 반영 | Python 표준 라이브러리 + sqlite3 | 가이드 Phase 5 |
| FastAPI 앱 | EC2 | 검색·상세·메타 수정 API | FastAPI, uvicorn, sqlite3 | 가이드 3장 |
| 정적 화면 | EC2 | 목록·검색·상세·3D 뷰어·비교 | HTML 1장 + 바닐라 JS + three.js (CDN) | 가이드 4장 |
| Nginx | EC2 | 정적 서빙, 대용량 파일 직접 전송, 리버스 프록시 | Nginx | 가이드 2.4 |
| systemd | EC2 | uvicorn 상시 구동, 재부팅 자동 시작 | — | 가이드 2.5 |

**왜 이렇게 나눴는가**

- **대용량은 앱을 거치지 않는다.** FastAPI가 3GB를 흘리면 워커 하나가 그 전송에 묶인다. Nginx `sendfile`은 커널이 처리한다.
- **변환은 로컬에서만.** SSAFY EC2는 보통 2 vCPU·GPU 없음이다. 김채원 사례(1,229만 삼각형, 473MB)를 EC2에서 데시메이션하면 수십 분 걸리거나 OOM이다. 로컬에는 Blender·Open3D가 이미 있다.
- **DB는 파일 하나.** 유물 수십 개, 파일 수백 개 규모에 Postgres는 과잉이다.
- **화면은 빌드 없이.** FE(공세민)는 VR UI에 집중해야 하고, 이 도구는 Infra 혼자 유지한다. npm 빌드 체인이 없어야 한다.

### 5.3 요청 흐름

```text
[검색]     브라우저 → GET /api/artifacts?q=EA_028 → FastAPI → SQLite → JSON
[상세]     브라우저 → GET /api/artifacts/RR_07_01_EA_028 → 변형·파일 목록 JSON
[뷰어]     브라우저 → GET /preview/RR_07_01_EA_028/source.glb → Nginx 직접 → three.js 로드
[다운로드] 브라우저 → GET /files/RR_07_01_EA_028/source/RR_07_01_EA_028.las → Nginx 직접
[메타 수정] 브라우저 → PATCH /api/variants/{id} {"owner":"장서진"} → FastAPI → SQLite
```

## 6. 저장 구조와 네이밍 규칙

### 6.1 세 층위: artifact → variant → file

| 층위 | 뜻 | 예 |
| --- | --- | --- |
| **artifact (유물)** | 하나의 실물 유물 | `bon004740`, `RR_07_01_EA_028` |
| **variant (변형)** | 그 유물의 한 버전 — 원본, 복원본, 실험 출력 | `source`, `restored`, `pointr_restored`, `symmetry_restored` |
| **file (파일)** | 변형 안의 개별 파일 | `digital_obj/bon004740-000-30000.obj` |

원본과 복원본을 **같은 artifact 아래 다른 variant**로 두는 것이 비교 뷰(4.1 B)의 기반이다.

**명세 3단계 복원과의 관계.** 명세는 ①손상 → ②모델 복원 → ③MCP 복원의 3단계를 정의한다(D-47). 이 서버의 `variant`는 그보다 넓은 개념이다 — 실험 출력(`pointr_raw_yup`)도 variant다. 자산이 제품 `assets/<artifact-id>/`로 승격될 때 `variant`를 `1-damaged / 2-model-restored / 3-mcp-restored`로 매핑한다. 이 서버에서 강제하지 않는다.

### 6.2 디렉터리 트리 (EC2)

```text
/srv/catalog/
├── files/
│   ├── bon004740/
│   │   ├── source/
│   │   │   ├── digital_obj/
│   │   │   │   ├── bon004740-000-30000.obj
│   │   │   │   ├── bon004740-000-30000.obj.gz      ← gzip_static용
│   │   │   │   ├── bon004740-000-30000.mtl         ← 상대경로로 수정된 것
│   │   │   │   ├── bon004740-000-30000.jpg
│   │   │   │   └── bon004740-000-30000_nor.jpg
│   │   │   ├── scan_ply/
│   │   │   │   ├── bon004740-000-30000_step3.ply
│   │   │   │   └── bon004740-000-30000_step3.ply.gz
│   │   │   ├── print_stl/
│   │   │   │   └── bon004740-000-30000_step3.stl
│   │   │   └── _meta.json                          ← make_preview.py가 기록
│   │   └── restored/
│   │       └── (같은 구조)
│   ├── RR_07_01_EA_028/
│   │   ├── source/
│   │   │   ├── RR_07_01_EA_028.las
│   │   │   ├── RR_07_01_EA_028.json                ← AIHub 메타 (있으면)
│   │   │   └── _meta.json
│   │   ├── pointr_raw_raw/
│   │   ├── pointr_raw_yup/
│   │   └── pointr_restored/
│   └── ...
├── preview/
│   ├── bon004740/
│   │   ├── source.glb
│   │   ├── source.png
│   │   ├── restored.glb
│   │   └── restored.png
│   └── RR_07_01_EA_028/
│       ├── source.glb
│       └── ...
├── catalog.db
├── app/
│   ├── main.py
│   ├── db.py
│   └── scan.py
├── web/
│   ├── index.html
│   ├── app.js
│   └── viewer.js
├── pyproject.toml
└── uv.lock
```

### 6.3 이름 정규화 표 (AS-09)

| 원명 | 정규화 |
| --- | --- |
| `디지털콘텐츠_OBJ` | `digital_obj` |
| `스캔_PLY` | `scan_ply` |
| `프린트_STL` | `print_stl` |
| `bon004740_restored` (zip 이름) | artifact `bon004740`, variant `restored` |
| `RR_07_01_EA_022_복원_공유` | artifact `RR_07_01_EA_022`, variant `shared_restore` |
| `RR_07_01_EA_028_pointr_raw_yup` | artifact `RR_07_01_EA_028`, variant `pointr_raw_yup` |
| 파일명 내부 한글·공백 | 그대로 두지 않고 `_`로 치환. 원명은 `files.original_name`에 보존 |

### 6.4 URL 규칙

```text
http://$SERVER_HOST/                                    화면
http://$SERVER_HOST/files/                              디렉터리 브라우징
http://$SERVER_HOST/files/bon004740/source/scan_ply/bon004740-000-30000_step3.ply
http://$SERVER_HOST/preview/bon004740/source.glb
http://$SERVER_HOST/api/artifacts?q=bon
```

URL은 한 번 정해지면 바꾸지 않는다. 팀원이 문서·노트에 붙여넣을 것이다.

## 7. 데이터 모델

### 7.1 DDL

```sql
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- 유물
CREATE TABLE artifacts (
  artifact_id   TEXT PRIMARY KEY,          -- bon004740 / RR_07_01_EA_028
  source_org    TEXT NOT NULL,             -- 'museum' | 'aihub' | 'other'
  title         TEXT,                      -- 사람이 채움. 예: "원형 토기편"
  region        TEXT,                      -- AIHub: 경기/강원/경상 (코드에서 디코딩)
  type_code     TEXT,                      -- AIHub: EA/PA/ST → 도·토기/탑·비/조형물
  license       TEXT NOT NULL DEFAULT 'unverified',  -- unverified | ok | restricted
  note          TEXT,
  tags          TEXT,                      -- 쉼표 구분
  created_at    TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 변형 (원본·복원본·실험 출력)
CREATE TABLE variants (
  variant_id    TEXT PRIMARY KEY,          -- '<artifact_id>/<variant>' 예: bon004740/restored
  artifact_id   TEXT NOT NULL REFERENCES artifacts(artifact_id) ON DELETE CASCADE,
  variant       TEXT NOT NULL,             -- source | restored | pointr_restored | ...
  method        TEXT,                      -- 'CIELAB 규칙 기반' / 'PoinTr ShapeNet-55' / '회전대칭' / 'U-Net' ...
  owner         TEXT,                      -- 만든 사람
  produced_at   TEXT,                      -- 제작일 (파일 mtime 또는 사람이 입력)
  preview_glb   TEXT,                      -- preview/bon004740/restored.glb (없으면 NULL)
  thumb_png     TEXT,
  tri_count     INTEGER,                   -- 대표 메시 삼각형 수 (_meta.json)
  pt_count      INTEGER,                   -- 대표 점군 점 수
  note          TEXT,
  updated_at    TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (artifact_id, variant)
);

-- 파일
CREATE TABLE files (
  path          TEXT PRIMARY KEY,          -- files/ 기준 상대경로 (URL과 동일)
  variant_id    TEXT NOT NULL REFERENCES variants(variant_id) ON DELETE CASCADE,
  original_name TEXT,                      -- 정규화 전 원명 (한글 보존)
  kind          TEXT NOT NULL,             -- obj | mtl | texture | normalmap | ply | stl | las | json | png | other
  size          INTEGER NOT NULL,
  sha256        TEXT,                      -- 중복 검출
  has_gz        INTEGER NOT NULL DEFAULT 0,
  mtime         TEXT,
  scanned_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_files_variant ON files(variant_id);
CREATE INDEX idx_files_sha ON files(sha256);
CREATE INDEX idx_variants_artifact ON variants(artifact_id);
```

### 7.2 채우는 주체

| 열 | 자동 (scan.py) | 자동 (make_preview.py → `_meta.json`) | 사람 (웹 UI) |
| --- | --- | --- | --- |
| `artifacts.artifact_id / source_org / region / type_code` | ✔ 경로·파일명 파싱 | | |
| `artifacts.title / license / note / tags` | | | ✔ |
| `variants.variant_id / variant` | ✔ 경로 | | |
| `variants.method / owner` | 파일명에서 1차 추정 (`pointr_*` → PoinTr) | | ✔ 보정 |
| `variants.preview_glb / thumb_png` | ✔ preview/ 존재 여부 | | |
| `variants.tri_count / pt_count` | | ✔ | |
| `files.*` | ✔ | | |

### 7.3 명세 19.2 manifest와의 대응

이 DB는 명세의 manifest 필수 필드를 **부분적으로 미리 채운다.** 자산 승격 시 그대로 옮긴다.

| 명세 manifest 필드 | 이 DB |
| --- | --- |
| `artifactId` | `artifacts.artifact_id` |
| `title, description, type` | `artifacts.title, note, type_code` |
| `source.kind` | `source_org` (scan) |
| `source.credit, license, url` | `license` (나머지는 승격 시 추가) |
| `stages[]` — 모델명·버전·사람 개입 | `variants.method, owner` |
| `provenance` | 없음 — 승격 시 추가 |
| `limitations[]` | 없음 — 승격 시 추가 |
| `runtime.triangles` | `variants.tri_count` |
| `review.*` | 없음 — 승격 시 추가 |

## 8. 파일명 파싱 규칙

`make_preview.py`가 zip 이름을 보고 `artifact_id`와 `variant`를 결정하고, 그 결과가 디렉터리 경로가 된다. `scan.py`는 경로만 읽으므로 파싱은 **로컬에서 한 번만** 일어난다.

### 8.1 규칙

| 순서 | 정규식 (zip 이름, 확장자 제외) | source_org | artifact_id | variant |
| --- | --- | --- | --- | --- |
| 1 | `^(bon\|duk\|don\|ssu\|lkh\|gae)(\d{6})(?:_restored)?$` | `museum` | `\1\2` | `_restored` 있으면 `restored`, 없으면 `source` |
| 2 | `^(RR_\d{2}_\d{2}_[A-Z]{2}_\d{3})$` | `aihub` | `\1` | `source` |
| 3 | `^(RR_\d{2}_\d{2}_[A-Z]{2}_\d{3})_(.+)$` | `aihub` | `\1` | `\2`를 소문자·영문 정규화 (8.3) |
| 4 | 그 외 | `other` | zip 이름 전체를 정규화 | `source` |

### 8.2 예시

| 입력 | artifact_id | variant | source_org |
| --- | --- | --- | --- |
| `bon004740.zip` | `bon004740` | `source` | museum |
| `bon004740_restored.zip` | `bon004740` | `restored` | museum |
| `duk003312_restored.zip` | `duk003312` | `restored` | museum (원본 없음 → `note`) |
| `RR_07_01_EA_028.las` | `RR_07_01_EA_028` | `source` | aihub |
| `RR_07_01_EA_028_pointr_raw_yup.las` | `RR_07_01_EA_028` | `pointr_raw_yup` | aihub |
| `RR_07_01_PA_033_symmetry_restored.las` | `RR_07_01_PA_033` | `symmetry_restored` | aihub |
| `RR_07_01_EA_022_복원_공유.zip` | `RR_07_01_EA_022` | `shared_restore` | aihub |

### 8.3 variant 접미어 정규화

| 접미어 | variant | method 1차 추정 |
| --- | --- | --- |
| `pointr_raw_raw` | `pointr_raw_raw` | `PoinTr (ShapeNet-55, 원자세)` |
| `pointr_raw_yup` | `pointr_raw_yup` | `PoinTr (ShapeNet-55, Y-up)` |
| `pointr_raw_output` | `pointr_raw_output` | `PoinTr (ShapeNet-55)` |
| `pointr_restored` | `pointr_restored` | `PoinTr 보충점 병합 (class 12)` |
| `symmetry_restored` | `symmetry_restored` | `회전대칭 + 점유격자 + ICP` |
| `복원_공유` | `shared_restore` | (미상) |
| `restored` | `restored` | (미상 — 확인 후 `CIELAB 규칙 기반` 등으로 보정) |

### 8.4 AIHub 코드 디코딩 (`region`, `type_code`)

바탕화면 `전시_후보_안내.md` 기준.

| 코드 위치 | 값 | 뜻 |
| --- | --- | --- |
| 2번째 (`RR_02`, `RR_03`, `RR_07`) | 02 / 03 / 07 | 경기도 / 강원도 / 경상도 |
| 3번째 (`_01_`) | 01 | 지정 문화재 |
| 4번째 (`EA`, `PA`, `ST`) | EA / PA / ST | 도·토기류 / 탑·비 / 조형물 |

**공식 ID–문화재명 대응표가 없다.** `title`에 고유명을 넣지 않는다. 형태 분류만 적는다 (예: "원형 토기편", "석등형 객체"). 이건 팀이 이미 정한 원칙이다 (`전시_후보_안내.md` 정정 기록, DECISIONS R10 ④).

## 9. 구현 요약

구현 상세는 전부 [DEV_GUIDE.md](DEV_GUIDE.md)에 있다. 여기서는 설계 수준의 결정만 적는다.

### 9.1 프리뷰 (가이드 1장)

| 항목 | 상한 | 근거 |
| --- | --- | --- |
| 메시 삼각형 | **≤ 200,000** | 웹 three.js에서 저사양 노트북 포함 부드러운 선. 김채원 VR 채택값(400k)보다 보수적 |
| 점군 점 수 | **≤ 300,000** | THREE.Points 렌더 부담 기준 |
| 텍스처 | **2048×2048, JPEG q85** | 8K 원본은 다운로드용. 프리뷰에 8K를 넣으면 GLB가 30MB를 넘는다 |
| GLB 파일 크기 | 목표 ≤ 15MB | 3초 로딩 기준 (LTE 환경 가정) |
| 썸네일 | 512×512 PNG, Workbench 렌더 | GPU 불필요, 형태 확인용 |

| 입력 | 도구 | 이유 |
| --- | --- | --- |
| OBJ+MTL+텍스처, PLY, STL | **Blender headless** | Decimate 모디파이어가 UV를 보존한다. Open3D 데시메이션은 UV를 버린다 |
| LAS 점군 | **laspy + Open3D + trimesh** | Blender에 LAS 임포터가 없다 |

명세 22.1이 Trimesh·Open3D·NumPy·Blender(headless)를 확정 스택으로 올려뒀다. 새 도구가 없다.

### 9.2 서버 스택 (가이드 2장)

| 층 | 선택 | 이유 |
| --- | --- | --- |
| 웹서버 | Nginx | 대용량 파일 직접 서빙(`sendfile`), `gzip_static`, `autoindex` |
| API | FastAPI + uvicorn (systemd) | 명세 22.1의 Python 3.11 + `uv`와 동일 스택 |
| DB | SQLite (WAL) | 파일 하나 |
| 스캔 | Python 표준 라이브러리 | EC2에 Open3D·Blender를 설치하지 않는다 (AS-05) |
| 화면 | HTML 1장 + 바닐라 JS + three.js (CDN import map) | 빌드 없음 |

### 9.3 API 개요 (가이드 3장)

`/api/artifacts` 검색·목록, `/api/artifacts/{id}` 상세(변형·파일 포함), `PATCH /api/artifacts/{id}`·`PATCH /api/variants/{id}` 메타 수정, `/api/files` 중복 조회, `/api/stats`, `POST /api/rescan`, `/api/health`. JSON, 인증 없음.

### 9.4 화면 개요 (가이드 4장)

좌측 목록(썸네일 카드) + 우측 상세(3D 뷰어·변형·파일). **원본/복원 비교 모드(분할 + 카메라 동기화)가 MUST.** 인라인 메타 편집.

---

# 4부. 일정과 리스크

## 10. 일정 개요

**총 약 2일 (16~20시간), Infra 1인.** 단계별 명령·검증은 가이드 5장.

| Phase | 내용 | 위치 | 예상 | 누적 |
| --- | --- | --- | ---: | ---: |
| 0 | 실측·인벤토리 확정 | 로컬+EC2 | 1h | 1h |
| 1 | Drive 다운로드·해제·정규화 | 로컬 | 2h | 3h |
| 2 | 프리뷰 생성 파이프라인 | 로컬 | 4h | 7h |
| 3 | EC2 기본 구성 | EC2 | 0.5h | 7.5h |
| 4 | 파일 전송 | 로컬→EC2 | 1h | 8.5h |
| 5 | `scan.py` + DB | EC2 | 2h | 10.5h |
| 6 | FastAPI | EC2 | 2h | 12.5h |
| 7 | 화면 + 뷰어 | EC2 | 4h | 16.5h |
| 8 | systemd·Nginx 마무리 | EC2 | 1h | 17.5h |
| 9 | 팀 공개·메타 채우기 | — | — | — |

**게이트.** Phase 0의 디스크 실측이 계획 전체의 전제다. Phase 2가 가장 실패 확률이 높다.

**Fallback.** W1 게이트와 시간이 겹치면 **Phase 6까지만** 끝낸다. `/files/` autoindex + `/api/`로 A(개별 파일)·C(검색)는 달성된다. B(뷰어)는 뒤로 민다.

**착수 시점.** 미정. 명세 W1 게이트(G1~G4)보다 우선하지 않는다. `U-12` 결정 시점이 W1(~9/7)이므로 이 안에 최소 Phase 0은 끝내는 것이 맞다.

## 11. 리스크와 대응

| # | 리스크 | 가능성 | 영향 | 예방 | 발생 시 |
| --- | --- | --- | --- | --- | --- |
| 1 | EC2 디스크 부족 | 중 | 큼 | Phase 0 실측, 번들 중복 제거, CSV 제외 | 원본 zip 미적재, 8K 텍스처를 Drive에만 |
| 2 | Blender 데시메이션이 대형 파일에서 실패 | 중 | 중 | 가이드 §1.8 2단계 감축, 작은 파일부터 | 해당 variant는 프리뷰 없이 등록(`preview_glb NULL`), 화면에 "프리뷰 없음" 표시 |
| 3 | Blender 5.2 API 옵션명 불일치 | 높음 | 작음 | Phase 2 단독 검증 먼저 | 옵션명 수정 |
| 4 | MTL·텍스처 이름 불일치로 텍스처 안 보임 | 중 | 중 | 가이드 §1.4 수정 + 로그 | 로그 보고 수동 매핑 |
| 5 | CDN 차단 환경에서 뷰어 불능 | 낮음 | 중 | `web/vendor/`에 three.js 복사본 준비 | import map 경로 전환 |
| 6 | EC2 소실 | 낮음 | 중 | Drive가 원본 백업, DB 주간 백업 | Phase 1~4 재실행 (반나절) |
| 7 | 한글 경로 인코딩 문제 | 중 | 작음 | AS-09 영문 정규화 | — |
| 8 | 8K 텍스처 다운로드가 느리다는 불만 | 중 | 작음 | 프리뷰는 2K, 원본은 명시적 다운로드 | — |
| 9 | 명세 범위 논란 ("웹은 MAY인데") | 낮음 | 중 | 1.3절 근거 명시, 제품 저장소·발표에 넣지 않음 | 팀 회의에서 FR-OPS-005 이행으로 설명 |
| 10 | 라이선스 미확인 데이터 노출 | — | — | AS-04 결정으로 수용. `license` 열로 상태 추적만 | U-02 결정에 따름 |
| 11 | W1 게이트와 시간 경쟁 | 중 | 큼 | 2일 타임박스, Phase 7 SHOULD 이하는 뒤로 | Phase 0~6까지만 하고 화면은 autoindex로 대체 (10장 Fallback) |

## 12. 제품 문서 갱신 초안

**적용은 팀 회의 결정 후.** 이 계획서는 제안만 한다. 저장소 편집은 별도 MR로, 협업 규칙(CONTRIBUTING 8절 절차)을 따른다.

### 12.1 `docs/DECISIONS.md` 추가 초안

```markdown
### D-54. 공유 스토리지: EC2 자료 서버 (U-12 확정)

- 3D 원본·중간 산출물의 보관 위치를 **팀 EC2(`$SERVER_HOST`)의 자료 서버**로 확정한다.
- Google Drive `데이터샘플` 폴더는 원본 백업으로 유지하되 연동하지 않는다.
- 서버는 압축 해제된 개별 파일·브라우저 3D 미리보기·검색을 제공한다.
- **팀 내부 도구다.** 제품 산출물·시연에 포함하지 않는다. 명세 5.3의 MAY(웹·API 서버)와 무관하다.
- 근거: FR-OPS-005 이행. 계획서 `c201-asset-server/PLAN.md` (AS-PLAN-001).
- 담당: 권영호(Infra).
```

### 12.2 명세 22.3 표 갱신 초안

| 구분 | 선택 | 상태 |
| --- | --- | --- |
| 3D 원본 보관 | ~~공유 스토리지 — Infra가 위치 확보~~ **EC2 자료 서버 (`$SERVER_HOST`), Drive 백업** | **확정 (D-54)** |

### 12.3 명세 4부 U-12

| ID | 미확정 내용 | 결정 시점 | 결정 못 하면 |
| --- | --- | --- | --- |
| ~~U-12~~ | ~~공유 스토리지 위치~~ → **D-54로 확정** | | |

## 13. 미결 사항

| # | 항목 | 확인 방법 | 시점 |
| --- | --- | --- | --- |
| 1 | EC2 OS·디스크·CPU·메모리 | 가이드 Phase 0 명령 | 착수 직후 |
| 2 | Drive `zip` 하위 폴더 내용 | 열어보기 | Phase 0 |
| 3 | `유물복원_자료.zip` 내용·출처 | `unzip -l`, 팀에 질문 | Phase 0 |
| 4 | `duk003312` 원본 소재 | 팀에 질문 | Phase 0 |
| 5 | `_restored` zip의 제작 방법 (CIELAB 규칙 기반 추정) | 장서진 확인 | Phase 9 |
| 6 | 국립박물관 접두어 의미 (`bon/duk/don/ssu/lkh/gae`) | 장서진 확인 | Phase 9 (표시용, 기능 무관) |
| 7 | Blender 5.2 glTF 익스포터 옵션명 | Phase 2 실행 | Phase 2 |
| 8 | 점군 썸네일 생성 여부 | Phase 2 판단 | Phase 2 |
| 9 | three.js 버전 고정값 | 착수 시 최신 안정판 | Phase 7 |
| 10 | 착수 시점 | 권영호 판단. W1 게이트 우선 | — |

---

## 부록 A. 로컬 저장소 구조 (`c201-asset-server/`)

이 계획서가 있는 폴더. 서버 코드·배포 설정·로컬 도구는 **`infra/web/`** 에 둔다 (2026-09-10 변경, 이전에는 별도 폴더로 분리했음). 자료는 넣지 않는다.

```text
c201-asset-server/
├── PLAN.md                 ← 이 문서 (계획서)
├── DEV_GUIDE.md            ← 개발 순서와 구현 가이드
├── README.md               ← 사용법 요약 (Phase 9에서 작성)
├── local/                  ← 로컬 PC에서 실행
│   ├── pyproject.toml      (laspy, open3d, trimesh, numpy, pillow)
│   ├── make_preview.py
│   ├── blender_preview.py
│   └── tools/dedupe_report.py
├── server/                 ← EC2 /srv/catalog 에 배치
│   ├── pyproject.toml      (fastapi, uvicorn)
│   ├── app/{main.py, db.py, scan.py}
│   └── web/{index.html, app.js, viewer.js}
├── deploy/
│   ├── nginx-catalog.conf
│   └── catalog-api.service
└── inventory.csv           ← Phase 0 산출물
```

## 부록 B. 참고

- 짝 문서: [DEV_GUIDE.md](DEV_GUIDE.md)
- 제품 명세: `S15P21C201/docs/PROJECT_MASTER_SPEC.md` — 6.2 Infra, 12.4 FR-OPS, 19장 자산 계약, 22장 기술 스택, 4부 U-12
- 결정 기록: `S15P21C201/docs/DECISIONS.md` — D-26, D-37, D-49, R10 ④
- 팀 조사: `Study` 브랜치 — 장서진 2026-08-27 (데이터 품질 이슈), 김채원 2026-08-28 (LOD 실패 사례, CSV 사본), 권영호 2026-08-28 (classification 분리)
- 바탕화면: `ufw 포트 설정하기.txt`, `VR_유적지_복원_전시_후보_9선/전시_후보_안내.md` (AIHub 코드 해석)
