from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def read_file(file_path: str) -> str:
    """
    Read a text file located inside the project directory.

    The tool is read-only and prevents access to files outside
    the personal-ai-agent project.
    """

    requested_path = (PROJECT_ROOT / file_path).resolve()

    try:
        requested_path.relative_to(PROJECT_ROOT)
    except ValueError:
        return "Error: Access outside the project directory is not allowed."

    if not requested_path.exists():
        return f"Error: File does not exist: {file_path}"

    if not requested_path.is_file():
        return f"Error: Path is not a file: {file_path}"

    try:
        return requested_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"Error: File is not a supported UTF-8 text file: {file_path}"
    except OSError as error:
        return f"Error reading file: {error}"