"""원화 스카이라인 아래 화면 영역 중 DEM 데이터가 실제로 존재하는 비율 (구/신 DEM 비교)."""
import json, numpy as np, raycast

CFG = "/mnt/user-data/outputs/best_fit.json"
W, H = 600, 343                       # 3000x1715의 1/5


def coverage(dem):
    sc = raycast.Scene(cfg=CFG, dem=dem)
    c = json.load(open(CFG, encoding="utf-8"))
    PW, PH = c["painting_size"]
    cam = c["camera"]
    f = cam["focal_px"] * W / PW
    ppx = cam["principal_x_px"] * W / PW
    ppy = cam["horizon_y_px"] * H / PH

    jx, jy = np.meshgrid(np.arange(W) - ppx + .5, np.arange(H) - ppy + .5)
    d = np.stack([jx.ravel(), -jy.ravel(), np.full(W*H, f)], 1)
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    fw, rt = sc.fwd, sc.rgt
    dirs = np.stack([d[:, 0]*rt[0] + d[:, 2]*fw[0],
                     d[:, 0]*rt[1] + d[:, 2]*fw[1],
                     d[:, 1]], 1)
    dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
    eye = (sc.vx, sc.vy, sc.cam_z)
    P, m = sc.trace(eye, dirs, exag=True, tmax=4000., step=8., refine=4)
    return m.reshape(H, W), sc


sky = np.load("painting_skyline.npy")            # 원화 스카이라인 (열별 y, 원본 해상도)
skyd = np.interp(np.linspace(0, len(sky)-1, W), np.arange(len(sky)), sky) * H / 1715.0
rows = np.arange(H)[:, None]
below = rows > skyd[None, :]                      # 스카이라인 아래 = 지형이어야 하는 영역

out = {}
for name, dem in [("구 DEM (2도엽)", "inwang_5m_5179.tif"),
                  ("신 DEM (10도엽)", "dem10_5m_5179.tif")]:
    hit, sc = coverage(dem)
    cov = (hit & below).sum() / below.sum()
    out[name] = cov
    print(f"{name:18s} 지형 커버율 {cov*100:5.1f}%   (결손 {100-cov*100:4.1f}%)")
    np.save(f"cov_{'old' if '구' in name else 'new'}.npy", (hit & below))

np.save("cov_below.npy", below)
print("\n개선:", f"{(out['신 DEM (10도엽)']-out['구 DEM (2도엽)'])*100:+.1f}%p")
