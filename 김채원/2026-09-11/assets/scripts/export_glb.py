"""
지형 메시 + 인왕제색도 프로젝션 텍스처 → GLB
- 카메라 정렬 격자(시야 방향 기준)로 만들어 화면 안 정점 비율을 높인다
- 텍스처 아틀라스: 위쪽=원화(보이는 면), 아래쪽=DEM 음영기복(화면 밖·가려진 면)
"""
import json, os, numpy as np, rasterio, trimesh
from PIL import Image
from matplotlib.colors import LightSource
import matplotlib.pyplot as plt
from pyproj import Transformer
from build_terrain_mesh import Sampler, load
Image.MAX_IMAGE_PIXELS = None

PAINT="inwang_masked.jpg"   # 화제·인장을 제거한 원화 (build_inscription.py 생성)
STEP=6.0; HALF_W=1250.0; DEPTH=2600.0; BACK=250.0; TEX_W=2048
STRETCH_MAX=12.0            # 원화 화소가 이 배율 이상 늘어나면 투영을 포기한다(=검은 띠 방지)

def main():
    c,s,d = load(); smp=Sampler(s,d)
    t=Transformer.from_crs("EPSG:4326","EPSG:5179",always_xy=True)
    vp,cam=c["viewpoint"],c["camera"]
    vx,vy=t.transform(vp["lon"],vp["lat"]); cam_z=vp["ground_elev_m"]+vp["eye_height_m"]
    az0=np.radians(cam["azimuth_deg"]); f=cam["focal_px"]
    ppx,ppy=cam["principal_x_px"],cam["horizon_y_px"]; g=c["distortion"]["vertical_gain_g"]
    PW,PH=c["painting_size"]
    fwd=np.array([np.sin(az0),np.cos(az0)]); rgt=np.array([np.cos(az0),-np.sin(az0)])

    # 카메라 정렬 격자
    xc=np.arange(-HALF_W,HALF_W+STEP,STEP); zc=np.arange(-BACK,DEPTH+STEP,STEP)
    Xc,Zc=np.meshgrid(xc,zc); ny,nx=Xc.shape
    X=vx+Xc*rgt[0]+Zc*fwd[0]; Y=vy+Xc*rgt[1]+Zc*fwd[1]
    Z=smp(X,Y); inside=np.isfinite(Z)
    Z=np.where(inside,Z,np.nanmin(Z))
    print(f"격자 {ny}x{nx} = {Xc.size:,} 정점, DEM 안 {100*inside.mean():.1f}%")

    E,N,U=X-vx,Y-vy,Z-cam_z
    hz=np.maximum(np.hypot(E,N),1e-6); el=np.arctan2(U,hz)
    import json as _j
    from curves import Curves
    CV=Curves(_j.load(open("distortion_curves.json",encoding="utf-8")))
    U_g=CV.deform(Z, hz, vp["ground_elev_m"]) - cam_z        # 깊이별 g(d)·h(d)

    sky=np.load("painting_skyline.npy"); sky_u=np.linspace(0,PW-1,len(sky))
    with np.errstate(divide="ignore",invalid="ignore"):
        _u=ppx+f*Xc/Zc
    sky_y=np.interp(np.clip(_u,0,PW-1),sky_u,sky)
    U_lim=(ppy-sky_y)/f*Zc
    over=(Zc>30)&(_u>=0)&(_u<PW)&(U_g>U_lim)
    print(f"원화 능선 위로 솟은 정점 {over.sum():,} ({100*over.mean():.1f}%) → 능선 높이로 눌러 내림")
    U_g=np.where(over,U_lim,U_g); U=np.where(over,np.minimum(U,U_lim),U)

    mx=np.full(el.shape,-np.pi/2)
    for sf in np.linspace(0.05,0.96,36):
        zz=smp(vx+E*sf,vy+N*sf)-cam_z
        mx=np.maximum(mx,np.arctan2(np.where(np.isnan(zz),-1e4,zz),hz*sf))
    vis=el>=mx-np.radians(0.25)

    with np.errstate(divide="ignore",invalid="ignore"):
        u_px=ppx+f*Xc/Zc; v_px=ppy-f*U_g/Zc
    
    from grazing import view_stretch
    st=view_stretch(Xc,Zc,U_g,STEP,STEP)
    graze=st>=STRETCH_MAX
    inframe=(Zc>30)&(u_px>=0)&(u_px<PW)&(v_px>=0)&(v_px<PH)&vis&inside&(~graze)
    print(f"스침각 제외 정점 {graze.sum():,} ({100*graze.mean():.1f}%)  "
          f"— 신축 배율 {STRETCH_MAX:.0f}배 이상, 원화를 끌어다 붙이면 검은 띠가 된다")
    print(f"원화 텍스처가 붙는 정점 {inframe.sum():,} ({100*inframe.mean():.1f}%)")

    # --- 텍스처 아틀라스 : 위=원화 / 아래=평면(위에서 내려다본) 베이스컬러
    #     아래쪽 판은 build_normalmap.py가 만든 것으로, 스침각 보정·전경 지면 톤·
    #     절차적 잔결이 이미 들어 있다. 음영기복 원본보다 화풍에 가깝다.
    art=Image.open(PAINT).convert("RGB")
    tw=TEX_W; ah=int(round(tw*PH/PW))
    art=art.resize((tw,ah),Image.LANCZOS)
    if os.path.exists("tex_terrain_basecolor.png"):
        hh=tw
        hill=Image.open("tex_terrain_basecolor.png").convert("RGB").resize((tw,hh),Image.LANCZOS)
        planar=True
    else:                                            # 예비 경로 (예전 음영기복)
        with rasterio.open("dem10_5m_5179_filled.tif") as r:
            A=r.read(1).astype(float); A[A<=-9998]=np.nan; bb=r.bounds
        ls=LightSource(azdeg=315,altdeg=45)
        rgb=(ls.shade(np.nan_to_num(A,nan=np.nanmin(A)),cmap=plt.cm.gray,blend_mode="soft",
                      vert_exag=2.0,dx=5,dy=5)[...,:3]*255).astype(np.uint8)
        hh=int(round(tw*A.shape[0]/A.shape[1]))
        hill=Image.fromarray(rgb).resize((tw,hh),Image.LANCZOS); planar=False
    tex=Image.new("RGB",(tw,ah+hh)); tex.paste(art,(0,0)); tex.paste(hill,(0,ah))
    tex.save("tex_inwang.png"); TH=ah+hh
    print(f"아틀라스 {tex.size} (원화 {ah}px + {'평면 베이스컬러' if planar else '음영기복'} {hh}px)")

    uu_a=np.clip(u_px/PW,0,1); vv_a=np.clip(v_px/PH,0,1)*(ah/TH)
    if planar:
        uu_h=np.clip((Xc+HALF_W)/(2*HALF_W),0,1)
        vv_h=(ah+np.clip((Zc+BACK)/(DEPTH+BACK),0,1)*hh)/TH
    else:
        uu_h=np.clip((X-bb.left)/(bb.right-bb.left),0,1)
        vv_h=(ah+np.clip((bb.top-Y)/(bb.top-bb.bottom),0,1)*hh)/TH
    uu=np.where(inframe,uu_a,uu_h); vv=np.where(inframe,vv_a,vv_h)
    UVs=np.stack([uu.ravel(),1.0-vv.ravel()],axis=1)

    # 전경 지면 잔결(절차적 연출층) — UV·스침각 판정을 마친 뒤에 형상에만 얹는다
    import micro
    if micro.available():
        mr=micro.sample(Xc,Zc)
        U=U+mr; U_g=U_g+mr
        print(f"전경 잔결 적용  진폭 99% {np.percentile(np.abs(mr),99):.2f} m "
              f"(절차적 연출층, micro_relief.json 참조)")

    idx=np.arange(ny*nx).reshape(ny,nx)
    a=idx[:-1,:-1]; b2=idx[:-1,1:]; c2=idx[1:,1:]; d2=idx[1:,:-1]
    keep=(inside[:-1,:-1]&inside[:-1,1:]&inside[1:,1:]&inside[1:,:-1]).ravel()
    faces=np.vstack([np.stack([a.ravel(),b2.ravel(),c2.ravel()],1)[keep],
                     np.stack([a.ravel(),c2.ravel(),d2.ravel()],1)[keep]])

    out={}
    for tag,Uv,desc in [("real",U,"실측 지형"),("jeongseon",U_g,f"앙각 {g:.2f}배 과장 = 정선의 지형")]:
        V=np.stack([Xc.ravel(),Uv.ravel(),-Zc.ravel()],axis=1)
        mat=trimesh.visual.material.PBRMaterial(baseColorTexture=tex,
             metallicFactor=0.0,roughnessFactor=1.0)
        m=trimesh.Trimesh(vertices=V,faces=faces,process=False,
             visual=trimesh.visual.TextureVisuals(uv=UVs,material=mat))
        m.remove_unreferenced_vertices()
        p=f"inwang_{tag}.glb"; m.export(p)
        out[p]=desc
        print(f"{p}  {os.path.getsize(p)/1e6:.1f} MB  정점 {len(m.vertices):,} 면 {len(m.faces):,}  높이 {Uv.min():.0f}~{Uv.max():.0f}m")

    json.dump({"convention":"glTF 2.0 GLB, Y-up, -Z forward, 카메라=원점","unit":"meter",
      "grid_step_m":STEP,"extent_m":{"half_width":HALF_W,"depth":DEPTH},
      "camera":{"hfov_deg":cam["hfov_deg"],"focal_px":f,"azimuth_deg":cam["azimuth_deg"],
                "principal_px":[ppx,ppy],"eye_height_m":vp["eye_height_m"]},
      "viewpoint_wgs84":[vp["lat"],vp["lon"]],"ground_elev_m":vp["ground_elev_m"],
      "distortion_curves":CV.to_dict(),"meshes":out,
      "texture":"tex_inwang.png (위=원화 / 아래=DEM 음영기복, 화면 밖·가려진 면에 사용)",
      "distance_to_peak_m":1217}, open("mesh_manifest.json","w"),ensure_ascii=False,indent=2)

if __name__=="__main__": main()
