#!/bin/zsh
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

if [[ ! -f ".env.production" ]]; then
  echo "Missing .env.production" >&2
  exit 1
fi

if [[ ! -x ".venv/bin/gunicorn" ]]; then
  echo "Missing .venv/bin/gunicorn" >&2
  exit 1
fi

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

set -a
source ".env.production"
set +a

export PAI_ENV="production"
export PAI_REQUIRE_AUTH="true"
export PAI_WEB_HOST="127.0.0.1"
export PAI_GUNICORN_BIND="127.0.0.1:8000"

mkdir -p "workspace/logs"

for attempt in {1..60}; do
  if /usr/bin/curl -fsS     --max-time 2     "http://127.0.0.1:11434/api/tags"     >/dev/null 2>&1; then
    break
  fi

  if [[ "$attempt" -eq 60 ]]; then
    echo "Ollama was not ready after 120 seconds; starting the app anyway." >&2
  else
    /bin/sleep 2
  fi
done

exec ".venv/bin/gunicorn"   --config "gunicorn.conf.py"   "wsgi:app"
