from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = PROJECT_ROOT / "workspace"

ALLOWED_EXTENSIONS = {
    ".md",
    ".txt",
}


def save_document(file_path: str, content: str) -> str:
    """
    Save a new text document inside the workspace directory.

    Rules:
    - Files can only be written inside workspace/.
    - Only .md and .txt files are allowed.
    - Existing files cannot be overwritten.
    """

    clean_path = Path(file_path)

    # Allow either:
    # agent-capabilities.md
    # workspace/agent-capabilities.md
    if clean_path.parts and clean_path.parts[0] == "workspace":
        clean_path = Path(*clean_path.parts[1:])

    requested_path = (WORKSPACE_ROOT / clean_path).resolve()

    try:
        requested_path.relative_to(WORKSPACE_ROOT)
    except ValueError:
        return "Error: Writing outside the workspace directory is not allowed."

    if requested_path.suffix.lower() not in ALLOWED_EXTENSIONS:
        return (
            "Error: Unsupported file type. "
            "Only .md and .txt files are allowed."
        )

    if requested_path.exists():
        return (
            f"Error: File already exists: {clean_path}. "
            "Overwriting is not allowed."
        )

    try:
        requested_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        requested_path.write_text(
            content,
            encoding="utf-8",
        )

        relative_path = requested_path.relative_to(PROJECT_ROOT)

        return f"Document saved successfully: {relative_path}"

    except OSError as error:
        return f"Error saving document: {error}"