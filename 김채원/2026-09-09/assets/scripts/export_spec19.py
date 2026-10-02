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
PAINT = "/mnt/user-data/uploads/landscape_to_3D/PICs/inwangjesaekdo.jpg"
RUNTIME_BUDGET = 30_000          # 명세 20장 임시 기준 (유물 1점 면 수)

for d in ("source", "master", "runtime", "records"):
    os.makedirs(f"{ROOT}/{d}", exist_ok=True)

# X=우, Y=상, -Z=전방  →  X=우, Y=전방, Z=상  (X축 +90도)
R = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], float)

PARTS = [("terrain_real",  "inwang_real.glb",      "실측 지형"),
         ("terrain_jeong", "inwang_jeongseon.glb", "정선 과장 지형 g(d)"),
         ("trees",         "obj_trees.glb",        "소나무 297"),
         ("house",         "obj_house.glb",        "기와집 2동"),
         ("fog",           "obj_fog.glb",          "운무 사면 껍질")]

meshes = {}
for key, path, _ in PARTS:
    m = trimesh.load(path, force="mesh")
    m.vertices = np.asarray(m.vertices) @ R.T
    meshes[key] = m

# 공통 pivot: '정선 지형' 발자국의 XY 중심 + 전체 최저 Z  (단계 간 정렬 보장)
ref = meshes["terrain_jeong"].vertices
cx = 0.5*(ref[:, 0].min()+ref[:, 0].max())
cy = 0.5*(ref[:, 1].min()+ref[:, 1].max())
cz = min(m.vertices[:, 2].min() for m in meshes.values())
OFF = np.array([cx, cy, cz])
for m in meshes.values():
    m.vertices = np.asarray(m.vertices) - OFF
print(f"공통 pivot(바닥 중심) 이동량 {OFF.round(1).tolist()}  (모든 파트 동일)")

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

# ── runtime : 지형만 감면, 개체는 이미 가볍다
rt = []
# 나무는 낱개 원뿔 297개라 감면하면 사라진다 → 그대로 두고 지형·운무를 줄인다
TARGET = {"terrain_real": 12000, "terrain_jeong": 12000}
LOD_FILE = {"fog": "obj_fog_lod.glb"}
for key, _, desc in PARTS:
    m = meshes[key].copy()
    if key in LOD_FILE:
        m = trimesh.load(LOD_FILE[key], force="mesh")
        m.vertices = np.asarray(m.vertices) @ R.T - OFF
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
          "eye_scan2.json", "fog_null.json", "tree_height_check.json", "tree_refit.json"):
    src = f if os.path.exists(f) else f"/mnt/user-data/outputs/{f}"
    if os.path.exists(src):
        shutil.copy(src, f"{ROOT}/records/{os.path.basename(f)}")

man = {
  "artifactId": AID,
  "version": "0.3.0",
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
                  "운무 두께 80 m·380 m 이내 청천 — 원화 관찰에 의한 조형 선택"]
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
    "DEM 화소의 10.2 %는 미보유 도엽(37608068·078) 구간을 최근접+확산으로 외삽한 값이다. "
    "원화 시야 안에는 거의 들어오지 않는다.",
    "기와집 폭 22.3 m는 지붕선 획 2개를 한 채로 병합한 결과다. 두 채일 가능성이 있다."
  ],
  "runtime": {"triangles": int(scene_tris),
              "textures": 0, "master_textures": 1,
              "note": "master 지형은 2048x3380 아틀라스 1장(위=원화 투영/아래=음영기복). runtime 지형은 그 아틀라스를 정점색으로 구워 텍스처 0장.",
              "budget_spec20": RUNTIME_BUDGET},
  "review": {"by": None, "at": None, "decision": "pending"},
  "coordinate_contract": {"spec": "19.3", "unit": "meter", "up_axis": "Z",
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
