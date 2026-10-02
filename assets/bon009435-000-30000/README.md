# bon009435-000-30000

**유물 선정(`U-06`) 미확정.** 전시에 쓸지 정해지지 않았다.

| 파일 | 크기 |
| --- | --- |
| `source/bon009435-000-30000.obj` + `.mtl` | 5.2 MB |
| `source/bon009435-000-30000_alpha.jpg` | 8.3 MB |
| `source/bon009435-000-30000_pristine.jpg` | 8.9 MB |

## 상태

- 엔진에 임포트만 해봤고 **레벨에 배치하지 않았다.** 그래서 `vr/testproj` 쪽 `.uasset`은 제거했다.
- 임포트 당시 **노멀맵이 `TC_Default` + sRGB로 잘못 설정**됐다. 다시 임포트할 때
  `TC_Normalmap` / sRGB 끔 / `MaxTextureSize` 지정이 필요하다. 원본 해상도 그대로는 Quest 2에서 못 쓴다.
- 3단계(`D-47`) 형태가 아니다. `master/1-damaged` `2-model-restored` `3-mcp-restored` 구성은
  전시에 쓰기로 정해진 뒤 AI 직군이 만든다.

## 위치에 대해

공유 스토리지(`U-12`)가 아직 없어 임시로 저장소에 둔다. 스토리지가 정해지면
`source/` 원본은 그쪽으로 옮기고 여기에는 경로만 남긴다 (`FR-OPS-004`).
