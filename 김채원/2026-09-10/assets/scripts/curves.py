"""깊이별 왜곡 곡선 g(d) · h(d) — 파이프라인 공용 모듈"""
import json, numpy as np

DEFAULT = {
  "camera_eye_height_m": 1.6,
  "g_knots": [[0,1.00],[120,1.35],[300,2.05],[700,2.10],[1150,1.71],[4000,1.71]],
  "h_knots": [[0,1.6],[150,1.6],[4000,1.6]],
}

class Curves:
    def __init__(self, cfg=None):
        c = dict(DEFAULT); c.update(cfg or {})
        self.h0 = float(c["camera_eye_height_m"])
        self.gk = np.array(c["g_knots"], float)
        self.hk = np.array(c["h_knots"], float)
    def g(self, d): return np.interp(d, self.gk[:,0], self.gk[:,1])
    def h(self, d): return np.interp(d, self.hk[:,0], self.hk[:,1])
    def deform(self, Z, d, ground0):
        """실측 고도 Z(수평거리 d)를 '정선의 지형'으로 변형.
        고정 카메라(눈높이 h0)로 봤을 때, 눈높이 h(d)에서 본 것과 같은 앙각이 되게 한다."""
        d = np.maximum(d, 1e-6)
        el = np.arctan2(Z - ground0 - self.h(d), d)
        return ground0 + self.h0 + d*np.tan(np.clip(self.g(d)*el, -1.4, 1.4))
    def to_dict(self):
        return {"camera_eye_height_m": self.h0,
                "g_knots": self.gk.tolist(), "h_knots": self.hk.tolist()}
