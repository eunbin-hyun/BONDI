# 젠킨스 트러블슈팅 — 현재 설정 상태와 문제 해결

구축 순서는 [`JENKINS_BUILD_GUIDE.md`](JENKINS_BUILD_GUIDE.md) 에 있다. 이 문서는 **지금 어떻게 되어 있는지**와 **문제가 났을 때 어디를 보는지**를 다룬다.

---

## 1. 현재 구성 (2026-09-10 실측)

```
GitLab dev 병합 ──webhook──▶ Jenkins :8912 ──▶ infra/web/Jenkinsfile
                                                 ├ infra/web/ 이 바뀐 커밋인가? 아니면 NOT_BUILT 종료
                                                 ├ sudo /srv/catalog/bin/deploy-from-workspace.sh  (root 소유·저장소 밖)
                                                 │   → server/app, server/web 복사 · uv sync · nginx·systemd 갱신 · API 재시작
                                                 └ /api/health 와 화면 200 확인
```

**자료(`files/` `preview/` `catalog.db`)는 배포가 건드리지 않는다.**

| 항목 | 값 |
| --- | --- |
| Jenkins | 2.568.3 LTS · Java 21.0.12 · 플러그인 94개 (로드 실패 0) |
| 주소 | http://$SERVER_HOST:8912/ (기본 8080 회피 — SSAFY 지침) · ufw 8912 열림 |
| 로그인 | `admin` + **초기 비밀번호 32자** (마법사에서 "Create First Admin User" 를 건너뜀) |
| 잡 | `infra-web-deploy` — SCM `*/dev`, Script Path `infra/web/Jenkinsfile` |
| 자격증명 | Credentials ID `gitlab-deploy-token` (`gitlab+deploy-token-6644`, scope `read_repository`) |
| 웹훅 | Push events(wildcard `dev`) + Merge request events, SSL 검증 끔 |
| 배포 스크립트 | `/srv/catalog/bin/deploy-from-workspace.sh` — root 소유. `jenkins` 는 **이 파일 하나만** sudo 가능 (`/etc/sudoers.d/jenkins-deploy`) |
| 서비스 포트 | 80 (자료 서버) · 8912 (Jenkins) · 8412 (FastAPI, `127.0.0.1` 전용) |

### 검증 통과 기록 (빌드 #5)

```
Started by GitLab push by 권영호
Commit message: "Merge branch 'feature/S15P21C201-121-infra-web' into 'dev'"
바뀐 파일 33개 · infra/web 포함: true
+ sudo /srv/catalog/bin/deploy-from-workspace.sh .../infra/web
배포 완료 · API 정상
화면 HTTP 200
Finished: SUCCESS          (35초)
```

---

## 2. 상태를 보는 명령

```bash
# 서비스 세 개
ssh c201 'systemctl is-active jenkins nginx catalog-api; systemctl is-enabled jenkins nginx catalog-api'

# 마지막 빌드의 핵심 줄만
ssh c201 'B=$(sudo ls /var/lib/jenkins/jobs/infra-web-deploy/builds/ | grep -E "^[0-9]+$" | sort -n | tail -1)
echo "빌드 #$B"; sudo cat /var/lib/jenkins/jobs/infra-web-deploy/builds/$B/log \
  | grep -E "Started by|Commit message|바뀐 파일|배포 완료|화면 HTTP|Finished|ERROR"'

# 로그
ssh c201 'sudo journalctl -u jenkins     -n 50 --no-pager'   # Jenkins 자체
ssh c201 'sudo journalctl -u catalog-api -n 30 --no-pager'   # 배포된 앱
ssh c201 'sudo tail -30 /var/log/nginx/catalog.error.log'    # 웹서버

# 배포가 실제로 반영됐는지 (파일 수정 시각)
ssh c201 'stat -c "%y  %n" /srv/catalog/app/main.py /srv/catalog/web/app.js'
```

```powershell
# 밖에서 최종 확인
curl.exe -s -o NUL -w "화면 %{http_code}`n" http://$env:SERVER_HOST/
curl.exe -s http://$env:SERVER_HOST/api/stats
```

---

## 3. 우리가 실제로 막혔던 것

### 3.1 IPv6 — 플러그인 설치가 대량 실패 (가장 크게 헤맨 것)

**증상.** 설치 마법사의 `Install suggested plugins` 가 다운로드 단계에서 16개 실패. `Failed to load: Pipeline`, `github-branch-source` 등.

**원인.** 이 EC2 에는 전역 IPv6 주소가 **없는데** 시스템이 IPv6 를 먼저 시도한다. Python·Java 의 다운로드가 `Network is unreachable (Errno 101)` 로 죽는다. `curl` 은 알아서 IPv4 로 넘어가므로 따로 테스트하면 정상으로 보여 원인 파악이 늦어졌다.

**처치.**
```bash
# 시스템 전체 IPv4 우선
echo "precedence ::ffff:0:0/96  100" | sudo tee -a /etc/gai.conf

# Jenkins JVM 도 IPv4 강제
sudo tee /etc/systemd/system/jenkins.service.d/override.conf <<'EOF'
[Service]
Environment="JENKINS_PORT=8912"
Environment="JAVA_OPTS=-Djava.awt.headless=true -Djava.net.preferIPv4Stack=true"
EOF
sudo systemctl daemon-reload && sudo systemctl restart jenkins
```

깨진 플러그인은 카탈로그로 의존성을 계산해 같은 시점 버전으로 일괄 재설치했다.
```bash
ssh c201 'curl -4 -sfL https://updates.jenkins.io/current/update-center.actual.json -o /tmp/uc.json'
# 설치된 플러그인 목록의 의존성 폐쇄를 구해 각 url 을 curl -4 로 받아 plugins/<이름>.jpi 로 두고 재시작
# 결과: 94개, 로드 실패 0
```

### 3.2 `Unlock Jenkins` 가 다시 뜨고 초기 비밀번호가 "incorrect"

**원인.** 3.1 로 마법사가 중단되면서 Jenkins 가 재시작 대기 상태가 됐고, **관리자 계정은 이미 만들어졌는데** `secrets/initialAdminPassword` 가 남아 마법사가 처음으로 되돌아갔다. 그 시점의 초기 비밀번호는 더 이상 유효하지 않다.

**처치 A (계정을 이미 만든 경우 — 마법사만 완료 처리).**
```bash
ssh c201 'J=/var/lib/jenkins; V=$(dpkg -s jenkins | awk "/^Version/{print \$2}")
sudo systemctl stop jenkins
echo -n "$V" | sudo tee $J/jenkins.install.InstallUtil.lastExecVersion >/dev/null
echo -n "$V" | sudo tee $J/jenkins.install.UpgradeWizard.state >/dev/null
sudo sed -i "s|<installStateName>[^<]*</installStateName>|<installStateName>RUNNING</installStateName>|" $J/config.xml
sudo rm -f $J/secrets/initialAdminPassword          # 더 이상 필요 없다
sudo chown jenkins:jenkins $J/config.xml $J/jenkins.install.*
sudo systemctl start jenkins'
```

**처치 B (비밀번호를 아무도 모르는 경우 — 마법사를 깨끗이 다시).**
```bash
ssh c201 'J=/var/lib/jenkins
sudo systemctl stop jenkins
sudo mv $J/config.xml $J/config.xml.bak-$(date +%H%M%S)    # 백업하고 치운다
sudo rm -f $J/jenkins.install.InstallUtil.lastExecVersion $J/jenkins.install.UpgradeWizard.state
sudo systemctl start jenkins'
# → Jenkins 가 새 설치로 인식해 initialAdminPassword 를 새로 발급한다.
#   플러그인(plugins/)과 잡(jobs/)은 파일로 남아 그대로 유지된다.
```

> **인증을 끄는 방법은 쓰지 않았다.** 8912 가 공개 포트라 인증 없는 Jenkins 는 서버 전권이 열리는 것과 같다. 위 두 방법은 인증을 유지한다.

### 3.3 초기 비밀번호가 29자로 잘림

PowerShell 이 `ssh` 출력을 배열로 쪼개면서 값이 깨진다.

```powershell
$p = (ssh c201 "sudo cat /var/lib/jenkins/secrets/initialAdminPassword") -join ''   # ← -join '' 필수
$p.Length        # 32 여야 한다
$p | Set-Clipboard
(Get-Clipboard).Length   # 32 확인
```

값을 눈으로 보고 복사하려면:
```powershell
ssh c201 "sudo cat /var/lib/jenkins/secrets/initialAdminPassword"
```

### 3.4 Jenkins 로그인 칸에 Deploy Token 을 넣어 실패

둘은 완전히 다른 것이다.

| | 무엇 | 어디에 |
| --- | --- | --- |
| Jenkins 로그인 | `admin` + 마법사에서 정한(또는 초기) 비밀번호 | 로그인 화면 |
| GitLab Deploy Token | `gitlab+deploy-token-…` + `gldt-…` | 로그인 **후** `Jenkins 관리 → Credentials` |

### 3.5 Credentials 화면에 `API token` 칸만 보임

`Kind` 가 **GitLab API token** 으로 선택돼 있다. 저장소 clone 에는 그 종류를 쓰지 않는다.
→ `Kind` 를 **Username with password** 로 바꾼다. 그러면 Username / Password / ID 칸이 나온다.

### 3.6 Deploy Token 이 `Authentication failed`

| 확인 | 있어야 하는 값 |
| --- | --- |
| 위치 | `Settings → Repository → **Deploy** tokens` (Access tokens 아니다) |
| Scopes | ☑ `read_repository` |
| Username | 발급 화면에 표시된 `gitlab+deploy-token-1234`. **내가 적은 Name 이 아니다** |
| 만료일 | 오늘 이후 |

토큰 값은 발급 직후 한 번만 보인다. 놓치면 지우고 다시 만든다.

미리 검증하는 방법 (명령 기록에 값이 남지 않는다):
```powershell
git -c credential.helper= ls-remote https://lab.ssafy.com/s15-ai-image-sub1/S15P21C201.git HEAD
# Username / Password 를 물어보면 위 두 값을 넣는다. 커밋 해시가 나오면 정상
```

### 3.7 빌드가 `infra/web/Jenkinsfile not found` 로 실패

`dev` 브랜치에 `infra/web/` 이 아직 없다. **MR 을 먼저 병합**해야 한다. clone·토큰·트리거는 정상이라는 뜻이므로 나쁜 신호가 아니다.

### 3.8 `sudo: a password is required`

`jenkins` 계정이 배포 스크립트를 sudo 할 수 없다.
```bash
ssh c201 'sudo cat /etc/sudoers.d/jenkins-deploy; sudo visudo -cf /etc/sudoers.d/jenkins-deploy'
# jenkins ALL=(root) NOPASSWD: /srv/catalog/bin/deploy-from-workspace.sh
# 경로가 한 글자라도 다르면 안 된다. "parsed OK" 가 나와야 한다
```

### 3.9 웹훅 Test 가 403 / 404

| 확인 | |
| --- | --- |
| URL 의 `project/<이름>` | 잡 이름과 정확히 같아야 한다 (`infra-web-deploy`) |
| Secret token | GitLab 웹훅의 값과 잡 `config.xml` 의 `<secretToken>` 이 같아야 한다 |
| 잡 트리거 | `Build when a change is pushed to GitLab` 체크돼 있어야 한다 |

```bash
# 잡에 심어진 secret token 확인
ssh c201 "sudo grep -oP '(?<=<secretToken>)[^<]+' /var/lib/jenkins/jobs/infra-web-deploy/config.xml"
```

> 빈 POST 로 `curl` 테스트하면 **404 가 정상**이다. GitLab 은 JSON payload 와 `X-Gitlab-Token` 헤더를 함께 보낸다. 잘못된 토큰으로 보내면 **401** 이 와야 맞다 (검증이 작동한다는 뜻).

### 3.10 `curl -d '{"note":"한글"}'` 이 `400 error parsing the body`

Windows 콘솔이 한글을 CP949 로 보내 JSON 이 UTF-8 이 아니게 된다. 서버 문제가 아니다.
→ 웹 화면이나 Python `urllib` 로 보낸다.

### 3.11 배포는 됐는데 화면이 옛것

열려 있던 탭이 옛 `app.js` 를 쓰고 있다. **Ctrl+F5**.

---

## 4. 되돌리기

| 상황 | 명령 |
| --- | --- |
| API 만 재시작 | `ssh c201 "sudo systemctl restart catalog-api"` |
| nginx 설정만 다시 | `ssh c201 "sudo nginx -t && sudo systemctl reload nginx"` |
| 자동 배포 잠시 멈추기 | Jenkins 잡 → 구성 → GitLab 트리거 체크 해제 |
| Jenkins 화면 닫기 | `ssh c201 "sudo ufw delete allow 8912/tcp"` (되돌리기 `allow 8912/tcp`) |
| 자료 서버 화면 닫기 | `ssh c201 "sudo ufw delete allow 80/tcp"` |
| 이전 코드로 | 저장소에서 되돌린 뒤 다시 병합, 또는 `bash infra/web/deploy/deploy.sh` 로 손으로 배포 |

**배포가 실패해도 자료와 DB 는 그대로다.** `deploy-from-workspace.sh` 는 `files/` `preview/` `catalog.db` 를 건드리지 않는다.

---

## 5. 남은 권고

- **채팅·이슈·커밋에 노출된 토큰은 즉시 Revoke 하고 재발급한다.** 구축 중 노출된 `gitlab+deploy-token-6643` 은 폐기 대상이다 (현재 쓰는 것은 6644).
- Jenkins 비밀번호가 아직 초기값이면 `admin → Security` 에서 바꾼다. 초기값은 서버 파일에 남아 있다.
- `docs/DECISIONS.md` 에 "내부 도구 `infra/web/` 한정 CI — `D-49` 와 범위가 다름" 을 한 줄 남긴다.
- VR·AI 커밋이 병합되면 빌드는 시작되고 **회색(NOT_BUILT)** 으로 끝난다. 배포는 되지 않는다. 회색 기록이 쌓이는 게 거슬리면 GitLab 웹훅 대신 경로 기반 폴링으로 바꿀 수 있다.
