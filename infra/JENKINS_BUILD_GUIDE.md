# Jenkins 자동 배포 구축 가이드 — 처음부터 순서대로

`infra/web/` 이 `dev` 에 병합되면 자료 서버(http://$SERVER_HOST/)에 자동 배포되게 만드는 전 과정.
**2026-09-10 에 실제로 이 순서로 구축했고, 마지막 검증까지 통과한 기록이다.** 명령마다 `#` 주석으로 무엇을 하는지 적었다.

| 문서 | 다루는 것 |
| --- | --- |
| **이 문서** (`JENKINS_BUILD_GUIDE.md`) | Jenkins 자동 배포를 **처음부터 만드는 순서** |
| [`JENKINS_TROUBLESHOOTING.md`](JENKINS_TROUBLESHOOTING.md) | 현재 설정 상태와 **문제 해결** |
| [`WEB_APP_DEV_GUIDE.md`](WEB_APP_DEV_GUIDE.md) | 화면·API 코드 구조 |
| [`WEB_SERVER_BUILD_GUIDE.md`](WEB_SERVER_BUILD_GUIDE.md) | Jenkins 없이 손으로 배포하는 방법 (`deploy.sh`) |
| [`ASSET_DB_BUILD_GUIDE.md`](ASSET_DB_BUILD_GUIDE.md) | 자료·DB 만들기와 투입 |

---

## 0. 무엇을 만드는가

```
개발자: infra/web/ 수정 → 브랜치 → MR → dev 병합
                                        │
                                        ▼  ① GitLab 웹훅 (HTTP POST + 비밀 토큰)
                              Jenkins :8912  (EC2 안, 로그인 필요)
                                        │
                                        ▼  ② infra/web/Jenkinsfile 을 저장소에서 읽어 실행
                              [1단계] 바뀐 파일에 infra/web/ 이 있나?
                                        │  없으면 → NOT_BUILT(회색)로 종료. VR·AI 커밋은 여기서 걸린다
                                        ▼  있으면
                              [2단계] sudo /srv/catalog/bin/deploy-from-workspace.sh
                                        │     · server/app, server/web 을 /srv/catalog 로 복사
                                        │     · uv sync (의존성)
                                        │     · nginx·systemd 설정이 달라졋으면 갱신
                                        │     · catalog-api 재시작
                                        ▼
                              [3단계] /api/health 와 화면 200 확인
                                        ▼
                              http://$SERVER_HOST/ 반영 완료
```

**자료(`files/` `preview/` `catalog.db`)는 배포가 건드리지 않는다.** 코드·화면·서버 설정만 바뀐다.

### 실측 환경 (2026-09-10)

| 항목 | 값 |
| --- | --- |
| 서버 | `$SERVER_HOST` (Ubuntu 24.04, 4코어, 15GB RAM, 309GB) |
| Jenkins | 2.568.3 LTS · Java 21.0.12 · 플러그인 94개 |
| 포트 | 80 (자료 서버) · 8912 (Jenkins) · 8412 (FastAPI, 내부 전용) |
| 접속 별명 | `ssh c201` (`~/.ssh/config`) |

### 미리 알아둘 것

- **`dev` 병합 권한 = 배포 권한**이 된다. 팀 규칙의 "MR 리뷰 1명"이 곧 배포 승인이다.
- **Jenkins 화면에는 반드시 로그인을 걸어야 한다.** 자료 서버는 무인증(`AS-04`)이지만 Jenkins 는 빌드 실행 권한이라 다르다.
- 팀 명세 `D-49` 는 제품(VR·AI) CI/CD 폐기다. 이 파이프라인은 **내부 도구 `infra/web/` 한정**이라 충돌이 아니다. `docs/DECISIONS.md` 에 한 줄 남길 것.

---

## 1. SSH 접속 별명 만들기 (필수 — infra 문서와 `deploy.sh` 가 모두 이 별명을 쓴다)

이후 모든 명령이 `ssh c201` 로 짧아진다. 서버 주소가 저장소에 없으므로 주소는 이 설정 한 곳에만 적는다.

```powershell
# PowerShell — 개인 PC 에서. 파일이 없으면 만든다
notepad $env:USERPROFILE\.ssh\config
```

```ssh-config
# ~/.ssh/config — 이 항목을 추가한다
Host c201
    HostName <SERVER_HOST>                         # infra/web/.env 의 값 — ssh 설정은 환경변수를 못 읽는다
    User ubuntu
    IdentityFile C:/Users/SSAFY/Desktop/J15C201T.pem   # 팀 pem 위치에 맞게
    IdentitiesOnly yes
    ServerAliveInterval 30                              # 긴 작업 중 연결이 끊기지 않게
```

```powershell
# pem 권한 조이기 — Windows ssh.exe 는 "본인만 읽기" 가 아니면 키를 거부한다
icacls C:\Users\SSAFY\Desktop\J15C201T.pem /inheritance:r          # 상속 끊기
icacls C:\Users\SSAFY\Desktop\J15C201T.pem /grant:r "${env:USERNAME}:(R)"  # 본인 읽기만 남기기

ssh c201 "hostname; uptime -p"      # 접속 확인
```

---

## 2. 서버에 Jenkins 설치

```bash
ssh c201        # 이후 명령은 서버 안에서 실행
```

```bash
# ── (a) IPv4 우선으로 바꾼다 — 이걸 먼저 해야 한다 ★
# 이 EC2 에는 전역 IPv6 주소가 없는데 시스템이 IPv6 를 먼저 시도해서
# Jenkins 의 플러그인 다운로드가 전부 실패한다. 우리가 여기서 크게 헤맸다.
echo "precedence ::ffff:0:0/96  100" | sudo tee -a /etc/gai.conf

# ── (b) Jenkins 서명 키와 apt 저장소 등록
sudo wget -q -O /usr/share/keyrings/jenkins-keyring.asc \
  https://pkg.jenkins.io/debian-stable/jenkins.io-2023.key       # 키 파일명은 해마다 바뀐다. 404 면 아래 주석 참고
echo "deb [signed-by=/usr/share/keyrings/jenkins-keyring.asc] https://pkg.jenkins.io/debian-stable binary/" \
  | sudo tee /etc/apt/sources.list.d/jenkins.list
sudo apt-get update -qq
# 키가 404 거나 NO_PUBKEY 오류가 나면 키서버에서 직접 받는다:
#   gpg --keyserver keyserver.ubuntu.com --recv-keys 7198F4B714ABFC68
#   gpg --export --armor 7198F4B714ABFC68 | sudo tee /usr/share/keyrings/jenkins-keyring.asc

# ── (c) Java 21 + Jenkins + 배포에 쓸 rsync 설치
sudo apt-get install -y fontconfig openjdk-21-jre-headless jenkins rsync
java -version && dpkg -s jenkins | grep ^Version      # 확인

# ── (d) 포트를 8912 로 바꾼다
# SSAFY 지침: "솔루션 기본 포트(8080·9000·5000 등)를 변경해서 쓸 것"
sudo mkdir -p /etc/systemd/system/jenkins.service.d
sudo tee /etc/systemd/system/jenkins.service.d/override.conf <<'EOF'
[Service]
Environment="JENKINS_PORT=8912"
Environment="JAVA_OPTS=-Djava.awt.headless=true -Djava.net.preferIPv4Stack=true"
EOF
# JAVA_OPTS 의 preferIPv4Stack: Jenkins JVM 도 IPv4 로 나가게 한다 (a 와 같은 이유)

sudo systemctl daemon-reload            # 유닛 변경을 systemd 에 알림
sudo systemctl enable --now jenkins     # 부팅 시 자동 시작 + 지금 시작

# ── (e) 방화벽에 8912 추가. 22 는 절대 건드리지 않는다
sudo ufw allow 8912/tcp
sudo ufw status                         # 22 · 80 · 8912 만 있어야 한다

# ── (f) 확인
systemctl is-active jenkins             # active
ss -tlnp | grep :8912                   # LISTEN
```

---

## 3. 배포 스크립트와 권한 — 여기가 안전장치의 핵심

Jenkins 가 서버를 바꾸려면 `root` 권한이 필요하다. 하지만 `jenkins` 계정에 전권을 주면
**MR 을 올릴 수 있는 사람이 곧 서버 전권을 갖게 된다.** 그래서 이렇게 막는다.

- 실제 작업은 **`root` 소유 스크립트 하나**가 한다
- 그 스크립트는 **저장소 밖**에 둔다 → MR 로는 내용을 바꿀 수 없다
- `jenkins` 계정은 **그 스크립트 하나만** `sudo` 할 수 있다

```bash
sudo mkdir -p /srv/catalog/bin
sudo tee /srv/catalog/bin/deploy-from-workspace.sh <<'EOF'
#!/usr/bin/env bash
# Jenkins 가 호출: sudo /srv/catalog/bin/deploy-from-workspace.sh <워크스페이스의 infra/web 경로>
# 저장소의 infra/web/server → /srv/catalog 로 복사하고 nginx·systemd 를 갱신한다.
# 자료(files/ preview/ catalog.db)는 건드리지 않는다.
set -euo pipefail
W="${1:?infra/web 경로}"; R=/srv/catalog

# 넘어온 경로가 정말 infra/web 인지 확인 — 엉뚱한 폴더로 배포되는 것을 막는다
[ -d "$W/server/app" ] && [ -d "$W/server/web" ] || { echo "infra/web 구조가 아님: $W"; exit 2; }

# 코드·화면 복사. --delete 로 저장소에서 지운 파일도 서버에서 지운다
rsync -a --delete --chown=ubuntu:ubuntu "$W/server/app/" "$R/app/"
rsync -a --delete --chown=ubuntu:ubuntu "$W/server/web/" "$R/web/"
install -o ubuntu -g ubuntu -m 644 "$W/server/pyproject.toml" "$R/pyproject.toml"
[ -f "$W/server/uv.lock" ] && install -o ubuntu -g ubuntu -m 644 "$W/server/uv.lock" "$R/uv.lock"

# 의존성 설치. ubuntu 계정으로 실행 (venv 소유자를 일관되게)
sudo -u ubuntu bash -c "cd $R && ~/.local/bin/uv sync --quiet"

# nginx 설정이 달라졋을 때만 갱신하고 문법 검사 후 reload
if ! cmp -s "$W/deploy/nginx-catalog.conf" /etc/nginx/sites-available/catalog; then
  install -m 644 "$W/deploy/nginx-catalog.conf" /etc/nginx/sites-available/catalog \
    && nginx -t && systemctl reload nginx && echo "nginx 설정 갱신"
fi

# systemd 유닛도 달라졋을 때만
if ! cmp -s "$W/deploy/catalog-api.service" /etc/systemd/system/catalog-api.service; then
  install -m 644 "$W/deploy/catalog-api.service" /etc/systemd/system/catalog-api.service \
    && systemctl daemon-reload && echo "systemd 유닛 갱신"
fi

# 앱 재시작 후 살아났는지 확인. 실패하면 로그를 남기고 빌드를 실패시킨다
systemctl restart catalog-api; sleep 2
curl -sf http://127.0.0.1:8412/api/health >/dev/null \
  && echo "배포 완료 · API 정상" \
  || { echo "API 응답 없음"; journalctl -u catalog-api -n 20 --no-pager; exit 1; }
EOF

sudo chmod 755 /srv/catalog/bin/deploy-from-workspace.sh
sudo chown root:root /srv/catalog/bin/deploy-from-workspace.sh   # root 소유 = jenkins 가 못 고침

# jenkins 계정에 이 스크립트 하나만 비밀번호 없이 sudo 허용
echo "jenkins ALL=(root) NOPASSWD: /srv/catalog/bin/deploy-from-workspace.sh" \
  | sudo tee /etc/sudoers.d/jenkins-deploy
sudo chmod 440 /etc/sudoers.d/jenkins-deploy
sudo visudo -cf /etc/sudoers.d/jenkins-deploy      # 문법 검사. "parsed OK" 가 나와야 한다
```

> **왜 `sudoers` 문법 검사를 하나** — 이 파일이 깨지면 `sudo` 자체가 동작하지 않아 서버 복구가 어려워진다. 반드시 `visudo -cf` 로 확인한다.

---

## 4. Jenkins 초기 설정 (브라우저)

```powershell
# 초기 비밀번호를 클립보드에 담는다.
# -join '' 이 없으면 PowerShell 이 출력을 배열로 쪼개면서 값이 잘린다 (우리가 여기서 한 번 막혔다)
$p = (ssh c201 "sudo cat /var/lib/jenkins/secrets/initialAdminPassword") -join ''
$p.Length            # 32 가 나와야 한다
$p | Set-Clipboard
```

브라우저에서 **http://$SERVER_HOST:8912/** 접속 후 순서대로:

| 화면 | 할 일 |
| --- | --- |
| **Unlock Jenkins** | `Administrator password` 칸에 Ctrl+V → Continue |
| **플러그인 선택** | `Install suggested plugins` 를 눌러도 되지만, 2절 (a) 를 안 했다면 대량 실패한다. 실패하면 다음 화면 `Resume Installation` 에서 **Resume** |
| **Create First Admin User** | **여기서 아이디·비밀번호를 직접 정한다.** 건너뛰면 로그인이 `admin` + 위 32자 초기 비밀번호가 된다 |
| **Instance Configuration** | Jenkins URL 을 `http://$SERVER_HOST:8912/` 로 두고 Save and Finish |

```bash
# 설치된 플러그인 중 우리가 반드시 필요한 것들 확인
ssh c201 'for p in gitlab-plugin git git-client workflow-aggregator workflow-cps workflow-job \
  pipeline-model-definition credentials credentials-binding; do
  printf "%-28s %s\n" "$p" "$(sudo test -e /var/lib/jenkins/plugins/$p.jpi && echo 있음 || echo 없음)"
done'
```

**하나라도 "없음" 이면** `Jenkins 관리 → Plugins → Available` 에서 이름으로 검색해 설치하고 재시작한다.
UI 설치가 계속 실패하면 오프라인으로 넣을 수 있다:

```bash
# 플러그인 카탈로그를 받아 의존성까지 계산해 한 번에 설치하는 방법 (우리가 쓴 방법)
ssh c201 'curl -4 -sfL https://updates.jenkins.io/current/update-center.actual.json -o /tmp/uc.json && \
  python3 -c "import json;d=json.load(open(\"/tmp/uc.json\"));print(len(d[\"plugins\"]),\"개 카탈로그\")"'
# 이후 각 플러그인의 url 을 curl -4 로 받아 /var/lib/jenkins/plugins/<이름>.jpi 로 두고 재시작
```

---

## 5. GitLab Deploy Token 발급 (Jenkins 가 저장소를 읽을 열쇠)

저장소가 비공개이고 SSH(22번)가 막혀 있어서 **HTTPS + 토큰**만 가능하다.

```
GitLab 프로젝트 → Settings → Repository → Deploy tokens → Add token
  Name       jenkins
  Expiration 프로젝트 종료 이후 날짜
  Scopes     ☑ read_repository        ← 이것만. 쓰기 권한은 주지 않는다
→ Create deploy token
```

발급 직후 화면에 **Username** 과 **Token** 이 한 번만 보인다. 둘 다 복사한다.

- **Username 은 위에 적은 Name 이 아니다.** `gitlab+deploy-token-1234` 처럼 GitLab 이 만들어 준다
- 토큰 값은 다시 볼 수 없다. 놓치면 지우고 다시 만든다

```powershell
# 토큰이 실제로 되는지 미리 확인 — 명령 기록에 값이 남지 않는다
git -c credential.helper= ls-remote https://lab.ssafy.com/s15-ai-image-sub1/S15P21C201.git HEAD
# Username 과 Password 를 물어보면 위 두 값을 넣는다. 커밋 해시가 나오면 정상
```

---

## 6. Jenkins 에 토큰 등록

```
Jenkins 관리 → Credentials → System → Global credentials (unrestricted) → + Add Credentials
  Kind      Username with password     ← "GitLab API token" 이 아니다. clone 에는 이 종류를 쓴다
  Scope     Global
  Username  gitlab+deploy-token-1234
  Password  gldt-…
  ID        gitlab-deploy-token        ← 반드시 채운다. 잡이 이 이름으로 찾는다
→ Create
```

```bash
ssh c201 'sudo grep -oE "<id>[^<]*</id>" /var/lib/jenkins/credentials.xml'   # gitlab-deploy-token 이 보여야 한다
```

---

## 7. 저장소에 `Jenkinsfile` 넣기

`infra/web/Jenkinsfile` — **이 파일이 파이프라인 정의다.** 이미 저장소에 있다.

```groovy
pipeline {
  agent any
  options { disableConcurrentBuilds(); timestamps() }   // 동시 배포 방지 + 로그에 시각 표시

  stages {
    stage('infra/web 변경 확인') {                       // ★ 여기서 다른 폴더 커밋을 걸러낸다
      steps {
        script {
          // 병합 커밋이면 HEAD~1..HEAD 가 병합된 전체 변경. 일반 커밋이면 그 커밋 하나
          def changed = sh(returnStdout: true,
            script: 'git diff --name-only HEAD~1 HEAD 2>/dev/null || git show --name-only --pretty=format: HEAD').trim()
          def hit = changed.split('\n').any { it.startsWith('infra/web/') }
          echo "바뀐 파일 ${changed.split('\n').size()}개 · infra/web 포함: ${hit}"
          if (!hit) {
            currentBuild.result = 'NOT_BUILT'           // 회색으로 끝낸다 (실패가 아니다)
            error('infra/web 변경 없음 — 배포 건너뜀 (VR·AI 커밋)')
          }
        }
      }
    }
    stage('배포') {
      steps {
        // 경로를 못 박아 넘긴다. 스크립트는 이 아래만 건드린다
        sh 'sudo /srv/catalog/bin/deploy-from-workspace.sh "$WORKSPACE/infra/web"'
      }
    }
    stage('확인') {
      steps {
        sh 'curl -sf http://127.0.0.1/api/health && echo && curl -sf -o /dev/null -w "화면 HTTP %{http_code}\\n" http://127.0.0.1/'
      }
    }
  }
  post {
    success { echo '배포 완료 — 서버 안쪽(127.0.0.1) 확인 통과' }
    failure { echo '배포 실패 — 콘솔 로그의 deploy-from-workspace.sh 출력을 본다.' }
  }
}
```

---

## 8. Jenkins 잡 만들기

### 방법 A — 화면에서

```
New Item → 이름 infra-web-deploy → Pipeline → OK

Build Triggers
  ☑ Build when a change is pushed to GitLab
     [고급] → Secret token [Generate]  → 나온 값을 복사해 둔다 (9절에서 GitLab 에 넣는다)
  Enabled GitLab triggers: ☑ Push Events   ☑ Accepted Merge Request Events
  Allowed branches → Filter branches by name → Include: dev

Pipeline
  Definition        Pipeline script from SCM
  SCM               Git
  Repository URL    https://lab.ssafy.com/s15-ai-image-sub1/S15P21C201.git
  Credentials       gitlab-deploy-token
  Branches to build */dev
  Script Path       infra/web/Jenkinsfile
  Lightweight checkout  체크 해제   ← 변경 파일 목록을 보려면 전체 clone 이 필요하다
→ Save
```

### 방법 B — 설정 파일로 (우리가 쓴 방법. 화면 클릭이 많아서)

```bash
ssh c201
sudo mkdir -p /var/lib/jenkins/jobs/infra-web-deploy
sudo tee /var/lib/jenkins/jobs/infra-web-deploy/config.xml <<'EOF'
<?xml version="1.1" encoding="UTF-8"?>
<flow-definition plugin="workflow-job">
  <description>infra/web 이 dev 에 병합되면 자료 서버에 자동 배포</description>
  <keepDependencies>false</keepDependencies>
  <properties>
    <jenkins.model.BuildDiscarderProperty>
      <strategy class="hudson.tasks.LogRotator">
        <daysToKeep>30</daysToKeep><numToKeep>50</numToKeep>       <!-- 빌드 기록 보관 한도 -->
        <artifactDaysToKeep>-1</artifactDaysToKeep><artifactNumToKeep>-1</artifactNumToKeep>
      </strategy>
    </jenkins.model.BuildDiscarderProperty>
    <org.jenkinsci.plugins.workflow.job.properties.PipelineTriggersJobProperty>
      <triggers>
        <com.dabsquared.gitlabjenkins.GitLabPushTrigger plugin="gitlab-plugin">
          <spec></spec>
          <triggerOnPush>true</triggerOnPush>                        <!-- dev 에 push -->
          <triggerOnAcceptedMergeRequest>true</triggerOnAcceptedMergeRequest>  <!-- MR 병합 -->
          <triggerOnMergeRequest>false</triggerOnMergeRequest>       <!-- MR 생성만으론 배포 안 함 -->
          <triggerOnClosedMergeRequest>false</triggerOnClosedMergeRequest>
          <triggerOnApprovedMergeRequest>false</triggerOnApprovedMergeRequest>
          <triggerOnNoteRequest>false</triggerOnNoteRequest>
          <triggerOnPipelineEvent>false</triggerOnPipelineEvent>
          <triggerOpenMergeRequestOnPush>never</triggerOpenMergeRequestOnPush>
          <ciSkip>true</ciSkip>                                      <!-- 커밋 메시지에 [ci skip] 이면 건너뜀 -->
          <skipWorkInProgressMergeRequest>true</skipWorkInProgressMergeRequest>
          <setBuildDescription>true</setBuildDescription>
          <branchFilterType>NameBasedFilter</branchFilterType>
          <includeBranchesSpec>dev</includeBranchesSpec>              <!-- dev 만 -->
          <excludeBranchesSpec></excludeBranchesSpec>
          <sourceBranchRegex></sourceBranchRegex><targetBranchRegex></targetBranchRegex>
          <secretToken></secretToken>                                <!-- 9절에서 채운다 -->
        </com.dabsquared.gitlabjenkins.GitLabPushTrigger>
      </triggers>
    </org.jenkinsci.plugins.workflow.job.properties.PipelineTriggersJobProperty>
  </properties>
  <definition class="org.jenkinsci.plugins.workflow.cps.CpsScmFlowDefinition" plugin="workflow-cps">
    <scm class="hudson.plugins.git.GitSCM" plugin="git">
      <configVersion>2</configVersion>
      <userRemoteConfigs>
        <hudson.plugins.git.UserRemoteConfig>
          <url>https://lab.ssafy.com/s15-ai-image-sub1/S15P21C201.git</url>
          <credentialsId>gitlab-deploy-token</credentialsId>          <!-- 6절에서 만든 ID -->
        </hudson.plugins.git.UserRemoteConfig>
      </userRemoteConfigs>
      <branches><hudson.plugins.git.BranchSpec><name>*/dev</name></hudson.plugins.git.BranchSpec></branches>
      <doGenerateSubmoduleConfigurations>false</doGenerateSubmoduleConfigurations>
      <submoduleCfg class="empty-list"/>
      <extensions>
        <hudson.plugins.git.extensions.impl.CloneOption>
          <shallow>false</shallow>      <!-- HEAD~1 을 보려면 얕은 clone 이면 안 된다 -->
          <noTags>true</noTags><reference></reference><depth>0</depth><honorRefspec>false</honorRefspec>
        </hudson.plugins.git.extensions.impl.CloneOption>
      </extensions>
    </scm>
    <scriptPath>infra/web/Jenkinsfile</scriptPath>
    <lightweight>false</lightweight>
  </definition>
  <disabled>false</disabled>
</flow-definition>
EOF
sudo chown -R jenkins:jenkins /var/lib/jenkins/jobs
sudo systemctl restart jenkins        # 잡을 인식시키려면 재시작 (또는 화면에서 Reload Configuration from Disk)
```

```bash
# 웹훅용 비밀 토큰을 만들어 잡에 심는다 (방법 B 로 만들었을 때)
ssh c201 'C=/var/lib/jenkins/jobs/infra-web-deploy/config.xml
T=$(openssl rand -hex 24)                                  # 48자 무작위 값
sudo python3 -c "
import sys,re
p,t=sys.argv[1],sys.argv[2]; s=open(p,encoding=\"utf-8\").read()
s=re.sub(r\"<secretToken>[^<]*</secretToken>\", \"<secretToken>%s</secretToken>\"%t, s)
open(p,\"w\",encoding=\"utf-8\").write(s)" $C $T
sudo chown jenkins:jenkins $C && sudo systemctl restart jenkins'

# 심어진 값 확인 (9절에서 GitLab 에 넣을 값)
ssh c201 "sudo grep -oP '(?<=<secretToken>)[^<]+' /var/lib/jenkins/jobs/infra-web-deploy/config.xml"
```

---

## 9. GitLab 웹훅 등록 (마지막 연결)

```
GitLab 프로젝트 → Settings → Webhooks → Add new webhook

  Name          Jenkins — infra/web 자동 배포
  URL           http://$SERVER_HOST:8912/project/infra-web-deploy
                                                    ↑ 잡 이름과 정확히 같아야 한다
  Secret token  8절에서 만든 48자 값
  Trigger       ☑ Push events → Wildcard pattern → dev      ← dev 만 알림이 오게
                ☑ Merge request events
  SSL verification  체크 해제  ← URL 이 http 라서
→ Add webhook
```

등록 후 목록에서 **Test → Push events**:

```
Hook executed successfully: HTTP 200      ← 이게 나와야 성공
```

---

## 10. 검증

```bash
# Jenkins 가 요청을 받고 빌드를 만들었는지
ssh c201 'sudo ls /var/lib/jenkins/jobs/infra-web-deploy/builds/ | grep -E "^[0-9]+$"'

# 마지막 빌드 로그에서 핵심 줄만
ssh c201 'B=$(sudo ls /var/lib/jenkins/jobs/infra-web-deploy/builds/ | grep -E "^[0-9]+$" | sort -n | tail -1)
sudo cat /var/lib/jenkins/jobs/infra-web-deploy/builds/$B/log \
  | grep -E "Started by|Commit message|바뀐 파일|배포 완료|화면 HTTP|Finished"'
```

실제 성공 로그 (빌드 #5, 2026-09-10):

```
Started by GitLab push by 권영호
Commit message: "Merge branch 'feature/S15P21C201-121-infra-web' into 'dev'"
바뀐 파일 33개 · infra/web 포함: true
+ sudo /srv/catalog/bin/deploy-from-workspace.sh .../infra/web
배포 완료 · API 정상
화면 HTTP 200
배포 완료 — 서버 안쪽(127.0.0.1) 확인 통과
Finished: SUCCESS          (35초)
```

```bash
# 서버에 코드가 실제로 갱신됐는지 (배포 시각과 기능 포함 여부)
ssh c201 'stat -c "%y  app/main.py" /srv/catalog/app/main.py
stat -c "%y  web/app.js" /srv/catalog/web/app.js
systemctl is-active catalog-api nginx'
```

```powershell
# 밖에서 최종 확인
curl.exe -s -o NUL -w "화면 %{http_code}`n" http://$env:SERVER_HOST/
curl.exe -s http://$env:SERVER_HOST/api/stats
```

### 마지막 실전 확인

`infra/web/` 안의 아무 파일(예: 이 문서)을 한 줄 고쳐 브랜치 → MR → `dev` 병합.
1분 안에 Jenkins 에 빌드가 생기고 초록색으로 끝나면 완성이다.
반대로 **VR·AI 폴더만 바뀐 병합은 회색(NOT_BUILT)** 으로 끝나야 정상이다.

---

## 11. 평소 운영

| 하고 싶은 것 | 방법 |
| --- | --- |
| 코드 배포 | `infra/web/` 수정 → MR → `dev` 병합 (자동) |
| 급할 때 손으로 배포 | `bash infra/web/deploy/deploy.sh` (같은 결과) |
| 빌드 다시 돌리기 | Jenkins → `infra-web-deploy` → 지금 빌드 |
| 자료를 새로 넣었을 때 | 배포와 무관. `ASSET_DB_BUILD_GUIDE.md` 6절 → `POST /api/rescan` |
| 배포 잠시 멈추기 | Jenkins 잡 → 구성 → GitLab 트리거 체크 해제 |

```bash
# 자주 보는 로그
ssh c201 'sudo journalctl -u jenkins -n 50 --no-pager'                    # Jenkins 자체
ssh c201 'sudo journalctl -u catalog-api -n 30 --no-pager'                # 배포된 앱
ssh c201 'sudo tail -30 /var/log/nginx/catalog.error.log'                 # 웹서버
```

---

## 12. 우리가 실제로 막혔던 것 (같은 데서 막히면)

| 증상 | 원인 | 처치 |
| --- | --- | --- |
| 마법사의 플러그인 설치가 대량 실패 | **전역 IPv6 가 없는데 시스템이 IPv6 우선** | 2절 (a)(d) — `gai.conf` + `preferIPv4Stack`. 그다음 `Resume Installation` |
| `Unlock Jenkins` 가 다시 뜨고 초기 비밀번호가 "incorrect" | 플러그인 실패로 마법사가 되돌아갔는데 계정은 이미 생성됨 | `config.xml` 제거 후 재시작 → 마법사가 초기 비밀번호를 새로 발급 |
| 초기 비밀번호가 29자로 잘림 | PowerShell 이 ssh 출력을 배열로 쪼갬 | `(ssh … ) -join ''` 로 합친 뒤 `Set-Clipboard` |
| 로그인 화면에 Deploy Token 을 넣어 실패 | Jenkins 계정과 GitLab 토큰은 별개 | Jenkins 로그인은 `admin`+비밀번호. 토큰은 Credentials 에 |
| Credentials 화면에 `API token` 칸만 보임 | Kind 가 `GitLab API token` | Kind 를 **Username with password** 로 |
| 빌드가 `infra/web/Jenkinsfile not found` 로 실패 | `dev` 에 아직 `infra/web/` 이 없음 | MR 을 먼저 병합 |
| `sudo: a password is required` | `sudoers.d/jenkins-deploy` 누락·경로 불일치 | 3절 다시. 경로가 정확히 같아야 한다 |
| 웹훅 Test 가 403/404 | 잡 이름과 URL 의 `project/<이름>` 불일치, Secret token 불일치 | 9절 확인 |
| Deploy Token 이 `Authentication failed` | Scope 에 `read_repository` 없음 / Username 을 Name 으로 착각 | 5절. 안 되면 지우고 재발급 |
| `curl -d '{"note":"한글"}'` 이 400 | Windows 콘솔이 CP949 로 보냄 | 브라우저나 Python 으로. 서버 문제 아님 |

---

## 13. 보안상 지킬 것

- **pem 과 토큰은 채팅·이슈·커밋에 붙이지 않는다.** 노출되면 즉시 GitLab 에서 Revoke 하고 재발급한다.
- Deploy Token 은 **`read_repository` 만** 준다. 쓰기 권한은 필요 없다.
- Jenkins 화면은 로그인을 유지한다. 초기 비밀번호로 쓰고 있으면 `admin → Security` 에서 바꾼다.
- FastAPI 는 `127.0.0.1:8412` 에만 바인딩한다. 외부에 8412 를 열지 않는다.
- `ufw` 는 항상 enable 상태로 두고, **22 번은 건드리지 않는다.** 방화벽 작업 전 SSH 세션을 2개 이상 열어 둔다.
