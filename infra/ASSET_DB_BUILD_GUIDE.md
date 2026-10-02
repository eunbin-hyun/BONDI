# 자료 서버 DB 배포 러너북 — 따라 하기

실제로 2026-09-07~08에 한 순서 그대로다. 단계마다 **확인** 명령이 있다. 확인이 다르면 다음으로 넘어가지 않는다.

| 위치 | 경로 |
| --- | --- |
| 자료·DB·프리뷰 (내 PC) | `C:\Users\SSAFY\c201-assets\` → `staging/` `catalog.db` `preview/` `work/` |
| 코드 (내 PC) | `C:\Users\SSAFY\source\repos\c201-asset-server\` |
| 서버 (EC2) | `ssh c201` → `/srv/catalog/` |

**셸 두 가지를 쓴다.** 명령 블록 첫 줄에 적어 뒀다.
- `PowerShell` — 일반 명령, ssh
- `Git Bash` — `tar | ssh` 파이프. **PowerShell 에서 `tar | ssh` 를 하면 바이너리가 깨진다.** (시작 메뉴 → Git Bash)

---

## 0. 한 장 그림

```
내 PC                                             EC2 ($SERVER_HOST)
─────────────────────────────                     ──────────────────────────────
staging/  9.31 GB  (정규화된 자료)  ──② tar|ssh──▶  /srv/catalog/files/
preview/  775 MB   (GLB·썸네일)     ──④ tar|ssh──▶  /srv/catalog/preview/
server/app, web    (코드·화면)      ──⑤ deploy──▶  /srv/catalog/app, web
                                                   /srv/catalog/catalog.db  ◀── ⑥ scan.py (서버에서 생성)
① scan.py → catalog.db (로컬 시험판)               nginx:80 ─▶ 화면·/files·/preview
③ make_preview.py → preview/                       FastAPI:8412(내부) ─▶ /api → catalog.db
```

DB 는 **서버에서 새로 만든다.** 로컬 `catalog.db` 는 구조·한글·검색을 미리 검증하는 시험판이다. 두 트리(`staging/` = `files/`)가 같아서 결과가 같다.

---

## 1. 로컬에서 DB 만들어 보기 (시험판)

```powershell
# PowerShell
cd C:\Users\SSAFY\source\repos\c201-asset-server\server\app
python scan.py
```

`scan.py` 는 `~/c201-assets/staging/` 을 훑어 `~/c201-assets/catalog.db` 를 만든다. 1초.

**확인**
```powershell
cd C:\Users\SSAFY\c201-assets
python query.py                 # artifacts 231 · assets 376 · files 1654
python query.py 반가            # 카드 10건 (원본 4·복원 2·사진 4)
python query.py files 달항아리  # 파일 목록 + /files/… URL
```

내용을 엑셀로 보려면 `db_export\cards.csv` `artifacts.csv` `files.csv`.

한글이 비었거나 이상하면 여기서 고친다 — 코드가 아니라 데이터 파일이다.

| 고칠 것 | 어디 |
| --- | --- |
| 유물 한글명·시대·재질 | `staging/<그룹>/<유물>/_meta.json` |
| 공식 설명 없는 유물의 설명 | `server/app/descriptions_ko.json` (소장품번호 → 문장) |
| 한자만인 이름 | `server/app/scan.py` 의 `NAME_KO_FIX` |

고친 뒤 `python scan.py` 다시. 표를 통째로 다시 만들지만 **웹에서 사람이 적은 메모·태그·담당자는 유지**된다.

---

## 2. 자료 전송 — `staging/` → 서버 `files/`

```bash
# Git Bash
bash ~/c201-assets/work/transfer.sh
```

그룹(`photos_2d` → `aihub` → `restored` → `originals`)별로 `tar | ssh` 로 보내고, 그룹마다 **파일 수·바이트를 원격과 대조**한다. 중간에 끊기면 다시 실행 — 이미 일치하는 그룹은 건너뛴다.

실측: 5.3 MB/s, 9.31 GB 에 **30분**.

**확인** (`transfer.log` 마지막 줄들)
```
originals: 완료 ✓  1544s  5.3 MB/s
원격 합계: 1944 파일  9.4G
```
```powershell
ssh c201 "find /srv/catalog/files -type f | wc -l"     # 1944
```

---

## 3. 프리뷰 만들기 — 3D 카드마다 GLB + 썸네일 (로컬)

```powershell
# PowerShell
cd C:\Users\SSAFY\source\repos\c201-asset-server\local
python make_preview.py
```

`catalog.db` 의 3D 카드 148건을 돌며 대표 파일(OBJ > PLY > STL > LAS)을 골라
- 메시 → Blender 헤드리스: 원점·2 m 정규화, 20만 삼각형으로 데시메이션, 텍스처 2K, GLB + 512px PNG
- 점군(LAS) → 순수 파이썬: 30만 점 이하로 추려 GLB(POINTS) + PNG

결과 `~/c201-assets/preview/<유물>/<variant>.glb .png`. 148건 **15분**. 이미 있는 건 건너뛴다 (`--force` 로 다시).

**확인**
```powershell
Get-ChildItem C:\Users\SSAFY\c201-assets\preview -Recurse -Filter *.glb | Measure-Object   # Count 148
python scan.py   # (server\app 에서) 다시 돌리면 preview_path 가 채워진다
python C:\Users\SSAFY\c201-assets\query.py sql "SELECT preview_kind, COUNT(*) FROM assets GROUP BY 1"   # glb 148 · image 228
```

썸네일을 눈으로 훑으려면 `work\preview_contact.jpg`.

> 처음엔 불상이 옆으로 누워 나왔다. 박물관 스캔이 Z-up 인데 Blender 가 Y-up 으로 읽어 90° 돌린 것. `blender_preview.py` 에서 `up_axis="Z"` 로 고쳤다.

---

## 4. 프리뷰 전송

```bash
# Git Bash
cd ~/c201-assets && tar -cf - preview | ssh c201 "tar -xf - -C /srv/catalog"
```

**확인**
```powershell
ssh c201 "find /srv/catalog/preview -type f | wc -l"    # 296 (glb 148 + png 148)
```

---

## 5. 코드·설정 배포 → 서비스 기동

```bash
# Git Bash
cd /c/Users/SSAFY/source/repos/c201-asset-server && bash deploy/deploy.sh
```

`deploy.sh` 가 하는 일 (순서대로, 각각 단독으로도 실행 가능):

| # | 하는 일 | 서버 명령 |
| --- | --- | --- |
| 1 | `server/app` `server/web` `pyproject.toml` 전송 | `tar \| ssh … -C /srv/catalog` |
| 2 | 파이썬 의존성 | `cd /srv/catalog && uv sync` |
| 3 | **DB 생성** (없을 때만) | `uv run python app/scan.py` |
| 4 | nginx 설정 | `/etc/nginx/sites-available/catalog` 설치 → `nginx -t` → `reload` |
| 5 | systemd 서비스 | `catalog-api.service` 설치 → `enable --now` |
| 6 | 확인 | `/api/health`, 외부 `HTTP 200` |

**확인**
```powershell
ssh c201 "systemctl is-active catalog-api nginx"          # active active
ssh c201 "curl -s http://127.0.0.1:8412/api/health"       # {"ok":true,...}
curl.exe -s http://$env:SERVER_HOST/api/stats           # 카드 수 JSON
```
브라우저: **http://$SERVER_HOST/**

실측(2026-09-08 11:29): `fastapi 0.141.1` · 서버 DB `artifacts 231 · assets 376 · files 1654` (로컬 시험판과 동일) · 외부 `/` `/api/stats` `/files/` 모두 200.

### 5-1. 텍스트 파일 사전 압축 (AS-AT-08: 전송량 1/3)

nginx `gzip_static` 은 `파일.gz` 가 옆에 있어야 동작한다. 파일이 이미 서버에 있으니 **서버에서** 만든다.

```powershell
ssh c201 "cd /srv/catalog && nohup ~/.local/bin/uv run python app/make_gz.py > make_gz.log 2>&1 &"
ssh c201 "cat /srv/catalog/make_gz.log"          # 만듦 N · … GB → … GB (%)
```

OBJ·MTL·JSON·LAS 와 ASCII 인 PLY/STL 만 압축한다 (판정 규칙은 `make_gz.py` 머리말). 새 파일을 넣은 뒤에도 한 번 더 돌린다.

**확인**
```powershell
curl.exe -sI -H "Accept-Encoding: gzip" http://$env:SERVER_HOST/files/originals/bon002789_pensive-bodhisattva-nt78/digital_obj/bon002789_model.obj
# Content-Encoding: gzip 이 있고 Content-Length 가 원본(23,933,031)보다 훨씬 작아야 한다
```

---

## 6. 운영 — 파일을 새로 넣었을 때

DB 는 파일을 감시하지 않는다. **넣고 → 재스캔** 두 단계다.

```bash
# Git Bash — 예: 새 유물 폴더를 originals/ 에 추가한 뒤
tar -cf - -C ~/c201-assets/staging originals/<새폴더> | ssh c201 "tar -xf - -C /srv/catalog/files"
```
```powershell
curl.exe -s -X POST http://$env:SERVER_HOST/api/rescan     # 또는 화면 하단 [재스캔] 버튼
```

새 유물 폴더 규칙 (안 지키면 이름이 폴더명으로, 파일이 `other` 로 들어간다):
```
originals/<소장품번호>_<영문슬러그>/
├── _meta.json          name_ko · period · material · category · size (한글)
├── digital_obj/  scan_ply/  print_stl/     ← 3D
└── photo_2d/                               ← 2D
```

프리뷰까지 붙이려면 로컬에서 `python scan.py` → `python make_preview.py` → 4번(전송) → 재스캔.

---

## 6-1. 폴더 통째로 받기 (ZIP)

OBJ 는 `mtllib` → MTL → `map_Kd` 텍스처가 **같은 폴더**에 있어야 열린다. 파일 하나씩 받으면 못 연다.
카드 상세의 **"폴더 통째로 받기"** 에서 `digital_obj/` 등 폴더별 ZIP 을 받는다. 풀면 `<유물폴더>/digital_obj/…` 구조가 그대로 나온다.

```
GET /api/groups?asset=<asset_id>                → 폴더별 파일 수·용량
GET /api/zip?asset=<asset_id>&group=digital_obj → ZIP 만들고(없을 때만) /zips/<번호>_<variant>_<그룹>.zip 으로 302
```

ZIP 은 `/srv/catalog/zips/` 에 캐시된다(저장만, 압축 안 함 — 이미 jpg 라). 원본이 더 새로우면 자동으로 다시 만든다.
실측: lkh000002 모델 세트 66.5MB — 첫 요청 빌드 1초 미만, 두 번째부터 0.03초(캐시).

캐시 비우기: `ssh c201 "rm -f /srv/catalog/zips/*.zip"` (다음 요청 때 다시 만들어진다).

---

## 7. 서버 상태 보기 (자주 쓰는 것)

```powershell
ssh c201
```
```bash
df -h /                                    # 디스크 (309G 중 ~10G 사용)
systemctl status catalog-api --no-pager    # API
sudo journalctl -u catalog-api -n 30       # API 로그
sudo tail -20 /var/log/nginx/catalog.access.log
sudo ufw status                            # 22 · 80 만 열림
sqlite3 /srv/catalog/catalog.db "SELECT media_type, COUNT(*) FROM assets GROUP BY 1"   # (sqlite3 없으면 sudo apt install sqlite3)
```

---

## 8. 되돌리기

| 상황 | 명령 |
| --- | --- |
| 화면을 잠시 내리고 싶다 | `ssh c201 "sudo ufw delete allow 80/tcp"` (다시: `allow 80/tcp`) |
| API 만 재시작 | `ssh c201 "sudo systemctl restart catalog-api"` |
| DB 를 처음부터 | `ssh c201 "rm /srv/catalog/catalog.db"` → 재스캔 (메모·태그는 사라진다 — 먼저 `cp catalog.db catalog.bak`) |
| nginx 기본 페이지로 | `sudo rm /etc/nginx/sites-enabled/catalog && sudo ln -s ../sites-available/default /etc/nginx/sites-enabled/ && sudo systemctl reload nginx` |

---

## 9. 막혔던 것들 (같은 데서 막히면)

| 증상 | 원인 | 처치 |
| --- | --- | --- |
| `ssh` 가 `Bad permissions … UNPROTECTED PRIVATE KEY` | pem 을 다른 계정도 읽을 수 있음 | `icacls pem /inheritance:r` → `/grant:r "$env:USERNAME:(R)"` |
| `ssh: Could not resolve hostname …iossh` | 명령을 두 번 붙여넣음 | 다시 |
| 재부팅 직후 `Connection closed by … port 22` | 부팅 중 | 1분 뒤 다시 |
| 사진 URL 이 `text/html` 로 옴 | 경로 정규식이 연도 `/2019/` 까지 지움 | 파일명 앞 크기 구간만 지우게 `(?=[^/]+$)` |
| 파일명에 공백 (`ssu01846 .jpg`) 이 거부됨 | urllib 이 공백 불허 | 경로만 `urllib.parse.quote` |
| 썸네일·뷰어에서 유물이 누워 있음 | 박물관 OBJ 가 **두 종류**: `# WaveFront *.obj file` (스캐너, Z-up) 105개 / `# Blender v3.2.1 OBJ File` (Y-up) 15개 | `blender_preview.py` 가 OBJ 머리말을 읽어 축을 고른다. 새 OBJ 가 또 누우면 머리말을 확인해 규칙 추가 |
| `PATCH` 응답에 `owner` 가 없음 | 뷰 `v_cards` 에 열이 없었음 | 스키마에서 `DROP VIEW` 후 재생성 |
| 재스캔하면 메모가 사라짐 | 표를 통째로 다시 만듦 | `scan.py` 가 `tags/note/owner/method` 를 떠 두고 복원 |
| `curl -d '{"note":"한글"}'` 이 `400 error parsing the body` | Windows 콘솔이 한글을 CP949 로 보냄 → JSON 이 UTF-8 이 아님 | 한글 PATCH 는 브라우저(웹 화면) 나 Python `urllib` 로. 서버 쪽 문제 아님 |
| 재스캔 후 3D 카드 미리보기가 없음 | `preview/` 를 아직 안 보냈거나 경로가 다름 | 4번 전송 후 재스캔. 경로는 `preview/<artifact_id>/<variant>.glb` |
