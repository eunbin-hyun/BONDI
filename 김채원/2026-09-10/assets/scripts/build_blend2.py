"""
인왕제색도 3D 복원 .blend — 2차 (개체 분리판)

포함
  지형   : 10도엽 5m DEM, 셰이프 키 0=실측 / 1=정선의 지형 g(d)
  나무   : 소나무 297그루 (전경 26 = 눈높이 17m / 중경·원경 271 = 1.6m)
  기와집 : 2동 (본채 141m, 좌측 처마 63m)
  운무   : 등고도 157m 상단선 + 두께 80m 사면 껍질 (반투명)
  카메라 : 원화 초점거리·주점 재현

컬렉션으로 나눠서 켜고 끄며 값 조정할 수 있게 했다.
좌표계는 Blender 표준 Z-up (X=우, Y=전방, Z=상) — 명세 19.3과 같은 축.
"""
import bpy, json, math, os, numpy as np, rasterio
from pyproj import Transformer
from mathutils import Euler
from PIL import Image

OUT = "inwang_recon_v2.blend"
STEP, HALF_W, DEPTH, BACK = 6.0, 1250.0, 2600.0, 250.0

cfg = json.load(open("/mnt/user-data/outputs/best_fit.json", encoding="utf-8"))
src = rasterio.open("dem10_5m_5179_filled.tif")
dem = src.read(1).astype("float32"); dem[dem <= -9998] = np.nan
inv = ~src.transform; Hh, Ww = dem.shape


def elev(x, y):
    c, r = inv*(x, y)
    ok = (c >= 0)&(c < Ww-1)&(r >= 0)&(r < Hh-1)
    c = np.clip(c-.5, 0, Ww-1.001); r = np.clip(r-.5, 0, Hh-1.001)
    c0 = c.astype(np.int32); r0 = r.astype(np.int32); fc = c-c0; fr = r-r0
    v = (dem[r0,c0]*(1-fc)*(1-fr)+dem[r0,c0+1]*fc*(1-fr)
         + dem[r0+1,c0]*(1-fc)*fr+dem[r0+1,c0+1]*fc*fr)
    return np.where(ok, v, np.nan)


t = Transformer.from_crs("EPSG:4326", "EPSG:5179", always_xy=True)
vp, cam = cfg["viewpoint"], cfg["camera"]
vx, vy = t.transform(vp["lon"], vp["lat"])
cam_z = vp["ground_elev_m"] + vp["eye_height_m"]
az0 = math.radians(cam["azimuth_deg"]); f = cam["focal_px"]
ppx, ppy = cam["principal_x_px"], cam["horizon_y_px"]
PW, PH = cfg["painting_size"]
fwd = np.array([math.sin(az0), math.cos(az0)]); rgt = np.array([math.cos(az0), -math.sin(az0)])

xc = np.arange(-HALF_W, HALF_W+STEP, STEP); zc = np.arange(-BACK, DEPTH+STEP, STEP)
Xc, Zc = np.meshgrid(xc, zc); ny, nx = Xc.shape
X = vx+Xc*rgt[0]+Zc*fwd[0]; Y = vy+Xc*rgt[1]+Zc*fwd[1]
Z = elev(X, Y); inside = np.isfinite(Z); Z = np.where(inside, Z, np.nanmin(Z))
E, N, U = X-vx, Y-vy, Z-cam_z
hz = np.maximum(np.hypot(E, N), 1e-6); el = np.arctan2(U, hz)

from curves import Curves
CV = Curves(json.load(open("distortion_curves.json", encoding="utf-8")))
U_gd = CV.deform(Z, hz, vp["ground_elev_m"]) - cam_z
Zc_ = E*fwd[0]+N*fwd[1]; Xc_ = E*rgt[0]+N*rgt[1]

# 원화 스카이라인 위로 솟은 지형은 잘라내지 않고 '능선 높이'로 눌러 내린다.
# 잘라내면 VR에서 구멍이 보이고, 눌러 내리면 면이 이어진 채 정선의 능선을 넘지 않는다.
sky = np.load("painting_skyline.npy")
sky_u = np.linspace(0, PW-1, len(sky))
with np.errstate(divide="ignore", invalid="ignore"):
    _u = ppx + f*Xc_/Zc_
sky_y = np.interp(np.clip(_u, 0, PW-1), sky_u, sky)
U_lim = (ppy - sky_y)/f*Zc_                      # 그 화면행에 해당하는 카메라 기준 높이
in_x = (Zc_ > 30) & (_u >= 0) & (_u < PW)
over = in_x & (U_gd > U_lim)
n_over = int(over.sum())
U_gd = np.where(over, U_lim, U_gd)
U = np.where(over, np.minimum(U, U_lim), U)
print(f"원화 능선 위로 솟은 정점 {n_over:,} ({100*over.mean():.1f}%) → 능선 높이로 눌러 내림")


# 가시성 + UV
mx = np.full(el.shape, -np.pi/2)
for sf in np.linspace(0.05, 0.96, 36):
    zz = elev(vx+E*sf, vy+N*sf)-cam_z
    mx = np.maximum(mx, np.arctan2(np.where(np.isnan(zz), -1e4, zz), hz*sf))
vis = el >= mx-math.radians(0.25)
with np.errstate(divide="ignore", invalid="ignore"):
    up_ = ppx+f*Xc_/Zc_; vp_ = ppy-f*U_gd/Zc_
# 스침각 제외 — 시선이 지면을 스치는 자리는 원화 화소가 수십 배로 늘어나 검은 띠가 된다
from grazing import view_stretch
STRETCH_MAX = 12.0
_st = view_stretch(Xc_, Zc_, U_gd, STEP, STEP)
_graze = _st >= STRETCH_MAX
inframe = (Zc_ > 30)&(up_ >= 0)&(up_ < PW)&(vp_ >= 0)&(vp_ < PH)&vis&inside&(~_graze)

TW, TH = Image.open("tex_inwang.jpg").size          # 아틀라스 실측 (하드코딩 금지)
AH = int(round(TW*PH/PW))                            # 위쪽 원화 영역 높이
# 아래쪽 판 = 평면(위에서 내려다본) 베이스컬러 → 평면 UV
uu = np.where(inframe, np.clip(up_/PW, 0, 1), np.clip((Xc_+HALF_W)/(2*HALF_W), 0, 1))
vv = np.where(inframe, np.clip(vp_/PH, 0, 1)*(AH/TH),
              (AH+np.clip((Zc_+BACK)/(DEPTH+BACK), 0, 1)*(TH-AH))/TH)
print(f"스침각 제외 {_graze.sum():,} ({100*_graze.mean():.1f}%)")
print(f"격자 {ny}x{nx}={Xc.size:,}  DEM 안 {100*inside.mean():.1f}%  "
      f"원화 텍스처 {inframe.sum():,} ({100*inframe.mean():.1f}%)  아틀라스 {TW}x{TH} (원화 {AH}px)")

# 전경 지면 잔결(절차적 연출층) — UV 판정을 마친 뒤 형상에만 얹는다
import micro
if micro.available():
    _mr = micro.sample(Xc_, Zc_)
    U = U + _mr; U_gd = U_gd + _mr
    print(f"전경 잔결 적용  진폭 99% {np.percentile(np.abs(_mr),99):.2f} m (절차적 연출층)")

# ── Blender 씬
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene


def coll(name):
    c = bpy.data.collections.new(name); sc.collection.children.link(c); return c


C_TER, C_TREE, C_TREE2, C_HOUSE, C_FOG, C_INSC, C_BASE, C_REF = (
    coll("01_지형"), coll("02_나무"), coll("02b_나무_런타임LOD_참고용"),
    coll("03_기와집"), coll("04_운무"), coll("05_화제"), coll("06_받침"), coll("07_기준점"))

me = bpy.data.meshes.new("인왕산_지형")
verts = np.stack([Xc_.ravel(), Zc_.ravel(), U.ravel()], 1).astype(np.float32)
idx = np.arange(ny*nx).reshape(ny, nx)
a = idx[:-1, :-1]; b2 = idx[:-1, 1:]; c2 = idx[1:, 1:]; d2 = idx[1:, :-1]
keep = (inside[:-1, :-1]&inside[:-1, 1:]&inside[1:, 1:]&inside[1:, :-1]).ravel()
quads = np.stack([a.ravel(), b2.ravel(), c2.ravel(), d2.ravel()], 1)[keep]
me.vertices.add(len(verts)); me.vertices.foreach_set("co", verts.ravel())
me.loops.add(quads.size); me.polygons.add(len(quads))
me.loops.foreach_set("vertex_index", quads.ravel())
me.polygons.foreach_set("loop_start", np.arange(len(quads))*4)
me.polygons.foreach_set("loop_total", np.full(len(quads), 4))
me.update(calc_edges=True)
uvl = me.uv_layers.new(name="UVMap")
loopUV = np.stack([uu.ravel()[quads.ravel()], 1.0-vv.ravel()[quads.ravel()]], 1).astype(np.float32)
uvl.data.foreach_set("uv", loopUV.ravel())
uvp = me.uv_layers.new(name="PlanarUV")
_pu = np.clip((Xc_.ravel() + HALF_W)/(2*HALF_W), 0, 1)
_pv = np.clip((Zc_.ravel() + BACK)/(DEPTH + BACK), 0, 1)
uvp.data.foreach_set("uv", np.stack([_pu[quads.ravel()], _pv[quads.ravel()]], 1)
                     .astype(np.float32).ravel())
ob = bpy.data.objects.new("인왕산_지형", me); C_TER.objects.link(ob)

ob.shape_key_add(name="실측_지형", from_mix=False)
sk = ob.shape_key_add(name="정선_과장_깊이별", from_mix=False)
sk.data.foreach_set("co", np.stack([Xc_.ravel(), Zc_.ravel(), U_gd.ravel()], 1)
                    .astype(np.float32).ravel())
sk.value = 1.0; sk.slider_min = 0.0; sk.slider_max = 2.0
ob.data.shape_keys.name = "과장_컨트롤"

mat = bpy.data.materials.new("원화_투영"); mat.use_nodes = True
nt = mat.node_tree
for n in list(nt.nodes):
    if n.type != "OUTPUT_MATERIAL":
        nt.nodes.remove(n)
outn = nt.nodes[0]
img = bpy.data.images.load(os.path.abspath("tex_inwang.jpg")); img.filepath = "//tex_inwang.jpg"
tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = img; tn.location = (-500, 200)
em = nt.nodes.new("ShaderNodeEmission"); em.location = (-200, 200)
em.inputs["Strength"].default_value = 1.0
nt.links.new(tn.outputs["Color"], em.inputs["Color"])
nt.links.new(em.outputs["Emission"], outn.inputs["Surface"])
# 노멀맵은 언릿(Emission)에는 걸리지 않는다. 그래서 노멀맵을 '가상의 빛'으로 직접 계산해
# (법선·광원 내적) 밝기에 곱한다. 채널 하나만 쓰던 이전 방식보다 요철이 훨씬 잘 읽힌다.
if os.path.exists("tex_terrain_normal_1k.png"):
    nimg = bpy.data.images.load(os.path.abspath("tex_terrain_normal_1k.png"))
    nimg.filepath = "//tex_terrain_normal_1k.png"      # 상대경로 — 블렌드와 같은 폴더에 둔다
    nimg.colorspace_settings.name = "Non-Color"
    uvn = nt.nodes.new("ShaderNodeUVMap"); uvn.uv_map = "PlanarUV"; uvn.location = (-1320, -260)
    ntex = nt.nodes.new("ShaderNodeTexImage"); ntex.image = nimg; ntex.location = (-1100, -260)
    nt.links.new(uvn.outputs["UV"], ntex.inputs["Vector"])
    nmap = nt.nodes.new("ShaderNodeNormalMap"); nmap.location = (-830, -260)
    nmap.uv_map = "PlanarUV"; nmap.inputs["Strength"].default_value = 1.6
    nt.links.new(ntex.outputs["Color"], nmap.inputs["Color"])
    dot = nt.nodes.new("ShaderNodeVectorMath"); dot.operation = "DOT_PRODUCT"
    dot.location = (-620, -260)
    dot.inputs[1].default_value = (-0.42, -0.30, 0.86)      # 가상 광원 (좌상 위쪽)
    nt.links.new(nmap.outputs["Normal"], dot.inputs[0])
    mapr = nt.nodes.new("ShaderNodeMapRange"); mapr.location = (-430, -260)
    mapr.inputs["From Min"].default_value = 0.05
    mapr.inputs["From Max"].default_value = 0.95
    mapr.inputs["To Min"].default_value = 0.55
    mapr.inputs["To Max"].default_value = 1.42
    nt.links.new(dot.outputs["Value"], mapr.inputs["Value"])
    mixn = nt.nodes.new("ShaderNodeMix"); mixn.data_type = "RGBA"
    mixn.blend_type = "MULTIPLY"; mixn.location = (-190, 320)
    mixn.inputs["Factor"].default_value = 1.0
    nt.links.new(tn.outputs["Color"], mixn.inputs[6])
    nt.links.new(mapr.outputs["Result"], mixn.inputs[7])
    nt.links.new(mixn.outputs[2], em.inputs["Color"])
me.materials.append(mat)
for p in me.polygons:
    p.use_smooth = True
print(f"지형  정점 {len(verts):,}  면 {len(quads):,} (quad)")

# ── 개체 3종 임포트 (glTF 임포터가 Y-up → Z-up 변환을 해준다)
def import_parts(path, target, prefix, mat_maker):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.abspath(path))
    new = [o for o in bpy.data.objects if o not in before]
    m = mat_maker()
    for i, o in enumerate(new):
        o.name = f"{prefix}" if len(new) == 1 else f"{prefix}_{i:02d}"
        for c in list(o.users_collection):
            c.objects.unlink(o)
        target.objects.link(o)
        if o.type == "MESH":
            o.data.materials.clear(); o.data.materials.append(m)
    return new


def vcol_mat(name, rgba_from_attr=True, alpha=False):
    """언릿(Emission) 먹 셰이더 — PBR 음영을 쓰지 않아 플라스틱처럼 보이지 않는다.
    지형이 원화 텍스처를 언릿으로 쓰고 있으므로 나무·집도 같은 방식이어야 화풍이 안 깨진다."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    outn = nt.nodes[0]
    ca = nt.nodes.new("ShaderNodeVertexColor"); ca.layer_name = "Color"; ca.location = (-600, 0)
    em = nt.nodes.new("ShaderNodeEmission"); em.location = (-300, 100)
    em.inputs["Strength"].default_value = 1.0
    nt.links.new(ca.outputs["Color"], em.inputs["Color"])
    if alpha:
        tp = nt.nodes.new("ShaderNodeBsdfTransparent"); tp.location = (-300, -120)
        mx = nt.nodes.new("ShaderNodeMixShader"); mx.location = (-80, 0)
        nt.links.new(ca.outputs["Alpha"], mx.inputs["Fac"])
        nt.links.new(tp.outputs["BSDF"], mx.inputs[1])
        nt.links.new(em.outputs["Emission"], mx.inputs[2])
        nt.links.new(mx.outputs["Shader"], outn.inputs["Surface"])
        m.blend_method = "BLEND"
        try:
            m.shadow_method = "NONE"
        except Exception:
            pass
    else:
        nt.links.new(em.outputs["Emission"], outn.inputs["Surface"])
    return m


tr = import_parts("obj_trees.glb", C_TREE, "나무", lambda: vcol_mat("나무_정점색"))
tr2 = import_parts("obj_trees_lod.glb", C_TREE2, "나무_LOD", lambda: vcol_mat("나무_LOD"))
C_TREE2.hide_viewport = True; C_TREE2.hide_render = True
ho = import_parts("obj_house.glb", C_HOUSE, "기와집", lambda: vcol_mat("기와집_정점색"))
fo = import_parts("obj_fog.glb", C_FOG, "운무_사면껍질", lambda: vcol_mat("운무_반투명", alpha=True))

def insc_mat():
    """화제 판 — 언릿 + 알파. 텍스처는 GLB에 들어 있으므로 임포트된 것을 그대로 쓴다."""
    return None

before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=os.path.abspath("obj_inscription.glb"))
ins = [o for o in bpy.data.objects if o not in before]
for o in ins:
    o.name = "화제_인장"
    for cc in list(o.users_collection):
        cc.objects.unlink(o)
    C_INSC.objects.link(o)
    for mt in o.data.materials:
        if mt and mt.use_nodes:
            mt.blend_method = "BLEND"
            nt2 = mt.node_tree
            tex = next((n for n in nt2.nodes if n.type == "TEX_IMAGE"), None)
            outn2 = next((n for n in nt2.nodes if n.type == "OUTPUT_MATERIAL"), None)
            if tex and outn2:
                for n in list(nt2.nodes):
                    if n.type not in ("TEX_IMAGE", "OUTPUT_MATERIAL"):
                        nt2.nodes.remove(n)
                em2 = nt2.nodes.new("ShaderNodeEmission")
                tp2 = nt2.nodes.new("ShaderNodeBsdfTransparent")
                mx2 = nt2.nodes.new("ShaderNodeMixShader")
                nt2.links.new(tex.outputs["Color"], em2.inputs["Color"])
                nt2.links.new(tex.outputs["Alpha"], mx2.inputs["Fac"])
                nt2.links.new(tp2.outputs["BSDF"], mx2.inputs[1])
                nt2.links.new(em2.outputs["Emission"], mx2.inputs[2])
                nt2.links.new(mx2.outputs["Shader"], outn2.inputs["Surface"])
print(f"화제  오브젝트 {len(ins)}")
bs = import_parts("obj_base.glb", C_BASE, "디오라마_받침", lambda: vcol_mat("받침_먹"))
print(f"받침  오브젝트 {len(bs)}  면 {sum(len(o.data.polygons) for o in bs if o.type=='MESH'):,}")
for tag, objs in (("나무", tr), ("나무 LOD", tr2), ("기와집", ho), ("운무", fo)):
    n = sum(len(o.data.polygons) for o in objs if o.type == "MESH")
    print(f"{tag}  오브젝트 {len(objs)}  면 {n:,}")

# ── 정합 카메라
cd = bpy.data.cameras.new("정합카메라"); cd.sensor_fit = "HORIZONTAL"; cd.sensor_width = 36.0
cd.lens = f*36.0/PW
cd.shift_x = (ppx-PW/2)/PW
cd.shift_y = (ppy-PH/2)/PW
cd.clip_start, cd.clip_end = 0.5, 12000.0
camo = bpy.data.objects.new("정합카메라", cd); sc.collection.objects.link(camo)
camo.location = (0, 0, 0); camo.rotation_euler = Euler((math.radians(90), 0, 0), "XYZ")
sc.camera = camo
sc.render.resolution_x, sc.render.resolution_y = PW, PH

# ── 전경 밴드 시점 (눈높이 17m) — 왜 전경 나무가 저기 있는지 눈으로 보이게
cd2 = bpy.data.cameras.new("전경밴드_눈높이17m")
cd2.sensor_fit = "HORIZONTAL"; cd2.sensor_width = 36.0
cd2.lens = f*36.0/PW; cd2.shift_x = cd.shift_x; cd2.shift_y = cd.shift_y
cd2.clip_start, cd2.clip_end = 0.5, 12000.0
cam2 = bpy.data.objects.new("전경밴드_눈높이17m", cd2); sc.collection.objects.link(cam2)
cam2.location = (0, 0, 17.0-CV.h0)
cam2.rotation_euler = Euler((math.radians(90), 0, 0), "XYZ")

# ── 기준점
for nm, (lo, la) in {"인왕산_338m": (126.95785, 37.58488),
                     "북악산_342m": (126.97370, 37.59302),
                     "수성동계곡": (126.9633, 37.5808)}.items():
    px_, py_ = t.transform(lo, la); ex, nn = px_-vx, py_-vy
    zc2 = ex*fwd[0]+nn*fwd[1]; xc2 = ex*rgt[0]+nn*rgt[1]
    zz = float(np.ravel(elev(np.array([px_]), np.array([py_])))[0])
    hh = math.hypot(ex, nn)
    zd = float(CV.deform(np.array([zz]), np.array([max(hh, 1e-6)]), vp["ground_elev_m"])[0])-cam_z
    e = bpy.data.objects.new(nm, None)
    e.empty_display_type = "SPHERE"; e.empty_display_size = 25
    e.location = (xc2, zc2, zd); C_REF.objects.link(e)

# 운무 상단고도 표시용 평면 하나 (157 m)
FOG_ALT = json.load(open("objects_manifest.json", encoding="utf-8"))["fog"]["altitude_m"]
bpy.ops.mesh.primitive_plane_add(size=2400, location=(0, 1200, FOG_ALT-cam_z))
pl = bpy.context.object; pl.name = f"운무_상단고도_{FOG_ALT:.0f}m"
for c in list(pl.users_collection):
    c.objects.unlink(pl)
C_REF.objects.link(pl); pl.display_type = "WIRE"; pl.hide_render = True

w = bpy.data.worlds.new("지본"); w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.72, 0.66, 0.58, 1)
sc.world = w
sun = bpy.data.objects.new("해", bpy.data.lights.new("해", "SUN"))
sun.data.energy = 3.0
sun.rotation_euler = Euler((math.radians(50), 0, math.radians(-135)))
sc.collection.objects.link(sun)
try:
    sc.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError:
    sc.render.engine = "BLENDER_EEVEE"

# 열자마자 화풍이 보이도록 뷰포트 셰이딩을 지정해서 저장한다
for scr in bpy.data.screens:
    for ar in scr.areas:
        if ar.type == "VIEW_3D":
            for sp in ar.spaces:
                if sp.type == "VIEW_3D":
                    sp.shading.type = "MATERIAL"          # Material Preview
                    sp.shading.color_type = "TEXTURE"      # Solid 모드로 내려도 텍스처 유지
                    sp.shading.use_scene_world = False
                    sp.clip_end = 12000.0
                    sp.overlay.show_relationship_lines = False
bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(OUT), relative_remap=True, compress=True)
print(f"\n저장: {OUT}  {os.path.getsize(OUT)/1e6:.1f} MB")
print(f"렌즈 {cd.lens:.2f}mm  shift=({cd.shift_x:.4f}, {cd.shift_y:.4f})  해상도 {PW}x{PH}")
