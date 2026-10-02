"""
전시실용 액자 + 원화 판  (2026-09-13)
====================================
출력 (둘 다 pivot = 그림 중심, 실물 크기 m, 앞면 = +z. 양면이라 언리얼에서 어느 쪽을 보든 그림이 보임 → 축 부호 걱정 없음):
  runtime/painting_inwang.glb : 원화 판 138.0 × 79.2 cm (국립중앙박물관 표기), 텍스처 = 원화 JPG 를 2048 px 로 줄인 것.
                                 !! 원화 이미지는 소장기관 이용조건 미확인(박물관 페이지 공공누리 4유형 표기) — 팀 내부 빌드 한정, 대외 공개물 금지
  runtime/frame_inwang.glb    : 액자 몰딩 — 폭 FRAME_W, 두께 FRAME_T, 안쪽 턱(lip) 이 그림을 살짝 덮음. 색 = 진묵보다 어두운 옻칠색(baseColorFactor)
언리얼: ue_build_room_inwang.py 가 임포트·배치. 실물 배율은 거기서 액터 스케일로 (pivot 이 중심이라 안전).
검증 로그: 판 크기·비율, 텍스처 크기, 액자 바운드, 면 방향(양면).
"""
import os, numpy as np, trimesh
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
RT = "assets/inwangjesaekdo/runtime"; SRC = "assets/inwangjesaekdo/source/frame"; os.makedirs(SRC, exist_ok=True)
PAINT = "/mnt/user-data/uploads/landscape_to_3D/PICs/inwangjesaekdo.jpg"
PW, PH = 1.380, 0.792                 # m (국립중앙박물관: 79.2 × 138.0 cm)
TEX_W = 2048
FRAME_W, FRAME_T, LIP = 0.09, 0.045, 0.012   # 몰딩 폭·두께·안쪽 턱 폭 (m)
FRAME_RGB = (0.055, 0.045, 0.040)            # linear — 옻칠 흑갈색
CANVAS_BACK = 0.004                          # 판 두께 (m)

# ── 1) 원화 판 (앞·뒤 두 면, 뒤는 u 반전 → 뒤에서 봐도 정상)
im = Image.open(PAINT).convert("RGB"); im = im.resize((TEX_W, round(TEX_W * im.size[1] / im.size[0])), Image.LANCZOS)
im.save(f"{SRC}/painting_tex.jpg", quality=92)
hx, hy = PW / 2, PH / 2
V = np.array([[-hx, -hy, 0], [hx, -hy, 0], [hx, hy, 0], [-hx, hy, 0],
              [-hx, -hy, -CANVAS_BACK], [hx, -hy, -CANVAS_BACK], [hx, hy, -CANVAS_BACK], [-hx, hy, -CANVAS_BACK]])
UV = np.array([[0, 0], [1, 0], [1, 1], [0, 1], [1, 0], [0, 0], [0, 1], [1, 1]], float)      # trimesh 규약 v=0 아래
F = np.array([[0, 1, 2], [0, 2, 3], [5, 4, 7], [5, 7, 6]])                                   # 앞면 +z, 뒷면 -z (바깥향)
mat = trimesh.visual.material.PBRMaterial(baseColorTexture=im, metallicFactor=0.0, roughnessFactor=0.85, doubleSided=True)
trimesh.Trimesh(V, F, process=False, visual=trimesh.visual.TextureVisuals(uv=UV, material=mat)).export(f"{RT}/painting_inwang.glb", include_normals=True)

# ── 2) 액자: 바깥 사각 링(두께 FRAME_T) + 안쪽 턱(얇은 링, 그림 앞면을 LIP 만큼 덮음). 상자 6개 면 전부 바깥향
Vo, Fo = [], []
def box(x0, x1, y0, y1, z0, z1):
    o = len(Vo); c = np.array([[x, y, z] for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]); Vo.extend(c.tolist())
    quads = [[1, 5, 7, 3], [4, 0, 2, 6], [5, 4, 6, 7], [0, 1, 3, 2], [3, 7, 6, 2], [0, 4, 5, 1]]
    ctr = c.mean(0)
    for q in quads:
        for t in ([q[0], q[1], q[2]], [q[0], q[2], q[3]]):
            P = c[t]; n = np.cross(P[1] - P[0], P[2] - P[0])
            Fo.append([o + i for i in (t if np.dot(n, P.mean(0) - ctr) >= 0 else t[::-1])])
ox, oy = hx + FRAME_W, hy + FRAME_W; z0, z1 = -FRAME_T * 0.6, FRAME_T * 0.4          # 판(z=0) 기준 뒤 60 %, 앞 40 %
box(-ox, -hx, -oy, oy, z0, z1); box(hx, ox, -oy, oy, z0, z1); box(-hx, hx, -oy, -hy, z0, z1); box(-hx, hx, hy, oy, z0, z1)   # 바깥 링
lz0, lz1 = 0.0005, FRAME_T * 0.25                                                    # 턱: 그림 앞면 바로 위
box(-hx, -hx + LIP, -hy, hy, lz0, lz1); box(hx - LIP, hx, -hy, hy, lz0, lz1); box(-hx, hx, -hy, -hy + LIP, lz0, lz1); box(-hx, hx, hy - LIP, hy, lz0, lz1)
fm = trimesh.visual.material.PBRMaterial(baseColorFactor=[*FRAME_RGB, 1.0], metallicFactor=0.0, roughnessFactor=0.5)
frame = trimesh.Trimesh(np.array(Vo), np.array(Fo), process=False)
frame.visual = trimesh.visual.TextureVisuals(uv=np.zeros((len(Vo), 2)), material=fm)
frame.export(f"{RT}/frame_inwang.glb", include_normals=True)

# ── 검증
p = trimesh.load(f"{RT}/painting_inwang.glb", force="mesh"); t = np.asarray(p.visual.material.baseColorTexture)
b = p.bounds; print(f"painting_inwang.glb: {(b[1][0]-b[0][0])*100:.1f} × {(b[1][1]-b[0][1])*100:.1f} cm (비율 {(b[1][0]-b[0][0])/(b[1][1]-b[0][1]):.3f}, 원화 픽셀 비율 {im.size[0]/im.size[1]:.3f})  텍스처 {t.shape[1]}x{t.shape[0]}  면 {len(p.faces)}  법선 z {np.round(p.face_normals[:, 2], 1)} (앞 +1, 뒤 -1)")
f_ = trimesh.load(f"{RT}/frame_inwang.glb", force="mesh"); b = f_.bounds
print(f"frame_inwang.glb: 바깥 {(b[1][0]-b[0][0])*100:.1f} × {(b[1][1]-b[0][1])*100:.1f} cm, 두께 {(b[1][2]-b[0][2])*100:.1f} cm (앞으로 {b[1][2]*100:.1f} cm 돌출)  면 {len(f_.faces)}  중심 {np.round((b[0]+b[1])/2*100, 1)} cm (0,0,·)")
print(f">>> OK  {os.path.getsize(f'{RT}/painting_inwang.glb')//1024} KB + {os.path.getsize(f'{RT}/frame_inwang.glb')//1024} KB")
