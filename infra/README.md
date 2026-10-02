# infra — Infra 직군 문서

저장소·빌드·데이터 보관에 관한 Infra 직군의 계획서와 운영 기록을 담는다.
담당 직군: **Infra**

## 여기에 넣는 것

### 계획

| 문서 | 내용 |
| --- | --- |
| [PLAN.md](PLAN.md) | **자료 서버 계획서** (AS-PLAN-001) — 배경, 확정 사항 AS-01~09, 현황, 설계 계약, 완료 기준 AS-AT-01~10, 리스크 |
| [DEV_GUIDE.md](DEV_GUIDE.md) | **자료 서버 개발 가이드** (AS-GUIDE-001) — Phase 0~9 개발 순서, 서버 설정, API, 뷰어, 운영 절차 |

### 구축 가이드 — 따라 하면 재현되는 순서

| 문서 | 무엇을 만드나 | 어디서 |
| --- | --- | --- |
| [ASSET_DB_BUILD_GUIDE.md](ASSET_DB_BUILD_GUIDE.md) | **자료·DB 구축** — 수집·정규화·프리뷰 생성·전송·DB 생성·운영(재스캔) | 로컬 → 서버 |
| [WEB_SERVER_BUILD_GUIDE.md](WEB_SERVER_BUILD_GUIDE.md) | **웹서버 구축·배포** — nginx·systemd·uv 구성과 손으로 하는 배포(`deploy.sh`) | 서버 |
| [JENKINS_BUILD_GUIDE.md](JENKINS_BUILD_GUIDE.md) | **젠킨스 자동 배포 구축** — Jenkins 설치부터 GitLab 웹훅 연결·검증까지 | 서버 + GitLab |

### 참고 문서

| 문서 | 내용 |
| --- | --- |
| [JENKINS_TROUBLESHOOTING.md](JENKINS_TROUBLESHOOTING.md) | 젠킨스 현재 설정 상태, 상태 확인 명령, 실제로 막혔던 11가지와 처치, 되돌리기 |
| [WEB_TROUBLESHOOTING.md](WEB_TROUBLESHOOTING.md) | 웹·미리보기 문제 해결 — 상태 보는 명령 4개, 증상별 표, 실제로 막혔던 11가지(libEGL·캐시·ID 재사용·방향·밝기), 잘못 올린 자료 되살리기 |
| [WEB_APP_DEV_GUIDE.md](WEB_APP_DEV_GUIDE.md) | 화면·API 코드 구조 — 어디를 고치면 무엇이 바뀌나 |

### 코드

| 위치 | 내용 |
| --- | --- |
| `web/server/` | FastAPI(`app/`) · 화면(`web/`, three.js 포함) · `pyproject.toml` |
| `web/deploy/` | `deploy.sh` · `nginx-catalog.conf` · `catalog-api.service` |
| `web/local/` | 프리뷰(GLB·썸네일) 생성 도구 |
| `web/Jenkinsfile` | 자동 배포 파이프라인 정의 — Jenkins 잡이 이 경로를 읽는다 |

자료(유물 파일·프리뷰·`catalog.db`)는 저장소에 넣지 않는다. `web/.gitignore` 로 막아 뒀다.

## 여기에 넣지 않는 것

| 대상 | 어디로 |
| --- | --- |
| 자산 검사·빌드 **스크립트** | `tools/` |
| 제품 명세·결정 기록 | `docs/` |
| **유물 자료·프리뷰·DB** | 저장소에 넣지 않는다. 서버 `/srv/catalog/` 와 로컬 `~/c201-assets/` (2026-09-10 결정: 코드는 `web/` 에 넣되 자료는 제외) |
| 3D 원본·모델 가중치 | 저장소 밖 — EC2 자료 서버 (PLAN.md 6장), `.gitignore` 처리됨 |

## 자료 서버는 팀 내부 도구다

- 팀 3D 자료를 EC2(`$SERVER_HOST`)에서 압축 해제 상태로 제공하고, 브라우저 3D 미리보기와 검색을 붙인다.
- **제품 범위 밖이다.** 명세 5.3에서 웹·API 서버는 MAY이고, D-26/D-37은 "현재 범위 아님"이다.
  발표 산출물·시연에 포함하지 않는다.
- 근거: `FR-OPS-005`(MUST, 3D 데이터를 한곳에 정리), `U-12`(공유 스토리지 위치).
- Jira: Epic `S15P21C201-114`, 관련 `S15P21C201-50` / `-51` / `-52` / `-121`(코드·CI).
- 운영 중: http://$SERVER_HOST/ (자료 서버, 인증 없음) · http://$SERVER_HOST:8912/ (Jenkins, 로그인 필요)
- **서버 주소는 저장소에 두지 않는다.** `web/.env.example` 을 `web/.env` 로 복사해 `SERVER_HOST` 를 채운다(값은 팀원에게).
  문서의 `$SERVER_HOST`·`$env:SERVER_HOST` 가 이 값이다 — bash `set -a; . infra/web/.env; set +a` ·
  PowerShell `$env:SERVER_HOST = '<값>'`. SSH·scp 는 `c201` 별명을 쓴다([JENKINS_BUILD_GUIDE.md](JENKINS_BUILD_GUIDE.md) 1절).
- **`web/` 을 고쳐 `dev` 에 병합하면 자동 배포된다.** 다른 폴더만 바뀐 커밋은 배포되지 않는다.

## 관련 명세

- Infra 책임 범위: `docs/PROJECT_MASTER_SPEC.md` 6.2
- 빌드·운영 요구사항: 12.4 (`FR-OPS-001` ~ `006`)
- 저장소·빌드 스택: 22.3
- 미확정 항목: 4부 `U-12`
