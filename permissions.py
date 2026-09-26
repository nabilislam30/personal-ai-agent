from collections.abc import Callable


WRITE_TOOLS = {
    "save_document",
    "index_knowledge",
}


def requires_write_approval(tool_name: str) -> bool:
    """Return whether a tool requires explicit human approval."""

    return tool_name in WRITE_TOOLS


def describe_write_request(
    tool_name: str,
    tool_arguments: dict,
) -> str:
    """Return a concise description of a write request."""

    if tool_name == "save_document":
        file_path = tool_arguments.get("file_path", "unknown file")
        return f"Save document: {file_path}"

    if tool_name == "index_knowledge":
        return "Rebuild local knowledge index"

    return f"Run write tool: {tool_name}"


def request_write_approval(
    tool_name: str,
    tool_arguments: dict,
    input_fn: Callable[[str], str] = input,
) -> bool:
    """Request explicit approval before a write tool runs."""

    print(
        f"\n[Write Request] "
        f"{describe_write_request(tool_name, tool_arguments)}"
    )

    approval = input_fn(
        "Approve this write? [y/N]: "
    ).strip().lower()

    return approval in {"y", "yes"}
