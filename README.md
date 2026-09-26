# Personal AI Agent

A local-first Python AI agent powered by Ollama and Qwen3 8B.

The project supports organisation, technical documentation, research,
coding, DevOps investigation, GitHub Actions analysis, and content
creation while maintaining explicit security boundaries around write
and destructive operations.

## Current Architecture

User
↓
Python Agent
↓
Ollama
↓
Qwen3 8B
↓
Tool Layer

## Current Capabilities

### General Assistant

- Conversational terminal interface
- Session conversation memory
- Organisation and planning
- Professional content creation

### Local Files

- List project directories
- Read UTF-8 text files
- Search project files
- Inspect log tails
- Restricted to the project directory

### Documentation

- README drafting
- Project documentation
- Jira updates
- Incident reports
- RCA documents
- Architecture documentation
- Technical summaries

Generated Markdown and text documents can be saved inside
`workspace/` only after explicit user approval.

### Research

- Public web search
- Public webpage extraction
- Source URLs returned with research results

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
- inspect existing plan/state files

The agent has no `terraform apply` or `terraform destroy` capability.

### GitHub Actions

Read-only pipeline investigation:

- Check GitHub CLI authentication
- List recent workflow runs
- Inspect a specific workflow run
- Retrieve failed-step logs
- Deterministically investigate the latest failed workflow run

The latest-failure investigation gathers the run, details, and failed
logs before the model reasons over the evidence.

The agent does not expose workflow rerun, cancellation, deletion,
deployment approval, or repository-secret modification tools.

### Cloud

Initial read-only AWS check:

- AWS caller identity

Azure and Azure DevOps authentication are not currently configured.

## Security Model

### READ

May run automatically.

Examples:

- file inspection
- Git status/diff/log
- Terraform validation
- web research
- log inspection
- GitHub Actions investigation
- AWS identity inspection

### WRITE

Requires explicit user approval.

Current example:

- saving generated documentation into `workspace/`

### DESTRUCTIVE

Not available.

Examples intentionally unavailable:

- `terraform apply`
- `terraform destroy`
- `kubectl delete`
- cloud resource deletion
- Git push
- IAM/security changes
- service restarts
- workflow reruns/cancellation

## Requirements

- macOS
- Python 3.13+
- Ollama
- `qwen3:8b`
- Git
- GitHub CLI (`gh`) for GitHub Actions investigation

Optional depending on the tools being used:

- Terraform CLI
- AWS CLI

## Setup

Create and activate the virtual environment:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
```

Install Python dependencies:

```bash
python -m pip install -r requirements.txt
```

Ensure Ollama is running and the model is installed:

```bash
ollama pull qwen3:8b
ollama list
```

Authenticate the GitHub CLI for pipeline investigation:

```bash
gh auth login
gh auth status
```

## Run

```bash
python main.py
```

## Examples

```text
What files are in this project?
```

```text
Search the project for references to Ollama.
```

```text
Show me the current Git status and explain the changes.
```

```text
Validate the Terraform configuration in terraform/.
```

```text
Research the official Terraform validate documentation and cite the sources.
```

```text
Inspect logs/deployment.log and identify evidence of the failure.
```

```text
Show me the most recent GitHub Actions runs for this repository.
```

```text
Investigate the most recent failed GitHub Actions run.
Separate observed evidence, likely cause, uncertainty, and remediation.
```

```text
Create an RCA from the available evidence and save it as incident-rca.md.
```

## Tests

Run the general smoke tests:

```bash
PYTHONPATH=. python tests/smoke_tests.py
```

Run the GitHub Actions pipeline smoke test:

```bash
PYTHONPATH=. python tests/pipeline_smoke_tests.py
```

## CI

The repository includes `.github/workflows/ci.yml`.

Normal pushes to `main` validate:

- Python 3.13 setup
- dependency installation
- dependency consistency
- Python source compilation

The workflow can also be manually triggered with
`force_failure=true` to create a controlled failed run for pipeline
investigation testing.

## Planned Integrations

Future additions may include:

- Azure DevOps when authentication is available
- broader read-only AWS/Azure inspection
- Google Drive
- persistent knowledge/RAG
- task/calendar integrations
- specialist agents when justified
- local web UI
