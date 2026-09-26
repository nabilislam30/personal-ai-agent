# Private Production Deployment

This deployment model keeps the AI model, personal knowledge, session
history, and AWS CLI access on the Mac mini.

The recommended exposure path is **Tailscale Serve**, not a public
internet port.

## Target Architecture

```text
Your authorised devices
        |
        | Tailscale encrypted tailnet
        v
Tailscale Serve (HTTPS)
        |
        v
127.0.0.1:8000
        |
        v
Gunicorn
        |
        v
Personal AI Agent
        |
        +--> Ollama on macOS
        +--> local knowledge
        +--> local session database
        +--> read-only tools
```

For the Mac mini, running Gunicorn directly on macOS is the preferred
production path because Ollama can continue using the Mac's native
acceleration without exposing its API to a Docker network.

Docker support is included as an optional portable deployment.

## 1. Prerequisites

Install and verify:

- Python 3.13
- Ollama
- Tailscale
- the required Ollama models

```bash
ollama pull qwen3:8b
ollama pull embeddinggemma:300m-qat-q4_0
ollama list
```

The current Tailscale macOS documentation recommends its Standalone
client. CLI integration can be enabled from Tailscale settings.

## 2. Create Production Authentication

From the repository root:

```bash
source .venv/bin/activate
python scripts/generate_auth.py
```

Copy:

```bash
cp .env.production.example .env.production
```

Replace the placeholder password hash and secret key with the generated
values.

Never commit `.env.production`.

## 3. Start the Preferred Mac Production Server

Make sure Ollama is already running.

Load the production environment:

```bash
set -a
source .env.production
set +a
```

Keep the Gunicorn bind address on loopback:

```bash
export PAI_GUNICORN_BIND=127.0.0.1:8000
export PAI_WEB_HOST=127.0.0.1
```

Start the production server:

```bash
gunicorn --config gunicorn.conf.py wsgi:app
```

The application is now reachable only from the Mac itself at:

```text
http://127.0.0.1:8000
```

Verify:

```bash
curl http://127.0.0.1:8000/health
```

Expected:

```json
{"status":"ok"}
```

The readiness endpoint additionally checks Ollama and the session DB:

```bash
curl http://127.0.0.1:8000/ready
```

## 4. Enable Private HTTPS with Tailscale Serve

Do **not** use Tailscale Funnel for this personal agent.

Serve the loopback application privately to your tailnet:

```bash
tailscale serve --bg http://127.0.0.1:8000
```

Check the generated private HTTPS URL:

```bash
tailscale serve status
```

Tailscale Serve terminates HTTPS and makes the service available only
inside the tailnet, subject to your Tailscale access-control rules.

Use that HTTPS URL from your authorised devices.

## 5. Authentication and Cookies

For Tailscale HTTPS access keep:

```text
PAI_ENV=production
PAI_REQUIRE_AUTH=true
PAI_COOKIE_SECURE=true
```

Production mode refuses to start through `wsgi.py` if authentication is
disabled or authentication secrets are missing.

The app also includes:

- password authentication
- strict same-site session cookies
- CSRF protection
- login/chat rate limits
- security response headers
- localhost-first binding

## 6. Optional Docker Deployment

Docker files are provided for portability:

```bash
docker compose build
docker compose up -d
```

The container still publishes only:

```text
127.0.0.1:8000
```

Docker Desktop reaches host Ollama through:

```text
host.docker.internal:11434
```

Depending on the local Ollama networking configuration, additional host
configuration may be required for the container to reach Ollama. Do not
expose the Ollama API directly to the internet.

For the Mac mini, prefer direct Gunicorn if Docker would require widening
Ollama's listening interface.

## 7. Backups

Create a backup:

```bash
python scripts/backup.py
```

Backups contain:

- `knowledge/`
- a consistent SQLite backup of conversation sessions
- backup metadata

The derived RAG vector index is not backed up because it can be rebuilt.

By default the seven newest archives are retained under `backups/`.

Restore:

```bash
python scripts/restore.py backups/<archive>.tar.gz --confirm
```

Restore automatically creates a pre-restore safety backup and removes
the old derived knowledge index. Rebuild the RAG index afterward.

## 8. Updating

```bash
git pull origin main
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
```

Then restart Gunicorn and verify:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ready
```

## 9. Logs and Performance Metrics

Application logs are JSON and deliberately exclude prompt contents.

The browser also reports per-turn performance data such as:

```text
Route: simple_chat · first token: 620 ms · total: 1.84 s
```

Structured logs include:

- request ID
- HTTP method/path/status
- request duration
- route selected
- tool-call count
- first-token latency
- model latency
- total latency

## 10. Stop Private Remote Access

Disable Tailscale Serve:

```bash
tailscale serve reset
```

Stop Gunicorn with the process manager or terminal session that started
it.

For Docker:

```bash
docker compose down
```

## Security Position

This design deliberately avoids:

- opening port 8000 to the public internet
- Tailscale Funnel
- exposing the Ollama API publicly
- destructive AWS operations
- arbitrary shell execution by the model
- committed authentication secrets

The application remains private and single-user. A public multi-user
service would require a different identity, authorisation, audit,
tenancy, and data-isolation architecture.
