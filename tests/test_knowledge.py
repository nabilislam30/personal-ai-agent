from tools import knowledge_tools


def test_chunk_text_creates_overlapping_chunks():
    text = "A" * 1800

    chunks = knowledge_tools._chunk_text(
        text
    )

    assert len(chunks) >= 2
    assert all(chunks)


def test_list_knowledge_documents(
    monkeypatch,
    tmp_path,
):
    root = tmp_path / "knowledge"
    root.mkdir()

    (root / "README.md").write_text(
        "ignored",
        encoding="utf-8",
    )
    (root / "notes.md").write_text(
        "hello",
        encoding="utf-8",
    )
    (root / "notes.txt").write_text(
        "world",
        encoding="utf-8",
    )
    (root / "binary.bin").write_bytes(
        b"123"
    )

    monkeypatch.setattr(
        knowledge_tools,
        "KNOWLEDGE_ROOT",
        root,
    )

    result = (
        knowledge_tools
        .list_knowledge_documents()
    )

    assert "notes.md" in result
    assert "notes.txt" in result
    assert "README.md" not in result
    assert "binary.bin" not in result


def test_search_knowledge_reports_missing_index(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        knowledge_tools,
        "INDEX_PATH",
        tmp_path / "missing.sqlite3",
    )

    result = knowledge_tools.search_knowledge(
        "terraform"
    )

    assert "has not been built" in result
