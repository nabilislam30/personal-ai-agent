import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent

WORKSPACE_ROOT = Path(
    os.getenv(
        "PAI_WORKSPACE_ROOT",
        str(PROJECT_ROOT / "workspace"),
    )
).expanduser().resolve()

KNOWLEDGE_ROOT = Path(
    os.getenv(
        "PAI_KNOWLEDGE_ROOT",
        str(PROJECT_ROOT / "knowledge"),
    )
).expanduser().resolve()

CHAT_MODEL = os.getenv(
    "PAI_CHAT_MODEL",
    "qwen3:8b",
)
EMBEDDING_MODEL = os.getenv(
    "PAI_EMBEDDING_MODEL",
    "embeddinggemma:300m-qat-q4_0",
)
OLLAMA_KEEP_ALIVE = os.getenv(
    "PAI_OLLAMA_KEEP_ALIVE",
    "30m",
)

APP_ENV = os.getenv(
    "PAI_ENV",
    "development",
).strip().lower()

PRODUCTION_MODE = (
    APP_ENV == "production"
)

WEB_HOST = os.getenv(
    "PAI_WEB_HOST",
    "127.0.0.1",
)

WEB_REQUIRE_AUTH = (
    os.getenv(
        "PAI_REQUIRE_AUTH",
        "false",
    ).strip().lower()
    in {
        "1",
        "true",
        "yes",
        "on",
    }
)

WEB_PASSWORD_HASH = os.getenv(
    "PAI_PASSWORD_HASH",
    "",
).strip()

WEB_SECRET_KEY = os.getenv(
    "PAI_SECRET_KEY",
    "",
).strip()

WEB_COOKIE_SECURE = (
    os.getenv(
        "PAI_COOKIE_SECURE",
        "false",
    ).strip().lower()
    in {
        "1",
        "true",
        "yes",
        "on",
    }
)


def _env_int(
    name: str,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    raw_value = os.getenv(
        name,
        str(default),
    )

    try:
        value = int(raw_value)
    except ValueError:
        value = default

    return max(
        minimum,
        min(value, maximum),
    )


def _env_bool(
    name: str,
    default: bool,
) -> bool:
    raw_value = os.getenv(
        name,
        "true" if default else "false",
    ).strip().lower()

    return raw_value in {
        "1",
        "true",
        "yes",
        "on",
    }


MAX_TOOL_ROUNDS = _env_int(
    "PAI_MAX_TOOL_ROUNDS",
    8,
    1,
    20,
)

SIMPLE_CHAT_HISTORY_LIMIT = _env_int(
    "PAI_SIMPLE_CHAT_HISTORY_LIMIT",
    12,
    4,
    60,
)

TOOL_HISTORY_LIMIT = _env_int(
    "PAI_TOOL_HISTORY_LIMIT",
    24,
    8,
    100,
)

SESSION_SUMMARY_MAX_CHARS = _env_int(
    "PAI_SESSION_SUMMARY_MAX_CHARS",
    6000,
    1000,
    20000,
)

PRELOAD_MODEL = _env_bool(
    "PAI_PRELOAD_MODEL",
    True,
)

SHOW_TIMINGS = _env_bool(
    "PAI_SHOW_TIMINGS",
    True,
)

KNOWLEDGE_CHUNK_SIZE = _env_int(
    "PAI_KNOWLEDGE_CHUNK_SIZE",
    1400,
    400,
    8000,
)

KNOWLEDGE_CHUNK_OVERLAP = _env_int(
    "PAI_KNOWLEDGE_CHUNK_OVERLAP",
    200,
    0,
    2000,
)

KNOWLEDGE_EMBED_BATCH_SIZE = _env_int(
    "PAI_KNOWLEDGE_EMBED_BATCH_SIZE",
    24,
    1,
    128,
)

KNOWLEDGE_MAX_TOP_K = _env_int(
    "PAI_KNOWLEDGE_MAX_TOP_K",
    10,
    1,
    30,
)

KNOWLEDGE_MAX_RESULT_CHARS = _env_int(
    "PAI_KNOWLEDGE_MAX_RESULT_CHARS",
    2200,
    500,
    12000,
)

KNOWLEDGE_MAX_FILE_BYTES = _env_int(
    "PAI_KNOWLEDGE_MAX_FILE_BYTES",
    25_000_000,
    1_000_000,
    100_000_000,
)

WEB_PORT = _env_int(
    "PAI_WEB_PORT",
    8000,
    1024,
    65535,
)

WEB_MAX_UPLOAD_BYTES = _env_int(
    "PAI_WEB_MAX_UPLOAD_BYTES",
    25_000_000,
    1_000_000,
    100_000_000,
)

WEB_CHAT_RATE_LIMIT = _env_int(
    "PAI_CHAT_RATE_LIMIT_PER_MINUTE",
    30,
    1,
    300,
)

WEB_LOGIN_RATE_LIMIT = _env_int(
    "PAI_LOGIN_RATE_LIMIT_PER_MINUTE",
    10,
    1,
    100,
)

SESSION_DB_PATH = (
    WORKSPACE_ROOT
    / "sessions.sqlite3"
)

KNOWLEDGE_INDEX_PATH = (
    WORKSPACE_ROOT
    / "knowledge_index.sqlite3"
)
