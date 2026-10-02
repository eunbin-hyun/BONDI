"""
스침각(grazing) 판정 — 원화를 지형에 투영해도 되는 자리인지 가른다.

시선과 지면이 거의 평행하면 원화 화소 하나가 지면 위에서 수십 배로 늘어난다.
그러면 먹의 짙은 획이 길게 끌리며 '검은 띠'가 된다. 전경 지면이 딱 그 경우다.

  신축 배율 = 1 / |cos(입사각)|

입사각은 지표면 법선과 시선이 이루는 각. 90°에 가까울수록(=스칠수록) 커진다.
"""
import numpy as np


def view_stretch(Xc, Zc, Uc, step_x, step_z):
    """카메라 정렬 격자에서 화소 신축 배율을 구한다.

    Xc, Zc : 카메라 기준 수평 좌표 (m). 카메라는 (0, 0).
    Uc     : 같은 격자의 높이 (카메라 눈높이 기준, m).
    반환   : 신축 배율 (1 = 정면, 클수록 스침).
    """
    gx = np.gradient(Uc, step_x, axis=1)
    gz = np.gradient(Uc, step_z, axis=0)
    nrm = np.dstack([-gx, -gz, np.ones_like(Uc)])
    nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
    ray = np.dstack([Xc, Zc, Uc])
    ray /= np.maximum(np.linalg.norm(ray, axis=2, keepdims=True), 1e-6)
    cosi = np.abs(np.sum(nrm*ray, axis=2)).clip(1e-3, 1.0)
    return 1.0/cosi
