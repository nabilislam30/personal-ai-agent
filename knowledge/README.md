# Local Knowledge Base

The local knowledge base provides semantic retrieval over personal
reference material while keeping source documents on the local machine.

## Supported Formats

- Markdown: `.md`
- Plain text: `.txt`
- PDF: `.pdf`
- Word: `.docx`

PDF ingestion extracts embedded text. Image-only or scanned PDFs are not
OCR'd automatically.

DOCX ingestion extracts paragraph text and table contents.

## Privacy

Personal files under `knowledge/` are ignored by Git by default.

The tracked README exists only to document the folder. Any documents
added locally remain untracked unless Git settings are deliberately
changed.

The derived vector index is stored under `workspace/`, which is also
ignored by Git.

## Recommended Structure

```text
knowledge/
├── notes/
├── projects/
├── documentation/
├── articles/
└── inbox/
```

The local web UI stores uploaded knowledge documents under
`knowledge/inbox/`.

## Embedding Model

The default embedding model is:

```text
embeddinggemma:300m-qat-q4_0
```

Install it once:

```bash
ollama pull embeddinggemma:300m-qat-q4_0
```

## Build or Refresh the Index

CLI:

```bash
python main.py
```

Then ask:

```text
Rebuild my knowledge index.
```

Web UI:

```bash
python web_app.py
```

Then use the **Rebuild index** button.

The index records a source-state fingerprint. If source documents change
after indexing, knowledge status reports that the source state changed
and search results include a warning until the index is rebuilt.

## Search Examples

```text
What have I documented about Kubernetes networking?
```

```text
Search my knowledge for Terraform troubleshooting.
```

```text
Use my PDF notes to summarise the ECS architecture.
```

Retrieved results identify the source path and chunk number so answers
can remain grounded in the local material.
