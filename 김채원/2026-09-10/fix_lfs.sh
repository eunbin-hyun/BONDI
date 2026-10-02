#!/usr/bin/env bash
# Study 브랜치: .gitattributes 를 dev 와 맞추고, 아직 push 안 된 커밋을 되감아
# glb/png/jpg 가 LFS 를 타도록 다시 커밋한다. 검사 전부 통과하면 push 까지 한다.
# 실패하면 그 자리에서 멈추고 이유를 출력한다. (파일은 어떤 경우에도 지우지 않는다)

cd "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null || {
  echo "❌ git 저장소가 아니다. 저장소 안에서 실행할 것."; exit 1; }

BR=Study
fail() { echo; echo "❌ $1"; echo "   여기서 멈춤. 파일은 그대로다."; exit 1; }
ok()   { echo "   ✔ $1"; }

echo "=============================================="
echo " 0. 사전 점검"
echo "=============================================="
if [ -d .git/rebase-merge ] || [ -d .git/rebase-apply ]; then
  fail "리베이스가 아직 진행 중이다. 'git rebase --continue' 또는 'git rebase --abort' 먼저."
fi
if [ -f .git/MERGE_HEAD ]; then
  fail "머지가 진행 중이다. 'git merge --abort' 먼저."
fi
CUR=$(git rev-parse --abbrev-ref HEAD)
[ "$CUR" = "$BR" ] || fail "현재 브랜치가 '$CUR' 이다. '$BR' 에서 실행할 것."
ok "브랜치 $BR, 진행 중인 리베이스·머지 없음"

git fetch -q origin || fail "git fetch 실패 (네트워크·인증 확인)"
AHEAD=$(git rev-list --count origin/$BR..HEAD)
BEHIND=$(git rev-list --count HEAD..origin/$BR)
echo "   원격 대비  ahead=$AHEAD  behind=$BEHIND"
[ "$BEHIND" = "0" ] || fail "원격에 새 커밋이 있다. 'git pull --rebase origin $BR' 먼저."
[ "$AHEAD" != "0" ] || fail "되감을 로컬 커밋이 없다. 이미 push 됐거나 커밋이 안 된 상태다."
ok "로컬 전용 커밋 $AHEAD 개 — 되감아도 원격에 영향 없음"
echo "   (되돌리고 싶으면: git reflog 로 $(git rev-parse --short HEAD) 찾아서 git reset --hard)"

echo
echo "=============================================="
echo " 1. dev 의 .gitattributes 가져오기"
echo "=============================================="
git fetch -q origin 'refs/heads/dev:refs/remotes/origin/dev' || fail "origin/dev 를 못 받아왔다."
# ':' 이 들어간 인자는 Git Bash 가 경로로 바꿔버린다 → checkout 형식을 쓴다
git checkout origin/dev -- .gitattributes || fail "dev 에 .gitattributes 가 없다."
SZ=$(wc -c < .gitattributes | tr -d ' ')
NL=$(grep -c 'filter=lfs' .gitattributes)
echo "   크기 ${SZ} B,  filter=lfs 줄 ${NL} 개"
[ "$SZ" -gt 500 ] || fail "가져온 .gitattributes 가 너무 작다 (${SZ} B). 내용을 확인할 것."
grep -q '^\*\.glb' .gitattributes || fail ".gitattributes 에 *.glb 규칙이 없다."
ok "dev 규칙 확보 (glb·png·jpg 포함)"

grep -q '^\*\.blend' .gitattributes || \
  printf '\n# 학습 정리용 (Study)\n*.blend  filter=lfs diff=lfs merge=lfs -text\n*.npy    filter=lfs diff=lfs merge=lfs -text\n' >> .gitattributes
ok "blend·npy 규칙 추가"

echo
echo "=============================================="
echo " 2. 커밋 되감고 LFS 태워서 다시 커밋"
echo "=============================================="
git reset -q --mixed origin/$BR || fail "reset 실패"
ok "커밋 $AHEAD 개 되감음 (파일은 디스크에 그대로)"

git add .gitattributes || fail "add 실패"
git add -A "김채원" || fail "add 실패"
N=$(git diff --cached --name-only | wc -l | tr -d ' ')
ok "다시 담은 파일 ${N} 개"
[ "$N" -gt 0 ] || fail "담긴 게 없다."

git commit -q -m "docs(study): 인왕제색도 v0.10 — 스침각 보정·DEM 슬리버 제거·전경 잔결·명세 19장 개정안" \
  || fail "commit 실패"
ok "커밋 완료: $(git log --oneline -1)"

echo
echo "=============================================="
echo " 3. 검사"
echo "=============================================="
PASS=1
for e in glb png jpg blend npy; do
  a=$(git lfs ls-files | grep -c "\.$e$")
  b=$(git ls-files "김채원/2026-09-10" | grep -c "\.$e$")
  if [ "$b" -eq 0 ]; then printf "   .%-6s (없음)\n" "$e"; continue; fi
  if [ "$a" -ge "$b" ]; then printf "   ✔ .%-6s LFS %s / 전체 %s\n" "$e" "$a" "$b"
  else printf "   ✘ .%-6s LFS %s / 전체 %s  ← raw 로 들어감\n" "$e" "$a" "$b"; PASS=0; fi
done

HEAD_GLB="김채원/2026-09-10/assets/spec19/runtime/terrain_jeong.glb"
if git show "HEAD:$HEAD_GLB" 2>/dev/null | head -c 20 | grep -q 'git-lfs'; then
  ok "실제 저장 형태 = LFS 포인터"
else
  echo "   ✘ 실제 저장 형태 = raw 바이너리"; PASS=0
fi

DIRTY=$(git status --porcelain | grep -v '^??' | wc -l | tr -d ' ')
[ "$DIRTY" = "0" ] && ok "워킹트리 깨끗" || { echo "   ✘ 커밋 안 된 변경 ${DIRTY} 개"; PASS=0; }

echo
if [ "$PASS" = "1" ]; then
  echo "=============================================="
  echo " 4. 전부 통과 → push"
  echo "=============================================="
  git push origin $BR && echo && echo "🎉 끝. origin/$BR 에 반영됐다." \
    || fail "push 실패 (권한·네트워크 확인). 커밋은 로컬에 남아 있다."
else
  echo "=============================================="
  echo " ❌ 검사 실패 — push 하지 않았다"
  echo "=============================================="
  echo " 커밋은 로컬에 있다. 위 ✘ 줄을 그대로 복사해서 물어보면 된다."
  exit 1
fi
