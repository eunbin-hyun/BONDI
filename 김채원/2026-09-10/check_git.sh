#!/usr/bin/env bash
# Study 브랜치 정리가 잘 됐는지 한 번에 확인
cd /c/KCW_SSAFY/특화/S15P21C201 || exit 1
echo "==================== 1. 최근 커밋 ===================="
git log --oneline -5
echo
echo "==================== 2. 원격과의 차이 ===================="
git fetch -q origin
git status -sb | head -1
echo "  (ahead = 아직 push 안 됨 / behind = 아직 pull 안 됨 / 둘 다 없으면 동기화 완료)"
echo
echo "==================== 3. 남은 변경 ===================="
git status --short
echo "  (아무것도 안 나오면 깨끗함)"
echo
echo "==================== 4. 9/10 폴더가 들어갔나 ===================="
echo -n "  추적 중인 파일 수: "; git ls-files "김채원/2026-09-10" | wc -l
echo "  (50이면 정상)"
echo
echo "==================== 5. LFS 적용 현황 ===================="
echo -n "  LFS로 들어간 파일 수: "; git lfs ls-files | wc -l
for ext in glb png jpg blend npy; do
  n=$(git lfs ls-files | grep -c "\.$ext$")
  t=$(git ls-files "김채원/2026-09-10" | grep -c "\.$ext$")
  echo "    .$ext  LFS $n개 / 9-10폴더 전체 $t개"
done
echo "  (두 숫자가 같아야 그 확장자는 LFS를 제대로 탄 것)"
echo
echo "==================== 6. 실제 포인터인지 확인 ===================="
f="김채원/2026-09-10/assets/spec19/runtime/terrain_jeong.glb"
echo "  $f"
git show "HEAD:$f" 2>/dev/null | head -c 60 | tr -d '\0' | sed 's/^/    /'
echo
echo "  ↑ 'version https://git-lfs...' 로 시작하면 LFS 포인터 (정상)"
echo "    깨진 바이너리처럼 보이면 raw 로 들어간 것"
echo
echo "==================== 7. 9/9 폴더 원상복구 확인 ===================="
git diff --stat HEAD -- "김채원/2026-09-09" | tail -1
echo "  (아무것도 안 나오면 커밋 상태 그대로 = 정상)"
