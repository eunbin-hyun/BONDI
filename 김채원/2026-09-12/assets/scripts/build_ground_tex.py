"""땅 텍스처 — 흙 / 풀 (2026-09-14). 절차 생성, 원화 팔레트 기준. 이음새 없이 타일됨.
출력: runtime/ground_soil.png, runtime/ground_grass.png (각 1024²)"""
import os, numpy as np
from PIL import Image
from scipy import ndimage
RT = "assets/inwangjesaekdo/runtime"; N = 1024
def wn(sig, seed, shape=(N, N)):
    r = np.random.default_rng(seed).random(shape); n = ndimage.gaussian_filter(r, sig, mode="wrap"); return (n - n.mean()) / (n.std() + 1e-9)
# 흙: 담묵~옅은담묵 얼룩 + 잔입자
base = np.clip(0.5 + 0.30 * wn(28, 1) + 0.18 * wn(7, 2) + 0.10 * wn(1.2, 3), 0, 1)
A, B = np.array([96, 84, 70], float), np.array([158, 143, 120], float)      # 젖은 흙 → 마른 흙
soil = (A[None, None] * (1 - base[..., None]) + B[None, None] * base[..., None]).astype(np.uint8)
Image.fromarray(soil).save(f"{RT}/ground_soil.png")
# 풀: 먹 녹조 계열(채도 낮게) + 가느다란 결
g = np.clip(0.5 + 0.28 * wn(22, 4) + 0.22 * wn(3, 5), 0, 1)
blade = np.clip(wn((1.0, 9.0), 6) * 0.5 + 0.5, 0, 1)                        # 세로로 긴 결
g = np.clip(g * 0.8 + blade * 0.2, 0, 1)
C, D = np.array([72, 82, 58], float), np.array([132, 140, 104], float)
grass = (C[None, None] * (1 - g[..., None]) + D[None, None] * g[..., None]).astype(np.uint8)
Image.fromarray(grass).save(f"{RT}/ground_grass.png")
for nm, im in (("ground_soil", soil), ("ground_grass", grass)):
    seam = (np.abs(im[:, 0].astype(int) - im[:, -1].astype(int)).mean() + np.abs(im[0].astype(int) - im[-1].astype(int)).mean()) / 2
    print(f"{nm}.png {N}x{N}  평균색 {im.reshape(-1,3).mean(0).round(0)}  타일 이음새 {seam:.1f}/255 (작을수록 좋음)")
