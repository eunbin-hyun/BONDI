"""
DEM 레이마칭 렌더러 — 삼각형 래스터라이저 없이 조밀한 텍스처 렌더를 만든다.
지형 표면은 두 가지: 실측(Z) / 정선형(Z를 정합 시점 기준으로 g배 과장)
텍스처는 정합 카메라로 역투영해 원화를 샘플링, 화면 밖이면 음영기복.
"""
import json, numpy as np, rasterio
from pyproj import Transformer
from PIL import Image
from matplotlib.colors import LightSource
import matplotlib.pyplot as plt
Image.MAX_IMAGE_PIXELS=None

class Scene:
    def __init__(self, cfg="/mnt/user-data/outputs/best_fit.json", dem="dem10_5m_5179_filled.tif",
                 paint="/mnt/user-data/uploads/landscape_to_3D/PICs/inwangjesaekdo.jpg"):
        c=json.load(open(cfg,encoding="utf-8")); self.c=c
        s=rasterio.open(dem); self.s=s
        d=s.read(1).astype("float32"); d[d<=-9998]=np.nan
        self.d=d; self.inv=~s.transform; self.H,self.W=d.shape; self.b=s.bounds
        t=Transformer.from_crs("EPSG:4326","EPSG:5179",always_xy=True)
        vp,cam=c["viewpoint"],c["camera"]
        self.vx,self.vy=t.transform(vp["lon"],vp["lat"])
        self.az0=np.radians(cam["azimuth_deg"]); self.f=cam["focal_px"]
        self.ppx,self.ppy=cam["principal_x_px"],cam["horizon_y_px"]
        self.g=c["distortion"]["vertical_gain_g"]; self.PW,self.PH=c["painting_size"]
        self.ground0=vp["ground_elev_m"]
        import json as _j, os as _o
        from curves import Curves
        _p=_o.path.join(_o.path.dirname(_o.path.abspath(__file__)),"distortion_curves.json")
        self.cv=Curves(_j.load(open(_p,encoding="utf-8")) if _o.path.exists(_p) else None)
        self.cam_z=self.ground0+self.cv.h0
        self.fwd=np.array([np.sin(self.az0),np.cos(self.az0)])
        self.rgt=np.array([np.cos(self.az0),-np.sin(self.az0)])
        self.art=np.asarray(Image.open(paint).convert("RGB"))
        ls=LightSource(azdeg=315,altdeg=45)
        # 순수 음영(고도와 무관) → 원화의 지본색↔먹색 사이 듀오톤으로 착색
        sh=ls.hillshade(np.nan_to_num(d,nan=np.nanmin(d)),vert_exag=2.0,dx=5,dy=5)
        sh=np.clip((sh-0.15)/0.75,0,1)[...,None]
        a=self.art.reshape(-1,3)
        paper=np.percentile(a,88,axis=0); ink=np.percentile(a,6,axis=0)*1.15
        self.hill=(ink+(paper-ink)*sh).clip(0,255).astype(np.uint8)
        self.paper=paper.astype(np.uint8)

    def set_curves(self, cfg):
        """곡선 교체 — cfg는 distortion_curves.json과 같은 형식"""
        from curves import Curves
        self.cv=Curves(cfg); self.cam_z=self.ground0+self.cv.h0; return self

    def elev(self,x,y):
        c,r=self.inv*(x,y)
        ok=(c>=0)&(c<self.W-1)&(r>=0)&(r<self.H-1)
        c=np.clip(c-.5,0,self.W-1.001); r=np.clip(r-.5,0,self.H-1.001)
        c0=c.astype(np.int32); r0=r.astype(np.int32); fc=c-c0; fr=r-r0
        d=self.d
        v=(d[r0,c0]*(1-fc)*(1-fr)+d[r0,c0+1]*fc*(1-fr)
           +d[r0+1,c0]*(1-fc)*fr+d[r0+1,c0+1]*fc*fr)
        return np.where(ok,v,np.nan)

    def surf(self,x,y,exag=True):
        z=self.elev(x,y)
        if not exag: return z
        hz=np.maximum(np.hypot(x-self.vx,y-self.vy),1e-6)
        return self.cv.deform(z, hz, self.ground0)

    def trace(self,eye,dirs,exag=True,tmax=2600.,step=6.,refine=6):
        """eye=(x,y,z) 5179 좌표, dirs=(N,3) 단위벡터 → 히트점 (N,3), mask"""
        ex,ey,ez=eye
        N=len(dirs); t=np.full(N,step); hit=np.zeros(N,bool); tt=np.full(N,np.nan)
        prev=np.zeros(N,bool)
        for _ in range(int(tmax/step)):
            p=np.stack([ex+dirs[:,0]*t, ey+dirs[:,1]*t, ez+dirs[:,2]*t],1)
            zs=self.surf(p[:,0],p[:,1],exag)
            under=np.isfinite(zs)&(p[:,2]<zs)
            new=under&~hit
            tt[new]=t[new]; hit|=under
            t=t+step
            if hit.all(): break
        for _ in range(refine):   # 이분 세분화
            m=np.isfinite(tt)
            if not m.any(): break
            lo=tt[m]-step; hi=tt[m]
            mid=(lo+hi)/2
            p=np.stack([ex+dirs[m,0]*mid, ey+dirs[m,1]*mid, ez+dirs[m,2]*mid],1)
            zs=self.surf(p[:,0],p[:,1],exag)
            below=np.isfinite(zs)&(p[:,2]<zs)
            newhi=np.where(below,mid,hi); tt[m]=newhi; step/=2
        m=np.isfinite(tt)
        P=np.full((N,3),np.nan)
        P[m]=np.stack([ex+dirs[m,0]*tt[m], ey+dirs[m,1]*tt[m], ez+dirs[m,2]*tt[m]],1)
        return P,m

    def shade(self,P,m):
        out=np.full(P.shape[:1]+(3,),235,np.uint8)
        if not m.any(): return out
        X,Y,Z=P[m,0],P[m,1],P[m,2]
        E,Nn,U=X-self.vx,Y-self.vy,Z-self.cam_z
        Zc=E*self.fwd[0]+Nn*self.fwd[1]; Xc=E*self.rgt[0]+Nn*self.rgt[1]
        with np.errstate(divide="ignore",invalid="ignore"):
            u=self.ppx+self.f*Xc/Zc; v=self.ppy-self.f*U/Zc
        ok=(Zc>30)&(u>=0)&(u<self.PW)&(v>=0)&(v<self.PH)
        col=np.empty((m.sum(),3),np.uint8)
        ui=np.clip(u,0,self.PW-1).astype(int); vi=np.clip(v,0,self.PH-1).astype(int)
        col[:]=self.art[vi,ui]
        c,r=self.inv*(X,Y)
        hc=np.clip(c.astype(int),0,self.W-1); hr=np.clip(r.astype(int),0,self.H-1)
        hillc=self.hill[hr,hc]
        # 화면 경계에서 부드럽게 섞기 (딱딱한 사각 자국 방지)
        du=np.minimum(u,self.PW-1-u)/(0.045*self.PW)
        dv=np.minimum(v,self.PH-1-v)/(0.045*self.PH)
        w=np.clip(np.minimum(du,dv),0,1)[:,None]*ok[:,None]
        col=(col*w+hillc*(1-w)).astype(np.uint8)
        out[m]=col
        return out

    def render(self,eye,yaw_deg,pitch_deg=0.,hfov=45.,W=800,H=500,pp=None,**kw):
        yaw=np.radians(yaw_deg); pit=np.radians(pitch_deg)
        f=(W/2)/np.tan(np.radians(hfov)/2)
        cxp,cyp=(W/2,H/2) if pp is None else pp
        jx,jy=np.meshgrid(np.arange(W)-cxp+.5,np.arange(H)-cyp+.5)
        d=np.stack([jx.ravel(),-jy.ravel(),np.full(W*H,f)],1)
        d/=np.linalg.norm(d,axis=1,keepdims=True)
        cp,sp=np.cos(pit),np.sin(pit)
        dy=d[:,1]*cp-d[:,2]*sp; dz=d[:,1]*sp+d[:,2]*cp
        fw=np.array([np.sin(yaw),np.cos(yaw)]); rt=np.array([np.cos(yaw),-np.sin(yaw)])
        dirs=np.stack([d[:,0]*rt[0]+dz*fw[0], d[:,0]*rt[1]+dz*fw[1], dy],1)
        dirs/=np.linalg.norm(dirs,axis=1,keepdims=True)
        P,m=self.trace(eye,dirs,**kw)
        return Image.fromarray(self.shade(P,m).reshape(H,W,3))

    def panorama(self,eye,W=4096,H=2048,**kw):
        lon=(np.arange(W)+.5)/W*2*np.pi - np.pi        # -π..π (0 = 정합 방위각)
        lat=np.pi/2-(np.arange(H)+.5)/H*np.pi
        LO,LA=np.meshgrid(lon,lat)
        az=self.az0+LO
        dirs=np.stack([(np.cos(LA)*np.sin(az)).ravel(),
                       (np.cos(LA)*np.cos(az)).ravel(),
                       np.sin(LA).ravel()],1)
        P,m=self.trace(eye,dirs,**kw)
        img=self.shade(P,m).reshape(H,W,3)
        img[~m.reshape(H,W)]=self._sky()
        return Image.fromarray(img)

    def _sky(self):
        return self.paper

    def panorama_origin(self, W=8192, H=4096, exag=True, tmax=3000., step=6., eye=None):
        """정합 시점 기준 equirectangular 파노라마.
        가로 중앙(u=W/2)이 정합 방위각. 지형은 열별 누적최대각 + 이분탐색 없이 searchsorted."""
        ex,ey,ez = eye if eye is not None else (self.vx,self.vy,self.cam_z)
        az=self.az0+((np.arange(W)+.5)/W*2*np.pi-np.pi)
        D=np.arange(step,tmax,step)
        sa,ca=np.sin(az)[:,None],np.cos(az)[:,None]
        X=ex+sa*D[None,:]; Y=ey+ca*D[None,:]
        Z=self.surf(X,Y,exag)
        ANG=np.arctan2(np.where(np.isnan(Z),-1e4,Z-ez), D[None,:])
        CMAX=np.maximum.accumulate(ANG,axis=1)
        pit=np.pi/2-(np.arange(H)+.5)/H*np.pi           # 위→아래 (내림차순)
        asc=pit[::-1]                                    # 오름차순
        img=np.empty((H,W,3),np.uint8); sky=self._sky()
        for j in range(W):
            k=np.searchsorted(CMAX[j],asc)               # 첫 d where CMAX>=e
            k=k[::-1]                                    # 다시 위→아래
            hitm=k<len(D)
            dd=np.where(hitm,D[np.clip(k,0,len(D)-1)],np.nan)
            cp=np.cos(pit)
            px=ex+np.sin(az[j])*dd*cp; py=ey+np.cos(az[j])*dd*cp
            pz=ez+np.sin(pit)*dd
            col=np.empty((H,3),np.uint8)
            P=np.stack([px,py,pz],1)
            col[:]= self.shade(P,hitm)
            if (~hitm).any():                            # 하늘: 방향을 카메라로 투영해 지본 샘플
                d3=np.stack([np.sin(az[j])*cp,np.cos(az[j])*cp,np.sin(pit)],1)[~hitm]
                Zc=d3[:,0]*self.fwd[0]+d3[:,1]*self.fwd[1]
                Xc=d3[:,0]*self.rgt[0]+d3[:,1]*self.rgt[1]
                with np.errstate(divide="ignore",invalid="ignore"):
                    u=self.ppx+self.f*Xc/Zc; v=self.ppy-self.f*d3[:,2]/Zc
                ok=(Zc>1e-3)&(u>=0)&(u<self.PW)&(v>=0)&(v<self.PH)
                c2=np.repeat(sky[None,:],len(d3),0)
                ui=np.clip(u,0,self.PW-1).astype(int); vi=np.clip(v,0,self.PH-1).astype(int)
                c2[ok]=self.art[vi[ok],ui[ok]]
                col[~hitm]=c2
            img[:,j]=col
        return Image.fromarray(img)
