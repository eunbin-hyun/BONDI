# 웹 화면 만들기 → 로컬 확인 → 배포 가이드

DB 러너북(`ASSET_DB_BUILD_GUIDE.md`)의 짝. **웹(화면)과 API 를 내 PC 에서 만들고 확인한 뒤 서버에 올리는** 과정을, 실제로 한 순서와 실제 코드로 적었다. 코드 발췌마다 `←` 주석이 "왜 그렇게 했는지" 다.

---

## 0. 전체 흐름 한 장

```
내 PC                                                      서버 (EC2)
─────────────────────────────────────────                  ─────────────────────────────
server/web/   index.html · app.css · app.js · viewer.js    /srv/catalog/web/    ← nginx 가 그대로 내줌
server/app/   main.py (API) · db.py · scan.py              /srv/catalog/app/    ← systemd 가 uvicorn 으로 실행
server/dev.py 로컬 확인용 (nginx 역할까지 흉내)             nginx-catalog.conf   ← /  /files  /preview  /zips  /api
deploy/deploy.sh ─────────── tar | ssh ──────────────────▶ 코드 복사 · uv sync · nginx reload · 서비스 재시작

작업 한 바퀴:  코드 수정 → python dev.py 로 127.0.0.1:8412 에서 확인 → bash deploy/deploy.sh → 공개 URL 확인
```

빌드 도구(npm·webpack)는 **없다.** HTML·CSS·JS 파일을 그대로 서빙한다. three.js 는 `web/vendor/` 에 파일로 복사해 뒀다.

---

## 1. 파일이 각각 무엇인가

```
server/web/
├── index.html    화면 뼈대. 두 "페이지"(목록·상세)가 한 파일에 있고 hidden 으로 전환
├── app.css       스타일. CSS 변수로 색 관리
├── app.js        화면 로직 전부: 목록·검색·상세·미리보기·비교·편집·재스캔
├── viewer.js     three.js 뷰어 (GLB 메시·점군 로드, 카메라 동기화)
└── vendor/       three.module.js + OrbitControls + GLTFLoader (0.170.0 고정)

server/app/
├── main.py       FastAPI. 화면이 부르는 /api/* 전부
├── db.py         SQLite 연결·질의 도우미, 수정 가능 열 화이트리스트
├── scan.py       files/ → catalog.db  (RUNBOOK 1·5절)
├── make_gz.py    .gz 사전 압축 (RUNBOOK 5-1절)
└── schema.sql    표 정의 + v_cards 뷰

server/dev.py     로컬에서 web·/files·/preview·/zips·/api 를 한 포트로 (서버의 nginx 역할 대행)
deploy/
├── deploy.sh             코드 전송 → uv sync → DB(없으면) → nginx → systemd → 확인
├── nginx-catalog.conf    서버 nginx 설정
└── catalog-api.service   systemd 유닛 (포트 8412, 환경변수)
```

---

## 2. 화면이 API 를 부르는 방식

화면은 DB 를 모른다. **JSON 만 요청**한다. 유저플로우 4단계가 그대로 엔드포인트다.

| 화면 동작 | 호출 | 응답에서 쓰는 것 |
| --- | --- | --- |
| 첫 화면 · 3D/2D 개수 | `GET /api/stats` | `by_media['3d'].cards` |
| 목록 (3D 선택, 검색어) | `GET /api/cards?media=3d&q=반가&limit=60&offset=0` | `items[]` — `title_ko` `thumb_url` `badges` |
| 카드 클릭 | `GET /api/cards/<asset_id>` | `files[]` (`url`·`preview_url`·`label_ko`), `siblings[]`, `artifact` |
| 폴더 ZIP 버튼 | `GET /api/groups?asset=<asset_id>` → 버튼마다 `GET /api/zip?asset=…&group=…` | 302 → `/zips/….zip` |
| 메모 저장 | `PATCH /api/artifacts/<id>` `PATCH /api/cards/<asset_id>` | 화이트리스트 열만 |
| 카드 ☆ 클릭 / 상세 ☆ | `PUT /api/favorites/<asset_id>` · 해제 `DELETE …` | `total` 로 상단 카운트 갱신 |
| 원본 상세 → 복원본 등록 | `POST /api/artifacts/<artifact_id>/restored` (multipart) | `stored[]` `reference_fixed[]` `asset_id` |
| 상단 "★ 즐겨찾기" 모드 | `GET /api/cards?starred=true&sort=vr` (2D·3D 모두) | `items[]` — **VR 가능한 것이 먼저**, 그다음 최신 등록순 |
| 복원 종류로 거르기 | `GET /api/cards?restore_type=shape` (shape\|color\|img2mesh\|symmetry\|pointr) | 해당 종류로 복원한 카드만 |
| 복원 종류 저장 | `PATCH /api/cards/<asset_id>` `{"restore_types":"color,img2mesh"}` | 사람이 고른 값이 추정보다 우선 |

즐겨찾기는 **팀 공용**이다(인증이 없으니 개인별이 아니다). 서버 `favorites` 표에 저장되고 재스캔에도 남는다. `v_cards.starred` 열로 목록·필터에 붙는다. 전시 후보 고를 때 후보를 ★ 로 모아 보는 용도.

### 복원 종류와 VR — 시연 흐름 (2026-09-17 피드백 반영)

**복원 종류.** "복원본 (팀 AI)" 한 덩어리로는 무엇을 복원했는지 모른다는 지적이 있었다. 카드마다 종류 배지를 따로 붙인다.

| 코드 | 배지 | 어떻게 정해지나 |
| --- | --- | --- |
| `shape` | 형태 | `_meta.json` 의 `restore_types` → 없으면 variant·`restoration_method` 글에서 추정 (`scan.py restore_types_of`) |
| `color` | 색 | 방식 글에 색·CIELAB·채색·질감 등이 있으면 |
| `img2mesh` | 2D→3D | 방식 글에 2D·사진·TRELLIS·LaS-Comp 등이 있으면 |
| `symmetry` | 회전대칭 | variant 가 `symmetry_restored` |
| `pointr` | 점군 완성 | variant 가 `pointr_*` |

- 저장 위치는 `assets.restore_types` (쉼표 구분). **사람이 상세 → 메모 탭에서 고른 값은 재스캔에도 남는다** (`keep_ast`).
- 열을 새로 붙일 때 `db._backfill_restore_types()` 가 기존 행을 한 번 채우므로, **배포만 해도 배지가 보인다**(재스캔은 `_meta.json` 까지 보고 더 정확히 덮어쓴다).
- 원본(`variant='source'`)은 비운다 — 복원한 것이 없다.

**VR.** 유물 태그(`artifacts.tags`)에 `VR` 을 넣으면 그 유물의 카드가 VR 대상이 된다. `v_cards.vr` 열이 태그를 읽어 1/0 으로 준다.
시연은 "즐겨찾기로 보여준 뒤 VR 로 넘어간다" 는 흐름이라, 즐겨찾기 목록은 `sort=vr` 로 **VR 가능한 것을 맨 앞에** 놓고 그 뒤에 구분선(`.vrsep`)을 긋는다.

### 복원본 등록 — 사용자는 파일만 올린다

원본 3D 카드 상세에만 나오는 기능. 유물명·시대·재질·출처·라이선스는 **원본 `_meta.json` 에서 상속**하므로 입력하지 않는다.

```
POST /api/artifacts/{artifact_id}/restored   (multipart/form-data)
  files      복원 결과 파일 여러 개 (obj mtl ply stl jpg png json txt md npy las)
  method     복원 방식 (선택)   owner 만든 사람 (선택)   note 메모 (선택)
  overwrite  기존 복원본을 바꿀 때만 true
```

서버가 하는 일:

1. **폴더 배치** — 확장자로 정한다. `obj/mtl/텍스처 → digital_obj`, `ply → scan_ply`, `stl → print_stl`, `json/txt/npy·비교이미지 → records`
2. **이름 정규화** — `<소장품번호>_restored_<역할>.<확장자>` (`model` `diffuse` `normal` `scan` `print` …). 역할 중복 번호는 **같은 확장자 안에서만** 센다 — `model.obj` 와 `model.mtl` 이 둘 다 `model` 이어야 하기 때문
3. **참조 재작성** — 이름이 바뀌었으므로 OBJ 의 `mtllib` 과 MTL 의 `map_*`·`norm`·`bump` 를 새 파일명으로 다시 쓴다. 이걸 안 하면 모델이 재질·텍스처를 못 찾는다
4. **`_meta.json` 생성** — 원본에서 상속 + `kind=restored`, `counterpart` 를 서로 가리키게 기록, `restoration_method/owner/note` 와 올린 원본 파일명(`source_files`) 보존
5. **한글 표지** `_<유물명>.md` 생성 (원본과 같은 방식)
6. **자동 재스캔** — 끝나면 복원본 카드가 바로 생기고 비교가 가능해진다

임시 폴더(`…​.uploading`)에 모두 받은 뒤 성공했을 때만 제자리로 옮긴다. 중간에 실패하면 반쯤 올라간 폴더가 남지 않는다.

7. **3D 미리보기 생성** — 업로드가 끝나면 백그라운드 스레드가 Blender 헤드리스로 GLB + 512px 썸네일을 만든다 (보통 10~30초, 실측 8.1초 / GLB 0.57MB).

nginx `client_max_body_size 2g` 와 `proxy_request_buffering off` 가 필요하다 (`deploy/nginx-catalog.conf`).

### 미리보기를 서버에서 만든다

원래는 로컬 PC 에서 `local/make_preview.py` 로 만들어 `tar | ssh` 로 보냈다(기존 148건이 그렇게 만들어졌다). 업로드 기능이 생기면서 **서버에서도 만들 수 있어야** 해서 Blender 5.2.1 을 서버에 설치했다.

> **GLB 생성은 GPU 가 필요 없다.** 데시메이션·텍스처 축소·glTF 내보내기는 전부 CPU 작업이고, 썸네일도 Workbench 엔진이라 소프트웨어 렌더로 충분하다. `AS-05`("변환은 로컬 GPU에서")는 148건을 한 번에 돌릴 때의 이야기고, 업로드 한 건씩은 서버로 충분하다.

```
/opt/blender/                  Blender 5.2.1 LTS (1.2GB), /usr/local/bin/blender 로 심볼릭 링크
server/app/blender_preview.py  local/ 의 사본 — 업로드 프리뷰용
/srv/catalog/jobs/             생성 진행 상태 (asset_id 당 JSON 하나) + 중복 실행 잠금
```

> **진행 상태를 왜 파일에 두나.** API 는 `uvicorn --workers 2` 로 돈다. 업로드를 받은 워커와
> 상태를 묻는 워커가 다를 수 있어서, 메모리에 두면 절반은 "생성 중"도 "실패"도 못 본다.
> `jobs/<asset_id>.json` 에 적고 `.lock` 파일(`O_EXCL`)로 중복 실행을 막는다 — 워커가 몇 개든 같게 동작하고,
> API 를 재시작해도 상태가 남는다. `jobs/` 는 배포 때 건드리지 않는다.

| 엔드포인트 | 용도 |
| --- | --- |
| `GET /api/preview-status?asset=` | 화면이 3초마다 물어본다. `running` / `done`(+`preview_url`) / `failed` |
| `POST /api/preview/rebuild?asset=` | 다시 만들기. 프리뷰가 없는 기존 카드의 **"지금 만들기"** 버튼과 실패 시 **"다시 시도"** 가 이걸 부른다 |

화면은 업로드 후 복원본 카드로 이동해 `waitPreview()` 로 완료를 기다리다가, 되면 뷰어를 자동으로 켠다.

서버에 Blender 를 설치하는 명령:
```bash
sudo apt-get install -y libxi6 libxrender1 libxxf86vm1 libxfixes3 libgl1 libsm6 libxkbcommon0 xz-utils
curl -4 -sfL -o /tmp/bl.tar.xz https://download.blender.org/release/Blender5.2/blender-5.2.1-linux-x64.tar.xz
sudo mkdir -p /opt/blender && sudo tar -xJf /tmp/bl.tar.xz -C /opt/blender --strip-components=1
sudo ln -sf /opt/blender/blender /usr/local/bin/blender
blender -b --version      # Blender 5.2.1 LTS
```
| [재스캔] | `POST /api/rescan` | `scan.artifacts` 등 |

`app.js` 의 호출 도우미 하나로 전부 처리한다:

```js
// app.js — fetch 한 겹 감싼 것. 실패하면 서버가 준 detail 을 에러 메시지로 던진다.
const api = async (p, opt) => {
  const r = await fetch(p, opt);
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.status);   // ← 400/404 의 이유를 화면에 그대로 보여주기 위해
  return r.json();
};
```

---

## 3. 화면 코드 읽기 — 핵심 부분에 주석

### 3.1 한 파일 두 페이지 (`index.html` + `app.js route()`)

```html
<main id="list" class="page"> … </main>          <!-- 목록 -->
<section id="detail" class="page" hidden> … </section>   <!-- 상세. hidden 으로 숨김 -->
```
```js
// app.js — URL 해시로 페이지를 정한다. 새로고침·뒤로가기·링크 공유가 그냥 된다.
function route() {
  const m = location.hash.match(/^#card\/(.+)$/);          // #card/<asset_id> 면 상세
  if (m) openCard(decodeURIComponent(m[1]));
  else { disposeViewers(); $('#detail').hidden = true; $('#list').hidden = false; if (!$('#grid').children.length) loadList(); }
}
window.addEventListener('hashchange', route);
```
`asset_id` 에 `/` 가 들어 있어(`bon…/3d/source`) 링크에 넣을 때는 `encodeURIComponent` 로 감싼다.

### 3.2 목록 — 카드 한 장 만들기

```js
function cardEl(c) {
  const el = document.createElement('article'); el.className = 'card';
  const th = c.thumb_url ? `<img loading="lazy" src="${c.thumb_url}" alt="">`      // ← lazy: 카드 376장 썸네일을 한 번에 안 받게
                         : `<span class="ph">${c.media_type === '3d' ? '◈' : '▣'}</span>`;
  el.innerHTML = `<div class="thumb ${c.media_type === '2d' ? 'photo' : ''}">${th}</div>
    <div class="cbody"><div class="ctitle">${esc(c.name_ko)}</div>                  // ← esc(): 유물명에 < > " 가 있어도 HTML 이 안 깨지게
    <div class="csub">${esc([c.period, c.material, c.museum].filter(Boolean).join(' · '))}</div>
    <div class="badges">${badge(c)}<span class="b">${c.file_count}개 · ${fmtMB(c.total_bytes)}</span></div></div>`;
  el.onclick = () => { location.hash = '#card/' + encodeURIComponent(c.asset_id); };  // ← 클릭 = 해시 변경 → route()
  return el;
}
```

### 3.3 검색 — 타이핑 멈추고 0.25초 뒤에 한 번만

```js
let t;
$('#q').addEventListener('input', () => {
  clearTimeout(t);
  t = setTimeout(() => { state.q = $('#q').value.trim(); loadList(); }, 250);   // ← 글자마다 요청하지 않게 (디바운스)
});
```
서버 쪽은 단어마다 `search_text LIKE '%단어%'` 를 AND 로 건다 — 유물 수백 건이라 이걸로 충분하다.

### 3.4 상세 — 미리보기 두 종류

```js
async function showPreview(file, card) {
  if (card.media_type === '2d' || (file && file.kind === 'photo')) {   // 2D: 클릭한 사진을 <img> 로 그대로
    const img = document.createElement('img'); img.src = file.url; pv.appendChild(img); return;
  }
  if (!state.viewer) state.viewer = createViewer(pv);                 // 3D: three.js 뷰어는 한 번만 만들어 재사용
  const info = await state.viewer.load(card.preview_url);             // ← 원본 OBJ(24MB) 가 아니라 경량 GLB(6MB) 를 읽는다
}
```
**왜 원본을 안 읽나** — 원본 OBJ+텍스처는 60~140MB 라 브라우저에서 느리다. Phase 2 에서 20만 삼각형·2K 텍스처로 줄인 GLB 를 미리 만들어 두고(RUNBOOK 3절) 그걸 읽는다. 원본은 다운로드용.

### 3.5 원본 ↔ 복원 비교 — 카메라 동기화

```js
state.viewer.onChange(() => state.viewer2.setPose(state.viewer.getPose()));   // 왼쪽 돌리면 오른쪽도
state.viewer2.onChange(() => state.viewer.setPose(state.viewer2.getPose()));  // 오른쪽 돌리면 왼쪽도
```
```js
// viewer.js — 되돌아오는 무한 루프를 막는 플래그
setPose(pose) { syncing = true; camera.position.fromArray(pose.p); controls.target.fromArray(pose.t); controls.update(); syncing = false; }
controls.addEventListener('change', () => { if (onChange && !syncing) onChange(camera, controls); });   // ← syncing 중엔 이벤트를 안 낸다
```

### 3.6 뷰어 — 메시와 점군을 같은 코드로

```js
// viewer.js — GLTFLoader 는 메시(Mesh)도 점군(Points)도 같은 scene 으로 준다
model.traverse((o) => {
  if (o.isPoints) o.material = new THREE.PointsMaterial({ size: 0.012, vertexColors: !!o.geometry.attributes.color });  // LAS→GLB 점군
  if (o.isMesh && o.material) o.material.side = THREE.DoubleSide;   // ← 스캔 메시는 뒷면이 뚫려 보이는 곳이 있어 양면 렌더
});
fit();   // 바운딩박스로 카메라 거리 계산. GLB 가 최대 2 m 로 정규화돼 있어 어떤 유물이든 같은 크기감
```

### 3.7 폴더 ZIP 버튼 (최근 추가 — "OBJ 는 폴더째 있어야 열린다")

```js
const g = await api('/api/groups?asset=' + encodeURIComponent(c.asset_id));   // 폴더별 파일 수·용량
g.groups.forEach((x) => {
  if (x.group === 'all' && g.groups.length === 2) return;     // ← 폴더가 하나뿐이면 '전체' 버튼은 중복이라 숨김
  li.innerHTML = `<a href="${x.zip_url}" class="${x.group === 'digital_obj' ? 'primary' : ''}"> …ZIP 받기</a>`;   // ← 모델 세트를 강조
});
```
`<a href>` 로만 연결한다. 서버가 ZIP 을 만든 뒤 `302 → /zips/…` 로 보내면 브라우저가 알아서 저장한다(nginx 가 `Content-Disposition: attachment`).

---

## 4. API 코드 읽기 (`main.py`)

```python
@app.get("/api/cards")
def cards(media=Query(None, pattern="^(2d|3d)$"), q=None, ..., limit=Query(60, ge=1, le=500), offset=Query(0, ge=0)):
    where, args = [], []
    if media: where.append("media_type=?"); args.append(media)
    if q:
        for term in q.lower().split():                               # ← 띄어쓴 단어는 전부 포함(AND)
            where.append("search_text LIKE ?"); args.append("%" + term + "%")
    ...
    items = db.rows("SELECT * FROM v_cards %s ORDER BY %s LIMIT ? OFFSET ?" % (w, order), *args, limit, offset)   # ← 값은 전부 ? 바인딩 (SQL 인젝션 차단)
```

```python
def _patch(table, key_col, key, body, editable):
    bad = [k for k in body if k not in editable]                      # ← 수정 가능한 열만 (db.py 의 화이트리스트)
    if bad: raise HTTPException(400, "editable: %s (got %s)" % (list(editable), bad))
```
인증은 없지만(AS-04) **어떤 열을 고칠 수 있는지는 코드가 정한다.** `name_ko` 같은 건 API 로 못 바꾼다.

```python
@app.get("/api/zip")
def zip_group(asset: str, group: str = "all"):
    ...
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_STORED) as z:          # ← 저장만. jpg·obj 라 압축 이득이 적고 속도가 중요
        for f in files:
            z.write(os.path.join(FILES_DIR, f["path"]), "/".join(f["path"].split("/")[1:]))   # ← ZIP 안 경로 = <유물폴더>/<그룹>/파일
    os.replace(tmp, out)                                              # ← 다 쓴 뒤 이름 바꾸기: 받는 사람이 반쪽 파일을 못 본다
    return RedirectResponse("/zips/" + name, status_code=302)         # ← 파일 본문은 nginx 가 내준다
```

**주의 — 라우트 순서.** `@app.get("/api/cards/{asset_id:path}")` 는 뒤 경로를 전부 먹는다. 그래서 `/api/cards/<id>/groups` 는 404 가 났고, `/api/groups?asset=` 처럼 **쿼리 파라미터**로 바꿨다. 새 엔드포인트를 `/api/cards/…` 밑에 두지 말 것.

---

## 5. 로컬에서 돌려 보기

```powershell
# PowerShell
cd C:\Users\SSAFY\source\repos\c201-asset-server\server
uv run python dev.py          # http://127.0.0.1:8412/
```

`dev.py` 가 하는 일 — 서버에서 nginx 가 하는 정적 서빙을 흉내낸다:

```python
os.environ.setdefault("CATALOG_DB", "~/c201-assets/catalog.db")       # ← 로컬 시험판 DB
os.environ.setdefault("CATALOG_FILES", "~/c201-assets/staging")       # ← 서버의 /srv/catalog/files 와 같은 트리
app.mount("/files",   StaticFiles(directory=FILES_DIR))                 # nginx location /files/ 대신
app.mount("/preview", StaticFiles(directory=PREVIEW_DIR))
app.mount("/zips",    StaticFiles(directory=ZIPS_DIR))
app.mount("/",        StaticFiles(directory=WEB, html=True))           # nginx root /srv/catalog/web 대신
```

**확인 순서** (유저플로우 그대로)
1. 첫 화면에 `3D 148` `2D 228` 이 뜬다 → `/api/stats` 정상
2. `반가` 검색 → 6건
3. 카드 클릭 → 3D 뷰어가 돌아간다 · 파일 목록 · "폴더 통째로 받기"
4. `원본 ↔ 복원 비교` → 뷰어 두 개가 같이 움직인다
5. 메모 입력 → 저장 → 새로고침해도 남아 있다

브라우저 F12 콘솔에 빨간 에러가 없어야 한다. 끄는 건 `Ctrl+C`.

> 코드를 고치면 **브라우저 새로고침**만 하면 된다(정적 파일). `main.py` 를 고쳤을 때만 `dev.py` 를 다시 띄운다.

---

## 6. 배포

```bash
# Git Bash
cd /c/Users/SSAFY/source/repos/c201-asset-server && bash deploy/deploy.sh
```

```bash
# deploy.sh 가 하는 일 — 각 줄이 단독 실행 가능
tar -cf - -C server app web pyproject.toml | ssh c201 "tar -xf - -C /srv/catalog"   # 1 코드·화면 복사 (덮어씀)
ssh c201 "cd /srv/catalog && uv sync"                                              # 2 의존성 (pyproject 기준)
ssh c201 "[ -f /srv/catalog/catalog.db ] || uv run python app/scan.py"             # 3 DB 없을 때만 생성 — 있으면 건드리지 않음 ★
scp deploy/nginx-catalog.conf c201:/tmp/ && ssh c201 "sudo install … && sudo nginx -t && sudo systemctl reload nginx"   # 4
scp deploy/catalog-api.service c201:/tmp/ && ssh c201 "sudo install … && sudo systemctl daemon-reload && sudo systemctl enable --now catalog-api && sudo systemctl restart catalog-api"   # 5
curl http://$SERVER_HOST/api/stats                                            # 6 확인
```

★ **3번이 핵심 안전장치.** 배포는 DB 를 지우지 않는다. 팀원이 웹에서 적은 메모·태그가 배포로 사라지지 않는다.

배포 후 확인:
```powershell
curl.exe -s http://$env:SERVER_HOST/api/stats          # JSON 이 오면 API 정상
ssh c201 "systemctl is-active catalog-api nginx"          # active active
```
브라우저 **http://$SERVER_HOST/** — 아까 5절과 같은 다섯 가지를 다시 본다.

> 화면이 바뀐 게 안 보이면 **Ctrl+F5**. nginx 가 `/` 에 `Cache-Control: no-cache` 를 걸어 두긴 했지만, 이미 열려 있던 탭은 옛 `app.js` 를 쓰고 있을 수 있다. (ZIP 버튼을 넣고 처음 확인할 때 이걸로 한 번 헷갈렸다.)

---

## 7. 자료 넣고 빼기 — 등록·삭제

| 하는 일 | 화면 | API |
| --- | --- | --- |
| 새 유물 등록 | 목록 위 **+ 새 유물 등록** | `POST /api/artifacts` |
| 복원본 등록 | 원본 상세 → **복원본 등록 · 메모** 탭 | `POST /api/artifacts/{id}/restored` |
| 유물 삭제 | 상세 → 메모 탭 맨 아래 **이 유물 삭제** | `DELETE /api/artifacts/{id}?confirm={id}&what=all` |
| 복원본만 삭제 | 복원본 상세에서 같은 자리 | `…&what=restored` |

**등록은 칸이 곧 분류다.** `files_3d`(3D 칸)와 `files_2d`(사진 칸)를 따로 받는다.
이름으로 짐작하면 모델의 텍스처가 '유물 사진'으로 등록되는 사고가 나서, 짐작하지 않기로 했다.
이름만 필수이고 설명을 비우면 시대·재질로 한 줄 초안을 만들며 `description_source=derived_team`
으로 표시한다(공식 설명인 척하지 않는다). 소장품번호를 비우면 `new<날짜>_NN` 으로 만든다.

**삭제는 지우지 않는다.** 인증이 없는 서버(AS-04)라 진짜로 지우면 실수 한 번에 자료가 사라진다.
`files/_trash/<날짜시각>_<유물ID>/` 로 **옮기고** 재스캔한다. `scan.py` 는 `originals`·`restored`·`aihub`
만 훑으므로 옮기는 것만으로 목록에서 사라진다.

```bash
# 되살리기 — 폴더를 도로 옮기고 재스캔하면 끝
ssh c201
sudo -u ubuntu mv /srv/catalog/files/_trash/20260911-144036_<유물ID>/originals                  /srv/catalog/files/originals/<유물ID>
curl -s -X POST http://127.0.0.1:8412/api/rescan

# 진짜로 비우기 (되돌릴 수 없다)
sudo -u ubuntu rm -rf /srv/catalog/files/_trash/<그 폴더>
```

> 실수 방지로 `confirm` 에 유물 ID 를 그대로 다시 적게 했다(화면도 입력을 받는다).
> 그래도 **인증이 없으므로 링크를 아는 사람은 누구나 지울 수 있다** — 휴지통이 그 위험을 받아 내는 장치다.

---

## 8. 자주 하는 수정 — 어디를 고치나

| 하고 싶은 것 | 고칠 파일 | 그다음 |
| --- | --- | --- |
| 카드에 표시 항목 추가 (예: 크기) | `app.js` `cardEl()` — `c.size` 는 `v_cards` 에 이미 있음 | 새로고침 |
| 색·글꼴·간격 | `app.css` 의 `:root` 변수 | 새로고침 |
| 새 필터 (예: 시대) | `main.py` `cards()` 에 파라미터 + `app.js` `loadList()` 에 `p.set(...)` + `index.html` 에 `<select>` | `dev.py` 재시작 |
| 새 API | `main.py` 에 `@app.get("/api/…")` — **`/api/cards/` 밑은 피한다** (4절 주의) | `dev.py` 재시작 |
| 수정 가능한 열 추가 | `db.py` `ARTIFACT_EDITABLE` / `ASSET_EDITABLE` | `dev.py` 재시작 |
| 목록 한 페이지 개수 | `app.js` `state.limit` (60) | 새로고침 |
| assets 에 열 추가 | `schema.sql` + **`db.py migrate()` 에도** 추가 | 이미 만들어진 DB 는 `CREATE TABLE IF NOT EXISTS` 로 안 바뀐다 |
| 복원 종류 늘리기 | `db.py RESTORE_TYPES` + `scan.py METHOD_HINTS` + `app.js RT_KO` + `index.html` 두 곳(`#fRestore`·`#rtPick`) + `app.css .b.rt.<코드>` | 재스캔하면 옛 카드도 다시 판정 |
| '더 보기' 위치 | `app.js placeMore()` — 줄은 카드의 `offsetTop` 으로 센다 | 새로고침 |
| three.js 버전 | `web/vendor/` 네 파일 교체 (`cdn.jsdelivr.net/npm/three@<ver>/…`) | 새로고침 |

셋 다 끝나면 `bash deploy/deploy.sh`.

---

## 9. 막혔던 것

| 증상 | 원인 | 처치 |
| --- | --- | --- |
| `/api/cards/<id>/groups` 가 404 | `{asset_id:path}` 가 하위 경로까지 먹음 | `/api/groups?asset=` 로 |
| 배포했는데 화면에 새 버튼이 없음 | 열려 있던 탭의 옛 `app.js` | Ctrl+F5 |
| 뷰어에서 유물이 누워 있음 | OBJ 의 위 축이 두 종류 (WaveFront Z-up / Blender Y-up) | `blender_preview.py` 가 머리말 보고 축 선택 (RUNBOOK 9절) |
| 화면 상단 `<select>` 글자가 겹침 | 창이 900px 이하로 좁을 때 | `app.css` `@media (max-width:900px)` 에서 세로 배치 — 필요하면 |
| `PATCH` 가 `400 error parsing the body` | Windows 콘솔 curl 이 한글을 CP949 로 보냄 | 화면이나 Python `urllib` 로 (서버 문제 아님) |
| '더 보기' 가 두 **줄** 위가 아니라 두 **칸** 위에 놓였다 | 목록을 막 채운 직후 `gridTemplateColumns` 를 읽으면 열 수가 1 로 잡힌다 | `placeMore()` 가 카드의 `offsetTop` 으로 줄을 센다 |
| 새 열을 넣었는데 배포 후에도 값이 전부 비어 있다 | `ALTER TABLE` 은 열만 붙이고 기존 행은 NULL — 재스캔 전까지 빈칸 | `db._backfill_restore_types()` 처럼 **마이그레이션에서 한 번 채운다** |
| 썸네일이 늦게 와 목록이 덜컥거린다 | 이미지 자리가 안 잡혀 도착할 때마다 레이아웃이 밀림 | `.thumb` 에 `aspect-ratio:1/1` 로 자리 확보 + `.thumb.load` 자리표시, `loading="lazy" decoding="async"` |
