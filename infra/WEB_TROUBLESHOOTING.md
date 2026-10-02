# 웹·미리보기 트러블슈팅 — 실제로 막혔던 것과 해결법

자료 서버(`http://$SERVER_HOST/`)를 쓰다 막히면 여기부터 본다.
젠킨스 쪽은 [JENKINS_TROUBLESHOOTING.md](JENKINS_TROUBLESHOOTING.md), 구축은 [WEB_SERVER_BUILD_GUIDE.md](WEB_SERVER_BUILD_GUIDE.md).

---

## 1. 상태를 보는 명령 — 이 네 개면 대부분 원인이 나온다

```bash
# ① 미리보기 작업 기록 — "왜 안 만들어졌나" 는 거의 항상 여기 적혀 있다
ssh c201 "for f in /srv/catalog/jobs/*.json; do echo \"\$(basename \$f): \$(cat \$f)\"; done"

# ② 하나 다시 만들기 (화면의 '지금 만들기'/'다시 시도' 와 같은 것)
A='굽다리바리유물ID/3d/restored'
curl -s -X POST "http://$SERVER_HOST/api/preview/rebuild?asset=$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1],safe=''))" "$A")"
curl -s "http://$SERVER_HOST/api/preview-status?asset=..."      # running → done / failed

# ③ Blender 가 실제로 그림을 그릴 수 있나 (--version 으로는 알 수 없다. 3.1 참고)
ssh c201 'SRC=$(ls /srv/catalog/files/originals/*/digital_obj/*.obj | head -1); \
  blender -b --python-exit-code 1 -P /srv/catalog/app/blender_preview.py -- "$SRC" /tmp/t.glb /tmp/t.png 60000 \
  | grep PREVIEW_REPORT; ls -l /tmp/t.glb /tmp/t.png'

# ④ 서버와 내 PC 의 미리보기가 같은지 (파일명+크기 해시가 같아야 한다)
ssh c201 "cd /srv/catalog/preview && find . -name '*.glb' -o -name '*.png' | sort | xargs stat -c '%n %s' | md5sum"
cd ~/c201-assets/preview && find . -name '*.glb' -o -name '*.png' | sort | xargs stat -c "%n %s" | md5sum
```

---

## 2. 증상별 빠른 표

| 증상 | 먼저 볼 것 | 자세히 |
| --- | --- | --- |
| 올렸는데 "미리보기가 아직 없습니다" | ①의 jobs 기록 | [3.1](#31-libegl) |
| GLB 를 올렸는데 안 뜬다 | ①의 jobs 기록 — 형식 문제가 아니다 | [3.1](#31-libegl) · [3.2](#32-glb) |
| LAS 점군만 미리보기가 없다 | pillow 설치 여부 | [3.3](#33-las) |
| AIHub 자료 '다시 만들기' 실패 | `자료 폴더를 찾지 못했습니다` | [3.4](#34-aihub) |
| 목록 썸네일과 상세가 **다른 유물** | Ctrl+F5 → ④ 해시 대조 | [3.5](#35-mismatch) |
| 지운 유물의 옛 사진이 보인다 | Ctrl+F5 | [3.6](#36-id) |
| 썸네일이 새까맣다 | 청동·나전이면 원래 어둡다 | [3.7](#37-dark) |
| 상세 뷰어만 너무 밝다 / 색이 다르다 | 화면 오른쪽 아래 밝기 슬라이더 | [3.8](#38-bright) |
| 유물이 옆으로 누워 있다 | `orientation_overrides.json` | [3.9](#39-up) |
| 모델이 회색으로만 보인다 | MTL·텍스처를 같이 올렸나 | [3.10](#310-grey) |
| 상태가 계속 "생성 중" 인데 끝난 것 같다 | `jobs/*.lock` | [3.11](#311-worker) |

---

## 3. 우리가 실제로 막혔던 것

<a id="31-libegl"></a>
### 3.1 서버 미리보기가 **전부** 실패 — `libEGL.so.1` (가장 크게 놓친 것)

**증상** 원본·복원본을 올려도 목록엔 뜨는데 3D 미리보기만 "아직 없습니다".
GLB 파일은 `preview/` 에 생겼는데 DB 에 경로가 기록되지 않았다.

**기록** jobs 에 세 건 모두 같은 줄:
```
{"state": "failed", "error": "blender rc=-6: Couldn't open libEGL.so.1: cannot open shared object file"}
```

**원인** Blender 가 **썸네일을 렌더할 때** 그래픽 라이브러리를 못 찾아 죽었다.
GLB 내보내기는 그 앞 단계라 파일은 이미 생겼고, 그래서 "파일은 있는데 안 보이는" 모습이 됐다.

**왜 못 잡았나** 설치 확인을 `blender -b --version` 으로만 했다. **버전 출력은 그래픽을 초기화하지 않는다.**
→ 확인은 반드시 위 ③처럼 **실제로 한 장 렌더**해 본다.

```bash
sudo apt-get install -y libegl1 libglx0 libgl1-mesa-dri libxext6
# 그 뒤 실패한 것만 다시 만들면 된다 (②). 파일을 다시 올릴 필요 없다.
```
`EGL Error (0x3009): EGL_BAD_MATCH` 경고는 소프트웨어 렌더로 넘어가는 것이라 **무해하다**.

<a id="32-glb"></a>
### 3.2 GLB 를 올렸는데 미리보기가 안 뜬다

3.1 과 **같은 원인**이었다 — 형식 문제가 아니다. 지금은 한 가지가 더 바뀌었다:

**GLB 는 브라우저가 바로 읽는 형식이라 변환을 기다리지 않는다.** 30MB 이하면 올린 GLB 를
그대로 미리보기로 써서 **업로드 직후 바로** 돌려 볼 수 있고, 뒤이어 Blender 가 경량 판본
(20만 삼각형·2K 텍스처)과 썸네일을 만들어 갈아 끼운다.

`.gltf` 분리형은 받지 않는다 — `.bin`·텍스처 참조가 흩어져 깨진다. **GLB 로 내보내서** 올린다.

<a id="33-las"></a>
### 3.3 LAS 점군만 미리보기가 없다

**원인** Blender 는 LAS 를 못 읽는다. 서버에 처리기가 아예 없었다(내 PC 에만 있었다).

**해결** `app/las_preview.py` 를 두어 순수 파이썬으로 glTF POINTS 로 내보내고, 썸네일은 PIL 로
점을 직접 찍는다. `pillow` 가 필요하다 — 배포 스크립트의 `uv sync` 가 설치한다.
안 되면 `ssh c201 "cd /srv/catalog && ~/.local/bin/uv sync"`. (18만 점 0.1초)

<a id="34-aihub"></a>
### 3.4 `자료 폴더를 찾지 못했습니다` — AIHub 자료

AIHub 는 변형이 한 칸 더 들어간다. `_artifact_folder()` 가 세 배치를 다 본다.

```
originals/<유물>/digital_obj/…          박물관·팀 등록
restored/<유물>/digital_obj/…           복원본
aihub/<유물>/<변형>/pointcloud_las/…    AIHub  ← 여기만 한 칸 더
```

<a id="35-mismatch"></a>
### 3.5 목록 썸네일과 상세 뷰어가 **다른 유물**로 보인다

원인이 **세 가지**였다. 먼저 **Ctrl+F5** 로 캐시를 지워 본다 — 대개 그것이다.

| # | 원인 | 확인·해결 |
| --- | --- | --- |
| 1 | **캐시** — `/preview/` 7일, `/files/` 1시간. 파일을 다시 만들어도 URL 이 같으면 브라우저가 옛것을 쓴다. 썸네일만 새것이고 GLB 는 옛것이면 서로 다른 유물처럼 보인다 | URL 에 `?v=수정시각` 을 붙여 해결. 옛 캐시는 Ctrl+F5 |
| 2 | **서버 파일 1건이 다른 판본** — 톤 보정 때 "GLB 는 안 바뀐다" 고 보고 PNG 만 보냈는데, 데시메이션 결과가 미세하게 달라진 게 1건 있었다 | 재생성 후엔 **항상** ④ 로 양쪽 해시를 대조한다 |
| 3 | **앞 카드의 그림이 남음** — 화면을 비우면서 뷰어 객체를 남겨 둬, 화면에 없는 캔버스에 계속 그렸다 | 비울 때 뷰어도 버리게 고쳤다(`showPreview`). 늦게 온 로드 결과는 번호표로 버린다 |

<a id="36-id"></a>
### 3.6 지운 유물의 **옛 사진**이 보인다

**있었던 일** 시험용 유물 하나를 지우고 다른 유물을 등록했더니 자동 ID `new20260911_01` 이
**재사용**됐다. 파일 경로가 글자 하나까지 같아져서 브라우저가 1시간 캐시에서 지운 자료의
사진을 꺼내 보여줬다. 파일은 정상이었다.

**해결** 지운 번호를 다시 쓰지 않는다(`originals`·`restored`·휴지통·DB 를 모두 본다).
`/files/` URL 에도 `?v=` 를 붙였다. **이미 본 화면은 Ctrl+F5** 한 번.

<a id="37-dark"></a>
### 3.7 썸네일이 새까맣다

**대부분은 유물이 원래 어둡다.** 가장 어두운 14건이 전부 청동·철제·나전·화각이었다.
그래도 렌더가 사진보다 더 어두웠던 이유:

- **Blender 5 의 기본 색 변환이 AgX**(필름 톤). 스캔 텍스처에는 촬영 조명이 이미 구워져
  있는데 거기 필름 톤을 한 번 더 씌우니 어두운 유물은 형체를 알아보기 어려워졌다.
  → `blender_preview.py` 에서 `view_transform="Standard"` + `exposure=0.5`.
  (백자에서도 흰 부분이 날아가지 않는다 — 실측 0.0%)
- 색 항목이 **전부 0** 인 LAS(PoinTr 원출력)는 점이 검게 찍혔다 → 전부 0 이면 색 없음으로 보고 회색.

바꿨으면 148건 재생성(`make_preview.py --force`, 13.5분) 후 **PNG 만** 보내면 된다(23MB).
색 변환은 GLB 에 영향이 없다 — 단, 보낸 뒤 ④ 로 대조할 것(3.5 의 2번).

<a id="38-bright"></a>
### 3.8 상세 뷰어만 너무 밝다 / 썸네일과 색이 다르다

**원인** 어두운 유물을 살리려고 전방위광(Ambient)을 크게 줬는데, 전방위광은 어두운 유물을
통째로 들뜨게 해서 반대로 과해졌다. 실측해서 썸네일에 맞췄다:

| | 썸네일 | Ambient 크게 | 맞춘 뒤 |
| --- | --- | --- | --- |
| 나전침 | 19 | 57 | 26 |
| 죽순 주전자 | 71 | 107 | 58 |
| 백자 병 | 129 | 229 | 127 |

`viewer.js`: Ambient 없음 · Hemisphere 0.2 · key 1.2 · fill 0.2 · rim 0.15,
재질은 `metalness=0, roughness=0.95`(MTL 에서 온 낮은 거칠기 때문에 반사가 강해 어두웠다).

유물마다 원래 색이 크게 다르니 **화면 오른쪽 아래 밝기 슬라이더**(0.4~2.4배)로 올려 본다.
비교 모드에서는 좌우가 따로 조절된다.

<a id="39-up"></a>
### 3.9 유물이 옆으로 누워 있다

**원인** 박물관 OBJ 는 위 축이 파일마다 다르다(WaveFront Z-up / Blender Y-up, 머리말과 실제가
다른 것도 있다). 148건 중 판정은 Y 87 · Z 40 · X 8 로 갈렸다.

**해결** `blender_preview.py` 가 형상으로 추정(바닥 슬랩 비율 × 원형 단면)한다. 틀리는 것은
`local/orientation_overrides.json` 에 적는다 — 현재 13건.

```json
{ "유물ID/3d/source": { "up": "Y", "flip": false } }
```
`up` = 파일 좌표에서 위를 향하는 축, `flip` = 그 축의 + 끝이 바닥이면 true.
**판단이 애매하면 그 유물의 `photo_2d/` 사진과 맞춰 본다** — 금관은 원형 관테가 아니라
고깔형 모관이어서 처음 추정이 맞았고, 청자 조롱박 병은 위아래가 뒤집혀 있었다.
고친 뒤 `python make_preview.py --force --only "<유물ID>/3d/source"`.

<a id="310-grey"></a>
### 3.10 모델이 색 없는 회색으로만 보인다

OBJ 만 올리고 **MTL·텍스처를 빠뜨린** 것이다. OBJ 는 세 개가 한 벌이다.
등록할 때 **폴더째** 넣으면 하위 폴더까지 훑는다.

빠진 참조가 있으면 등록 직후 알려준다:
```
같이 올렸어야 할 파일이 빠졌습니다: model.mtl — 모델이 회색으로 보입니다
```

<a id="311-worker"></a>
### 3.11 상태가 계속 "생성 중" 이다

API 는 `uvicorn --workers 2` 로 돈다. 진행 상태를 프로세스 메모리에 두면 올린 워커와
상태를 묻는 워커가 달라 절반은 아무것도 못 본다 → `/srv/catalog/jobs/<asset>.json` 에
파일로 적고 `.lock` 으로 중복 실행을 막는다.

- 30분+2분이 지나면 자동으로 `failed` 로 바뀐다.
- `409 이미 생성 중입니다` 가 계속 나오면 죽은 잠금이다:
  `ssh c201 "sudo -u ubuntu rm /srv/catalog/jobs/<…>.json.lock"`

---

## 4. 자료를 잘못 올렸을 때

**지우지 않고 휴지통으로 옮긴다.** 상세 → 메모 탭 맨 아래 → `이 유물 삭제`
(복원본 카드에서는 `이 복원본만 삭제`). 확인으로 유물 ID 를 그대로 타이핑해야 진행된다.

```bash
# 되살리기 — 폴더를 도로 옮기고 재스캔
ssh c201
sudo -u ubuntu mv /srv/catalog/files/_trash/<날짜시각>_<유물ID>/originals \
                 /srv/catalog/files/originals/<유물ID>
curl -s -X POST http://127.0.0.1:8412/api/rescan

# 진짜로 비우기 (되돌릴 수 없다)
sudo -u ubuntu rm -rf /srv/catalog/files/_trash/<그 폴더>
```

> 인증이 없는 서버(계획서 AS-04)라 링크를 아는 사람은 누구나 지울 수 있다.
> 휴지통이 그 위험을 받아 내는 장치다.
