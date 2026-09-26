import argparse
import json
import shutil
import sqlite3
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import sys


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

sys.path.insert(
    0,
    str(PROJECT_ROOT),
)

from config import (  # noqa: E402
    KNOWLEDGE_ROOT,
    SESSION_DB_PATH,
)


DEFAULT_BACKUP_ROOT = (
    PROJECT_ROOT
    / "backups"
)


def _copy_knowledge(
    source: Path,
    destination: Path,
) -> None:
    destination.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not source.exists():
        return

    for path in source.rglob(
        "*"
    ):
        if path.is_symlink():
            continue

        relative = path.relative_to(
            source
        )
        target = (
            destination
            / relative
        )

        if path.is_dir():
            target.mkdir(
                parents=True,
                exist_ok=True,
            )
            continue

        if not path.is_file():
            continue

        target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.copy2(
            path,
            target,
        )


def _backup_sessions(
    destination: Path,
) -> bool:
    if not SESSION_DB_PATH.exists():
        return False

    source = sqlite3.connect(
        SESSION_DB_PATH
    )
    target = sqlite3.connect(
        destination
    )

    try:
        source.backup(
            target
        )
    finally:
        target.close()
        source.close()

    return True


def _read_version() -> str:
    version_file = (
        PROJECT_ROOT
        / "VERSION"
    )

    if not version_file.exists():
        return "unknown"

    return (
        version_file
        .read_text(
            encoding="utf-8"
        )
        .strip()
    )


def _enforce_retention(
    backup_root: Path,
    keep: int,
) -> None:
    backups = sorted(
        backup_root.glob(
            "personal-ai-agent-*.tar.gz"
        ),
        key=lambda item: (
            item.stat().st_mtime
        ),
        reverse=True,
    )

    for old_backup in backups[
        keep:
    ]:
        old_backup.unlink(
            missing_ok=True
        )


def create_backup(
    backup_root: Path = DEFAULT_BACKUP_ROOT,
    keep: int = 7,
) -> Path:
    backup_root = (
        Path(backup_root)
        .expanduser()
        .resolve()
    )

    backup_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = (
        datetime.now(
            timezone.utc
        )
        .strftime(
            "%Y%m%dT%H%M%SZ"
        )
    )

    archive_path = (
        backup_root
        / (
            "personal-ai-agent-"
            f"{timestamp}.tar.gz"
        )
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        staging = Path(
            temp_dir
        )

        knowledge_copy = (
            staging
            / "knowledge"
        )

        _copy_knowledge(
            KNOWLEDGE_ROOT,
            knowledge_copy,
        )

        session_copy = (
            staging
            / "sessions.sqlite3"
        )

        session_included = (
            _backup_sessions(
                session_copy
            )
        )

        metadata = {
            "created_at": (
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),
            "version": (
                _read_version()
            ),
            "session_database_included": (
                session_included
            ),
            "knowledge_included": True,
        }

        (
            staging
            / "metadata.json"
        ).write_text(
            json.dumps(
                metadata,
                indent=2,
            ),
            encoding="utf-8",
        )

        with tarfile.open(
            archive_path,
            "w:gz",
        ) as archive:
            archive.add(
                staging
                / "metadata.json",
                arcname=(
                    "metadata.json"
                ),
            )

            archive.add(
                knowledge_copy,
                arcname="knowledge",
            )

            if session_included:
                archive.add(
                    session_copy,
                    arcname=(
                        "sessions.sqlite3"
                    ),
                )

    _enforce_retention(
        backup_root,
        max(
            1,
            int(keep),
        ),
    )

    return archive_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Create a local backup of "
            "knowledge files and conversation sessions."
        )
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_BACKUP_ROOT,
        help=(
            "Backup directory. "
            "Default: ./backups"
        ),
    )

    parser.add_argument(
        "--keep",
        type=int,
        default=7,
        help=(
            "Number of newest backups "
            "to retain."
        ),
    )

    args = parser.parse_args()

    archive = create_backup(
        backup_root=args.output,
        keep=args.keep,
    )

    print(
        f"Backup created: "
        f"{archive}"
    )


if __name__ == "__main__":
    main()
