# Personal AI Agent

A local-first Python AI agent powered by Ollama.

Version: **2.0.0**

V2 builds on the stable v1 agent with document ingestion, deeper
read-only AWS inspection, and a local browser interface.

## Architecture

```text
CLI (main.py)          Local Web UI (web_app.py)
       \                    /
        \                  /
         v                v
            agent.py
         orchestration
              |
        Ollama / Qwen3
              |
   +----------+-----------+
   |          |           |
Local RAG   DevOps      General
   |          |           |
PDF/DOCX    Git         Research
MD/TXT      Terraform   Documentation
SQLite      GitHub      Planning
Embeddings  AWS
              |
      Permission Layer
READ -> automatic
WRITE -> explicit approval
DESTRUCTIVE -> unavailable
```

## V2 Features

### Local Web UI

Start the browser interface:

```bash
python web_app.py
```

Open:

```text
http://127.0.0.1:8000
```

The server binds to localhost by default.

The web UI supports:

- persistent conversation sessions
- creating and switching sessions
- local chat through Qwen3/Ollama
- per-message approval for agent write tools
- knowledge document uploads
- knowledge-index rebuilds
- knowledge-index status

The **Approve write tools for this message** checkbox is intentionally
off by default. It provides explicit approval only for the current
message.

### PDF and DOCX Knowledge Ingestion

Supported local knowledge formats:

- `.md`
- `.txt`
- `.pdf`
- `.docx`

PDF ingestion extracts embedded text. Scanned/image-only PDFs are not
OCR'd automatically.

DOCX ingestion extracts paragraphs and table contents.

Documents can be copied directly into `knowledge/` or uploaded through
the local web UI. Web uploads are stored under `knowledge/inbox/`.

Knowledge files are ignored by Git by default.

### Knowledge Index State Detection

The local RAG system records a fingerprint of the source-document state.

If files change after indexing:

- `knowledge_status` reports that sources changed
- semantic search warns that the index may be stale
- rebuilding the index refreshes the embeddings

### Deeper Read-Only AWS Inspection

Available AWS tools:

- caller identity
- configured region
- EC2 instance inventory
- ECS cluster listing
- ECS service listing
- EKS cluster listing
- CloudWatch alarm inspection
- Route 53 hosted-zone inspection
- S3 bucket inventory

These tools use fixed AWS CLI read operations. The agent cannot create,
modify, scale, restart, deploy, or delete AWS resources.

## Existing Core Capabilities

### Persistent Conversation Memory

Conversations are stored locally in SQLite under `workspace/`.

CLI commands:

```text
/new          Start a new conversation
/sessions     List saved conversations
/use <id>     Switch to a saved conversation
/help         Show commands
exit          Quit
```

Only user and assistant messages are persisted. Old tool traces are not
replayed after restarting the application.

### Documentation

The agent can draft:

- README files
- project documentation
- Jira updates
- incident reports
- RCAs
- architecture documentation
- troubleshooting documentation
- technical summaries

Generated `.md` and `.txt` files can be saved only under
`workspace/`, require explicit approval, and cannot overwrite existing
files automatically.

### Research

- public web search
- public webpage extraction
- source URLs in research results
- preference for primary technical documentation

### Git

Read-only inspection:

- `git status`
- `git diff`
- staged diffs
- recent commit history

### Terraform

Read-only inspection:

- Terraform version
- formatting checks
- `terraform validate`
- existing plan/state inspection

There is no `terraform apply` or `terraform destroy` capability.

### GitHub Actions

Read-only pipeline investigation:

- GitHub CLI authentication
- workflow run listing
- workflow-run details
- failed-step logs
- deterministic latest-failed-run analysis

## Security Model

### READ

May run automatically:

- local file inspection
- local knowledge search
- Git inspection
- Terraform validation
- GitHub Actions investigation
- AWS inspection
- web research
- log inspection

### WRITE

Requires explicit human approval:

- saving generated documents
- rebuilding the knowledge index

Direct web UI actions such as uploading a knowledge file or pressing
**Rebuild index** are themselves explicit user actions.

### DESTRUCTIVE

Not exposed:

- `terraform apply`
- `terraform destroy`
- `kubectl delete`
- Git push/reset
- AWS resource mutation/deletion
- IAM changes
- service restarts
- workflow reruns/cancellation

## Requirements

Required:

- macOS or Linux
- Python 3.13+
- Ollama
- Git
- `qwen3:8b`
- `embeddinggemma:300m-qat-q4_0`

Optional depending on the feature:

- GitHub CLI (`gh`)
- Terraform CLI
- AWS CLI

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

Install development/test dependencies:

```bash
python -m pip install -r requirements-dev.txt
```

Pull local models:

```bash
ollama pull qwen3:8b
ollama pull embeddinggemma:300m-qat-q4_0
```

For GitHub Actions investigation:

```bash
gh auth login
gh auth status
```

For AWS inspection, use your existing AWS CLI authentication and
least-privilege credentials.

## Run

Terminal:

```bash
python main.py
```

Web:

```bash
python web_app.py
```

## Configuration

Configuration is centralised in `config.py`.

Environment overrides are documented in `.env.example`, including:

- chat and embedding models
- knowledge chunking limits
- maximum knowledge file size
- web host/port
- maximum web upload size

The default web host is `127.0.0.1`.

## Tests

Run unit tests:

```bash
python -m pytest -q
```

Run the manual general smoke suite:

```bash
PYTHONPATH=. python tests/smoke_tests.py
```

Run the GitHub Actions smoke suite:

```bash
PYTHONPATH=. python tests/pipeline_smoke_tests.py
```

## CI

GitHub Actions validates:

- dependency installation
- dependency consistency
- Python compilation
- automated pytest tests

A manual `force_failure=true` input remains available for controlled
pipeline-failure investigation testing.

## Release

Current version: **2.0.0**

See `CHANGELOG.md` for release contents.

## Later Expansion

Potential future additions:

- Google Drive
- task/calendar integration
- OCR for scanned PDFs
- richer AWS service-specific investigations
- specialist internal workflows where they materially improve reliability
