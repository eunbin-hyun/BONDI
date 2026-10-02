"""
집 2채 분리 — house_ink.glb → house_ink_a.glb(작은 채) · house_ink_b.glb(큰 채)   (2026-09-14)
==================================================================================================
왜: 두 채가 한 메시로 묶여 있어 언리얼에서 한 채만 옮기거나 크기를 바꿀 수 없었다.
무엇을: house_ink.glb 를 건물별로 잘라 각각 따로 내보낸다. UV·텍스처는 그대로라 겉모습은 동일.
피벗: 채마다 '발밑 한가운데' (가로는 그 채 바닥면 중심, 높이는 그 채 최저점) → 언리얼에서 회전·크기 조절이 자연스럽다.
배치 정보: records/house_split.json 에 원본 glb 바운드와 채마다의 피벗 위치(원본 좌표)를 남긴다.
          언리얼 쪽 ue_split_house.py 가 이 값으로 '원래 있던 자리'에 정확히 놓는다.
확인 지표: 두 파일의 면 수 합 = 원본 면 수, 채마다 바운드 크기가 원본 안에 들어옴.
"""
import json, os, numpy as np, trimesh

RT = "assets/inwangjesaekdo/runtime"; REC = "assets/inwangjesaekdo/records"; os.makedirs(REC, exist_ok=True)
SPLIT_X = 10.0            # 원본 좌표에서 이 값보다 작으면 작은 채, 크면 큰 채 (build_house_ink.py 와 같은 기준)

src = trimesh.load(f"{RT}/house_ink.glb", force="mesh")
V = np.asarray(src.vertices); F = np.asarray(src.faces); UV = np.asarray(src.visual.uv)
mat = src.visual.material
full_lo, full_hi = V.min(0), V.max(0)
print(f"원본: 정점 {len(V)}  면 {len(F)}  바운드 {np.round(full_lo,2).tolist()} ~ {np.round(full_hi,2).tolist()}")

cen = V[F].mean(1)
groups = {"a": cen[:, 0] < SPLIT_X, "b": cen[:, 0] >= SPLIT_X}
info = {"source_bounds_min": full_lo.tolist(), "source_bounds_max": full_hi.tolist(), "buildings": {}}
tot = 0
for key, sel in groups.items():
    Fi = F[sel]
    used = np.unique(Fi)
    remap = -np.ones(len(V), int); remap[used] = np.arange(len(used))
    Vi = V[used].copy(); UVi = UV[used].copy(); Fi2 = remap[Fi]
    lo, hi = Vi.min(0), Vi.max(0)
    pivot = np.array([(lo[0] + hi[0]) / 2, lo[1], (lo[2] + hi[2]) / 2])     # 발밑 한가운데 (y 가 높이)
    Vi -= pivot
    out = trimesh.Trimesh(Vi, Fi2, process=False)
    out.visual = trimesh.visual.TextureVisuals(uv=UVi, material=mat)
    out.vertex_normals = np.repeat(out.face_normals, 3, axis=0) if False else out.vertex_normals
    path = f"{RT}/house_ink_{key}.glb"
    out.export(path, include_normals=True)
    tot += len(Fi2)
    info["buildings"][key] = {
        "file": os.path.basename(path), "faces": int(len(Fi2)),
        "pivot_in_source": pivot.tolist(),
        "size_m": (hi - lo).tolist(),
        "label": "house_ink_small" if key == "a" else "house_ink_big",
    }
    print(f"  {key} ({'작은 채' if key=='a' else '큰 채'}): 면 {len(Fi2)}  크기 {np.round(hi-lo,2).tolist()} m  "
          f"피벗(원본좌표) {np.round(pivot,2).tolist()}  {os.path.getsize(path)//1024} KB")

json.dump(info, open(f"{REC}/house_split.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"면 수 합 {tot} / 원본 {len(F)}  ({'OK' if tot == len(F) else '!! 다름'})")

# 검증: 각 파일을 다시 읽어 피벗을 되돌리면 원본 위치와 같아야 한다
for key, d in info["buildings"].items():
    g = trimesh.load(f"{RT}/{d['file']}", force="mesh")
    back = np.asarray(g.vertices) + np.array(d["pivot_in_source"])
    inside = (back >= full_lo - 1e-4).all() and (back <= full_hi + 1e-4).all()
    print(f"  검증 {key}: 피벗 복원 후 원본 바운드 안 {inside}  (True 여야 함)  최저점 y 오프셋 {np.asarray(g.vertices)[:,1].min():.3f} (0 이어야 함)")
print(">>> OK — records/house_split.json 과 함께 ue_split_house.py 로 배치")
