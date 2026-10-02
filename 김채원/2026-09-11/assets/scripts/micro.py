"""micro_relief.npy 를 임의의 카메라정렬 좌표에서 읽는다 (쌍선형)."""
import json, os, numpy as np

_H = _M = None


def _load():
    global _H, _M
    if _H is None:
        _H = np.load("micro_relief.npy")
        _M = json.load(open("micro_relief.json", encoding="utf-8"))
    return _H, _M


def available():
    return os.path.exists("micro_relief.npy") and os.path.exists("micro_relief.json")


def sample(Xc, Zc):
    """Xc(우), Zc(전방) [m] → 잔결 높이 [m]. 범위 밖은 0."""
    H, M = _load()
    nz, nx = H.shape
    cc = (np.asarray(Xc, float)+M["half_width_m"])/(2*M["half_width_m"])*(nx-1)
    rr = (np.asarray(Zc, float)+M["back_m"])/(M["depth_m"]+M["back_m"])*(nz-1)
    ok = (cc >= 0) & (cc <= nx-1) & (rr >= 0) & (rr <= nz-1)
    cc = np.clip(cc, 0, nx-1.001); rr = np.clip(rr, 0, nz-1.001)
    c0 = cc.astype(np.int32); r0 = rr.astype(np.int32); fc = cc-c0; fr = rr-r0
    val = (H[r0, c0]*(1-fc)*(1-fr) + H[r0, c0+1]*fc*(1-fr)
           + H[r0+1, c0]*(1-fc)*fr + H[r0+1, c0+1]*fc*fr)
    return np.where(ok, val, 0.0)
