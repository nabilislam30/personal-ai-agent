# Changelog

## 2.1.0

Performance and private-production-readiness release.

### Performance

- Added deterministic request routing before model execution
- Simple conversational requests receive no tool schemas
- Domain requests receive only relevant tool groups
- Latest failed GitHub Actions investigations use a deterministic evidence path
- Local knowledge questions can retrieve evidence directly before generation
- Simple/general responses use Ollama streaming
- Simple no-tool responses request non-thinking mode for lower latency
- Ollama model keep-alive is configurable
- Optional model preloading keeps Qwen resident after startup
- Reduced recent-message context windows
- Added deterministic local compaction of older conversation history
- Added first-token/model/total latency reporting
- Added structured performance logging without prompt contents

### Private production readiness

- Added single-user password authentication
- Added CSRF protection
- Added login/chat rate limiting
- Added strict security response headers
- Added production configuration validation
- Added /health and /ready endpoints
- Added Gunicorn production serving
- Added Docker deployment support
- Added localhost-first deployment defaults
- Added Tailscale Serve private HTTPS deployment documentation
- Added local backup and guarded restore tooling
- Added automatic pre-restore safety backups
- Added authentication/configuration helper script

### Testing

- Added router tests
- Added fast-path guardrail tests
- Added security configuration tests
- Added conversation compaction tests
- Added streaming web tests
- Added authentication tests
- Added backup/archive safety tests

## 2.0.0

Core V2 feature release.

### Added

- PDF ingestion for the local knowledge base
- DOCX ingestion for the local knowledge base
- Knowledge-index source change detection
- Local knowledge file upload through the web interface
- Local Flask web UI for chat and persistent sessions
- Web UI session creation and switching
- Per-message explicit approval for agent write tools in the web UI
- Explicit web action for rebuilding the knowledge index
- Read-only AWS EC2 inventory
- Read-only AWS ECS cluster/service inspection
- Read-only AWS EKS cluster inspection
- Read-only AWS CloudWatch alarm inspection
- Read-only Route 53 hosted-zone inspection
- Read-only S3 bucket inventory

### Security

- Web server binds to 127.0.0.1 by default
- Knowledge uploads are extension restricted, size limited, and no-overwrite
- AWS commands remain fixed read-only operations
- No destructive cloud actions are exposed
- Existing READ / WRITE / DESTRUCTIVE boundaries remain in place

## 1.0.0

Initial stable local-first release.

### Included

- Ollama + Qwen3 conversational agent
- Persistent local conversation sessions
- Local file read/search/list tooling
- Controlled document writes with approval
- Documentation, incident, RCA, and Jira workflows
- Public web research
- Read-only Git inspection
- Read-only Terraform inspection
- Log investigation
- Read-only AWS identity inspection
- Read-only GitHub Actions investigation
- Deterministic latest-failed-run diagnosis
- Local RAG knowledge base with Ollama embeddings
- Centralised configuration
- Explicit permission-layer separation
- Automated pytest security and reliability tests
- GitHub Actions CI
