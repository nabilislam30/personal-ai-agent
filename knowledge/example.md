# Example Knowledge Note

This file exists only to verify the local knowledge/RAG workflow.

The Personal AI Agent is designed around a local-first architecture.

Key principles:

- The main chat model runs locally through Ollama.
- Personal knowledge retrieval uses a local embedding model.
- Knowledge embeddings are stored in a local SQLite index.
- Read-only investigation is preferred before write operations.
- Document writes require explicit human approval.
- Destructive infrastructure actions are not exposed to the model.

This example can be deleted after the knowledge workflow has been tested.
