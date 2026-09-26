from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MAX_LINES = 1000


def read_log_tail(
    file_path: str,
    lines: int = 200,
) -> str:
    """
    Read the last section of a text log file.

    Args:
        file_path: Project-relative log file path.
        lines: Number of lines to return, from 1 to 1000.

    Returns:
        Tail of the requested log file.
    """

    requested_path = (
        PROJECT_ROOT / file_path
    ).resolve()

    try:
        requested_path.relative_to(PROJECT_ROOT)
    except ValueError:
        return (
            "Error: Access outside the project "
            "directory is not allowed."
        )

    if not requested_path.exists():
        return f"Error: File does not exist: {file_path}"

    if not requested_path.is_file():
        return f"Error: Path is not a file: {file_path}"

    lines = max(1, min(int(lines), MAX_LINES))

    try:
        content = requested_path.read_text(
            encoding="utf-8"
        )
    except UnicodeDecodeError:
        return "Error: Log file is not valid UTF-8 text."
    except OSError as error:
        return f"Error reading log file: {error}"

    file_lines = content.splitlines()

    selected = file_lines[-lines:]

    return "\n".join(selected)