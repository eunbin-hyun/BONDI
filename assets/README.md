# assets — 전시 자산 번들

유물별 손상·복원 모델과 출처 기록을 담는다.
담당 직군: **AI** (제작) · **Infra** (검사)

## 구조

유물 하나당 디렉터리 하나다.

```text
assets/<artifact-id>/
├── source/
│   ├── input.png              # 입력 사진 (observed — 유일한 관측 근거)
│   └── (scan.stl)             # 실측 스캔이 있는 경우에만
├── master/
│   ├── damaged.glb            # 손상 상태 3D (1차 AI 추정)
│   └── restored.glb           # 복원 상태 3D (2차 AI 추정)
├── runtime/
│   ├── damaged.glb            # 경량화된 전시용
│   ├── restored.glb           # 경량화된 전시용
│   └── thumbnail.png
├── mcp/
│   ├── prompts.md             # 프롬프트 전문
│   ├── log.txt                # MCP 호출 로그
│   └── snapshots/             # 복원 전·중·후 스냅샷
└── manifest.json
```

- `master`는 제작용, `runtime`은 전시용이다. 경량화가 `master`를 수정하지 않는다.
- **`mcp/`가 비어 있으면 자산 검사 실패다.**

## 대용량 파일

GLB·텍스처는 Git LFS 대상이다. **아직 LFS를 활성화하지 않았다** —
GitLab 인스턴스의 LFS 지원과 용량 한도를 확인한 뒤 `.gitattributes`의 주석을 푼다.
확인 전에는 큰 파일을 여기에 commit하지 않는다.

## 관련 명세

- 자산 계약: `docs/PROJECT_MASTER_SPEC.md` 21장
- manifest 필수 필드: 21.2
- 좌표·단위 계약: 21.3
- 자산 예산: 22장 *(W1 실기 측정 전까지 임시 기준 — 유물당 30k면 이하, 텍스처 1024 이하)*
