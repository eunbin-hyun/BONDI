# SLAT 조각남의 진짜 원인 — intersected 임계 실험과 v1 검토

- 작성자: 현은빈
- 확인일: 2026-09-11
- 상태: **완료** — 임계 가설 반증. SLAT 형상 경로 종결
- 주제: 22~168조각이 왜 났는가. 디코더를 열어 재고, TRELLIS v1 로 바꾸면 되는지까지 본다
- 관련: [trellis2-복원-파이프라인-재구성.md](%5BAI%5D%20trellis2-%EB%B3%B5%EC%9B%90-%ED%8C%8C%EC%9D%B4%ED%94%84%EB%9D%BC%EC%9D%B8-%EC%9E%AC%EA%B5%AC%EC%84%B1.md) §7.9 · [trellis2-모델-구조.md](%5BAI%5D%20trellis2-%EB%AA%A8%EB%8D%B8-%EA%B5%AC%EC%A1%B0.md) · [복원-일반화-로드맵.md](%EB%B3%B5%EC%9B%90-%EC%9D%BC%EB%B0%98%ED%99%94-%EB%A1%9C%EB%93%9C%EB%A7%B5.md) S4
- 도구: `restore/probe_intersected.py`

---

## 0. 한 줄 요약

**조각남은 임계 문제가 아니었다.** `intersected` logit 중앙값이 12.156 이고,
임계를 ±3 흔들어도 조각 수가 2 로 고정이다.

그리고 재는 과정에서 더 큰 것이 나왔다 — **GLB 위상은 디코더 위상이 아니다.**
`remesh` 가 경계변 26,921 개를 전부 닫는다. 지금까지의 위상 측정이 전부 그 위에서 이뤄졌다.

---

## 1. 디코더를 열어보니 메커니즘이 달랐다

`trellis2/pipelines/trellis2_image_to_3d.py:505-516` 이 실제 메시 생성부다.
(`fdg_vae.py:103` 에도 같은 코드가 있으나 파이프라인은 인라인 판을 쓴다.)

```python
h = h.replace(h.feats.float())
vertices    = h.replace((1 + 2*margin) * torch.sigmoid(h.feats[..., 0:3]) - margin)
intersected = h.replace(h.feats[..., 3:6] > 0)          # ← 하드 임계
quad_lerp   = h.replace(F.softplus(h.feats[..., 6:7]))
mesh = flexible_dual_grid_to_mesh(h.coords[:, 1:], ...)
```

디코더 출력은 복셀당 7채널이다.

| 채널 | 뜻 |
| --- | --- |
| `[0:3]` | dual vertex 위치 — 복셀 *안* 어디에 정점이 놓이나 |
| `[3:6]` | **intersected 플래그 3개** (x·y·z 축 edge 별) |
| `[6:7]` | quad split weight |

`o-voxel/o_voxel/convert/flexible_dual_grid.py` 의 메시 생성은 이렇다.

```python
connected_voxel = edge_neighbor_voxel[intersected_flag]
connected_voxel_valid = (connected_voxel_indices != 0xffffffff).all(dim=1)
quad_indices = connected_voxel_indices[connected_voxel_valid]
```

여기서 두 가지가 나온다.

**① 정점은 항상 공유된다.** `mesh_vertices` 는 복셀 하나당 정점 하나이고 쿼드는 그걸 **인덱스로**
참조한다. 잠재값이 어긋나면 정점이 엉뚱한 데 놓일 뿐 **면이 찢어질 수는 없다.**

**② 면이 빠지는 경우는 둘뿐이다.**

| | 원인 |
| --- | --- |
| **(a)** | `intersected` logit ≤ 0 → 그 edge 의 쿼드가 통째로 안 생긴다 |
| **(b)** | edge 를 둘러싼 **2×2 복셀** 중 하나라도 없음 → 쿼드 폐기 |

> ### §7.9 정정
>
> [trellis2-복원-파이프라인-재구성.md](%5BAI%5D%20trellis2-%EB%B3%B5%EC%9B%90-%ED%8C%8C%EC%9D%B4%ED%94%84%EB%9D%BC%EC%9D%B8-%EC%9E%AC%EA%B5%AC%EC%84%B1.md) §7.9 의
> *"O-Voxel 은 복셀 안의 표면 위치를 잠재값이 정하므로, 이웃 잠재값이 어긋나면
> 복셀이 붙어 있어도 면이 안 만난다"* 는 **현상 기술은 맞지만 메커니즘이 틀렸다.**
> 위치가 어긋나는 것으로는 면이 안 찢어진다. 빠지는 것은 (a) 또는 (b) 다.
>
> 그리고 거기 쓴 **26-연결 측정은 이 표현에 맞지 않는 척도**다.
> dual quad 는 **2×2 블록이 꽉 차야** 생기는데 26-연결은 모서리 하나만 닿아도 연결로 센다.
> *"전 설정이 복셀 1덩어리인데 메시는 22~54조각"* 의 답이 이것이다 — 잘못 잰 것이다.

### 1.1 포크 주석이 (a) 를 가리켰다

임계 바로 위에 이런 주석이 있다.

```text
# Cast to fp32 — the edge intersection test (> 0) and sigmoid vertex offsets
# are precision-sensitive; fp16 rounding near zero creates stray quads
# that appear as vertical line/hair artifacts in the mesh.
```

포크 저자가 같은 문제를 겪고 fp32 로 올려놨다는 뜻이다. fp16 반올림(~1e-3)이 판정을 뒤집을 만큼
**logit 이 0 근처에 몰려 있다**는 근거로 읽었다. 그래서 (a) 를 먼저 쟀다.

---

## 2. 실험 설계 — GPU 1회, 나머지는 CPU

`intersected` 이후는 **순수 조합 로직**이고 dual vertex 위치는 임계와 무관하다.
그래서 `h.feats` 를 한 번만 덤프하면 임계 스윕 전체가 CPU 에서 끝난다.

대상은 **손상 원본 A** 다. `out/latent_A.npz` 에 SLAT 이 이미 있어 **샘플링이 필요 없고**,
정답도 안다 — **2조각**. 잘 붙는 경우의 logit 여유를 재는 것이 요점이다.

```powershell
& "...\venv\Scripts\python.exe" "C:\Users\SSAFY\Desktop\restore\probe_intersected.py" --dump
```

`intersected = logit > -τ` 로 쓴다. **τ>0 이 완화**(면이 는다), **τ<0 이 엄격**(면이 준다).

> `trellis2/` 는 한 줄도 안 건드렸다. `decode_shape_slat` 의 backbone 호출부만 외부에서 재현했다.
> latent 는 역정규화 상태로 저장돼 있고 디코더가 그 상태를 받는다 — 되돌리면 안 된다.
> 입력은 **fp32** 여야 한다. `convert_to_fp16` 이 `blocks`·`output_layer` 만 바꾸고
> `from_latent` 는 그대로라, half 로 주면 거기서 죽는다.

### 2.1 쿼드 생성 재현을 먼저 검증했다

CUDA 해시맵 룩업을 numpy 정렬+`searchsorted` 로 바꿨다. 그게 맞아야 실험이 성립한다.

| 합성 입력 | 기대 | 결과 |
| --- | --- | --- |
| 2×2×2 블록 · 전 축 on | 쿼드 6(정육면체 면) · 변 12 · 경계변 0 · 조각 1 | 일치 |
| 블록 2개 분리 | 쿼드 12 · 조각 2 | 일치 |
| x축 `intersected` off | 쿼드 4 · 경계변 8 · 경계루프 2 | 일치 |
| 복셀 1개 제거 | 쿼드 3 (2×2 완결성) | 일치 |

---

## 3. 결과 — 임계에 둔감하다

```text
복셀 1,242,676 · resolution 512 · backbone forward 2.4s
|logit| 중앙 12.156   ·   |logit| < 1.0 이 0.277%   ·   fp16 해상도(~1e-3) 안 0.0002%
```

| τ | 쿼드 | **조각** | 고립복셀 | 경계변 | 경계루프 | 비다양체 | 면적 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| −3.00 | 1,219,052 | 16 | 5,774 | 56,673 | 8,166 | 3,917 | 3.1338 |
| −2.00 | 1,230,137 | 3 | 2,536 | 42,932 | 7,890 | 10,548 | 3.1566 |
| −1.50 | 1,234,774 | **2** | 1,681 | 37,038 | 7,535 | 15,027 | 3.1664 |
| −0.50 | 1,241,460 | **2** | 733 | 29,288 | 6,807 | 23,438 | 3.1811 |
| **0.00** | 1,244,080 | **2** | 465 | **26,921** | 6,524 | 27,729 | 3.1870 |
| +1.00 | 1,248,615 | **2** | 174 | 24,085 | 5,973 | 37,199 | 3.1971 |
| +3.00 | 1,256,577 | **2** | 43 | 21,986 | 5,299 | 58,704 | 3.2141 |

![intersected 임계 스윕](images/slat-%EC%9E%84%EA%B3%84-%EC%8A%A4%EC%9C%84%ED%94%84.png)

> 왼쪽 = `intersected` logit 분포(세로 로그). 빨간 선이 현재 임계 `>0` 이다 —
> **양 끝에 몰리고 0 근처가 골짜기**다. 가운데 = τ 대 조각 수. τ ≥ −1.5 에서 평평하게 2다.
> 오른쪽 = 과채움 대리지표. 완화할수록 구멍이 막히고(파랑↓) 면적이 는다(주황↑).

**logit 히스토그램이 양 끝에 몰리고 0 근처가 골짜기다.** 디코더는 확신에 차 있다.
τ 를 −1.5 ~ +3 어디에 둬도 조각 수가 2 다.

> **(a) 는 조각남의 손잡이가 아니다.** 포크 주석의 *"stray quads"* 는
> 0.0002% 짜리 선 아티팩트 얘기였지 조각남의 원인이 아니었다.

임계를 완화하면 경계변과 경계루프가 줄고 면적이 느는 것은 예상대로다 —
**구멍이 막히는 것**이라 과채움 쪽 대가다. 조각남을 고치는 대신 쓸 손잡이는 아니다.

---

## 4. 더 큰 발견 — GLB 위상은 디코더 위상이 아니다

| | 디코더 직후 | `A_normal.glb` |
| --- | ---: | ---: |
| 조각 (위치 용접) | 2 | 2 |
| **경계변** | **26,921** | **0** |
| 비다양체 변 | 27,729 | 22 |

`export()` 가 마지막에 이걸 부른다.

```python
o_voxel.postprocess.to_glb(..., decimation_target=150000,
                           remesh=True, remesh_band=1, remesh_project=0)
```

**remesh 가 경계변 26,921 개를 전부 닫았다.**

> ### 결손-메우는-방법-검토 §1 정정
>
> [결손-메우는-방법-검토.md](%5B%EC%88%98%ED%95%99%5D%20%EA%B2%B0%EC%86%90-%EB%A9%94%EC%9A%B0%EB%8A%94-%EB%B0%A9%EB%B2%95-%EA%B2%80%ED%86%A0.md) §1 의
> *"TRELLIS 가 두께 있는 닫힌 껍질을 만들어서 파단부가 위상적 구멍이 아니다"* 는 **원인 지목이 틀렸다.**
> TRELLIS 디코더는 경계변 26,921 개짜리 **열린 면**을 만들었고, **`remesh=True` 가 닫았다.**
>
> 다만 **결론(A안을 못 쓴다)은 그대로다.** 우리가 입력으로 쓰는 것이 remesh 된 GLB 이기 때문이다.
> A안을 되살리려면 remesh 를 끄고 export 해야 하는데, 그러면 `region_carried` 자체가 달라진다.

기존 GLB 를 전부 다시 세어봤다. **22 · 54 · 25 는 정확했으나 전부 remesh 후 값이다.**

| GLB | 용접 후 조각 | 경계변 | 비다양체 | (인덱스 기준) |
| --- | ---: | ---: | ---: | ---: |
| `A_normal` | 2 | 0 | 22 | 1,306 |
| v7 fresh | 25 | 3 | 615 | 6,264 |
| v8 masked | 54 | 3 | 343 | 5,189 |
| v9 fresh | 22 | 5 | 944 | 8,569 |
| v9 spliced | 27 | 10 | 246 | 4,026 |

인덱스 기준(4천~8천)과 용접 후(22~54)의 차이는 UV 이음새다 —
[채움면-매끄럽게-만들기.md](%5B%EC%88%98%ED%95%99%5D%20%EC%B1%84%EC%9B%80%EB%A9%B4-%EB%A7%A4%EB%81%84%EB%9F%BD%EA%B2%8C-%EB%A7%8C%EB%93%A4%EA%B8%B0.md) §5.1 에서 짚은 함정이 여기도 있다.

> **앞으로 위상은 디코더 직후 쿼드에서 잰다.** GLB 에서 재면 remesh 를 재는 것이다.

---

## 5. TRELLIS v1 로 바꾸면 되는가

v2 의 조각남이 표현 탓이라면, **표현이 다른 v1 을 쓰면 되지 않나**는 물음이 남는다.

### 5.1 가중치는 이미 있다

```text
models/hub/models--microsoft--TRELLIS-image-large/  (3.1GB, 전부 받아져 있다)
  ckpts/slat_dec_mesh_swin8_B_64l8m256c_fp16   ← v1 메시 디코더
  ckpts/slat_dec_gs_... / slat_dec_rf_...
  ckpts/slat_flow_img_dit_L_64l8p2_fp16
  ckpts/ss_flow_img_dit_L_16l8_fp16
```

`ss_dec` 만 쓰는 줄 알았는데 **v1 전체가 캐시에 있다.** 다운로드는 필요 없다.

### 5.2 표현이 실제로 다르다 — 그리고 v1 쪽이 유리하다

v1 메시 디코더 설정은 `{"name": "SLatMeshDecoder", "resolution": 64, "representation_config": {"use_color": true}}` 다.

| | v1 `SLatMeshDecoder` | v2 `FlexiDualGrid` |
| --- | --- | --- |
| 표면 결정 | 격자 **꼭짓점의 SDF 값** | 복셀 중심 dual vertex + `intersected` 3개 |
| 이웃과의 공유 | **꼭짓점 값을 공유** → 부호가 하나로 정해진다 | **독립 예측** → 이웃과 어긋날 수 있다 |
| 면 연결 | 공유 스칼라장이라 **원리적으로 이어진다** | (a)·(b) 로 빠질 수 있다 |
| 해상도 | **64³** | 512 / 1024 |
| 재질 | vertex color | **PBR 4채널** |
| 잠재 | 8채널 | 32채널 |

**연결성 면에서 v1 이 구조적으로 유리한 것이 맞다.** 직감이 맞았다.

> v1 코드(`trellis/` 패키지)는 로컬에 없어 구현을 직접 확인하지 못했다.
> v1 메시 디코더가 FlexiCubes 계열(꼭짓점 SDF + 미분가능 마칭큐브)이라는 것은
> 논문·공개 코드 기준 지식이고, **로컬 검증은 안 된 것**이다.

### 5.3 그런데 잃는 것이 더 크다

| | 영향 |
| --- | --- |
| **해상도 64³** | §7.7 이 32³ 에서 겪은 양자화 인공물 문제가 두 배로 완화될 뿐이다. 이 유물은 벽 2복셀·투창 1~2복셀이다. v24 의 `(y,θ)` 는 96×144 에 upsample 2 라 실질 192×288 — **비교가 안 된다** |
| **PBR 없음** | vertex color 만. 재질 품질이 내려간다 |
| 코드 부재 | 가중치는 있으나 `trellis/` 패키지를 따로 받아 설치해야 한다. v2 설치에서 겪은 의존성 문제를 다시 치른다 |
| **주입 문제 그대로** | 조각남은 개선돼도 **coords 를 손으로 짓는 문제(§7.7)는 디코더와 무관**하다 |
| provenance 그대로 | `"AI 추정"` |

### 5.4 결론 — v1 은 안 쓰고, 그 원리만 가져온다

**v1 이 연결되는 이유는 "학습 모델이 좋아서"가 아니라 "공유 스칼라장(SDF)을 쓰기 때문"이다.**

그 원리는 학습 모델 없이도 얻는다. 그게
[복원-일반화-로드맵.md](%EB%B3%B5%EC%9B%90-%EC%9D%BC%EB%B0%98%ED%99%94-%EB%A1%9C%EB%93%9C%EB%A7%B5.md) 의 **S6(SDF 볼륨)** 다.

| | v1 메시 디코더 | S6 (SDF 볼륨) |
| --- | --- | --- |
| 연속면 보장 | 꼭짓점 SDF → 마칭큐브 | **같음** |
| 해상도 | 64³ 고정 | **자유** |
| 재질 | vertex color | v2 PBR 을 그대로 씀 (A단계 출력) |
| 학습 | 필요 | **없음** |
| provenance | "AI 추정" | **"곡률 연속 외삽" 등으로 내려간다** |

**S6 가 v1 의 장점만 가져오고 단점을 전부 피한다.**

---

## 6. 그래서 SLAT 주입은 끝났는가

**"원리적으로 불가능"이 아니라 "실측으로 22조각 아래를 못 봤고, 원인 후보 하나가 배제됐다"** 가 정확하다.

| 원인 후보 | 상태 |
| --- | --- |
| (a) 임계 | **배제됨** (§3) |
| (b) 2×2 완결성 | **남아 있음** — 미검증 |
| 표현 자체 (v1 이면 다름) | §5 — 유리하나 대가가 크다 |

(b) 를 고치려면 주입 coords 에 형태학적 닫힘(dilate→erode)을 걸어 2×2 를 채워야 한다.
그런데 그건 §7.7 의 결론 — *"32³ 격자에서 손으로 회전면을 짓는 한 양자화 인공물이
형태만 바꾸며 계속 나온다"* — 으로 되돌아간다. **고쳐도 다음 인공물이 나온다.**

그리고 이 경로가 이기려는 상대가 v24 다 — 이면각 중앙 **0.948°**, `region_carried` 원본과 차이 `0.00e+00`.
SLAT 이 거기까지 갈 근거가 없다.

> **SLAT 을 형상 복원에 쓰는 경로는 여기서 닫는다.**
> 2026-09-10 에는 *"latent 문제라서"* 라는 **틀린 이유**로 내려왔고, 이번에는 실측 근거로 닫는다.
> TRELLIS 의 역할은 **A단계(사진 → 손상 3D) 하나**로 확정한다.

남는 여지는 하나다 — **재질**. 형상이 아니라 텍스처 생성에서는 생성 모델이 여전히 후보다
([trellis2-복원-파이프라인-재구성.md](%5BAI%5D%20trellis2-%EB%B3%B5%EC%9B%90-%ED%8C%8C%EC%9D%B4%ED%94%84%EB%9D%BC%EC%9D%B8-%EC%9E%AC%EA%B5%AC%EC%84%B1.md) D단계).

---

## 7. 도구

```text
restore/probe_intersected.py
  --dump          latent_A → 디코더 backbone → out/probe/hfeats_A.npz   (GPU 1회, 2.4s)
  (기본)          τ 스윕 + out/fig_tau.png
  --tau -2 -1 0 1 2
  --latent / --dump-path / --resolution
```

- 그림은 `matplotlib` 이 없어 **PIL 로 직접 그린다** (`fig_*.py` 와 같은 방식)
- 덤프가 있으면 GPU 없이 스윕만 반복된다. 다른 latent 를 재려면 `--latent` 로 바꿔 `--dump`
