# Local Knowledge Base

Place personal reference material here for semantic search by the agent.

Supported source formats:

- `.md`
- `.txt`

Examples:

```text
knowledge/
├── notes/
│   └── kubernetes-notes.md
├── projects/
│   └── ecs-project.md
├── documentation/
│   └── terraform-troubleshooting.md
└── articles/
    └── draft-notes.txt
```

## Privacy

Files placed under `knowledge/` are ignored by Git by default.

Only this README is tracked.

That means personal notes and reference material stay local unless you
explicitly choose to version-control them.

## Embedding Model

The local vector index uses:

```text
embeddinggemma:300m-qat-q4_0
```

Install it once with:

```bash
ollama pull embeddinggemma:300m-qat-q4_0
```

## Build the Index

Start the agent:

```bash
python main.py
```

Then ask:

```text
Rebuild my knowledge index.
```

The agent will ask for explicit approval before rebuilding the index.

The derived SQLite index is stored under `workspace/`, which is also
ignored by Git.

## Search

After indexing, examples include:

```text
Search my knowledge for Kubernetes networking.
```

```text
What have I documented about Terraform troubleshooting?
```

```text
Use my stored project notes to summarise the ECS architecture.
```

Search results include source paths and chunk references so answers can
be grounded in the retrieved material.
