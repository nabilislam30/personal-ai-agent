import hashlib
import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from ollama import embed


PROJECT_ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_ROOT = PROJECT_ROOT / "knowledge"
INDEX_PATH = PROJECT_ROOT / "workspace" / "knowledge_index.sqlite3"

EMBEDDING_MODEL = "embeddinggemma:300m-qat-q4_0"

ALLOWED_EXTENSIONS = {
    ".md",
    ".txt",
}

EXCLUDED_FILENAMES = {
    "README.md",
}

CHUNK_SIZE = 1400
CHUNK_OVERLAP = 200
EMBED_BATCH_SIZE = 24
MAX_TOP_K = 10
MAX_RESULT_CHARS = 2200


def _knowledge_files() -> list[Path]:
    """
    Return supported knowledge files in a deterministic order.
    """

    if not KNOWLEDGE_ROOT.exists():
        return []

    files = []

    for path in KNOWLEDGE_ROOT.rglob("*"):
        if not path.is_file():
            continue

        if path.name in EXCLUDED_FILENAMES:
            continue

        if path.name.startswith("."):
            continue

        if path.suffix.lower() not in ALLOWED_EXTENSIONS:
            continue

        files.append(path)

    return sorted(
        files,
        key=lambda path: str(
            path.relative_to(KNOWLEDGE_ROOT)
        ).lower(),
    )


def _chunk_text(text: str) -> list[str]:
    """
    Split text into overlapping chunks while preferring paragraph breaks.
    """

    cleaned = text.strip()

    if not cleaned:
        return []

    chunks = []
    start = 0
    text_length = len(cleaned)

    while start < text_length:
        hard_end = min(
            start + CHUNK_SIZE,
            text_length,
        )

        end = hard_end

        if hard_end < text_length:
            search_start = start + int(
                CHUNK_SIZE * 0.6
            )

            paragraph_break = cleaned.rfind(
                "\n\n",
                search_start,
                hard_end,
            )

            if paragraph_break != -1:
                end = paragraph_break
            else:
                line_break = cleaned.rfind(
                    "\n",
                    search_start,
                    hard_end,
                )

                if line_break != -1:
                    end = line_break

        chunk = cleaned[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break

        next_start = max(
            end - CHUNK_OVERLAP,
            start + 1,
        )

        start = next_start

    return chunks


def _connect() -> sqlite3.Connection:
    """
    Open the local SQLite knowledge index.
    """

    INDEX_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(
        INDEX_PATH
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_path TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            embedding_json TEXT NOT NULL,
            embedding_model TEXT NOT NULL
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )

    connection.commit()

    return connection


def _cosine_similarity(
    left: list[float],
    right: list[float],
) -> float:
    """
    Calculate cosine similarity between two vectors.
    """

    if len(left) != len(right):
        return 0.0

    dot_product = sum(
        a * b
        for a, b in zip(left, right)
    )

    left_norm = math.sqrt(
        sum(value * value for value in left)
    )

    right_norm = math.sqrt(
        sum(value * value for value in right)
    )

    if left_norm == 0 or right_norm == 0:
        return 0.0

    return (
        dot_product
        / (left_norm * right_norm)
    )


def list_knowledge_documents() -> str:
    """
    List documents currently available to the local knowledge base.

    Returns:
        Supported Markdown and text files inside knowledge/.
    """

    files = _knowledge_files()

    if not files:
        return (
            "No knowledge documents were found. "
            "Add .md or .txt files inside knowledge/."
        )

    lines = [
        "Knowledge documents:",
    ]

    for path in files:
        relative_path = path.relative_to(
            KNOWLEDGE_ROOT
        )

        lines.append(
            f"- {relative_path} "
            f"({path.stat().st_size} bytes)"
        )

    return "\n".join(lines)


def knowledge_status() -> str:
    """
    Show the status of the local knowledge base and vector index.

    Returns:
        Knowledge document count, index state, chunk count, and model.
    """

    files = _knowledge_files()

    if not INDEX_PATH.exists():
        return (
            "Knowledge base status:\n"
            f"- Source documents: {len(files)}\n"
            "- Index: not built\n"
            "- Indexed chunks: 0\n"
            f"- Embedding model: {EMBEDDING_MODEL}"
        )

    try:
        connection = sqlite3.connect(
            INDEX_PATH
        )

        chunk_count = connection.execute(
            "SELECT COUNT(*) FROM chunks"
        ).fetchone()[0]

        indexed_documents = connection.execute(
            """
            SELECT COUNT(DISTINCT source_path)
            FROM chunks
            """
        ).fetchone()[0]

        metadata_rows = connection.execute(
            "SELECT key, value FROM metadata"
        ).fetchall()

        metadata = dict(metadata_rows)

        connection.close()

    except sqlite3.Error as error:
        return (
            "Error reading knowledge index: "
            f"{error}"
        )

    indexed_at = metadata.get(
        "indexed_at",
        "unknown",
    )

    indexed_model = metadata.get(
        "embedding_model",
        EMBEDDING_MODEL,
    )

    return (
        "Knowledge base status:\n"
        f"- Source documents: {len(files)}\n"
        f"- Indexed documents: {indexed_documents}\n"
        f"- Indexed chunks: {chunk_count}\n"
        f"- Embedding model: {indexed_model}\n"
        f"- Last indexed: {indexed_at}\n"
        f"- Index path: {INDEX_PATH.relative_to(PROJECT_ROOT)}"
    )


def index_knowledge() -> str:
    """
    Rebuild the local vector index from knowledge/ documents.

    This writes only derived index data inside workspace/.
    It never modifies the source documents in knowledge/.

    Returns:
        Indexing summary or an actionable error.
    """

    files = _knowledge_files()

    if not files:
        return (
            "No knowledge documents were found. "
            "Add .md or .txt files inside knowledge/ before indexing."
        )

    chunk_records = []

    for path in files:
        try:
            text = path.read_text(
                encoding="utf-8"
            )
        except UnicodeDecodeError:
            continue
        except OSError as error:
            return (
                f"Error reading {path.name}: {error}"
            )

        relative_path = str(
            path.relative_to(
                KNOWLEDGE_ROOT
            )
        )

        chunks = _chunk_text(text)

        for chunk_index, content in enumerate(
            chunks,
            start=1,
        ):
            content_hash = hashlib.sha256(
                content.encode("utf-8")
            ).hexdigest()

            chunk_records.append(
                {
                    "source_path": relative_path,
                    "chunk_index": chunk_index,
                    "content": content,
                    "content_hash": content_hash,
                }
            )

    if not chunk_records:
        return (
            "Knowledge documents were found, but no readable "
            "text chunks could be created."
        )

    embeddings = []

    try:
        for start in range(
            0,
            len(chunk_records),
            EMBED_BATCH_SIZE,
        ):
            batch = chunk_records[
                start:start + EMBED_BATCH_SIZE
            ]

            response = embed(
                model=EMBEDDING_MODEL,
                input=[
                    record["content"]
                    for record in batch
                ],
                truncate=True,
            )

            embeddings.extend(
                [
                    list(vector)
                    for vector in response.embeddings
                ]
            )

    except Exception as error:
        return (
            "Error generating embeddings. "
            f"Ensure Ollama is running and '{EMBEDDING_MODEL}' "
            "is installed. "
            f"Details: {error}"
        )

    if len(embeddings) != len(chunk_records):
        return (
            "Error: embedding count did not match the number "
            "of knowledge chunks."
        )

    try:
        connection = _connect()

        with connection:
            connection.execute(
                "DELETE FROM chunks"
            )

            connection.execute(
                "DELETE FROM metadata"
            )

            for record, vector in zip(
                chunk_records,
                embeddings,
            ):
                connection.execute(
                    """
                    INSERT INTO chunks (
                        source_path,
                        chunk_index,
                        content,
                        content_hash,
                        embedding_json,
                        embedding_model
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record["source_path"],
                        record["chunk_index"],
                        record["content"],
                        record["content_hash"],
                        json.dumps(vector),
                        EMBEDDING_MODEL,
                    ),
                )

            indexed_at = datetime.now(
                timezone.utc
            ).isoformat()

            connection.execute(
                """
                INSERT INTO metadata (key, value)
                VALUES (?, ?)
                """,
                (
                    "indexed_at",
                    indexed_at,
                ),
            )

            connection.execute(
                """
                INSERT INTO metadata (key, value)
                VALUES (?, ?)
                """,
                (
                    "embedding_model",
                    EMBEDDING_MODEL,
                ),
            )

        connection.close()

    except sqlite3.Error as error:
        return (
            "Error writing knowledge index: "
            f"{error}"
        )

    return (
        "Knowledge index rebuilt successfully.\n"
        f"- Documents indexed: {len(files)}\n"
        f"- Chunks indexed: {len(chunk_records)}\n"
        f"- Embedding model: {EMBEDDING_MODEL}\n"
        f"- Index: {INDEX_PATH.relative_to(PROJECT_ROOT)}"
    )


def search_knowledge(
    query: str,
    top_k: int = 5,
) -> str:
    """
    Search the local vector knowledge base semantically.

    Args:
        query:
            Natural-language search query.

        top_k:
            Number of relevant chunks to return, from 1 to 10.

    Returns:
        Ranked source excerpts with similarity scores.
    """

    if not query.strip():
        return (
            "Error: Knowledge search query cannot be empty."
        )

    top_k = max(
        1,
        min(int(top_k), MAX_TOP_K),
    )

    if not INDEX_PATH.exists():
        return (
            "Knowledge index has not been built yet. "
            "Run index_knowledge after adding documents to knowledge/."
        )

    try:
        connection = sqlite3.connect(
            INDEX_PATH
        )

        rows = connection.execute(
            """
            SELECT
                source_path,
                chunk_index,
                content,
                embedding_json,
                embedding_model
            FROM chunks
            """
        ).fetchall()

        connection.close()

    except sqlite3.Error as error:
        return (
            "Error reading knowledge index: "
            f"{error}"
        )

    if not rows:
        return (
            "Knowledge index contains no chunks. "
            "Run index_knowledge to rebuild it."
        )

    indexed_models = {
        row[4]
        for row in rows
    }

    if indexed_models != {
        EMBEDDING_MODEL
    }:
        return (
            "Knowledge index uses a different embedding model. "
            "Run index_knowledge to rebuild it."
        )

    try:
        response = embed(
            model=EMBEDDING_MODEL,
            input=query,
            truncate=True,
        )

        query_vector = list(
            response.embeddings[0]
        )

    except Exception as error:
        return (
            "Error embedding the knowledge query. "
            f"Ensure Ollama is running and '{EMBEDDING_MODEL}' "
            "is installed. "
            f"Details: {error}"
        )

    ranked = []

    for (
        source_path,
        chunk_index,
        content,
        embedding_json,
        _,
    ) in rows:
        try:
            vector = json.loads(
                embedding_json
            )
        except json.JSONDecodeError:
            continue

        score = _cosine_similarity(
            query_vector,
            vector,
        )

        ranked.append(
            (
                score,
                source_path,
                chunk_index,
                content,
            )
        )

    ranked.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    selected = ranked[:top_k]

    if not selected:
        return (
            "No searchable knowledge chunks were available."
        )

    output = [
        (
            "Knowledge search results "
            f"for: {query}"
        ),
    ]

    for rank, (
        score,
        source_path,
        chunk_index,
        content,
    ) in enumerate(
        selected,
        start=1,
    ):
        excerpt = content[
            :MAX_RESULT_CHARS
        ]

        if len(content) > MAX_RESULT_CHARS:
            excerpt += "\n[Excerpt truncated]"

        output.append(
            (
                f"\n[{rank}] Source: {source_path} "
                f"| Chunk: {chunk_index} "
                f"| Similarity: {score:.4f}\n"
                f"{excerpt}"
            )
        )

    return "\n".join(output)
