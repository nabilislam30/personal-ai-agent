import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from config import SESSION_DB_PATH


@dataclass(frozen=True)
class Session:
    id: str
    title: str
    created_at: str
    updated_at: str


class SessionStore:
    """Local SQLite-backed persistent conversation history."""

    def __init__(
        self,
        db_path: Path = SESSION_DB_PATH,
    ) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id)
                        REFERENCES sessions(id)
                        ON DELETE CASCADE
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_messages_session_id
                ON messages(session_id, id)
                """
            )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def create_session(
        self,
        title: str = "New session",
    ) -> Session:
        session_id = str(uuid.uuid4())
        now = self._now()

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO sessions (
                    id, title, created_at, updated_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (session_id, title, now, now),
            )

        return Session(
            id=session_id,
            title=title,
            created_at=now,
            updated_at=now,
        )

    def get_session(
        self,
        session_id: str,
    ) -> Session | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, title, created_at, updated_at
                FROM sessions
                WHERE id = ?
                """,
                (session_id,),
            ).fetchone()

        if row is None:
            return None

        return Session(
            id=row["id"],
            title=row["title"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def latest_session(self) -> Session | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, title, created_at, updated_at
                FROM sessions
                ORDER BY updated_at DESC
                LIMIT 1
                """
            ).fetchone()

        if row is None:
            return None

        return Session(
            id=row["id"],
            title=row["title"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def get_or_create_latest_session(self) -> Session:
        return self.latest_session() or self.create_session()

    def list_sessions(
        self,
        limit: int = 20,
    ) -> list[Session]:
        limit = max(1, min(int(limit), 100))

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, title, created_at, updated_at
                FROM sessions
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [
            Session(
                id=row["id"],
                title=row["title"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
    ) -> None:
        if role not in {"user", "assistant"}:
            raise ValueError(
                "Only user and assistant messages may be persisted."
            )

        if self.get_session(session_id) is None:
            raise ValueError(f"Unknown session: {session_id}")

        now = self._now()

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO messages (
                    session_id, role, content, created_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (session_id, role, content, now),
            )
            connection.execute(
                """
                UPDATE sessions
                SET updated_at = ?
                WHERE id = ?
                """,
                (now, session_id),
            )

    def load_messages(
        self,
        session_id: str,
        limit: int = 100,
    ) -> list[dict[str, str]]:
        limit = max(1, min(int(limit), 500))

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT role, content
                FROM (
                    SELECT id, role, content
                    FROM messages
                    WHERE session_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                )
                ORDER BY id ASC
                """,
                (session_id, limit),
            ).fetchall()

        return [
            {
                "role": row["role"],
                "content": row["content"],
            }
            for row in rows
        ]

    def update_title_from_prompt(
        self,
        session_id: str,
        prompt: str,
    ) -> None:
        session = self.get_session(session_id)

        if session is None or session.title != "New session":
            return

        compact = " ".join(prompt.split()).strip()

        if not compact:
            return

        title = compact[:60]

        if len(compact) > 60:
            title += "…"

        now = self._now()

        with self._connect() as connection:
            connection.execute(
                """
                UPDATE sessions
                SET title = ?, updated_at = ?
                WHERE id = ?
                """,
                (title, now, session_id),
            )
