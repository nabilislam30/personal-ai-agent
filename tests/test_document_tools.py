from tools import document_tools


def _isolate_workspace(
    monkeypatch,
    tmp_path,
):
    workspace = tmp_path / "workspace"

    monkeypatch.setattr(
        document_tools,
        "PROJECT_ROOT",
        tmp_path,
    )
    monkeypatch.setattr(
        document_tools,
        "WORKSPACE_ROOT",
        workspace,
    )

    return workspace


def test_save_document_writes_inside_workspace(
    monkeypatch,
    tmp_path,
):
    workspace = _isolate_workspace(
        monkeypatch,
        tmp_path,
    )

    result = document_tools.save_document(
        "report.md",
        "# Report",
    )

    assert (
        result
        == "Document saved successfully: workspace/report.md"
    )
    assert (
        workspace / "report.md"
    ).read_text(
        encoding="utf-8"
    ) == "# Report"


def test_save_document_blocks_path_escape(
    monkeypatch,
    tmp_path,
):
    _isolate_workspace(
        monkeypatch,
        tmp_path,
    )

    result = document_tools.save_document(
        "../escape.md",
        "blocked",
    )

    assert (
        "outside the workspace"
        in result
    )


def test_save_document_blocks_overwrite(
    monkeypatch,
    tmp_path,
):
    _isolate_workspace(
        monkeypatch,
        tmp_path,
    )

    first = document_tools.save_document(
        "report.md",
        "first",
    )
    second = document_tools.save_document(
        "report.md",
        "second",
    )

    assert "saved successfully" in first
    assert "Overwriting is not allowed" in second


def test_save_document_blocks_unsupported_extension(
    monkeypatch,
    tmp_path,
):
    _isolate_workspace(
        monkeypatch,
        tmp_path,
    )

    result = document_tools.save_document(
        "script.py",
        "print('no')",
    )

    assert "Unsupported file type" in result
