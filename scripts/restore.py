import argparse
import shutil
import tarfile
import tempfile
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
    KNOWLEDGE_INDEX_PATH,
    KNOWLEDGE_ROOT,
    SESSION_DB_PATH,
)
from scripts.backup import (  # noqa: E402
    create_backup,
)


ALLOWED_ROOTS = {
    "metadata.json",
    "sessions.sqlite3",
    "knowledge",
}


def _validate_member(
    member: tarfile.TarInfo,
) -> None:
    path = Path(
        member.name
    )

    if path.is_absolute():
        raise ValueError(
            "Backup contains an "
            "absolute path."
        )

    if ".." in path.parts:
        raise ValueError(
            "Backup contains a "
            "path traversal."
        )

    if (
        not path.parts
        or path.parts[0]
        not in ALLOWED_ROOTS
    ):
        raise ValueError(
            "Backup contains an "
            "unexpected path."
        )

    if (
        member.issym()
        or member.islnk()
        or member.isdev()
    ):
        raise ValueError(
            "Backup contains an "
            "unsafe special file."
        )


def _safe_extract(
    archive_path: Path,
    destination: Path,
) -> None:
    with tarfile.open(
        archive_path,
        "r:gz",
    ) as archive:
        members = (
            archive.getmembers()
        )

        for member in members:
            _validate_member(
                member
            )

        for member in members:
            target = (
                destination
                / member.name
            )

            if member.isdir():
                target.mkdir(
                    parents=True,
                    exist_ok=True,
                )
                continue

            if not member.isfile():
                continue

            target.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            source = (
                archive.extractfile(
                    member
                )
            )

            if source is None:
                raise ValueError(
                    "Could not read "
                    "backup member."
                )

            with (
                source,
                target.open(
                    "wb"
                ) as output,
            ):
                shutil.copyfileobj(
                    source,
                    output,
                )


def restore_backup(
    archive_path: Path,
) -> Path:
    archive_path = (
        Path(archive_path)
        .expanduser()
        .resolve()
    )

    if not archive_path.is_file():
        raise FileNotFoundError(
            f"Backup not found: "
            f"{archive_path}"
        )

    safety_backup = (
        create_backup()
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        staging = Path(
            temp_dir
        )

        _safe_extract(
            archive_path,
            staging,
        )

        restored_knowledge = (
            staging
            / "knowledge"
        )

        restored_sessions = (
            staging
            / "sessions.sqlite3"
        )

        if KNOWLEDGE_ROOT.exists():
            shutil.rmtree(
                KNOWLEDGE_ROOT
            )

        if restored_knowledge.exists():
            shutil.copytree(
                restored_knowledge,
                KNOWLEDGE_ROOT,
            )
        else:
            KNOWLEDGE_ROOT.mkdir(
                parents=True,
                exist_ok=True,
            )

        if restored_sessions.exists():
            SESSION_DB_PATH.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            shutil.copy2(
                restored_sessions,
                SESSION_DB_PATH,
            )

        KNOWLEDGE_INDEX_PATH.unlink(
            missing_ok=True
        )

    return safety_backup


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Restore knowledge and "
            "conversation sessions from a backup."
        )
    )

    parser.add_argument(
        "archive",
        type=Path,
        help=(
            "Path to a backup .tar.gz archive."
        ),
    )

    parser.add_argument(
        "--confirm",
        action="store_true",
        help=(
            "Required because restore "
            "replaces current local state."
        ),
    )

    args = parser.parse_args()

    if not args.confirm:
        raise SystemExit(
            "Restore not performed. "
            "Run again with --confirm "
            "after verifying the backup path."
        )

    safety_backup = (
        restore_backup(
            args.archive
        )
    )

    print(
        "Restore completed."
    )
    print(
        "Pre-restore safety backup: "
        f"{safety_backup}"
    )
    print(
        "Rebuild the knowledge index "
        "before using RAG."
    )


if __name__ == "__main__":
    main()
