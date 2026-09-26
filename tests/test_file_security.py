from tools import file_tools


def test_read_file_blocks_parent_escape(
    monkeypatch,
    tmp_path,
):
    project = tmp_path / "project"
    project.mkdir()

    outside = tmp_path / "outside.txt"
    outside.write_text(
        "secret",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        file_tools,
        "PROJECT_ROOT",
        project,
    )

    result = file_tools.read_file(
        "../outside.txt"
    )

    assert (
        "outside the project directory"
        in result
    )


def test_read_file_reads_project_file(
    monkeypatch,
    tmp_path,
):
    project = tmp_path / "project"
    project.mkdir()

    inside = project / "inside.txt"
    inside.write_text(
        "allowed",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        file_tools,
        "PROJECT_ROOT",
        project,
    )

    assert (
        file_tools.read_file("inside.txt")
        == "allowed"
    )
