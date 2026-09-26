import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from config import (
    SESSION_DB_PATH,
    SESSION_SUMMARY_MAX_CHARS,
)


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
        self.db_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.db_path
        )
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
                    updated_at TEXT NOT NULL,
                    summary TEXT NOT NULL DEFAULT '',
                    summary_through_id INTEGER NOT NULL DEFAULT 0
                )
                """
            )

            columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(sessions)"
                ).fetchall()
            }

            if "summary" not in columns:
                connection.execute(
                    """
                    ALTER TABLE sessions
                    ADD COLUMN summary TEXT NOT NULL DEFAULT ''
                    """
                )

            if "summary_through_id" not in columns:
                connection.execute(
                    """
                    ALTER TABLE sessions
                    ADD COLUMN summary_through_id
                    INTEGER NOT NULL DEFAULT 0
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
                CREATE INDEX IF NOT EXISTS
                idx_messages_session_id
                ON messages(session_id, id)
                """
            )

    @staticmethod
    def _now() -> str:
        return datetime.now(
            timezone.utc
        ).isoformat()

    def create_session(
        self,
        title: str = "New session",
    ) -> Session:
        session_id = str(
            uuid.uuid4()
        )
        now = self._now()

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO sessions (
                    id,
                    title,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    session_id,
                    title,
                    now,
                    now,
                ),
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
                SELECT
                    id,
                    title,
                    created_at,
                    updated_at
                FROM sessions
                WHERE id = ?
                """,
                (
                    session_id,
                ),
            ).fetchone()

        if row is None:
            return None

        return Session(
            id=row["id"],
            title=row["title"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def latest_session(
        self,
    ) -> Session | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    id,
                    title,
                    created_at,
                    updated_at
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

    def get_or_create_latest_session(
        self,
    ) -> Session:
        return (
            self.latest_session()
            or self.create_session()
        )

    def list_sessions(
        self,
        limit: int = 20,
    ) -> list[Session]:
        limit = max(
            1,
            min(int(limit), 100),
        )

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    title,
                    created_at,
                    updated_at
                FROM sessions
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (
                    limit,
                ),
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
        if role not in {
            "user",
            "assistant",
        }:
            raise ValueError(
                "Only user and assistant messages may be persisted."
            )

        if self.get_session(
            session_id
        ) is None:
            raise ValueError(
                f"Unknown session: {session_id}"
            )

        now = self._now()

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO messages (
                    session_id,
                    role,
                    content,
                    created_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    session_id,
                    role,
                    content,
                    now,
                ),
            )

            connection.execute(
                """
                UPDATE sessions
                SET updated_at = ?
                WHERE id = ?
                """,
                (
                    now,
                    session_id,
                ),
            )

    def load_messages(
        self,
        session_id: str,
        limit: int = 100,
    ) -> list[dict[str, str]]:
        limit = max(
            1,
            min(int(limit), 500),
        )

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
                (
                    session_id,
                    limit,
                ),
            ).fetchall()

        return [
            {
                "role": row["role"],
                "content": row["content"],
            }
            for row in rows
        ]

    @staticmethod
    def _normalise_summary_text(
        content: str,
        limit: int = 420,
    ) -> str:
        compact = " ".join(
            content.split()
        ).strip()

        if len(compact) <= limit:
            return compact

        return (
            compact[:limit]
            + "…"
        )

    @staticmethod
    def _trim_summary(
        summary: str,
        max_chars: int,
    ) -> str:
        if len(summary) <= max_chars:
            return summary

        head_size = min(
            1200,
            max_chars // 3,
        )
        tail_size = (
            max_chars
            - head_size
            - 38
        )

        return (
            summary[:head_size]
            + "\n\n[Older summary compressed]\n\n"
            + summary[-tail_size:]
        )

    def _refresh_summary(
        self,
        session_id: str,
        recent_limit: int,
    ) -> str:
        """
        Deterministically compact older messages.

        This avoids an extra model call while keeping older context bounded.
        Full messages remain stored in SQLite for the UI/history.
        """

        recent_limit = max(
            1,
            min(int(recent_limit), 100),
        )

        with self._connect() as connection:
            session_row = connection.execute(
                """
                SELECT
                    summary,
                    summary_through_id
                FROM sessions
                WHERE id = ?
                """,
                (
                    session_id,
                ),
            ).fetchone()

            if session_row is None:
                return ""

            boundary_row = connection.execute(
                """
                SELECT MIN(id) AS first_recent_id
                FROM (
                    SELECT id
                    FROM messages
                    WHERE session_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                )
                """,
                (
                    session_id,
                    recent_limit,
                ),
            ).fetchone()

            first_recent_id = (
                boundary_row["first_recent_id"]
                if boundary_row is not None
                else None
            )

            if first_recent_id is None:
                return session_row["summary"]

            boundary_id = (
                first_recent_id
                - 1
            )

            summary_through_id = int(
                session_row[
                    "summary_through_id"
                ]
            )

            if (
                boundary_id
                <= summary_through_id
            ):
                return session_row["summary"]

            rows = connection.execute(
                """
                SELECT id, role, content
                FROM messages
                WHERE
                    session_id = ?
                    AND id > ?
                    AND id <= ?
                ORDER BY id ASC
                """,
                (
                    session_id,
                    summary_through_id,
                    boundary_id,
                ),
            ).fetchall()

            if not rows:
                return session_row["summary"]

            additions = []

            for row in rows:
                label = (
                    "User"
                    if row["role"] == "user"
                    else "Assistant"
                )

                compact = (
                    self._normalise_summary_text(
                        row["content"]
                    )
                )

                if compact:
                    additions.append(
                        f"{label}: {compact}"
                    )

            existing = (
                session_row["summary"]
                or ""
            ).strip()

            combined = "\n".join(
                part
                for part in [
                    existing,
                    *additions,
                ]
                if part
            )

            combined = self._trim_summary(
                combined,
                SESSION_SUMMARY_MAX_CHARS,
            )

            newest_id = rows[-1]["id"]

            connection.execute(
                """
                UPDATE sessions
                SET
                    summary = ?,
                    summary_through_id = ?
                WHERE id = ?
                """,
                (
                    combined,
                    newest_id,
                    session_id,
                ),
            )

            return combined

    def load_context_messages(
        self,
        session_id: str,
        recent_limit: int,
    ) -> list[dict[str, str]]:
        """
        Return bounded model context with a compact summary of older turns.
        """

        summary = self._refresh_summary(
            session_id,
            recent_limit,
        )

        recent = self.load_messages(
            session_id,
            limit=recent_limit,
        )

        if not summary:
            return recent

        return [
            {
                "role": "system",
                "content": (
                    "Earlier conversation summary "
                    "(compressed locally; not external evidence):\n"
                    + summary
                ),
            },
            *recent,
        ]

    def update_title_from_prompt(
        self,
        session_id: str,
        prompt: str,
    ) -> None:
        session = self.get_session(
            session_id
        )

        if (
            session is None
            or session.title != "New session"
        ):
            return

        compact = " ".join(
            prompt.split()
        ).strip()

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
                SET
                    title = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    title,
                    now,
                    session_id,
                ),
            )
