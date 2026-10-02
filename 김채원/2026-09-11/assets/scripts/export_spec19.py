"""
Q5 — 명세 19장 자산 번들 계약에 맞춰 내보낸다.

19.3 좌표·단위 계약
  단위 meter / 전시 pivot = 바닥 중심 / 상하축 Z-up (UE5) / glTF 2.0 GLB
  단계 간 같은 좌표·pivot·크기  → 실측지형·정선지형 두 단계를 동일 변환으로 처리
19.1 디렉터리 : source / master / runtime / records / manifest.json
"""
import json, os, shutil, numpy as np, trimesh
from PIL import Image
import fast_simplification

AID = "inwangjesaekdo"
ROOT = f"assets/{AID}"
PAINT = "/mnt/user-data/uploads/landscape_to_3D/PICs/inwangjesaekdo.jpg"  # source/input 용은 원본
RUNTIME_BUDGET = 30_000          # 명세 20장 임시 기준 (유물 1점 면 수)

for d in ("source", "master", "runtime", "records"):
    os.makedirs(f"{ROOT}/{d}", exist_ok=True)

# glTF 2.0 규격은 +Y 가 위다. 예전에는 팀 계약(up_axis: Z)에 맞춘다고 X축 +90도를 걸어
# Z-up 으로 내보냈는데, 언리얼 임포터가 "glTF니까 Y-up"으로 보고 한 번 더 돌려서
# 자산이 90도 누워 들어왔다 (2026-09-11 실기에서 발견).
# → 규격대로 Y-up 을 유지한다. 언리얼이 임포트할 때 알아서 Z-up 으로 세운다.
R = np.eye(3)

PARTS = [("terrain_real",  "inwang_real.glb",      "실측 지형"),
         ("terrain_jeong", "inwang_jeongseon.glb", "정선 과장 지형 g(d)"),
         ("trees",         "obj_trees.glb",        "소나무 297"),
         ("house",         "obj_house.glb",        "기와집 2동"),
         ("fog",           "obj_fog.glb",          "운무 사면 껍질"),
         ("inscription",   "obj_inscription.glb",  "화제·인장 (공중 판)"),
         ("base",          "obj_base.glb",         "디오라마 받침")]

meshes = {}
for key, path, _ in PARTS:
    m = trimesh.load(path, force="mesh")
    m.vertices = np.asarray(m.vertices) @ R.T
    meshes[key] = m

# 공통 pivot: '정선 지형' 발자국(X-Z 평면)의 중심 + 전체 최저 Y  (Y-up 이므로 바닥은 Y 최소)
ref = meshes["terrain_jeong"].vertices
cx = 0.5*(ref[:, 0].min()+ref[:, 0].max())
cz = 0.5*(ref[:, 2].min()+ref[:, 2].max())
cy = min(m.vertices[:, 1].min() for m in meshes.values())
OFF = np.array([cx, cy, cz])
for m in meshes.values():
    m.vertices = np.asarray(m.vertices) - OFF
print(f"공통 pivot(바닥 중심) 이동량 {OFF.round(1).tolist()}  (모든 파트 동일, Y-up)")

rows = []
for key, _, desc in PARTS:
    m = meshes[key]
    p = f"{ROOT}/master/{key}.glb"
    m.export(p)
    b = m.bounds
    rows.append(dict(part=key, desc=desc, file=f"master/{key}.glb",
                     triangles=int(len(m.faces)),
                     size_m=[round(float(v), 1) for v in (b[1]-b[0])],
                     bytes=os.path.getsize(p)))
    print(f"master/{key}.glb  면 {len(m.faces):>7,}  크기 {np.round(b[1]-b[0],0)} m")

# ── 런타임 지형 텍스처 아틀라스 (1024x1024 한 장)
#    위 = 원화(클린 플레이트) / 아래 = 평면 베이스컬러(화면 밖·가려진 면·스침각용)
ATLAS = 1024
STRETCH_MAX = 12.0
ATLAS_PNG = "tex_runtime_atlas.png"
_cfg = json.load(open("/mnt/user-data/outputs/best_fit.json", encoding="utf-8"))
_cam = _cfg["camera"]
F, PPX, PPY = _cam["focal_px"], _cam["principal_x_px"], _cam["horizon_y_px"]
PWc, PHc = _cfg["painting_size"]
_art = Image.open("inwang_masked.jpg").convert("RGB")
AH_ = int(round(ATLAS*_art.size[1]/_art.size[0]))
_atl = Image.new("RGB", (ATLAS, ATLAS))
_atl.paste(_art.resize((ATLAS, AH_), Image.LANCZOS), (0, 0))
_atl.paste(Image.open("tex_terrain_basecolor_1k.png").convert("RGB")
           .resize((ATLAS, ATLAS-AH_), Image.LANCZOS), (0, AH_))
_atl.save(ATLAS_PNG)
print(f"런타임 아틀라스 {ATLAS}x{ATLAS} (원화 {AH_}px + 평면 {ATLAS-AH_}px) → {ATLAS_PNG}")

# ── runtime : 지형만 감면, 개체는 이미 가볍다
rt = []
# 나무는 낱개 원뿔 297개라 감면하면 사라진다 → 그대로 두고 지형·운무를 줄인다
TARGET = {"terrain_real": 10000, "terrain_jeong": 10000}
LOD_FILE = {"fog": "obj_fog_lod.glb", "trees": "obj_trees_lod.glb"}
for key, _, desc in PARTS:
    m = meshes[key].copy()
    if key in LOD_FILE:
        m = trimesh.load(LOD_FILE[key], force="mesh")
        m.vertices = np.asarray(m.vertices) - OFF
    if key in TARGET:
        V0 = np.asarray(m.vertices, np.float64)
        # 감면하면 UV가 사라지므로 먼저 텍스처를 정점색으로 굽는다
        C0 = None
        if isinstance(m.visual, trimesh.visual.texture.TextureVisuals):
            uv = np.asarray(m.visual.uv)
            tex = np.asarray(m.visual.material.baseColorTexture.convert("RGB"))
            th_, tw_ = tex.shape[:2]
            ui = np.clip((uv[:, 0]*(tw_-1)).astype(int), 0, tw_-1)
            vi = np.clip(((1-uv[:, 1])*(th_-1)).astype(int), 0, th_-1)
            C0 = np.c_[tex[vi, ui], np.full(len(uv), 255)].astype(np.uint8)
        elif key == "fog":
            C0 = np.tile(np.array([[246, 246, 246, 170]], np.uint8), (len(V0), 1))
        v, f = fast_simplification.simplify(
            np.asarray(m.vertices, np.float32), np.asarray(m.faces, np.int32),
            target_count=TARGET[key])
        vc = None
        if C0 is not None:
            from scipy.spatial import cKDTree
            _, nn = cKDTree(V0).query(v, k=1)
            vc = C0[nn]
        m = trimesh.Trimesh(vertices=v, faces=f, process=False,
                            visual=trimesh.visual.ColorVisuals(vertex_colors=vc) if vc is not None else None)
        if key.startswith("terrain") and os.path.exists(ATLAS_PNG):
            # 런타임 UV — 2026-09-11 변경
            #
            # 전에는 '위에서 내려다본 평면 UV' 를 썼다. 감면 뒤에도 정점 좌표로 다시 계산할 수
            # 있다는 게 이유였는데, 치명적인 부작용이 있었다: **시점을 향한 급사면은 위에서 보면
            # 면적이 거의 0** 이라, 원화의 먹이 몇 텍셀로 뭉개졌다 (런타임 베이스컬러 평균
            # RGB 154/141/127, 어두운 화소 20.8% — 사실상 먹그림이 사라짐).
            #
            # 카메라 투영 UV 역시 '정점 좌표의 함수' 라 감면 뒤에 똑같이 재계산할 수 있다.
            # 평면을 쓸 이유가 애초에 없었다. 그래서 master 와 같은 아틀라스 방식으로 바꾼다.
            #   · 시점에서 보이고 스치지 않는 정점 → 아틀라스 위쪽(원화)
            #   · 그 밖(화면 밖·가려짐·스침각)     → 아틀라스 아래쪽(평면 베이스컬러)
            #
            # 노멀맵은 런타임에서 뺀다. 머티리얼이 Unlit 이라 접선공간 노멀은 어차피 작동하지
            # 않고, 아틀라스 UV 와 평면 UV 를 한 메시에 동시에 물릴 수 없기 때문이다.
            # (master 용으로 tex_terrain_normal_1k.png 는 번들에 그대로 남겨 둔다)
            ex = json.load(open("terrain_uv_extent.json", encoding="utf-8"))
            HW, DP, BK = ex["half_width_m"], ex["depth_m"], ex["back_m"]
            vv = np.asarray(m.vertices)
            Xc = vv[:, 0] + OFF[0]                     # 우
            Uv = vv[:, 1] + OFF[1]                     # 눈높이 기준 높이
            Zc = -(vv[:, 2] + OFF[2])                  # 전방 거리
            Zs = np.maximum(Zc, 1e-6)
            u_px = PPX + F*Xc/Zs
            v_px = PPY - F*Uv/Zs
            inb = (Zc > 30) & (u_px >= 0) & (u_px < PWc) & (v_px >= 0) & (v_px < PHc)

            # 가림 판정 — 화면 z버퍼 (높이장이라 정점만으로도 충분히 걸러진다)
            BW, BH = 700, int(round(700*PHc/PWc))
            bx = np.clip((u_px/PWc*(BW-1)), 0, BW-1)
            by = np.clip((v_px/PHc*(BH-1)), 0, BH-1)
            buf = np.full((BH, BW), np.inf)
            ii = np.where(inb)[0]
            np.minimum.at(buf, (by[ii].astype(int), bx[ii].astype(int)), Zc[ii])
            near = np.full(len(vv), np.inf)
            near[ii] = buf[by[ii].astype(int), bx[ii].astype(int)]
            vis = Zc <= near*1.04

            # 스침각 — 원화 화소가 늘어나는 자리는 원화를 쓰지 않는다
            nrm = np.asarray(m.vertex_normals)
            ray = vv + OFF
            ray = ray/np.maximum(np.linalg.norm(ray, axis=1, keepdims=True), 1e-6)
            cosi = np.abs(np.sum(nrm*ray, axis=1)).clip(1e-3, 1.0)
            stretch = 1.0/cosi

            use = inb & vis & (stretch < STRETCH_MAX)

            # 아틀라스는 영역이 둘이라, 한 삼각형의 세 꼭짓점이 서로 다른 영역을 가리키면
            # UV가 아틀라스를 가로질러 보간돼 엉뚱한 무늬가 생긴다(경계 아티팩트).
            # → **면 단위로 영역을 정하고 정점을 분리한다.** 세 꼭짓점이 모두 '원화'일 때만 원화.
            Fi = np.asarray(m.faces)
            fpaint = use[Fi].all(1)
            V2 = vv[Fi].reshape(-1, 3)
            F2 = np.arange(len(V2)).reshape(-1, 3)
            Xc2 = V2[:, 0] + OFF[0]
            Uv2 = V2[:, 1] + OFF[1]
            Zc2 = -(V2[:, 2] + OFF[2])
            Zs2 = np.maximum(Zc2, 1e-6)
            u2 = PPX + F*Xc2/Zs2
            v2 = PPY - F*Uv2/Zs2
            pc = np.repeat(fpaint, 3)
            uu = np.where(pc, np.clip(u2/PWc, 0, 1), np.clip((Xc2 + HW)/(2*HW), 0, 1))
            vtop = np.where(pc, np.clip(v2/PHc, 0, 1)*(AH_/ATLAS),
                            (AH_ + np.clip((Zc2 + BK)/(DP + BK), 0, 1)*(ATLAS-AH_))/ATLAS)
            uvm = np.c_[uu, 1.0 - vtop]
            mat2 = trimesh.visual.material.PBRMaterial(
                baseColorTexture=Image.open(ATLAS_PNG),
                metallicFactor=0.0, roughnessFactor=1.0)
            m = trimesh.Trimesh(vertices=V2, faces=F2, process=False,
                                visual=trimesh.visual.TextureVisuals(uv=uvm, material=mat2))
            print(f"    {key}: 원화 면 {fpaint.sum():,}/{len(Fi):,} ({100*fpaint.mean():.1f}%) "
                  f"· 정점 분리 {len(vv):,}→{len(V2):,} (아틀라스 경계 무늬 방지)")
    p = f"{ROOT}/runtime/{key}.glb"
    m.export(p)
    rt.append(dict(part=key, file=f"runtime/{key}.glb", triangles=int(len(m.faces)),
                   bytes=os.path.getsize(p)))
    print(f"runtime/{key}.glb  면 {len(m.faces):>7,}")

# 한 단계(정선)를 켰을 때의 장면 면 수
scene_tris = sum(r["triangles"] for r in rt if r["part"] != "terrain_real")
print(f"\n단계 1개 표시 시 런타임 장면 면 수 {scene_tris:,} "
      f"(명세 20장 임시 기준 {RUNTIME_BUDGET:,})")

shutil.copy(PAINT, f"{ROOT}/source/input.jpg")
Image.open(PAINT).convert("RGB").resize((512, 293), Image.LANCZOS).save(f"{ROOT}/runtime/thumbnail.png")
for f in ("distortion_curves.json", "objects_manifest.json", "best_fit.json",
          "eye_scan2.json", "fog_null.json", "tree_height_check.json", "tree_refit.json",
          "terrain_uv_extent.json", "micro_relief.json"):
    src = f if os.path.exists(f) else f"/mnt/user-data/outputs/{f}"
    if os.path.exists(src):
        shutil.copy(src, f"{ROOT}/records/{os.path.basename(f)}")

man = {
  "artifactId": AID,
  "version": "0.11.0",
  # 명세 19장 개정안(docs/AMEND-19.md) 선반영. 현행 19.1은 손상 복원형(object)만 전제한다.
  # 개정 전까지는 선택 필드로 취급 — 자산 검사에서 필수로 보지 않는다.
  "artifactClass": "scene",
  "title": "정선 필 인왕제색도 — 실측 지형 기반 3D 복원",
  "description": "겸재 정선의 인왕제색도(1751)를 국토지리정보원 1:5,000 수치지형도에서 만든 "
                 "5 m DEM에 정합해 3D로 복원한 것. 지형·나무·기와집·운무를 각각 독립 개체로 분리했다.",
  "period": "조선 1751년 (신미년)",
  "type": "회화 기반 경관 복원",
  "source": {
    "kind": "photo",
    "credit": "정선 필 인왕제색도 (국보) — 소장기관 표기 확인 필요",
    "license": "확인 필요 — 공개 이미지 이용조건 미확인",
    "url": None,
    "terrain": "국토지리정보원 수치지형도 1:5,000 도엽 37608048·049·050·058·059·060·069·070·079·080"
  },
  "stages": [
    {"id": "terrain_real",  "label": "실측 지형",
     "method": "등고선·표고점 Delaunay 보간 5 m DEM", "human_in_loop": False, "ai_generated": False},
    {"id": "terrain_jeong", "label": "정선의 지형",
     "method": "앙각 깊이별 과장 g(d) 적용 (distortion_curves.json)",
     "human_in_loop": True, "ai_generated": False},
    {"id": "trees",  "label": "소나무", "method": "사람이 채집한 밑동 297점 + 높이 14그루 측정",
     "human_in_loop": True, "ai_generated": False},
    {"id": "house",  "label": "기와집", "method": "지붕선 채집 + 각크기 앵커 141 m",
     "human_in_loop": True, "ai_generated": False},
    {"id": "fog",    "label": "운무", "method": "운무 상단선 61점 → 등고도 157 m 층 + 사면 껍질",
     "human_in_loop": True, "ai_generated": False}
  ],
  "provenance": {
    "observed": ["지형 고도 (수치지형도 1:5,000 등고선·표고점)",
                 "시점 방위·초점거리 (스카이라인 정합)",
                 "나무 밑동 297점·높이 14그루·지붕선·기둥·운무 상단선 61점 (사람 채집)"],
    "ai_inferred": [],
    "estimated": ["과장계수 g(d) — 스카이라인·운무선 정합으로 추정",
                  "전경 밴드 눈높이 17 m — 나무 높이 일관성 최소화로 추정",
                  "나무 개체 높이 — 사람이 잰 14그루를 화면 최근접으로 전파",
                  "기와집 평면 깊이·벽 높이 — 정면 폭에서 비례 가정",
                  "운무 두께 80 m·380 m 이내 청천 — 원화 관찰에 의한 조형 선택",
                  "전경 지면 잔결 — 절차적 프랙탈 층(최대 1.15 m, 620 m 밖 0). "
                  "측정값이 아니라 연출층. micro_relief.json 참조"]
  },
  "limitations": [
    "기관 공식 유물 ID가 아직 배정되지 않았다 (작업용 ID: inwangjesaekdo).",
    "원화 이미지의 소장기관 표기와 이용조건을 확인하지 않았다. 확인 전 대외 공개 금지.",
    "외부 미술사 전문가 검토는 받지 않았다.",
    "나무 높이 자동 추출은 실패했다 — 먹 농도 기반 추출과 사람 측정의 상관 0.094. "
    "따라서 개체 높이는 사람이 잰 14그루에서 전파한 값이며 개별 나무의 실측이 아니다.",
    "전경 밴드에 눈높이 17 m를 쓴 것은 단일 시점으로 전경·중경을 동시에 만족시킬 수 없기 때문이다 "
    "(중경 나무·기와집은 1.6 m를 요구). 원화가 다시점으로 구성됐다는 해석이며 검증된 사실이 아니다.",
    "운무 상단선의 등고도성은 귀무모형 대비 0.51배로 유의하지만, 채집선을 아래로 100~200 px "
    "옮기면 산포가 더 작아져 채집 위치를 고유하게 지지하지는 않는다.",
    "런타임 지형의 색은 시점에서 보이는 사면(정점 28 %)에만 원화가 붙는다. 화면 밖·가려진 면·"
    "스침각 구역은 평면 베이스컬러(음영기복 + 원화 하단 지면 톤)다. 원화 해상도도 아틀라스 "
    "1024 폭으로 줄어 원본 3000 폭 대비 3배 손실이 있다.",
    "DEM 화소의 19.1 %는 자료가 없는 구간이다 — 미보유 도엽 + Delaunay가 자료 없는 쪽으로 "
    "만든 슬리버 삼각형(가장 가까운 입력점까지 65 m 초과)을 결측으로 되돌린 것. "
    "이 구간은 라플라스 막으로 매끄럽게 채웠고(mask_slivers.py + refill_dem.py), "
    "원화 시야 안에는 거의 들어오지 않는다. 시야 커버율은 99.2 %로 변화 없다.",
    "지형에 원화를 투영할 때 화소 신축이 12배(입사각 85.2°)를 넘는 자리는 투영을 포기하고 "
    "평면 베이스컬러로 대체했다. 그 결과 전경 지면의 무늬는 원화가 아니라 "
    "'원화 하단 지면 톤 + 지형 음영 + 절차적 잔결'이다.",
    "전경 지면 잔결(최대 1.15 m)은 연출용 절차적 층이다. 나무 밑동 역산으로 전경 지형을 "
    "복원하면 제거해야 한다.",
    "기와집 폭 22.3 m는 지붕선 획 2개를 한 채로 병합한 결과다. 두 채일 가능성이 있다."
  ],
  "runtime": {"triangles": int(scene_tris),
              "textures": 1, "master_textures": 1,
              "note": "runtime 지형은 1024x1024 아틀라스 한 장(위=원화 585px / 아래=평면 베이스컬러 439px). "
                      "UV는 카메라 투영 — 감면 뒤에도 정점 좌표로 재계산된다. 시점에서 보이고 스치지 않는 "
                      "정점만 원화를 쓰고(28%) 나머지는 평면 베이스컬러로 간다. "
                      "노멀맵은 런타임에서 뺐다 — 머티리얼이 Unlit이라 접선공간 노멀이 작동하지 않고, "
                      "아틀라스 UV와 평면 UV를 한 메시에 동시에 물릴 수 없다. "
                      "나무·기와집·운무·받침은 정점색(COLOR_0, 선형)이라 텍스처를 쓰지 않는다.",
              "budget_spec20": RUNTIME_BUDGET},
  "review": {"by": None, "at": None, "decision": "pending"},
  "coordinate_contract": {"spec": "19.3", "unit": "meter",
                          "up_axis_in_file": "Y",
                          "up_axis_note": "glTF 2.0 규격대로 파일 안은 +Y up이다. 언리얼 임포터가 "
                                          "Y-up→Z-up 변환과 m→cm 변환을 자동으로 하므로, 임포트 시 "
                                          "회전·스케일 보정이 필요 없다. 명세 19.3의 'up_axis: Z'는 "
                                          "'엔진에 들어간 뒤의 상태'를 가리키는 말로 정정이 필요하다 "
                                          "(docs/AMEND-19.md 2-5). 2026-09-11 실기에서 발견.",
                          "pivot": "바닥 중심", "format": "glTF 2.0 GLB",
                          "stages_aligned": True,
                          "pivot_offset_from_camera_frame_m": [round(float(v), 2) for v in OFF]},
  "parts_master": rows, "parts_runtime": rt
}
json.dump(man, open(f"{ROOT}/manifest.json", "w"), ensure_ascii=False, indent=2)
print(f"\n{ROOT}/manifest.json 작성 완료")
for r, dirs, fs in os.walk(ROOT):
    for f in sorted(fs):
        print(f"  {os.path.join(r,f)}  {os.path.getsize(os.path.join(r,f))/1e6:.2f} MB")
