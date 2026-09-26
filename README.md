# Personal AI Agent

A local-first, single-user Python AI agent powered by Ollama.

Current version: **2.1.0**

The project combines fast conversational chat, persistent local sessions,
RAG over personal documents, read-only DevOps investigation, controlled
document writing, and a private browser interface.

## What changed in 2.1

The agent now has a performance layer before the model:

```text
User request
    |
    v
Deterministic router
    |
    +--> Simple chat --------> no tools + short prompt + streaming
    |
    +--> Knowledge ----------> local RAG evidence
    |
    +--> GitHub Actions -----> pipeline tools only
    |
    +--> AWS ----------------> AWS read-only tools only
    |
    +--> Terraform ----------> Terraform/file/Git tools only
    |
    +--> Research -----------> web tools only
    |
    +--> Documentation ------> documentation/write tools only
```

Simple questions such as:

```text
What is your name?
```

no longer receive the schemas for Git, Terraform, GitHub Actions, AWS,
RAG, research, and document-writing tools.

For no-tool responses, the application also requests non-thinking mode
from Ollama and streams tokens to the browser as they are generated.

## Performance controls

Default performance settings:

```text
PAI_OLLAMA_KEEP_ALIVE=30m
PAI_PRELOAD_MODEL=true
PAI_SIMPLE_CHAT_HISTORY_LIMIT=12
PAI_TOOL_HISTORY_LIMIT=24
PAI_SESSION_SUMMARY_MAX_CHARS=6000
```

Older conversation turns remain stored in SQLite. The model receives a
bounded recent window plus a deterministic compact summary of older
conversation content instead of the full raw history.

The browser displays measurements such as:

```text
Route: simple_chat · first token: 620 ms · total: 1.84 s
```

Structured logs also record route/tool/timing metadata without storing
prompt contents.

## Core capabilities

### Local models

- Qwen3 8B through Ollama for chat
- EmbeddingGemma through Ollama for RAG
- configurable model keep-alive
- optional startup preload

### Persistent conversation memory

Conversations are stored locally in:

```text
workspace/sessions.sqlite3
```

CLI commands:

```text
/new
/sessions
/use <id>
/help
exit
```

### Local RAG

Supported formats:

- `.md`
- `.txt`
- `.pdf`
- `.docx`

Source documents live under `knowledge/`.

The derived vector index lives under `workspace/` and can be rebuilt at
any time.

PDF extraction is text-only. Image-only/scanned PDFs require a future OCR
extension.

### DevOps inspection

Read-only capabilities include:

- Git status/diff/log
- Terraform version/fmt/validate/show
- log tail inspection
- GitHub Actions runs/details/failed logs
- deterministic latest-failed-run evidence gathering
- AWS identity/region
- EC2 inventory
- ECS clusters/services
- EKS clusters
- CloudWatch alarms
- Route 53 hosted zones
- S3 bucket inventory

The agent does not expose destructive infrastructure operations.

### Documentation and research

The agent can:

- draft technical documentation
- create README/project/incident/RCA/Jira material
- search the public web
- inspect public webpages
- save approved Markdown/text output under `workspace/`

## Permission model

```text
READ
  automatic

WRITE
  explicit human approval

DESTRUCTIVE
  unavailable
```

Examples intentionally unavailable to the model include:

- `terraform apply`
- `terraform destroy`
- `kubectl delete`
- Git push/reset
- AWS resource mutation/deletion
- IAM changes
- arbitrary shell execution
- workflow rerun/cancellation

## Local web UI

Development/local use:

```bash
python web_app.py
```

Open:

```text
http://127.0.0.1:8000
```

The browser UI supports:

- streamed simple responses
- persistent sessions
- session switching
- local knowledge uploads
- knowledge-index rebuild
- per-message explicit write approval
- performance timing display

## Production security

Private production deployment adds:

- password authentication
- CSRF protection
- strict SameSite/HttpOnly cookies
- optional Secure cookies
- login/chat rate limits
- security headers
- request-size limits
- production configuration validation
- `/health`
- `/ready`
- Gunicorn
- JSON operational logs
- backup/restore tooling

Production mode refuses to start through `wsgi.py` if authentication is
disabled or required secrets are missing.

## Recommended live architecture

The recommended deployment is private and single-user:

```text
Authorised devices
       |
       | private Tailscale tailnet
       v
Tailscale Serve / HTTPS
       |
       v
127.0.0.1:8000 on Mac mini
       |
       v
Gunicorn
       |
       v
Personal AI Agent
       |
       +--> Ollama/Qwen on Mac
       +--> local knowledge
       +--> local sessions
       +--> read-only integrations
```

This avoids opening the agent or Ollama directly to the public internet.

See:

```text
DEPLOYMENT.md
```

for the production procedure.

## Setup

Create and activate the virtual environment:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Install development dependencies:

```bash
python -m pip install -r requirements-dev.txt
```

Install models:

```bash
ollama pull qwen3:8b
ollama pull embeddinggemma:300m-qat-q4_0
```

## Run

CLI:

```bash
python main.py
```

Web:

```bash
python web_app.py
```

## Production authentication setup

Generate a password hash and Flask secret:

```bash
python scripts/generate_auth.py
```

Then follow `DEPLOYMENT.md`.

Real production secrets belong in:

```text
.env.production
```

which is ignored by Git.

## Backups

Create:

```bash
python scripts/backup.py
```

Restore:

```bash
python scripts/restore.py backups/<archive>.tar.gz --confirm
```

Backups preserve personal knowledge and conversation sessions. The vector
index is derived data and is rebuilt after restore.

## Tests

Automated tests:

```bash
python -m pytest -q
```

Manual local smoke tests:

```bash
PYTHONPATH=. python tests/smoke_tests.py
```

GitHub Actions smoke test:

```bash
PYTHONPATH=. python tests/pipeline_smoke_tests.py
```

## Docker

Docker deployment support is included for portability:

```bash
docker compose build
docker compose up -d
```

On the Mac mini, direct Gunicorn is preferred when it avoids widening the
Ollama listening interface and preserves native local acceleration.

## Project structure

```text
personal-ai-agent/
├── main.py
├── web_app.py
├── wsgi.py
├── agent.py
├── router.py
├── config.py
├── security.py
├── observability.py
├── permissions.py
├── sessions.py
├── gunicorn.conf.py
├── Dockerfile
├── docker-compose.yml
├── DEPLOYMENT.md
├── CHANGELOG.md
├── VERSION
├── prompts/
├── tools/
├── scripts/
├── tests/
├── knowledge/
└── workspace/     # local, ignored by Git
```

## Current deployment boundary

The production design is intentionally **private and single-user**.

Turning this into a public multi-user service would require a separate
identity/authorisation model, per-user data isolation, tenant-aware RAG,
audit controls, abuse protection, and different cloud/security
architecture.
