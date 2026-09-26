# Personal AI Agent

A local-first Python AI agent powered by Ollama.

Version: **1.0.0**

The project supports persistent conversations, local knowledge retrieval,
technical documentation, research, coding, DevOps investigation,
GitHub Actions analysis, and content creation while maintaining explicit
security boundaries around write and destructive operations.

## Architecture

```text
User
  |
  v
main.py (CLI + persistent sessions)
  |
  v
agent.py (orchestration)
  |
  +--> Ollama / Qwen3 8B
  |
  +--> Tool Layer
         |
         +--> Local files / logs
         +--> Local RAG knowledge
         +--> Git
         +--> Terraform
         +--> GitHub Actions
         +--> AWS identity
         +--> Web research
         +--> Controlled document writes
```

## Core Capabilities

### Persistent Conversation Memory

Conversations are stored locally in SQLite under `workspace/`.

The CLI automatically resumes the most recently used session.

Commands:

```text
/new          Start a new conversation
/sessions     List saved conversations
/use <id>     Switch to a saved conversation
/help         Show commands
exit          Quit
```

Only user and assistant messages are persisted. Tool traces are not
replayed across processes, so stale tool output is not treated as
current evidence.

### Local Knowledge / RAG

The agent can semantically search personal Markdown and text documents.

- Source files: `knowledge/`
- Supported formats: `.md`, `.txt`
- Embedding model: `embeddinggemma:300m-qat-q4_0`
- Vector store: local SQLite under `workspace/`
- Personal knowledge files are ignored by Git by default

Typical prompts:

```text
Rebuild my knowledge index.
What have I documented about Kubernetes?
Search my knowledge for Terraform troubleshooting.
Use my stored project notes to summarise the ECS architecture.
```

Rebuilding the knowledge index is treated as a WRITE operation and
requires explicit approval.

### Local Files

Read-only tools can:

- list project directories
- read UTF-8 text files
- search project files
- inspect log tails

Filesystem access is restricted to the project directory.

### Documentation

The agent can draft:

- README files
- project documentation
- Jira updates and evidence
- incident reports
- RCAs
- architecture documentation
- troubleshooting documentation
- technical summaries

Generated `.md` and `.txt` files can be saved only under
`workspace/`, require explicit approval, and do not overwrite existing
files automatically.

### Research

- public web search
- webpage extraction
- source URLs in research results
- preference for primary technical documentation

### Git

Read-only inspection:

- `git status`
- `git diff`
- staged diffs
- recent commit history

No commit, push, reset, checkout, or history-modification tool is
exposed to the model.

### Terraform

Read-only inspection:

- Terraform version
- formatting checks
- `terraform validate`
- inspection of existing plan/state files

There is no `terraform apply` or `terraform destroy` capability.

### GitHub Actions

Read-only pipeline investigation:

- GitHub CLI authentication status
- recent workflow runs
- workflow-run details
- failed-step logs
- deterministic investigation of the latest failed run

The deterministic failure investigator gathers the run, jobs, and logs
before the model reasons over the evidence.

The agent does not expose workflow rerun, cancellation, deletion,
deployment approval, or repository-secret modification tools.

### Cloud

Current cloud capability is intentionally narrow:

- AWS caller identity

Azure and Azure DevOps authentication are not currently configured.

## Security Model

### READ

Read-only operations may run automatically.

Examples:

- local file inspection
- Git status/diff/log
- Terraform validation
- web research
- log inspection
- GitHub Actions investigation
- AWS identity inspection
- local knowledge search

### WRITE

Write operations require explicit human approval.

Current examples:

- saving generated documents
- rebuilding the derived local knowledge index

### DESTRUCTIVE

Destructive operations are not exposed.

Examples intentionally unavailable:

- `terraform apply`
- `terraform destroy`
- `kubectl delete`
- cloud resource deletion
- Git push/reset
- IAM/security changes
- service restarts
- workflow reruns/cancellation

## Project Structure

```text
personal-ai-agent/
├── main.py
├── agent.py
├── config.py
├── permissions.py
├── sessions.py
├── VERSION
├── CHANGELOG.md
├── requirements.txt
├── requirements-dev.txt
├── .env.example
├── prompts/
│   ├── system.py
│   └── documentation.py
├── tools/
│   ├── cloud_tools.py
│   ├── document_tools.py
│   ├── file_tools.py
│   ├── git_tools.py
│   ├── knowledge_tools.py
│   ├── log_tools.py
│   ├── pipeline_tools.py
│   ├── research_tools.py
│   └── terraform_tools.py
├── tests/
└── knowledge/
```

## Requirements

Required:

- macOS or Linux
- Python 3.13+
- Ollama
- Git
- `qwen3:8b`
- `embeddinggemma:300m-qat-q4_0`

Optional depending on features used:

- GitHub CLI (`gh`)
- Terraform CLI
- AWS CLI

## Setup

Create and activate a virtual environment:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Install development/test dependencies when contributing:

```bash
python -m pip install -r requirements-dev.txt
```

Pull the local models:

```bash
ollama pull qwen3:8b
ollama pull embeddinggemma:300m-qat-q4_0
```

For GitHub Actions investigation:

```bash
gh auth login
gh auth status
```

## Configuration

Configuration is centralised in `config.py` and can be overridden with
environment variables documented in `.env.example`.

Examples:

```bash
export PAI_CHAT_MODEL=qwen3:8b
export PAI_MAX_TOOL_ROUNDS=8
```

No secrets should be committed to the repository.

## Run

```bash
python main.py
```

## Build the Knowledge Index

Place personal `.md` or `.txt` files under `knowledge/`, then ask:

```text
Rebuild my knowledge index.
```

Approve the write when prompted.

## Tests

Run the automated unit tests:

```bash
pytest -q
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

`.github/workflows/ci.yml` automatically:

- installs development dependencies
- checks dependency consistency
- compiles Python source
- runs the pytest suite

The workflow also supports a manual `force_failure=true` input to
create a controlled failed run for pipeline-investigation testing.

## Release

Current version: **1.0.0**

See `CHANGELOG.md` for release contents.

## Future Expansion

Possible post-v1 additions include:

- Azure DevOps when authentication is available
- broader read-only cloud inspection
- PDF/Word knowledge ingestion
- Google Drive
- task/calendar integrations
- local web UI
- specialist sub-agents when justified
