"""
전경 지면 잔결(micro relief) — 절차적 요철층을 하나 만들어 파일로 굳힌다.

왜 필요한가
  2024년 수치지형도의 이 자리는 서촌 시가지라 이미 평탄화돼 있다.
  근경 0~200 m 기복이 4.6 m 뿐이고, 시선이 지면을 89°로 스치므로
  VR에서 '유리 바닥' 처럼 보인다. 노멀맵만으로는 스침각에서 거의 안 보인다.
  → 실제 형상에 아주 얕은 잔결을 얹어 바닥이 '땅'으로 읽히게 한다.

무엇이 아닌가
  **측정값이 아니다.** 고증이 아니라 연출용 조형이다. 진폭은 아래 MAX_AMP뿐이고,
  전경에서만 살아나며 600 m 밖에서는 0이 된다. manifest에 그렇게 기록한다.
  전경 지형의 진짜 복원(나무 밑동에서 역산 = 작업 ②)이 끝나면 이 층은 뺀다.

출력: micro_relief.npy (+ micro_relief.json) — export_glb / build_blend2 / build_normalmap 공용
"""
import json, numpy as np
from scipy.ndimage import gaussian_filter

HALF_W, DEPTH, BACK = 1250.0, 2600.0, 250.0
NX, NZ = 1024, 1168           # 격자 (약 2.44 m 칸)
SEED = 20260910
MAX_AMP = 1.15                # m — 전경 최대 진폭
WAVES = [(34.0, 1.00), (15.0, 0.58), (6.5, 0.31), (3.0, 0.16)]   # (파장 m, 세기)
NEAR_M, FAR_M = 260.0, 620.0  # 이 거리까지 최대 → 이 거리에서 0

px_x = 2*HALF_W/(NX-1); px_z = (DEPTH+BACK)/(NZ-1)
rng = np.random.default_rng(SEED)
wn = rng.standard_normal((NZ, NX))
h = np.zeros((NZ, NX))
for wl, amp in WAVES:
    b = gaussian_filter(wn, (max(wl/px_z, .5), max(wl/px_x, .5)))
    h += b/(b.std()+1e-9)*amp
h /= (h.std()+1e-9)

xs = np.linspace(-HALF_W, HALF_W, NX)
zs = np.linspace(-BACK, DEPTH, NZ)
Xc, Zc = np.meshgrid(xs, zs)
d = np.hypot(Xc, Zc)
ramp = np.clip((FAR_M - d)/(FAR_M - NEAR_M), 0, 1)      # 전경에서만
h = (h*MAX_AMP*ramp).astype("float32")

np.save("micro_relief.npy", h)
json.dump({"half_width_m": HALF_W, "depth_m": DEPTH, "back_m": BACK,
           "nx": NX, "nz": NZ, "seed": SEED, "max_amp_m": MAX_AMP,
           "wavelengths_m": [w for w, _ in WAVES],
           "fade": {"full_within_m": NEAR_M, "zero_beyond_m": FAR_M},
           "status": "절차적 연출층 — 측정값 아님",
           "why": "수치지형도가 평탄화한 전경(0~200 m 기복 4.6 m)이 스침각에서 "
                  "유리 바닥처럼 보이는 것을 막기 위한 임시 조형층. "
                  "나무 밑동 역산(작업 ②)으로 전경 지형을 복원하면 제거한다."},
          open("micro_relief.json", "w"), ensure_ascii=False, indent=2)
print(f"micro_relief.npy {h.shape}  진폭 99% {np.percentile(np.abs(h),99):.2f} m  "
      f"200 m 이내 표준편차 {h[d<200].std():.2f} m")
