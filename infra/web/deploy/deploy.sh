#!/usr/bin/env bash
# 코드·화면·설정을 EC2 에 올리고 서비스를 (재)시작한다. 자료(files/)·프리뷰(preview/)는 별도 전송(transfer.sh / send_preview).
#   bash deploy/deploy.sh            # 전체
#   bash deploy/deploy.sh code       # app/ web/ pyproject 만 (설정·서비스 재시작 포함)
set -euo pipefail
H=c201; R=/srv/catalog
HERE="$(cd "$(dirname "$0")/.." && pwd)"
if [ -f "$HERE/.env" ]; then . "$HERE/.env"; fi     # SERVER_HOST — 서버 주소는 저장소에 두지 않는다 (.env.example)
SERVER_HOST="${SERVER_HOST:-$(ssh -G $H | awk '$1 == "hostname" { print $2 }')}"   # 없으면 ~/.ssh/config 의 c201
log(){ printf '%s  %s\n' "$(date +%H:%M:%S)" "$*"; }

log "1) 코드·화면 전송"
tar -cf - -C "$HERE/server" app web pyproject.toml | ssh -o BatchMode=yes $H "tar -xf - -C $R && rm -rf $R/app/__pycache__ && mkdir -p $R/zips"

log "2) 파이썬 의존성 (uv sync)"
ssh -o BatchMode=yes $H "cd $R && ~/.local/bin/uv sync --quiet && ~/.local/bin/uv run python -c 'import fastapi, uvicorn; print(\"  fastapi\", fastapi.__version__)'"

log "3) DB — 없으면 스캔해서 만든다 (있으면 그대로; 갱신은 /api/rescan)"
ssh -o BatchMode=yes $H "cd $R && [ -f catalog.db ] && echo '  catalog.db 있음' || CATALOG_FILES=$R/files CATALOG_DB=$R/catalog.db CATALOG_PREVIEW=$R/preview ~/.local/bin/uv run python app/scan.py"

log "4) nginx 설정"
scp -q -o BatchMode=yes "$HERE/deploy/nginx-catalog.conf" $H:/tmp/catalog.conf
ssh -o BatchMode=yes $H "sudo install -m 644 /tmp/catalog.conf /etc/nginx/sites-available/catalog \
  && sudo ln -sf /etc/nginx/sites-available/catalog /etc/nginx/sites-enabled/catalog \
  && sudo rm -f /etc/nginx/sites-enabled/default && sudo nginx -t 2>&1 | tail -1 && sudo systemctl reload nginx"

log "5) systemd 서비스"
scp -q -o BatchMode=yes "$HERE/deploy/catalog-api.service" $H:/tmp/catalog-api.service
ssh -o BatchMode=yes $H "sudo install -m 644 /tmp/catalog-api.service /etc/systemd/system/catalog-api.service \
  && sudo systemctl daemon-reload && sudo systemctl enable --quiet catalog-api && sudo systemctl restart catalog-api \
  && sleep 2 && systemctl is-active catalog-api"

log "6) 확인"
ssh -o BatchMode=yes $H "curl -s http://127.0.0.1:8412/api/health; echo"
curl -s -o /dev/null -w '  /                    → HTTP %{http_code}\n' "http://$SERVER_HOST/"
curl -s -o /dev/null -w '  /api/stats           → HTTP %{http_code}\n' "http://$SERVER_HOST/api/stats"
curl -s -o /dev/null -w '  /files/ (autoindex)  → HTTP %{http_code}\n' "http://$SERVER_HOST/files/"
log "끝"
