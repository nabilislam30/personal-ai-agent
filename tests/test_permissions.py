from permissions import (
    describe_write_request,
    request_write_approval,
    requires_write_approval,
)


def test_write_tools_require_approval():
    assert requires_write_approval("save_document")
    assert requires_write_approval("index_knowledge")
    assert not requires_write_approval("read_file")


def test_request_write_approval_accepts_yes():
    approved = request_write_approval(
        "save_document",
        {"file_path": "report.md"},
        input_fn=lambda _: "yes",
    )

    assert approved is True


def test_request_write_approval_defaults_to_no():
    approved = request_write_approval(
        "save_document",
        {"file_path": "report.md"},
        input_fn=lambda _: "",
    )

    assert approved is False


def test_write_request_description_is_specific():
    assert (
        describe_write_request(
            "save_document",
            {"file_path": "report.md"},
        )
        == "Save document: report.md"
    )
