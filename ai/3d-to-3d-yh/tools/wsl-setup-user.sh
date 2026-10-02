#!/usr/bin/env bash
# WSL Ubuntu 초기 설정 — 사용자 계정과 기본 설정. root 로 실행된다.
set -euo pipefail

USER_NAME=ssafy

if ! id -u "$USER_NAME" >/dev/null 2>&1; then
  useradd -m -s /bin/bash -G sudo "$USER_NAME"
  echo "사용자 생성: $USER_NAME"
else
  echo "사용자 이미 있음: $USER_NAME"
fi

# 비밀번호는 정하지 않는다(잠금 상태). 빌드가 sudo 프롬프트에서 멈추지 않도록 NOPASSWD 로 둔다.
# 로컬 개발용 WSL 이라 외부 노출이 없다. 원하면 `sudo passwd ssafy` 로 직접 정하면 된다.
echo "$USER_NAME ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/90-$USER_NAME
chmod 0440 /etc/sudoers.d/90-$USER_NAME

# 기본 로그인 사용자 + systemd 활성화(서비스·빌드 도구가 기대하는 환경)
cat > /etc/wsl.conf <<EOF
[boot]
systemd=true

[user]
default=$USER_NAME

[interop]
appendWindowsPath=true
EOF

echo "--- /etc/wsl.conf ---"
cat /etc/wsl.conf
echo "--- 확인 ---"
id "$USER_NAME"
