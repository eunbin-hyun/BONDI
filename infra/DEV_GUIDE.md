# 유물 자료 서버 — 개발 순서와 구현 가이드

| 항목 | 내용 |
| --- | --- |
| 문서 ID | AS-GUIDE-001 |
| 버전 | v1.0 |
| 기준일 | 2026-09-03 |
| 짝 문서 | **[PLAN.md](PLAN.md)** — 계획서 (AS-PLAN-001). 배경·확정 사항·현황·설계 계약·리스크 |
| 대상 서버 | `$SERVER_HOST` (`infra/web/.env`) |
| 담당 | Infra (권영호) |
| 상태 | 착수 대기 |

## 0. 이 문서의 위치와 전제

### 0.1 두 문서의 관계

| 문서 | 담당 | 권위 |
| --- | --- | --- |
| [PLAN.md](PLAN.md) | 무엇을 왜 만드는가 | 확정 사항(AS-nn), 완료 기준(AS-AT-nn), 디렉터리·URL·DB 스키마·파일명 규칙, 리스크 |
| **이 문서** | 어떻게 어떤 순서로 만드는가 | 스크립트·설정 파일·API·화면 구현, Phase 0~9 명령과 검증, 운영 절차 |

설계 계약을 바꿔야 하면 **계획서를 먼저 고친다.** 이 문서는 그것을 구현한다.

### 0.2 전제 요약

계획서에서 가져온 것만 짧게 적는다. 근거는 계획서에 있다.

| 항목 | 값 |
| --- | --- |
| 서버 접속 | `ssh c201` — `~/.ssh/config` 별명, [JENKINS_BUILD_GUIDE.md](JENKINS_BUILD_GUIDE.md) 1절 (ufw는 22만 열림) |
| 서버 루트 | `/srv/catalog/` — `files/` `preview/` `catalog.db` `app/` `web/` |
| 로컬 작업 폴더 | `~/c201-assets/` — `download/` `staging/` |
| 로컬 도구 | Python 3.11.15, `uv`, **Blender 5.2.1 LTS** (`C:\Program Files\Blender Foundation\Blender 5.2\blender.exe`), ssh/scp. **rsync·WSL 없음** |
| 저장 구조 | `files/<artifact_id>/<variant>/<정규화 폴더>/파일` (계획서 6장) |
| 프리뷰 상한 | 메시 ≤200k 삼각형, 점군 ≤300k 점, 텍스처 2K, GLB ≤15MB (계획서 9.1) |
| 스택 | Nginx + FastAPI(uvicorn, systemd) + SQLite + three.js CDN. Docker·CI 없음 |

**확정 결정 요약 (계획서 2장)**

| ID | 한 줄 |
| --- | --- |
| AS-01 | Drive 연동 없음. 서버는 별도 사본 |
| AS-02 | 압축 해제 상태로 개별 파일 제공 |
| AS-03 | 브라우저 3D 미리보기 |
| AS-04 | 인증 없음. autoindex 켬 |
| AS-05 | EC2는 서빙만. 변환은 로컬 |
| AS-06 | Docker·CI 없음 |
| AS-07 | 투입은 Infra가 scp/tar-pipe로 |
| AS-08 | AIHub CSV는 올리지 않음 |
| AS-09 | 폴더·파일명 영문 정규화 |

### 0.3 읽는 순서

- 처음 만드는 사람: **5장 Phase 0부터 순서대로.** 각 Phase가 참조하는 1~4장을 그때 읽는다.
- 이미 돌아가는 서버에 파일을 추가하는 사람: **6.1**만 읽는다.
- 장애: **6.6.**

---

# 1부. 구현 참조

## 1. 프리뷰 생성 파이프라인 (로컬)

### 1.1 목표

variant마다 **브라우저에서 3초 안에 뜨는 GLB 하나 + 썸네일 PNG 하나**를 만든다.

| 항목 | 상한 | 근거 |
| --- | --- | --- |
| 메시 삼각형 | **≤ 200,000** | 웹 three.js에서 저사양 노트북 포함 부드러운 선. 김채원 VR 채택값(400k)보다 보수적 |
| 점군 점 수 | **≤ 300,000** | THREE.Points 렌더 부담 기준 |
| 텍스처 | **2048×2048, JPEG q85** | 8K 원본은 다운로드용. 프리뷰에 8K를 넣으면 GLB가 30MB를 넘는다 |
| GLB 파일 크기 | 목표 ≤ 15MB | 3초 로딩 기준 (LTE 환경 가정) |
| 썸네일 | 512×512 PNG, Workbench 렌더 | GPU 불필요, 형태 확인용 |

### 1.2 도구 선택

| 입력 | 도구 | 이유 |
| --- | --- | --- |
| **OBJ + MTL + 텍스처** | **Blender headless** | Decimate 모디파이어가 UV를 보존한다. Open3D의 `simplify_quadric_decimation`은 UV를 버린다. glTF 익스포터가 텍스처를 GLB에 내장한다 |
| **PLY (정점색)** / **STL** | **Blender headless** | 한 도구로 통일. PLY 정점색은 `Col` 속성으로 들어오고 glTF `COLOR_0`으로 나간다 |
| **LAS 점군** | **laspy + Open3D + trimesh** | Blender에 LAS 임포터가 없다. `laspy`로 읽고 Open3D `voxel_down_sample`로 줄이고 trimesh `PointCloud`를 GLB(POINTS primitive)로 내보낸다 |
| 썸네일 | Blender Workbench 엔진 | EEVEE보다 빠르고 GPU 없이도 돈다. 형태 파악에 충분 |
| `.gz` | Python `gzip` | Nginx `gzip_static`용 사전 압축 |

### 1.3 흐름

```text
make_preview.py <zip 또는 las> --out staging/
  1. 파싱      zip 이름 → artifact_id, variant             (계획서 8장)
  2. 해제      staging/files/<artifact>/<variant>/ 에 풂
  3. 정규화    폴더명 영문화, 파일명 한글·공백 → '_'         (계획서 6.3)
  4. MTL 수정  map_Kd 등 절대경로 → 파일명만               (1.4)
  5. 대표 파일 선정
       OBJ 있음 → OBJ (텍스처 포함)
       없고 PLY 있음 → PLY
       없고 STL → STL
       LAS → LAS
  6. 프리뷰    메시 → blender -b -P blender_preview.py     (1.5)
               점군 → las_to_glb()                          (1.6)
       → staging/preview/<artifact>/<variant>.glb, .png
  7. 사전 압축 .obj .mtl .ply(ASCII) .las .stl(ASCII) → .gz (1.7)
  8. _meta.json 기록
       { "artifact_id", "variant", "source_org", "method_guess",
         "representative": "digital_obj/xxx.obj",
         "tri_count": 1234567, "pt_count": null,
         "preview_tri_count": 198000,
         "classes": {"0": 166459, "20": 15047, "21": 8912},   # 점군일 때
         "original_names": {"digital_obj": "디지털콘텐츠_OBJ", ...},
         "generated_at": "2026-09-04T10:00:00", "tool_versions": {"blender": "5.2.1"} }
```

**옵션**

| 옵션 | 뜻 |
| --- | --- |
| `--extract-only` | 1~4단계만. Phase 1에서 사용 |
| `--from-staging <dir> --previews --gzip` | 이미 해제된 트리에 대해 6~8단계만. Phase 2에서 사용 |
| `--artifact <id> --variant <name>` | 파일명이 규칙에 안 맞을 때 직접 지정 |
| `--target-tris 200000` / `--max-points 300000` | 상한 조정 |

### 1.4 MTL 절대경로 수정

장서진 노트가 확인한 문제다. MTL 안의 `map_Kd C:\Users\...\xxx.jpg` 같은 절대경로는 브라우저·Blender 어디서도 안 열린다.

```python
import re, pathlib

def fix_mtl(mtl_path: pathlib.Path) -> list[str]:
    """map_* / bump / disp / decal 라인의 경로를 파일명만 남긴다. 참조된 텍스처 파일명 목록을 반환."""
    text = mtl_path.read_text(encoding="utf-8", errors="replace")
    refs = []
    def repl(m):
        key, target = m.group(1), m.group(2).strip()
        name = pathlib.PureWindowsPath(target).name      # 역슬래시·슬래시 모두 처리
        refs.append(name)
        return f"{key} {name}"
    fixed = re.sub(r"^(map_\w+|bump|disp|decal)\s+(.+)$", repl, text, flags=re.M)
    mtl_path.write_text(fixed, encoding="utf-8")
    return refs

def check_textures(mtl_path: pathlib.Path, refs: list[str]) -> list[str]:
    """MTL이 참조하는 텍스처가 같은 폴더에 실제로 있는지. 없는 것을 반환 → 로그."""
    return [r for r in refs if not (mtl_path.parent / r).exists()]
```

OBJ의 `mtllib` 줄도 같은 방식으로 파일명만 남긴다. 텍스처 파일명이 MTL 참조와 다르면(재질명 불일치 이슈) `check_textures`가 잡아내고 로그에 남긴다. **자동으로 추측해 고치지 않는다** — 사람이 확인한다.

### 1.5 Blender 스크립트 (`blender_preview.py`)

Blender 안에서 실행된다.

```bash
"/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b -P blender_preview.py -- \
  <입력.obj|.ply|.stl|.glb> <출력.glb> <썸네일.png> <목표삼각형수>
```

```python
import bpy, sys, math, pathlib
argv = sys.argv[sys.argv.index("--") + 1:]
src, out_glb, out_png, target_tris = argv[0], argv[1], argv[2], int(argv[3])
src_path = pathlib.Path(src)

# 초기화 (기본 큐브·조명·카메라 없이)
bpy.ops.wm.read_factory_settings(use_empty=True)

# 임포트 (Blender 4.x/5.x 신규 임포터)
ext = src_path.suffix.lower()
if ext == ".obj":
    bpy.ops.wm.obj_import(filepath=str(src_path))
elif ext == ".ply":
    bpy.ops.wm.ply_import(filepath=str(src_path))
elif ext == ".stl":
    bpy.ops.wm.stl_import(filepath=str(src_path))
elif ext == ".glb":
    bpy.ops.import_scene.gltf(filepath=str(src_path))   # 점군 GLB 썸네일용
else:
    raise SystemExit(f"unsupported: {ext}")

objs = [o for o in bpy.context.scene.objects if o.type in ("MESH", "POINTCLOUD")]
if not objs:
    raise SystemExit("nothing imported")
meshes = [o for o in objs if o.type == "MESH"]

# 여러 메시면 하나로 합침
if meshes:
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes: o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
obj = bpy.context.view_layer.objects.active or objs[0]

# 원점·크기 정규화: 바운딩박스 중심을 원점, 최대 변 2m
bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
obj.location = (0, 0, 0)
dims = max(obj.dimensions)
if dims > 0:
    s = 2.0 / dims
    obj.scale = (s, s, s)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# 데시메이션 (UV 보존) — 메시일 때만
tri_before = tri_after = 0
if obj.type == "MESH":
    tri_before = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    if tri_before > target_tris:
        mod = obj.modifiers.new("dec", "DECIMATE")
        mod.decimate_type = "COLLAPSE"
        mod.ratio = target_tris / tri_before
        mod.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier=mod.name)
    tri_after = sum(len(p.vertices) - 2 for p in obj.data.polygons)

# 텍스처 2K로 축소
for img in bpy.data.images:
    if img.size[0] > 2048 or img.size[1] > 2048:
        img.scale(2048, 2048)

# GLB 내보내기
if ext != ".glb":
    bpy.ops.export_scene.gltf(
        filepath=out_glb,
        export_format="GLB",
        export_image_format="JPEG",
        export_jpeg_quality=85,
        export_apply=True,
        export_vertex_color="ACTIVE",   # PLY 정점색 유지. ★ 5.2 익스포터 옵션명 확인 필요
        export_yup=True,
    )

# 썸네일: Workbench, 3/4 시점
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
has_uv = obj.type == "MESH" and bool(obj.data.uv_layers)
scene.display.shading.color_type = "TEXTURE" if has_uv else "VERTEX"
scene.render.resolution_x = scene.render.resolution_y = 512
scene.render.film_transparent = True
cam_data = bpy.data.cameras.new("cam"); cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam); scene.camera = cam
cam.location = (2.6, -2.6, 1.8)
cam.rotation_euler = (math.radians(63), 0, math.radians(45))
scene.render.filepath = out_png
bpy.ops.render.render(write_still=True)

# 리포트 (stdout → make_preview.py가 파싱)
print(f"PREVIEW_REPORT tri_before={tri_before} tri_after={tri_after}")
```

> **★ 확인 필요 (Phase 2 검증 항목):** `export_vertex_color` 옵션명, `bpy.ops.wm.ply_import`의 정점색 속성 이름, `import_scene.gltf`가 POINTS primitive를 어떻게 들여오는지. Blender 5.2에서 실제로 돌려 확인한다. 옵션명이 다르면 `bpy.ops.export_scene.gltf.get_rna_type().properties.keys()`로 목록을 뽑는다.

### 1.6 점군 프리뷰 (`las_to_glb`)

```python
import laspy, numpy as np, open3d as o3d, trimesh

def las_to_glb(las_path, out_glb, max_points=300_000):
    las = laspy.read(las_path)
    xyz = np.vstack([las.x, las.y, las.z]).T.astype(np.float64)
    dims = set(las.point_format.dimension_names)

    if {"red", "green", "blue"} <= dims:
        rgb = np.vstack([las.red, las.green, las.blue]).T.astype(np.float64)
        if rgb.max() > 255: rgb = rgb / 256.0            # 16-bit → 8-bit
        rgb = rgb.astype(np.uint8)
    else:
        rgb = np.full((len(xyz), 3), 180, dtype=np.uint8)

    # classification 보존 (권영호: 0 원본 / 20 채움 / 21 색보정, 장서진: 12 보충점)
    cls = np.asarray(las.classification) if "classification" in dims else None

    xyz -= xyz.mean(axis=0)                               # 원점 이동
    n = len(xyz)
    if n > max_points:
        # 랜덤 서브샘플. voxel 크기를 맞추는 이분탐색보다 단순하고 이 용도에 충분
        idx = np.random.default_rng(0).choice(n, max_points, replace=False)
        xyz, rgb = xyz[idx], rgb[idx]
        cls = cls[idx] if cls is not None else None

    rgba = np.hstack([rgb, np.full((len(rgb), 1), 255, np.uint8)])
    trimesh.PointCloud(vertices=xyz, colors=rgba).export(out_glb)   # GLB, POINTS primitive

    classes = None
    if cls is not None:
        u, c = np.unique(np.asarray(las.classification), return_counts=True)   # 전체 기준 통계
        classes = {int(k): int(v) for k, v in zip(u, c)}
    return {"pt_count": n, "preview_pt_count": len(xyz), "classes": classes}
```

`classes` 통계는 `_meta.json`에 남긴다. 권영호의 0/20/21, 장서진의 12 분류가 그대로 보이므로 **원본과 채운 영역의 점 수를 UI에 표시할 수 있다.** 제품의 `observed`/`ai_inferred` 구분과 같은 방향이다.

**점군 썸네일.** Open3D offscreen 렌더가 Windows에서 까다롭다. 두 가지 중 Phase 2에서 고른다.
- (a) 만든 GLB를 1.5 스크립트에 `.glb` 입력으로 넣어 Workbench로 찍는다.
- (b) 점군은 썸네일을 생략하고 뷰어에서 바로 본다 (`thumb_png NULL`, 화면은 아이콘).

### 1.7 `.gz` 사전 압축

텍스트 포맷만 압축한다. 바이너리(JPG·바이너리 PLY/STL·GLB)는 효과가 없다.

| 확장자 | 압축 | 판정 방법 |
| --- | --- | --- |
| `.obj`, `.mtl`, `.json` | ✔ | 항상 텍스트 |
| `.ply` | 헤더가 `format ascii`면 ✔ | 첫 300바이트 읽어 확인 |
| `.stl` | 처음 5바이트가 `solid`이고 바이너리 STL 헤더가 아니면 ✔ | 파일 크기 = 84 + 50×삼각형수 이면 바이너리 |
| `.las` | ✔ (1.5~2배) | LAZ(`.laz`)가 아니라면 |
| `.jpg .png .glb` | ✗ | |

```python
import gzip, shutil, pathlib

def make_gz(path: pathlib.Path) -> pathlib.Path:
    out = path.with_name(path.name + ".gz")
    with open(path, "rb") as f_in, gzip.open(out, "wb", compresslevel=6) as f_out:
        shutil.copyfileobj(f_in, f_out)
    return out

def is_ascii_ply(path: pathlib.Path) -> bool:
    head = path.open("rb").read(300)
    return b"format ascii" in head

def is_ascii_stl(path: pathlib.Path) -> bool:
    with path.open("rb") as f:
        head = f.read(5)
        if head != b"solid": return False
        f.seek(80); n = int.from_bytes(f.read(4), "little")
    return path.stat().st_size != 84 + 50 * n     # 바이너리 크기 공식과 다르면 ASCII
```

Nginx `gzip_static on`은 `.gz`의 mtime이 원본보다 오래되지 않아야 한다. 원본을 다시 만들면 `.gz`도 다시 만든다.

### 1.8 대형 입력 처리

Blender가 1,000만 삼각형 OBJ를 여는 데 수 분·수 GB가 든다.

| 상황 | 절차 |
| --- | --- |
| 텍스처 없는 PLY/STL, 500만 삼각형 이상 | ① Open3D `simplify_quadric_decimation(2_000_000)`으로 중간 PLY → ② Blender로 20만까지 → GLB. (UV가 없으니 Open3D를 써도 손실 없음) |
| 텍스처 있는 OBJ, 500만 삼각형 이상 | Blender 단일 단계 시도. 메모리 부족이면 Decimate를 **두 번 나눠** 적용 (ratio 0.2 → 다시 목표까지) |
| 점군 1,000만 점 이상 | `laspy`가 청크 읽기를 지원한다 (`laspy.open(...).chunk_iterator`). 청크마다 서브샘플해 합친다 |

Phase 2에서 **실제 최대 파일**로 검증한다. 김채원 석인상(1,329만 점 / 1,229만 삼각형)은 Drive에 없으므로 현재 최대는 `RR_07_01_PA_033_symmetry_restored.las` 52.9MB(약 150만 점)다.

## 2. 서버 구성

### 2.1 패키지

```bash
sudo apt update
sudo apt install -y nginx git curl sqlite3
curl -LsSf https://astral.sh/uv/install.sh | sh          # uv → ~/.local/bin/uv
source ~/.bashrc                                           # PATH 반영. 안 되면 export PATH="$HOME/.local/bin:$PATH"
```

### 2.2 디렉터리·권한

```bash
sudo mkdir -p /srv/catalog/{files,preview,app,web}
sudo chown -R ubuntu:ubuntu /srv/catalog
chmod -R u=rwX,go=rX /srv/catalog        # Nginx(www-data)가 읽을 수 있게
```

### 2.3 Python 프로젝트 (`/srv/catalog/pyproject.toml`)

```toml
[project]
name = "c201-asset-server"
version = "0.1.0"
requires-python = ">=3.11,<3.12"
dependencies = [
  "fastapi>=0.115",
  "uvicorn[standard]>=0.30",
]

[tool.uv]
python-preference = "managed"
```

```bash
cd /srv/catalog && uv python install 3.11 && uv sync
```

`scan.py`는 표준 라이브러리만 쓴다. **EC2에는 Open3D·Blender를 설치하지 않는다** (AS-05).

### 2.4 Nginx (`/etc/nginx/sites-available/catalog`)

```nginx
# 3D 포맷 MIME
types {
    model/gltf-binary   glb;
    model/gltf+json     gltf;
}

server {
    listen 80 default_server;
    server_name _;
    charset utf-8;

    root  /srv/catalog/web;
    index index.html;

    # 대용량 전송 기본
    sendfile        on;
    tcp_nopush      on;
    tcp_nodelay     on;
    keepalive_timeout 65;

    # 화면
    location / {
        try_files $uri $uri/ /index.html;
        add_header Cache-Control "no-cache";
    }

    # API
    location /api/ {
        proxy_pass         http://127.0.0.1:8000/api/;
        proxy_set_header   Host $host;
        proxy_set_header   X-Forwarded-For $remote_addr;
        proxy_read_timeout 60s;
    }

    # 원본 파일 — Nginx 직접 서빙
    location /files/ {
        alias /srv/catalog/files/;
        autoindex on;                 # AS-04: 디렉터리 브라우징 허용
        autoindex_exact_size off;
        autoindex_localtime on;
        gzip_static on;               # .gz가 있으면 그것을 보냄
        add_header Access-Control-Allow-Origin *;
        add_header Cache-Control "public, max-age=3600";
        # 텍스트 포맷이 브라우저 화면에 뿌려지지 않고 저장되게
        location ~* \.(obj|mtl|ply|stl|las)$ {
            add_header Content-Disposition 'attachment';
            add_header Access-Control-Allow-Origin *;
            gzip_static on;
        }
    }

    # 프리뷰 — 뷰어가 fetch
    location /preview/ {
        alias /srv/catalog/preview/;
        gzip_static on;
        add_header Access-Control-Allow-Origin *;
        add_header Cache-Control "public, max-age=604800";
    }

    access_log /var/log/nginx/catalog.access.log;
    error_log  /var/log/nginx/catalog.error.log;
}
```

```bash
sudo ln -sf /etc/nginx/sites-available/catalog /etc/nginx/sites-enabled/catalog
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

> `Content-Disposition: attachment`는 OBJ 링크를 클릭했을 때 브라우저가 텍스트를 화면에 뿌리지 않고 저장하게 한다. **뷰어가 원본 OBJ를 직접 fetch해 렌더할 때는 이 헤더가 무관하다** (fetch는 헤더를 무시하고 바디만 받는다).
>
> `alias` 안에 중첩 `location`을 쓰면 `add_header`가 상속되지 않으므로 안쪽에 다시 적었다.

### 2.5 systemd (`/etc/systemd/system/catalog-api.service`)

```ini
[Unit]
Description=C201 asset catalog API
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/srv/catalog
Environment=CATALOG_DB=/srv/catalog/catalog.db
Environment=CATALOG_ROOT=/srv/catalog
ExecStart=/home/ubuntu/.local/bin/uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now catalog-api
sudo systemctl status catalog-api --no-pager
```

### 2.6 방화벽

바탕화면 `ufw 포트 설정하기.txt` 6번 절차 그대로.

```bash
sudo ufw allow 80/tcp
sudo ufw status
```

**22번은 절대 건드리지 않는다.** 작업 전 SSH 세션을 2개 이상 열어둔다.

## 3. API 명세

FastAPI, JSON. 인증 없음 (AS-04). 모든 응답은 `application/json; charset=utf-8`. 스키마는 계획서 7.1.

| 메서드 | 경로 | 파라미터 | 응답 | 용도 |
| --- | --- | --- | --- | --- |
| GET | `/api/artifacts` | `q` (부분일치: id·title·note·tags·owner·method), `source_org`, `license`, `owner`, `has_preview` (bool), `limit`(기본 100), `offset` | `{items:[{artifact_id, source_org, title, license, variant_count, thumb_png, tags}], total}` | 목록·검색 |
| GET | `/api/artifacts/{id}` | — | `{artifact, variants:[{variant_id, variant, method, owner, preview_glb, thumb_png, tri_count, pt_count, files:[{path, kind, size, has_gz, url}]}]}` | 상세 |
| PATCH | `/api/artifacts/{id}` | body: `{title?, license?, note?, tags?, region?, type_code?}` | 갱신된 artifact | 메타 수정 |
| PATCH | `/api/variants/{variant_id}` | body: `{method?, owner?, produced_at?, note?}` | 갱신된 variant | 메타 수정. `variant_id`는 `bon004740/restored` 형태 — URL 인코딩 `bon004740%2Frestored` |
| GET | `/api/files` | `sha256` 또는 `kind` | `{items:[...]}` | 중복 검출·종류별 조회 |
| GET | `/api/stats` | — | `{artifacts, variants, files, total_bytes, by_source_org, by_license}` | 화면 상단 요약 |
| POST | `/api/rescan` | — | `{added, updated, removed, took_ms}` | `scan.py` 실행. 파일 투입 후 호출. 동시 실행 방지 락 1개 |
| GET | `/api/health` | — | `{ok:true, db:"...", files_root:"..."}` | 헬스체크 |

**검색 구현**은 `LIKE '%q%'`를 여러 열에 OR로 건다. 유물 수십 개 규모에서 FTS는 필요 없다. 필요해지면 FTS5 trigram으로 바꾼다.

**PATCH 허용 열은 화이트리스트로 고정한다.** body에 다른 키가 오면 400.

**예시 응답 — `GET /api/artifacts/RR_07_01_EA_028`**

```json
{
  "artifact": {
    "artifact_id": "RR_07_01_EA_028", "source_org": "aihub",
    "title": "원형 토기편", "region": "경상도", "type_code": "EA",
    "license": "unverified", "note": null, "tags": "토기,회전대칭,PoinTr"
  },
  "variants": [
    { "variant_id": "RR_07_01_EA_028/source", "variant": "source",
      "method": null, "owner": null,
      "preview_glb": "/preview/RR_07_01_EA_028/source.glb", "thumb_png": null,
      "pt_count": 179294,
      "files": [
        { "path": "RR_07_01_EA_028/source/RR_07_01_EA_028.las", "kind": "las",
          "size": 6454959, "has_gz": 1, "url": "/files/RR_07_01_EA_028/source/RR_07_01_EA_028.las" }
      ] },
    { "variant_id": "RR_07_01_EA_028/pointr_restored", "variant": "pointr_restored",
      "method": "PoinTr 보충점 병합 (class 12)", "owner": "장서진", "pt_count": 180254, "...": "..." }
  ]
}
```

**앱 구조**

```text
app/
├── main.py     FastAPI 앱, 라우터, 에러 핸들러(404/400 → JSON)
├── db.py       sqlite3 커넥션(check_same_thread=False, WAL), 쿼리 함수
└── scan.py     스캐너 (Phase 5). main.py에서 함수로도 호출 (/api/rescan)
```

## 4. 웹 화면과 뷰어

### 4.1 레이아웃

```text
┌──────────────────────────────────────────────────────────────┐
│ 본디 유물 자료   [검색창________________]  출처▾ 라이선스▾ 담당▾ │
│ 유물 24 · 변형 38 · 파일 156 · 3.1GB                            │
├───────────────────────┬──────────────────────────────────────┤
│ 목록 (썸네일 카드)     │ 상세                                   │
│ ┌──────┐ bon004740    │ RR_07_01_EA_028  원형 토기편  [AIHub]   │
│ │ 썸네일│ museum · 2변형│ 라이선스: unverified ▾  태그: 토기,…   │
│ └──────┘              │                                        │
│ ┌──────┐ RR_07_01_EA_ │ ┌── 3D 뷰어 ─────────────────────────┐ │
│ │      │ 028 · 4변형   │ │  [source ▾]  [비교: pointr_restored▾]│ │
│ └──────┘              │ │                                     │ │
│   ...                 │ │      (three.js 캔버스)              │ │
│                       │ │                                     │ │
│                       │ └─────────────────────────────────────┘ │
│                       │ 변형 목록                               │
│                       │ ▸ source        179,294점  담당: —      │
│                       │     RR_07_01_EA_028.las  6.2MB  [받기] │
│                       │ ▸ pointr_restored  담당: 장서진 ✎       │
│                       │     방법: PoinTr 보충점 병합 ✎          │
│                       │     ..._pointr_restored.las 6.2MB [받기]│
└───────────────────────┴──────────────────────────────────────┘
```

### 4.2 기능 목록

| 기능 | 우선순위 | 구현 |
| --- | --- | --- |
| 검색·필터·목록 | MUST | `GET /api/artifacts` 호출, 300ms 디바운스 |
| 상세: 변형·파일 목록, 다운로드 링크 | MUST | `GET /api/artifacts/{id}`. 파일 크기 사람이 읽는 단위 |
| 3D 뷰어: GLB 로드, 궤도 카메라, 자동 프레이밍 | MUST | three.js `GLTFLoader` + `OrbitControls`. 바운딩박스로 카메라 거리 계산 |
| **비교 모드**: 두 variant를 좌우 분할, 카메라 동기화 | MUST | 캔버스 2개, 컨트롤 1개가 두 카메라를 갱신. 또는 토글(같은 자리 전환) — 명세 D-47의 "같은 자리에서 바뀐다"와 같은 감각 |
| 인라인 메타 편집 (`owner`, `method`, `license`, `title`, `tags`, `note`) | MUST | 클릭 → input → blur/Enter 시 PATCH |
| 점군 렌더: 점 크기 조절 슬라이더 | SHOULD | `PointsMaterial.size`. 다운샘플된 점군은 점을 키워야 형태가 보인다 |
| 원본 OBJ 직접 로드 ("풀 해상도 보기") | SHOULD | `OBJLoader`+`MTLLoader`로 `/files/...obj` fetch. 60MB 이상이면 경고 |
| 썸네일 그리드 | SHOULD | `thumb_png` 있으면 표시, 없으면 아이콘 |
| URL 상태 (`#/artifact/bon004740?v=restored`) | SHOULD | 팀원이 특정 유물 링크를 공유할 수 있게 |
| 통계 헤더 | MAY | `GET /api/stats` |
| classification 점 수 표시 (원본/채움/색보정) | MAY | `_meta.json`의 `classes`를 API에 노출 → variant 아래 작은 표 |

### 4.3 three.js 로딩

빌드 없이 import map으로 CDN에서 가져온다. 우리 서버이므로 CSP 제약이 없다.

```html
<script type="importmap">
{ "imports": {
    "three": "https://cdn.jsdelivr.net/npm/three@0.170.0/build/three.module.js",
    "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.170.0/examples/jsm/"
} }
</script>
<script type="module">
  import * as THREE from 'three';
  import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
  import { GLTFLoader }    from 'three/addons/loaders/GLTFLoader.js';
</script>
```

> 버전은 착수 시점의 최신 안정판으로 고정한다. **한 번 고르면 바꾸지 않는다.**

**오프라인 대비.** 시연장·실습실 네트워크가 CDN을 막으면 뷰어가 죽는다. `web/vendor/three/`에 복사본을 두고 import map을 로컬 경로로 바꿀 수 있게 준비한다 (Phase 7 선택 항목).

```bash
# vendor 복사 (로컬에서, node 있음)
mkdir -p web/vendor/three && cd web/vendor/three
curl -sLO https://cdn.jsdelivr.net/npm/three@0.170.0/build/three.module.js
# examples/jsm 은 필요한 파일만: controls/OrbitControls.js, loaders/GLTFLoader.js, loaders/OBJLoader.js, loaders/MTLLoader.js, utils/BufferGeometryUtils.js
```

### 4.4 뷰어 핵심 로직 (초안)

```js
// viewer.js
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader }    from 'three/addons/loaders/GLTFLoader.js';

export function createViewer(canvas) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0xf4f4f4);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x888888, 1.2));
  const camera = new THREE.PerspectiveCamera(45, 1, 0.01, 100);
  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  let current = null;

  async function load(url) {
    if (current) { scene.remove(current); disposeTree(current); current = null; }
    const gltf = await new GLTFLoader().loadAsync(url);
    current = gltf.scene;
    current.traverse(o => {
      if (o.isPoints) {                       // 점군 GLB
        o.material.size = 0.01;
        o.material.vertexColors = true;
        o.material.sizeAttenuation = true;
      }
    });
    scene.add(current);
    frame(current);
  }
  function frame(obj) {
    const box = new THREE.Box3().setFromObject(obj);
    const size = box.getSize(new THREE.Vector3()).length();
    const center = box.getCenter(new THREE.Vector3());
    controls.target.copy(center);
    camera.position.copy(center).add(new THREE.Vector3(size, size * 0.6, size));
    camera.near = size / 100; camera.far = size * 10; camera.updateProjectionMatrix();
    controls.update();
  }
  function setPointSize(s) { current?.traverse(o => { if (o.isPoints) o.material.size = s; }); }
  function resize() {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix();
  }
  function disposeTree(root) {
    root.traverse(o => { o.geometry?.dispose(); if (o.material) [].concat(o.material).forEach(m => { m.map?.dispose(); m.dispose(); }); });
  }
  new ResizeObserver(resize).observe(canvas); resize();
  (function tick() { controls.update(); renderer.render(scene, camera); requestAnimationFrame(tick); })();
  return { load, camera, controls, setPointSize, resize };
}

// 비교 모드: A의 카메라를 B에 복사
export function linkCameras(a, b) {
  a.controls.addEventListener('change', () => {
    b.camera.position.copy(a.camera.position);
    b.camera.quaternion.copy(a.camera.quaternion);
    b.controls.target.copy(a.controls.target);
    b.controls.update();
  });
}
```

---

# 2부. 개발 순서

## 5. 단계별 작업

각 단계는 **목표 → 작업 → 명령 → 산출물 → 검증**으로 구성한다. **검증을 통과하지 못하면 다음 단계로 가지 않는다.**

**총 예상: 약 2일 (16~20시간).** Infra 1인.

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

**Fallback (계획서 10장).** W1 게이트와 시간이 겹치면 **Phase 6까지만** 끝낸다. `/files/` autoindex + `/api/`로 A·C는 달성된다.

---

### Phase 0 — 실측과 인벤토리 확정

**목표.** 계획의 전제(디스크·용량·중복)를 숫자로 확인한다. 여기서 틀어지면 설계를 바꾼다.

**작업**

1. EC2 접속, OS·디스크·CPU·메모리 확인
2. Drive `zip` 하위 폴더 내용 확인
3. 번들 2개의 내용 확인 (다운로드 후 목록만)
4. `duk003312` 원본 소재 확인 (팀 채널에 질문)
5. 최종 적재 목록 확정 → 계획서 3.3 인벤토리 갱신

**명령**

```bash
# EC2 실측 (SSH 세션은 항상 2개 이상 열어둔다)
ssh c201 \
  "lsb_release -a; echo; df -h /; echo; free -h; echo; nproc; echo; sudo ufw status; echo; python3 --version"
```

```bash
# 번들 내용 목록만 (다운로드 후)
unzip -l 유물복원_자료.zip | tail -20
unzip -l VR_유적지_복원_전시_후보_9선.zip | head -40
```

**산출물**

- 계획서 3.1 표의 "확인 필요" 항목 전부 채움
- 계획서 3.3 인벤토리에 `zip` 폴더 내용 추가
- 적재 대상 목록 `inventory.csv`: `drive_name, artifact_id, variant, include(Y/N), reason`

**검증**

- [ ] EC2 여유 디스크가 **적재 예정량 × 2 이상**이다 (해제·gz·프리뷰 작업 여유). 아니면 계획서 3.5 재계산 후 번들 제외
- [ ] 번들과 개별 파일의 중복 여부를 파일명 수준에서 판정했다 (해시 판정은 Phase 1)
- [ ] `duk003312` 원본 유무를 팀에 물었다 (답을 기다리지 않고 진행)
- [ ] `inventory.csv`가 있다

---

### Phase 1 — Drive 다운로드, 해제, 정규화

**목표.** 로컬에 `staging/files/<artifact>/<variant>/…` 트리를 완성한다. 아직 프리뷰는 없다.

**작업**

1. Drive에서 전체 다운로드 (브라우저 "전체 다운로드" 또는 `gdown --folder`)
2. `make_preview.py --extract-only`로 해제·정규화·MTL 수정만 수행
3. 해시 계산으로 번들 중복 판정 → 중복이면 번들 해제본 삭제
4. AIHub CSV 삭제 (AS-08)

**명령**

```bash
# 작업 폴더
mkdir -p ~/c201-assets/{download,staging} && cd ~/c201-assets

# 로컬 도구 프로젝트 (c201-asset-server/local/)
cd ~/source/repos/c201-asset-server/local && uv sync && cd ~/c201-assets

# (선택) 명령줄 다운로드 — 폴더가 공개 상태이므로 gdown이 동작한다
uv tool install gdown
gdown --folder "https://drive.google.com/drive/folders/1BoImuEunFExU9Gsw2q3-t7ePEdpSgl8f" -O download/
# gdown은 폴더당 50개 제한이 있다. 33개라 문제없다. 실패 시 브라우저로 받는다.

# 해제·정규화 (프리뷰 제외)
uv run --project ~/source/repos/c201-asset-server/local \
  python ~/source/repos/c201-asset-server/local/make_preview.py download/*.zip download/*.las --out staging/ --extract-only

# 중복 판정 — sha256 같은 파일 쌍 출력
uv run --project ~/source/repos/c201-asset-server/local \
  python ~/source/repos/c201-asset-server/local/tools/dedupe_report.py staging/files/ > dedupe_report.txt

# CSV 제거 (AS-08)
find staging/files -name "*.csv" -delete
```

**산출물**

- `staging/files/` 트리 (정규화 완료, MTL 상대경로)
- `dedupe_report.txt`
- `staging/files/**/_meta.json` (프리뷰 필드는 비어 있음)

**검증**

- [ ] `find staging/files -mindepth 2 -maxdepth 2 -type d | wc -l` 이 인벤토리의 variant 수와 일치
- [ ] 한글 폴더·파일명이 0개다: `find staging/files | grep -P '[\x{AC00}-\x{D7A3}]' | wc -l` → `0`
- [ ] 임의의 MTL 3개를 열어 `map_Kd`가 파일명만 가리킨다
- [ ] 각 OBJ 옆에 MTL이 참조하는 텍스처 파일이 실제로 있다 (`check_textures` 로그에 누락 0)
- [ ] `du -sh staging/files` 가 계획서 3.5 추정치 ±30% 안이다
- [ ] 중복 번들 해제본을 제거했거나, 중복 아님을 확인했다

---

### Phase 2 — 프리뷰 생성 파이프라인

**목표.** variant마다 GLB·PNG를 만들고 `_meta.json`을 채운다. **가장 시간이 걸리고 가장 많이 실패하는 단계다.** 작은 것부터 한다.

**작업**

1. `blender_preview.py`(1.5) 작성 → `lkh000002/source`(138MB, 텍스처 있음)로 단독 검증
2. `las_to_glb`(1.6) 작성 → `RR_07_01_EA_028.las`(6.2MB)로 단독 검증
3. 가장 큰 파일 1개로 한계 확인 (Blender 메모리·시간)
4. 점군 썸네일 방식 결정 (1.6의 a/b)
5. 전체 일괄 실행, 실패 목록 정리
6. `.gz` 생성 (1.7)

**명령**

```bash
BL="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
L=~/source/repos/c201-asset-server/local
cd ~/c201-assets

# 단독 검증 — 메시 (텍스처 있음)
mkdir -p staging/preview/lkh000002
"$BL" -b -P $L/blender_preview.py -- \
  staging/files/lkh000002/source/digital_obj/lkh000002-000-30000.obj \
  staging/preview/lkh000002/source.glb staging/preview/lkh000002/source.png 200000

# 단독 검증 — 점군
mkdir -p staging/preview/RR_07_01_EA_028
uv run --project $L python -c "
from make_preview import las_to_glb
print(las_to_glb('staging/files/RR_07_01_EA_028/source/RR_07_01_EA_028.las','staging/preview/RR_07_01_EA_028/source.glb'))"

# 전체
uv run --project $L python $L/make_preview.py --from-staging staging/ --previews --gzip 2>&1 | tee preview.log
grep -E "FAIL|ERROR|missing texture" preview.log
```

**로컬 `local/pyproject.toml`**

```toml
[project]
name = "c201-asset-local"
version = "0.1.0"
requires-python = ">=3.11,<3.12"
dependencies = ["laspy>=2.5", "open3d>=0.18", "trimesh>=4.4", "numpy", "pillow"]
```

**산출물**

- `staging/preview/<artifact>/<variant>.glb` + `.png`
- `_meta.json` 완성 (`tri_count`, `pt_count`, `preview_*`, `classes`, `tool_versions`)
- `.gz` 파일들
- `preview.log`, 실패 목록

**검증**

- [ ] GLB 하나를 [three.js editor](https://threejs.org/editor/) 또는 Blender에 드롭해서 텍스처가 보인다
- [ ] 모든 GLB가 15MB 이하다: `find staging/preview -name "*.glb" -size +15M` → 없음
- [ ] PLY 정점색이 GLB에 살아 있다 (권영호 OBJ 정점색으로 확인)
- [ ] LAS GLB에서 색이 보이고, `_meta.json`의 `classes`에 20/21 또는 12가 잡힌다
- [ ] 가장 큰 파일도 처리됐다 (또는 §1.8 2단계 감축으로 처리됐다)
- [ ] `blender_preview.py`의 5.2 API 옵션명(`export_vertex_color` 등) 확인·수정 완료 — ★ 표시 해제
- [ ] `.obj.gz` 크기가 원본의 40% 이하다
- [ ] 점군 썸네일 방식(a/b)을 정했고 계획서 13장 미결 #8을 갱신했다

---

### Phase 3 — EC2 기본 구성

**목표.** 빈 서버에 Nginx·uv·디렉터리·방화벽을 준비한다. 아직 파일은 없다.

**명령**

```bash
ssh c201
# --- EC2 안 --- (2.1 ~ 2.2, 2.6)
sudo apt update && sudo apt install -y nginx curl sqlite3
curl -LsSf https://astral.sh/uv/install.sh | sh && source ~/.bashrc
sudo mkdir -p /srv/catalog/{files,preview,app,web}
sudo chown -R ubuntu:ubuntu /srv/catalog
sudo ufw allow 80/tcp && sudo ufw status
echo "<h1>catalog ok</h1>" > /srv/catalog/web/index.html
```

2.4의 Nginx 설정을 `/etc/nginx/sites-available/catalog`에 올리고 활성화한다.

```bash
sudo nano /etc/nginx/sites-available/catalog        # 2.4 내용 붙여넣기
sudo ln -sf /etc/nginx/sites-available/catalog /etc/nginx/sites-enabled/catalog
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

**검증**

- [ ] 로컬 브라우저에서 `http://$SERVER_HOST/` → "catalog ok"
- [ ] `http://$SERVER_HOST/files/` → 빈 디렉터리 목록 (autoindex 동작)
- [ ] `uv --version` 동작
- [ ] `sudo ufw status`에 22/tcp, 80/tcp만 있다

---

### Phase 4 — 파일 전송

**목표.** `staging/files`, `staging/preview`를 EC2 `/srv/catalog/`로 옮긴다.

**방법 선택**

| 방법 | 장점 | 단점 | 권장 |
| --- | --- | --- | --- |
| `scp -r -C` | 이미 있음, 단순 | 중단 시 재개 불가, 파일 수 많으면 느림 | 초기 1회 |
| `tar \| ssh` 파이프 | 이미 있음, 파일 수 많아도 빠름 | 중단 시 재개 불가 | **초기 1회 권장** |
| WSL rsync | 증분·재개·검증 | WSL 설치 필요 | 이후 증분 투입 |

**명령**

```bash
# tar 파이프 (Git Bash). 3GB에 30분~1시간 (회선 의존)
cd ~/c201-assets/staging
tar cf - files preview | ssh c201 \
  "cd /srv/catalog && tar xf - && du -sh files preview"

# 또는 scp
scp -r -C files preview c201:/srv/catalog/
```

전송 후 무결성 확인:

```bash
# 로컬
cd ~/c201-assets/staging && find files preview -type f -exec sha256sum {} + | sort -k2 > ../local.sha
# EC2
ssh c201 \
  "cd /srv/catalog && find files preview -type f -exec sha256sum {} + | sort -k2" > ../remote.sha
diff ../local.sha ../remote.sha && echo OK
```

**검증**

- [ ] `diff local.sha remote.sha` 출력 없음
- [ ] `http://$SERVER_HOST/files/bon004740/source/scan_ply/` 에 PLY가 보이고 클릭하면 받아진다 (**AS-AT-03 조기 확인**)
- [ ] `http://$SERVER_HOST/preview/bon004740/source.glb` 가 200으로 내려온다
- [ ] `curl -sI -H "Accept-Encoding: gzip" http://$SERVER_HOST/files/.../xxx.obj | grep -i content-encoding` → `gzip` (**AS-AT-08**)

---

### Phase 5 — `scan.py`와 DB

**목표.** `files/`·`preview/`를 훑어 SQLite를 만든다. 재실행하면 변경분만 반영한다.

**설계**

```text
scan.py --root /srv/catalog --db catalog.db
  1. 계획서 7.1 DDL로 DB 초기화 (없으면 생성)
  2. files/<artifact>/<variant>/ 순회
       artifact 없으면 INSERT
         source_org: 'RR_' 접두 → aihub, 6자리 숫자 접두어 → museum, 그 외 other
         region/type_code: aihub면 계획서 8.4로 디코딩
       variant 없으면 INSERT (method 1차 추정은 계획서 8.3 표)
       파일마다: size·mtime 바뀐 것만 sha256 재계산 → UPSERT
         kind: 확장자 → obj|mtl|texture(.jpg/.png, '_nor' 없음)|normalmap('_nor')|ply|stl|las|json|png|other
         옆에 .gz 있으면 has_gz=1
       _meta.json 있으면 tri_count/pt_count/original_name 갱신
  3. preview/<artifact>/<variant>.glb/.png 존재 → variants.preview_glb/thumb_png
  4. DB에 있는데 디스크에 없는 파일 → DELETE (variant·artifact도 비면 삭제)
  5. 요약 출력: added/updated/removed/took_ms  (JSON 한 줄 — /api/rescan이 그대로 반환)
```

`.gz`·`_meta.json`은 `files` 테이블에 넣지 않는다 (부속 파일).

**명령**

```bash
# 코드 배치 (로컬 → EC2)
scp -r ~/source/repos/c201-asset-server/server/{pyproject.toml,app} \
  c201:/srv/catalog/

# EC2
cd /srv/catalog && uv python install 3.11 && uv sync
uv run python app/scan.py --root /srv/catalog --db catalog.db
sqlite3 catalog.db "select source_org, count(*) from artifacts group by 1;
select count(*) from variants;
select count(*), sum(size) from files;
select variant_id from variants where preview_glb is null;"
```

**검증**

- [ ] artifact·variant·file 수가 인벤토리와 일치한다
- [ ] 두 번 연속 실행하면 두 번째는 `added=0 updated=0 removed=0`
- [ ] 파일 하나를 지우고 실행하면 `removed=1`, 복구하면 `added=1`
- [ ] `preview_glb is null` 목록이 Phase 2 실패 목록과 일치
- [ ] `duk003312`에 `source` variant가 없음이 DB에 그대로 드러난다
- [ ] 실행 시간이 30초 이내 (해시는 변경분만)

---

### Phase 6 — FastAPI

**목표.** 3장 API를 구현한다.

**명령**

```bash
# EC2 — 개발 모드
cd /srv/catalog && uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload &
curl -s localhost:8000/api/health
curl -s "localhost:8000/api/artifacts?q=EA_028" | python3 -m json.tool | head -30
curl -s -X PATCH localhost:8000/api/variants/RR_07_01_EA_028%2Fpointr_restored \
  -H 'content-type: application/json' \
  -d '{"owner":"장서진","method":"PoinTr 보충점 병합 (class 12)"}'
curl -s -X POST localhost:8000/api/rescan
```

**검증**

- [ ] 8개 엔드포인트가 모두 응답한다
- [ ] `q=` 한글 검색이 된다 (`q=토기` → title/tags에 걸림)
- [ ] PATCH 후 GET에 반영되고 `updated_at`이 바뀐다
- [ ] PATCH body에 허용 외 키 → 400
- [ ] 없는 id → 404 JSON
- [ ] `/api/rescan`이 scan을 실행하고 요약을 반환한다. 두 번 동시에 호출하면 한쪽은 `409 busy`
- [ ] Nginx 경유 `http://$SERVER_HOST/api/health` 도 200

---

### Phase 7 — 화면과 뷰어

**목표.** 4장 화면. **비교 모드까지가 MUST다.**

**순서** (매 단계 끝에서 동작하는 상태 유지)

1. 목록 + 검색 → 상세 (파일 링크) — 여기서 이미 A·C 달성
2. 뷰어 단일 GLB 로드 + 프레이밍
3. variant 드롭다운으로 전환
4. 비교 모드 (분할 + `linkCameras`)
5. 인라인 편집
6. 점군 점 크기 슬라이더, URL 해시 상태
7. (선택) three.js `web/vendor/` 복사

**명령**

```bash
# 로컬에서 만들고 EC2로 밀어넣는 반복
scp ~/source/repos/c201-asset-server/server/web/* \
  c201:/srv/catalog/web/
```

**검증** (= 계획서 4.2 수용시험)

- [ ] AS-AT-01 인증 없이 열림
- [ ] AS-AT-02 `RR_07_01_EA_028` 검색 → 변형 4개
- [ ] AS-AT-03 PLY 하나만 다운로드
- [ ] AS-AT-04 프리뷰 3초 내 표시·회전 (개발자도구 Network로 GLB 로드 시간 확인)
- [ ] AS-AT-05 비교 모드 카메라 동기화
- [ ] AS-AT-06 메타 편집 저장·유지
- [ ] 점군(`RR_07_01_PA_033/symmetry_restored`)이 색과 함께 보인다
- [ ] 텍스처 있는 메시(`bon004740/source`)가 텍스처와 함께 보인다
- [ ] 모바일 폭(≤768px)에서 목록/상세가 위아래로 쌓인다
- [ ] 콘솔 에러 0

---

### Phase 8 — systemd·Nginx 마무리

**목표.** 재부팅해도 살아 있고, 로그가 남고, 설정이 문서와 일치한다.

**작업**

1. 2.5 systemd 유닛 등록, 개발 모드(`--reload`) 프로세스 종료
2. 2.4 Nginx 최종 설정 반영 확인
3. 재부팅 테스트
4. 로그 로테이션 확인 (`/etc/logrotate.d/nginx` 기본으로 충분)
5. 설정 파일 사본을 `c201-asset-server/deploy/`에 보관

**명령**

```bash
# EC2
sudo nano /etc/systemd/system/catalog-api.service     # 2.5 내용
sudo systemctl daemon-reload && sudo systemctl enable --now catalog-api
sudo systemctl status catalog-api --no-pager
sudo reboot
# 2분 후
curl -s http://$SERVER_HOST/api/health

# 설정 사본 회수 (로컬)
scp c201:/etc/nginx/sites-available/catalog \
  ~/source/repos/c201-asset-server/deploy/nginx-catalog.conf
scp c201:/etc/systemd/system/catalog-api.service \
  ~/source/repos/c201-asset-server/deploy/catalog-api.service
```

**검증**

- [ ] 재부팅 후 2분 안에 화면·API·파일이 전부 응답 (**AS-AT-09**)
- [ ] `systemctl status catalog-api` active, `journalctl -u catalog-api -n 20`에 에러 없음
- [ ] `sudo nginx -t` OK
- [ ] `deploy/`에 두 설정 파일 사본이 있다

---

### Phase 9 — 팀 공개와 메타 채우기

**목표.** 팀원이 쓰기 시작하고, 각자 자기 파일의 `owner`·`method`를 채운다.

**작업**

1. 팀 채널에 링크와 한 줄 사용법 공유
2. 각 팀원에게 요청: 자기가 만든 variant의 `owner`, `method` 채우기
3. `license` 필드는 데이터 확보 담당이 채움 (U-02 진행에 따라)
4. `duk003312` 원본, `유물복원_자료.zip` 출처 등 미해결 항목 정리
5. `README.md` 작성 (사용법 요약)
6. `DECISIONS.md`·명세 22.3 갱신 제안 (계획서 12장 초안) — **적용은 팀 회의 결정 후**

**공유 문구 초안**

> 유물 자료 서버 열었습니다 → http://$SERVER_HOST/
> 검색하면 유물별로 원본·복원본이 나오고, 브라우저에서 3D로 돌려볼 수 있고, 필요한 파일 하나만 받을 수 있습니다.
> 부탁: 자기가 만든 복원본에 담당자·방법을 채워주세요 (항목 클릭하면 바로 수정됩니다).
> 새 파일 올릴 건 저(영호)한테 주세요 — 프리뷰 만들어서 올립니다.

**검증**

- [ ] AS-AT-10: 새 파일 1건을 6.1 절차로 투입해 15분 안에 검색에 노출
- [ ] variant의 80% 이상에 `owner`가 채워짐 (1주 후 확인)

---

# 3부. 운영

## 6. 운영 절차

### 6.1 새 파일 투입 (AS-07)

```text
1. 팀원이 zip/las를 권영호에게 전달 (Drive 또는 직접)
2. 로컬:  uv run --project $L python $L/make_preview.py <파일> --out ~/c201-assets/staging/ --previews --gzip
3. 전송:  cd ~/c201-assets/staging && tar cf - files/<artifact> preview/<artifact> \
            | ssh c201 "cd /srv/catalog && tar xf -"
4. 재스캔: curl -X POST http://$SERVER_HOST/api/rescan
5. 확인:  화면에서 검색
```

한 건 15분 이내. 이름이 계획서 8장 규칙에 안 맞으면 `--artifact <id> --variant <name>`으로 직접 지정한다.

### 6.2 메타 수정

웹 화면에서 인라인 편집. CLI가 필요하면:

```bash
ssh c201 \
  "sqlite3 /srv/catalog/catalog.db \"update variants set owner='장서진' where variant_id='bon004740/restored'\""
```

### 6.3 삭제

파일을 지우고 재스캔하면 DB에서도 빠진다. **Drive 원본은 건드리지 않는다.**

```bash
ssh ... "rm -rf /srv/catalog/files/<artifact>/<variant> /srv/catalog/preview/<artifact>/<variant>.*"
curl -X POST http://$SERVER_HOST/api/rescan
```

### 6.4 디스크 감시

```bash
ssh c201 "df -h / | tail -1; du -sh /srv/catalog/{files,preview}"
```

주 1회 확인. **여유가 20% 미만이면** 번들·중복·`.gz` 효율을 점검한다.

### 6.5 백업

- **원본: Google Drive가 백업이다 (AS-01).** 서버가 사라지면 Phase 1~4를 다시 돈다 (반나절).
- **DB(`catalog.db`)와 `_meta.json`**: 사람이 채운 메타가 들어 있어 Drive에 없다. 주 1회 로컬로 복사한다.

```bash
mkdir -p ~/c201-assets/backup
scp c201:/srv/catalog/catalog.db \
  ~/c201-assets/backup/catalog-$(date +%F).db
```

- 프리뷰·gz는 재생성 가능하므로 백업하지 않는다.

### 6.6 장애 대응

| 증상 | 확인 | 조치 |
| --- | --- | --- |
| 화면은 뜨는데 목록이 빔 | `curl localhost:8000/api/health` | `sudo systemctl restart catalog-api`, `journalctl -u catalog-api -n 50` |
| 파일 404 | `ls /srv/catalog/files/<경로>` | 경로 오타·전송 누락 → 재전송 후 rescan |
| GLB 안 뜸 | 개발자도구 Network — 404/CORS/MIME | `preview/` 존재, Nginx `types`에 glb, CDN 차단 여부(4.3 vendor 전환) |
| 502 | Nginx는 살고 API 죽음 | `systemctl status catalog-api` |
| 디스크 풀 | `df -h` | 6.4 |
| gzip이 안 먹음 | `curl -sI -H "Accept-Encoding: gzip" <url>` | `.gz` 존재·mtime 확인, `gzip_static on` 위치 |
| SSH 안 됨 | — | AWS 콘솔(SSAFY 제공 여부 확인). **ufw 작업 중 22 삭제 금지** |

---

## 부록 A. 명령 모음

```bash
# 변수
HOST=c201                           # ~/.ssh/config 별명 (JENKINS_BUILD_GUIDE.md 1절)
L=~/source/repos/c201-asset-server/local
BL="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"

# 접속
ssh $HOST

# 실측
ssh $HOST "df -h / && free -h && nproc && lsb_release -a"

# 프리뷰 단독 (Blender)
"$BL" -b -P $L/blender_preview.py -- in.obj out.glb out.png 200000

# 전체 프리뷰
uv run --project $L python $L/make_preview.py --from-staging ~/c201-assets/staging/ --previews --gzip

# 전송 (tar 파이프)
cd ~/c201-assets/staging && tar cf - files preview | ssh $HOST "cd /srv/catalog && tar xf -"

# 재스캔
curl -X POST http://$SERVER_HOST/api/rescan

# 상태
ssh $HOST "systemctl status catalog-api --no-pager; sudo nginx -t; df -h / | tail -1"

# 로그
ssh $HOST "journalctl -u catalog-api -n 50 --no-pager; tail -50 /var/log/nginx/catalog.error.log"

# DB 백업
scp -i $PEM $HOST:/srv/catalog/catalog.db ~/c201-assets/backup/catalog-$(date +%F).db

# DB 질의
ssh $HOST "sqlite3 /srv/catalog/catalog.db 'select artifact_id, count(*) from variants group by 1'"
```

## 부록 B. 참고

- 계획서: [PLAN.md](PLAN.md)
- three.js: https://threejs.org/docs/ — GLTFLoader, OBJLoader, MTLLoader, PLYLoader, OrbitControls
- Blender Python API 5.x: https://docs.blender.org/api/current/ — `bpy.ops.wm.obj_import`, `bpy.ops.export_scene.gltf`
- laspy: https://laspy.readthedocs.io/
- Open3D: https://www.open3d.org/docs/
- trimesh: https://trimesh.org/
- uv: https://docs.astral.sh/uv/
- Nginx `gzip_static`: https://nginx.org/en/docs/http/ngx_http_gzip_static_module.html
- FastAPI: https://fastapi.tiangolo.com/
