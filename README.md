# Personal AI Agent

A local-first Python AI agent powered by Ollama.

The project is designed to support organisation, technical
documentation, research, coding, DevOps investigation and content
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
- Read text files
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

### Cloud

Initial read-only connection checks:

- AWS caller identity
- Azure account information
- Azure resource listing

No unrestricted cloud command execution is exposed to the model.

## Security Model

### READ

May run automatically.

Examples:

- file inspection
- Git status/diff/log
- Terraform validation
- web research
- log inspection

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

## Requirements

- macOS
- Python 3.13+
- Ollama
- `qwen3:8b`
- Git

Optional depending on the tools being used:

- Terraform CLI
- AWS CLI
- Azure CLI

## Setup

Create and activate the virtual environment:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
