import sqlite3
import tarfile

from scripts import backup
from scripts import restore


def test_backup_contains_knowledge_and_sessions(
    monkeypatch,
    tmp_path,
):
    knowledge = (
        tmp_path
        / "knowledge"
    )
    knowledge.mkdir()

    (
        knowledge
        / "notes.txt"
    ).write_text(
        "important notes",
        encoding="utf-8",
    )

    session_db = (
        tmp_path
        / "sessions.sqlite3"
    )

    connection = sqlite3.connect(
        session_db
    )
    connection.execute(
        "CREATE TABLE test (value TEXT)"
    )
    connection.execute(
        "INSERT INTO test VALUES ('ok')"
    )
    connection.commit()
    connection.close()

    monkeypatch.setattr(
        backup,
        "KNOWLEDGE_ROOT",
        knowledge,
    )
    monkeypatch.setattr(
        backup,
        "SESSION_DB_PATH",
        session_db,
    )

    archive = (
        backup.create_backup(
            backup_root=(
                tmp_path
                / "backups"
            ),
            keep=2,
        )
    )

    assert archive.exists()

    with tarfile.open(
        archive,
        "r:gz",
    ) as tar:
        names = {
            member.name
            for member in (
                tar.getmembers()
            )
        }

    assert (
        "knowledge/notes.txt"
        in names
    )
    assert (
        "sessions.sqlite3"
        in names
    )
    assert (
        "metadata.json"
        in names
    )


def test_restore_rejects_path_traversal():
    malicious = tarfile.TarInfo(
        "../outside.txt"
    )

    try:
        restore._validate_member(
            malicious
        )
    except ValueError as error:
        assert (
            "path traversal"
            in str(error)
        )
    else:
        raise AssertionError(
            "Unsafe archive member "
            "was not rejected."
        )


def test_restore_rejects_symlink():
    member = tarfile.TarInfo(
        "knowledge/link"
    )
    member.type = tarfile.SYMTYPE
    member.linkname = (
        "/tmp/target"
    )

    try:
        restore._validate_member(
            member
        )
    except ValueError as error:
        assert (
            "unsafe special file"
            in str(error)
        )
    else:
        raise AssertionError(
            "Symlink member "
            "was not rejected."
        )
