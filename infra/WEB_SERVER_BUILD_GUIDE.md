# 웹 배포 가이드 — 내 PC 의 화면·API 를 서버에 올려 공개하기

"배포"가 여기서 뜻하는 것: **파일을 서버로 복사하고, nginx 가 화면을, systemd 가 API 를 띄우게 하는 것.** 빌드도 Docker 도 없다.
아래는 실제로 한 순서 그대로이고, 명령마다 `#` 주석이 "왜 이걸 하는지"다.

```
내 PC                                   ssh (22)                  서버 /srv/catalog/
server/web/   ─────────────────────────────────────────────▶  web/        → nginx 가 :80 에서 그대로 내줌
server/app/   ─────────────────────────────────────────────▶  app/        → systemd 가 uvicorn 으로 :8412 (내부)
server/pyproject.toml ─────────────────────────────────────▶  pyproject   → uv sync 가 의존성 설치
deploy/nginx-catalog.conf ─────────────────────────────────▶  /etc/nginx/sites-available/catalog
deploy/catalog-api.service ────────────────────────────────▶  /etc/systemd/system/catalog-api.service
```

셸 표기: `PowerShell` 은 그냥 명령, `Git Bash` 는 `tar | ssh` 파이프 (PowerShell 에서는 바이너리가 깨진다).

---

## 0. 처음 한 번만 — 서버 준비 (이미 되어 있음)

```bash
ssh c201                                   # ~/.ssh/config 별명. pem 은 바탕화면, 권한은 본인만 읽기
sudo apt-get install -y nginx              # 웹서버. 설치하면 자동으로 :80 에 기본 페이지가 뜬다
curl -fsSL https://astral.sh/uv/install.sh | sh    # uv: 파이썬 의존성·실행. ~/.local/bin/uv
sudo mkdir -p /srv/catalog/{files,preview,app,web,zips} && sudo chown -R ubuntu:ubuntu /srv/catalog   # 우리 자리. ubuntu 소유라 sudo 없이 복사 가능
sudo ufw allow 80/tcp                      # 방화벽. 22 는 절대 건드리지 않는다 (SSAFY 지침 6번)
```

확인: `ssh c201 "systemctl is-active nginx; ~/.local/bin/uv --version; sudo ufw status | grep 80"`

---

## 1. 배포 한 번에 — `deploy.sh`

```bash
# Git Bash
cd /c/Users/SSAFY/source/repos/c201-asset-server && bash deploy/deploy.sh
```

아래 2~6절이 이 스크립트가 하는 일이다. **스크립트 없이 손으로 해도 같은 결과**가 나오게 절마다 명령을 그대로 적었다.

---

## 2. 파일 복사

```bash
# Git Bash — 내 PC 에서
tar -cf - -C server app web pyproject.toml \        # server/ 안의 세 항목을 tar 스트림으로
  | ssh c201 "tar -xf - -C /srv/catalog \           # 서버에서 /srv/catalog 밑에 풀기 → app/ web/ pyproject.toml 이 덮어써진다
              && rm -rf /srv/catalog/app/__pycache__ \   # 내 PC 파이썬 캐시가 따라가면 지운다
              && mkdir -p /srv/catalog/zips"        # ZIP 캐시 폴더
```

- **왜 tar|ssh 인가** — rsync 가 내 PC 에 없다. 파일 수십 개를 연결 1회로 보내는 데 scp 보다 빠르다.
- **덮어쓰기만 하고 지우지 않는다.** 내 PC 에서 파일을 삭제해도 서버에는 남는다. 지워야 하면 서버에서 직접 `rm`.
- `files/` `preview/` `catalog.db` 는 여기 포함되지 않는다 — 자료와 DB 는 배포와 별개(RUNBOOK 2·4·5절).

확인:
```powershell
ssh c201 "ls -la /srv/catalog/web /srv/catalog/app"
```

---

## 3. 파이썬 의존성

```bash
ssh c201 "cd /srv/catalog && ~/.local/bin/uv sync --quiet"     # pyproject.toml 을 읽어 .venv/ 에 fastapi·uvicorn 설치. 이미 맞으면 0초
ssh c201 "cd /srv/catalog && ~/.local/bin/uv run python -c 'import fastapi; print(fastapi.__version__)'"   # 0.141.1
```

- `uv` 는 `~/.local/bin/` 에 있어 **절대경로**로 부른다. ssh 로 들어온 비대화형 셸은 `PATH` 에 그게 없다.
- 시스템 파이썬(3.12)에는 아무것도 설치하지 않는다. 전부 `/srv/catalog/.venv/` 안.

---

## 4. DB — 없을 때만 만든다

```bash
ssh c201 "cd /srv/catalog && [ -f catalog.db ] && echo '있음' || \
  CATALOG_FILES=/srv/catalog/files CATALOG_DB=/srv/catalog/catalog.db CATALOG_PREVIEW=/srv/catalog/preview \
  ~/.local/bin/uv run python app/scan.py"          # files/ 를 훑어 catalog.db 생성 (1초)
```

- **배포는 DB 를 지우지 않는다.** 팀원이 웹에서 적은 메모·태그가 배포 때문에 사라지는 일이 없다.
- DB 를 갱신하려면 배포가 아니라 **재스캔**(`POST /api/rescan`, RUNBOOK 6절).

---

## 5. nginx — 화면과 파일을 :80 으로

```bash
scp deploy/nginx-catalog.conf c201:/tmp/catalog.conf
ssh c201 "sudo install -m 644 /tmp/catalog.conf /etc/nginx/sites-available/catalog \   # 설정 파일 놓기
       && sudo ln -sf /etc/nginx/sites-available/catalog /etc/nginx/sites-enabled/catalog \   # 켜기 (심볼릭 링크)
       && sudo rm -f /etc/nginx/sites-enabled/default \   # 기본 '환영' 페이지 끄기 — 둘 다 :80 default_server 라 충돌한다
       && sudo nginx -t \                                  # 문법 검사. 여기서 실패하면 reload 안 함 (&&)
       && sudo systemctl reload nginx"                     # 무중단 반영
```

### `nginx-catalog.conf` 한 줄씩

```nginx
types { model/gltf-binary glb; }        # .glb 는 nginx 기본 MIME 에 없다. 없으면 octet-stream 으로 나간다

server {
    listen 80 default_server;           # 도메인·IP 어느 쪽으로 와도 이 서버 블록
    root  /srv/catalog/web;             # ★ 화면 파일이 있는 곳. 2절에서 복사한 web/
    index index.html;

    location / {                        # 화면
        try_files $uri $uri/ /index.html;   # 없는 경로는 index.html 로 (해시 라우팅이라 서버는 한 파일만 안다)
        add_header Cache-Control "no-cache";  # 배포 직후 옛 app.js 를 오래 쓰지 않게
    }
    location /api/ {                    # API 만 파이썬으로
        proxy_pass http://127.0.0.1:8412/api/;   # ★ systemd 가 띄운 uvicorn. 127.0.0.1 이라 밖에서 8412 로 직접은 못 온다
        proxy_read_timeout 1800s;               # /api/rescan 이 오래 걸릴 수 있어
    }
    location /files/ {                  # 자료 원본 — nginx 가 디스크에서 바로. 파이썬을 거치지 않는다
        alias /srv/catalog/files/;
        autoindex on;                   # 폴더 목록 보이기 (인증 없음 결정 AS-04 에 맞춤)
        gzip_static on;                 # 옆에 .gz 가 있으면 그걸 보냄 (make_gz.py 가 만든 것). 전송량 1/3
        location ~* \.(obj|mtl|ply|stl|las|npy)$ {
            add_header Content-Disposition 'attachment';   # 텍스트 포맷이 브라우저 화면에 뿌려지지 않고 저장되게
            add_header Access-Control-Allow-Origin *;      # ★ alias 안 중첩 location 은 바깥 add_header 를 상속하지 않는다 → 다시 적음
            gzip_static on;
        }
    }
    location /zips/  { alias /srv/catalog/zips/;  add_header Content-Disposition 'attachment'; }   # 폴더 ZIP
    location /preview/ { alias /srv/catalog/preview/; gzip_static on; add_header Cache-Control "public, max-age=604800"; }   # GLB·썸네일. 자주 안 바뀌니 1주 캐시
}
```

확인:
```powershell
ssh c201 "sudo nginx -t"                                      # syntax is ok
curl.exe -sI http://$env:SERVER_HOST/ | findstr HTTP        # HTTP/1.1 200
curl.exe -sI http://$env:SERVER_HOST/preview/bon004740_seogamni-gold-buckle-pyeongyang/source.glb | findstr Content-Type   # model/gltf-binary
```

---

## 6. systemd — API 를 서비스로

```bash
scp deploy/catalog-api.service c201:/tmp/catalog-api.service
ssh c201 "sudo install -m 644 /tmp/catalog-api.service /etc/systemd/system/catalog-api.service \
       && sudo systemctl daemon-reload \            # 유닛 파일 바뀐 걸 systemd 에 알림
       && sudo systemctl enable --quiet catalog-api \   # 부팅 시 자동 시작 (enable 만 하면 지금은 안 뜬다)
       && sudo systemctl restart catalog-api \      # 지금 (재)시작 — 코드가 바뀌었으니 restart. reload 아님
       && sleep 2 && systemctl is-active catalog-api"   # active
```

### `catalog-api.service` 한 줄씩

```ini
[Unit]
Description=C201 asset catalog API (FastAPI, 127.0.0.1:8412)
After=network.target                         # 네트워크 뜬 뒤에

[Service]
User=ubuntu                                  # root 로 돌리지 않는다
WorkingDirectory=/srv/catalog                # app.main 을 찾는 기준 폴더
Environment=CATALOG_ROOT=/srv/catalog        # main.py 가 읽는 경로들 — 로컬(dev.py)과 서버가 이 변수로만 다르다
Environment=CATALOG_DB=/srv/catalog/catalog.db
Environment=CATALOG_FILES=/srv/catalog/files
Environment=CATALOG_PREVIEW=/srv/catalog/preview
Environment=CATALOG_ZIPS=/srv/catalog/zips
ExecStart=/home/ubuntu/.local/bin/uv run --project /srv/catalog uvicorn app.main:app --host 127.0.0.1 --port 8412 --workers 2
#          ↑ 절대경로 (systemd 에는 PATH 가 없다)                              ↑ 127.0.0.1: 외부 노출 없음   ↑ 8412: SSAFY "기본 포트 피하라"
Restart=always                               # 죽으면 살린다
RestartSec=3

[Install]
WantedBy=multi-user.target                   # enable 하면 부팅 시퀀스에 들어감 → 재부팅 후 자동 기동 (AS-AT-09)
```

확인:
```powershell
ssh c201 "systemctl status catalog-api --no-pager | head -5"
ssh c201 "curl -s http://127.0.0.1:8412/api/health"          # {"ok":true,...}  ← 서버 안에서만 8412 로 닿는다
curl.exe -s http://$env:SERVER_HOST/api/stats               # 밖에서는 nginx 를 거쳐 /api 로
```

---

## 7. 배포 끝났는지 — 다섯 가지

```powershell
curl.exe -s -o NUL -w "%{http_code}`n" http://$env:SERVER_HOST/              # 200  화면
curl.exe -s -o NUL -w "%{http_code}`n" http://$env:SERVER_HOST/api/stats     # 200  API
curl.exe -s -o NUL -w "%{http_code}`n" http://$env:SERVER_HOST/files/        # 200  파일 목록
ssh c201 "systemctl is-active nginx catalog-api"                                # active active
ssh c201 "systemctl is-enabled nginx catalog-api"                               # enabled enabled  ← 재부팅 대비
```

브라우저에서 **http://$SERVER_HOST/** → `3D 148 · 2D 228` 이 뜨고 카드 하나 클릭해 뷰어가 돌면 끝.
화면이 옛것처럼 보이면 **Ctrl+F5** (열려 있던 탭이 옛 `app.js` 를 쓰고 있을 수 있다).

---

## 8. 서버에서 3D 미리보기(GLB) 만들기 — Blender 설치

웹에서 복원본을 올리면 **서버가 직접** 경량 GLB 와 썸네일을 만든다. 이게 없으면 올린 파일은
목록에 뜨지만 빙글빙글 돌려 볼 수는 없다(다운로드만 된다).

> **GLB 가 뭔가.** glTF 의 단일 파일 형태 — 메시·재질·텍스처가 한 파일에 들어간 웹 3D 표준이다.
> 원본 OBJ 세트(모델+MTL+텍스처, 60~140MB)를 브라우저가 그대로 받으면 느리므로,
> **20만 삼각형 · 2K 텍스처로 줄인 사본**을 따로 두고 화면에는 그걸 보여준다.
> 원본은 `/files/` 와 폴더 ZIP 으로 그대로 받을 수 있다 — GLB 는 원본을 대체하지 않는다.

### 8-1. 왜 서버에서 되나

데시메이션·텍스처 축소·glTF 내보내기·썸네일 렌더는 **전부 CPU 작업**이다. 썸네일도 Workbench
엔진이라 소프트웨어 렌더로 충분하다. **GPU 가 없는 이 서버(4코어)로 된다** — 실측 8.1초 / GLB 0.57MB.

계획서 `AS-05`("변환은 로컬 GPU에서")는 148건을 **한 번에** 돌릴 때의 이야기다.
업로드 한 건씩은 서버가 맡고, 대량 일괄은 여전히 로컬에서 돌린다(8-6).

### 8-2. 설치 (처음 한 번)

```bash
# 헤드리스(-b)로 돌려도 Blender 는 이 X 라이브러리들을 링크한다. 없으면 실행 자체가 안 된다.
# libegl1 을 빠뜨리면 --version 은 되는데 렌더에서만 죽는다 (아래 8-7 의 첫 줄)
sudo apt-get install -y libxi6 libxrender1 libxxf86vm1 libxfixes3 libgl1 libsm6 libxkbcommon0                         libegl1 libglx0 libgl1-mesa-dri libxext6 xz-utils

# -4 를 꼭 붙인다. 이 EC2 는 전역 IPv6 가 없는데 시스템이 IPv6 를 먼저 시도해 그냥 멈춘다
curl -4 -sfL -o /tmp/bl.tar.xz https://download.blender.org/release/Blender5.2/blender-5.2.1-linux-x64.tar.xz

sudo mkdir -p /opt/blender
sudo tar -xJf /tmp/bl.tar.xz -C /opt/blender --strip-components=1   # 1.2GB
sudo ln -sf /opt/blender/blender /usr/local/bin/blender            # 앱이 이 경로를 본다
rm -f /tmp/bl.tar.xz
```

**확인은 `--version` 으로 하지 말 것.** 버전 출력은 그래픽을 초기화하지 않아서,
렌더에서만 죽는 상태를 통과시킨다. 반드시 **실제로 한 장 렌더**해 본다:

```bash
blender -b --version                                     # Blender 5.2.1 LTS
SRC=$(ls /srv/catalog/files/originals/*/digital_obj/*.obj | head -1)
blender -b --python-exit-code 1 -P /srv/catalog/app/blender_preview.py --         "$SRC" /tmp/t.glb /tmp/t.png 60000 | grep PREVIEW_REPORT
ls -l /tmp/t.glb /tmp/t.png          # 둘 다 만들어져야 한다
```

`PREVIEW_REPORT {...}` 가 찍히고 GLB·PNG 두 파일이 나오면 된다.
`EGL Error (0x3009): EGL_BAD_MATCH` 경고는 소프트웨어 렌더로 넘어가는 것이라 무해하다.

### 8-3. 앱이 Blender 를 찾는 법

```python
# server/app/main.py
BLENDER = os.environ.get("BLENDER", "/usr/local/bin/blender")   # 절대경로 (systemd 에는 PATH 가 없다)
PREVIEW_TARGET_TRIS = 200_000                                   # 이 이상이면 데시메이트
```

다른 곳에 깔았다면 systemd 유닛에 `Environment=BLENDER=/경로/blender` 를 넣고
`sudo systemctl daemon-reload && sudo systemctl restart catalog-api`.

### 8-4. 만들어지는 흐름

```
브라우저 ──POST /api/artifacts/<유물>/restored──▶ 파일 저장 → 재스캔 → 즉시 응답(카드 먼저 뜬다)
                                                      │
                                                      └─ 백그라운드 스레드
                                                           blender -b -P blender_preview.py
                                                             OBJ/GLB/PLY/STL → 20만 삼각형 · 2K 텍스처
                                                             → preview/<유물>/restored.glb + .png
                                                           assets.preview_path 갱신
브라우저 ──GET /api/preview-status?asset=…──▶ 3초마다 물어보다 done 이면 뷰어를 켠다
```

**진행 상태는 `/srv/catalog/jobs/` 에 파일로 남긴다.** API 가 `--workers 2` 로 돌기 때문에
올린 워커와 상태를 묻는 워커가 다를 수 있어서다 — 메모리에 두면 절반은 상태를 못 본다.

```
/srv/catalog/jobs/<asset_id>.json        {"state":"running|done|failed", ...}
/srv/catalog/jobs/<asset_id>.json.lock   같은 카드를 두 번 돌리지 않게 하는 잠금 (O_EXCL)
```

이 폴더는 `deploy.sh` 와 젠킨스 배포가 **건드리지 않는다**(`app/`·`web/` 만 덮어쓴다).

| 엔드포인트 | 용도 |
| --- | --- |
| `GET /api/preview-status?asset=<asset_id>` | `running` / `done`(+`preview_url`) / `failed`(+`error`) / `none` |
| `POST /api/preview/rebuild?asset=<asset_id>` | 다시 만들기. 이미 돌고 있으면 `409` |

### 8-5. 손으로 돌려 보기

```bash
# 카드 하나 다시 만들기 (화면의 "지금 만들기"/"다시 시도" 와 같은 것)
A='bon000219_celadon-bottle/3d/restored'
curl -s -X POST "http://$SERVER_HOST/api/preview/rebuild?asset=$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1],safe=''))" "$A")"

# 진행 보기 (10~30초)
watch -n3 "curl -s 'http://$SERVER_HOST/api/preview-status?asset=...'"

# Blender 만 따로 — 앱을 거치지 않고 원인 보기
ssh c201
blender -b --python-exit-code 1 -P /srv/catalog/app/blender_preview.py --   /srv/catalog/files/restored/<유물>/digital_obj/<파일>.obj /tmp/t.glb /tmp/t.png 200000
# 마지막 줄 PREVIEW_REPORT {...} 에 tri_before/after, textures, up, flip 이 찍힌다
```

### 8-5-1. 형식별로 무엇이 도는가

| 올린 형식 | 처리 | 결과 |
| --- | --- | --- |
| `.glb` | **변환 없이 그대로 미리보기로 쓴다**(30MB 이하) → 올린 즉시 돌려 볼 수 있다. 뒤이어 Blender 가 경량 판본+썸네일을 만들어 덮어쓴다 | 즉시 + 경량 |
| `.obj` (+MTL·텍스처) | Blender — 20만 삼각형·2K 텍스처로 줄여 GLB 로 | GLB + 썸네일 |
| `.ply` · `.stl` | Blender | GLB + 썸네일 |
| `.las` | **Blender 는 LAS 를 못 읽는다.** `app/las_preview.py` 가 순수 파이썬으로 glTF POINTS 로 내보내고 썸네일은 PIL 로 점을 찍는다 | GLB(점군) + 썸네일 |
| `.gltf` 분리형 | 받지 않는다 — `.bin`·텍스처 참조가 흩어져 깨진다. **GLB 로 내보내서** 올린다 | — |

한 카드에 여러 개가 있으면 **OBJ > GLB > PLY > STL > LAS** 순으로 대표를 고른다.
같은 확장자가 여럿이면 이름에 `model` 이 든 것, 그다음 짧은 이름을 먼저 본다
(`model.obj` 가 중복번호 붙은 `model-2.obj` 보다 앞선다).

> **미리보기 URL 에 `?v=수정시각` 이 붙는다.** `/preview/` 는 nginx 가 7일 캐시를 걸어 주는데
> (GLB 가 크니 그게 맞다), 파일을 다시 만들면 URL 도 바뀌어야 한다 — 안 그러면 브라우저가
> 썸네일은 새것, GLB 는 캐시된 옛것을 써서 **목록과 상세가 서로 다른 유물처럼 보인다**.

### 8-6. 대량 일괄은 로컬에서

148건을 한 번에 만드는 건 여전히 내 PC 가 빠르다(19.7분). 서버로는 파일만 보낸다:

```bash
# 내 PC (Git Bash) — 로컬 Blender 로 전부 다시 만들고
cd ~/source/repos/S15P21C201/infra/web/local
python make_preview.py --force

# 통째로 보내기 (776MB, 자료·DB 는 안 건드린다)
cd ~/c201-assets
tar -czf - preview | ssh c201 "tar -C /srv/catalog -xzf -"

# 옮겨졌는지 — 양쪽 해시가 같아야 한다
find . -name '*.glb' -o -name '*.png' | sort | xargs stat -c "%n %s" | md5sum
ssh c201 "cd /srv/catalog/preview && find . -name '*.glb' -o -name '*.png' | sort | xargs stat -c '%n %s' | md5sum"
```

경로가 그대로라 **재스캔은 필요 없다**. 브라우저에 옛 썸네일이 남으면 `Ctrl+F5`.

> **유물이 누워 보일 때.** 박물관 OBJ 는 위 축이 파일마다 다르다(머리말과 실제가 다른 것도 있다).
> `blender_preview.py` 가 형상으로 추정하지만 틀리는 것이 있어, 그런 카드는
> `local/orientation_overrides.json` 에 `{"asset_id": {"up":"X|Y|Z", "flip":true|false}}` 로 지정한다.
> 판단이 애매하면 그 유물의 `photo_2d/` 사진과 맞춰 보면 된다.

### 8-7. 안 될 때

| 증상 | 원인 · 조치 |
| --- | --- |
| `blender rc=-6: Couldn't open libEGL.so.1` | **렌더 단계에서만 죽는다.** `libegl1` 누락 → 8-2 의 `apt-get`. GLB 는 만들어졌는데 썸네일에서 죽으면 DB 갱신이 안 되어 "미리보기가 아직 없습니다" 로 보인다 |
| 상태가 계속 `running` | Blender 가 오래 걸리는 중(큰 메시는 몇 분). 30분+2분 지나면 자동으로 `failed` 처리 |
| `Blender 가 없습니다: /usr/local/bin/blender` | 8-2 미실행 또는 심볼릭 링크 없음 |
| `blender rc=1 ... error while loading shared libraries` | X 라이브러리 누락 → 8-2 의 `apt-get` |
| `프리뷰로 쓸 3D 파일이 없습니다` | 이미지·기록만 올린 카드. OBJ·GLB·PLY·STL·LAS 중 하나가 있어야 한다 |
| `자료 폴더를 찾지 못했습니다` | AIHub 자료는 `aihub/<유물>/<변형>/` 로 한 칸 더 들어간다 — `_artifact_folder()` 가 세 배치를 다 본다 |
| LAS 썸네일이 안 나옴 | `pillow` 미설치 → `cd /srv/catalog && uv sync` (배포 스크립트가 해 준다) |
| `409 이미 생성 중입니다` | 잠금이 살아 있다. 워커가 죽어 남은 잠금이면 32분 뒤 자동 회수, 급하면 `sudo rm /srv/catalog/jobs/<…>.json.lock` |
| 색 없는 회색 모델 | OBJ 만 올리고 MTL·텍스처를 빠뜨림 → 폴더째 다시 올리기 |
| 디스크 | GLB+썸네일 148쌍에 776MB. `df -h /srv` 로 확인(현재 17G/309G) |

---

## 9. 배포 뒤 문제가 나면

| 보고 싶은 것 | 명령 |
| --- | --- |
| API 가 왜 죽었나 | `ssh c201 "sudo journalctl -u catalog-api -n 50 --no-pager"` |
| nginx 가 왜 500/502 인가 | `ssh c201 "sudo tail -30 /var/log/nginx/catalog.error.log"` |
| 누가 무엇을 받아갔나 | `ssh c201 "sudo tail -30 /var/log/nginx/catalog.access.log"` |
| API 만 다시 | `ssh c201 "sudo systemctl restart catalog-api"` |
| nginx 설정만 다시 | `ssh c201 "sudo nginx -t && sudo systemctl reload nginx"` |
| 화면을 잠시 내리기 | `ssh c201 "sudo ufw delete allow 80/tcp"` (되돌리기 `allow 80/tcp`) |
| 이전 코드로 되돌리기 | 내 PC 에서 이전 커밋으로 checkout 후 `bash deploy/deploy.sh` 다시 — 서버에 버전 보관은 없다 |

**502 Bad Gateway** = nginx 는 살았는데 8412 가 죽음 → `journalctl -u catalog-api`.
**403/404 on /files/** = 경로 오타 또는 권한 → `ls -la /srv/catalog/files`, 소유자가 `ubuntu` 인지.
**화면은 뜨는데 카드가 0** = DB 비었거나 경로 변수 틀림 → `curl 127.0.0.1:8412/api/health` 의 `db` 경로 확인.

---

## 10. 이 구성에서 일부러 안 한 것

| 안 한 것 | 이유 |
| --- | --- |
| Docker | 서버 한 대·서비스 한 개. 이미지 빌드·레지스트리가 순손실 (AS-06) |
| CI/CD | 팀 명세가 폐기(D-49). 배포는 `deploy.sh` 한 줄 |
| HTTPS | 443 이 열려 있어 가능하지만 팀 내부 도구라 80 으로. 필요해지면 certbot 한 번 |
| 인증 | 사용자 결정 (AS-04). 대신 **PATCH 로 고칠 수 있는 열은 코드가 제한**(`db.py` 화이트리스트), 8412 는 외부 차단 |
| 8000 포트 | SSAFY 지침 "기본 포트 변경" → 8412 |
