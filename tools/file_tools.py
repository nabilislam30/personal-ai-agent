from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

EXCLUDED_DIRECTORIES = {
    ".git",
    ".venv",
    "__pycache__",
}

MAX_SEARCH_RESULTS = 50
MAX_SEARCH_FILE_SIZE = 1_000_000


def _resolve_project_path(path: str) -> Path:
    """
    Resolve a path and ensure it stays inside the project directory.
    """

    requested_path = (PROJECT_ROOT / path).resolve()

    try:
        requested_path.relative_to(PROJECT_ROOT)
    except ValueError as error:
        raise ValueError(
            "Access outside the project directory is not allowed."
        ) from error

    return requested_path


def read_file(file_path: str) -> str:
    """
    Read a UTF-8 text file inside the project directory.

    This tool is read-only and cannot access files outside
    the personal-ai-agent project.
    """

    try:
        requested_path = _resolve_project_path(file_path)
    except ValueError as error:
        return f"Error: {error}"

    if not requested_path.exists():
        return f"Error: File does not exist: {file_path}"

    if not requested_path.is_file():
        return f"Error: Path is not a file: {file_path}"

    try:
        return requested_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return (
            f"Error: File is not a supported UTF-8 text file: "
            f"{file_path}"
        )
    except OSError as error:
        return f"Error reading file: {error}"


def list_directory(directory: str = ".") -> str:
    """
    List files and directories inside a project directory.

    This tool is read-only and cannot access directories outside
    the personal-ai-agent project.
    """

    try:
        requested_path = _resolve_project_path(directory)
    except ValueError as error:
        return f"Error: {error}"

    if not requested_path.exists():
        return f"Error: Directory does not exist: {directory}"

    if not requested_path.is_dir():
        return f"Error: Path is not a directory: {directory}"

    try:
        entries = []

        for entry in sorted(
            requested_path.iterdir(),
            key=lambda item: item.name.lower(),
        ):
            if entry.name in EXCLUDED_DIRECTORIES:
                continue

            relative_path = entry.relative_to(PROJECT_ROOT)

            if entry.is_dir():
                entries.append(f"[DIR]  {relative_path}")
            else:
                entries.append(f"[FILE] {relative_path}")

        if not entries:
            return "Directory is empty."

        return "\n".join(entries)

    except OSError as error:
        return f"Error listing directory: {error}"


def search_files(search_term: str, directory: str = ".") -> str:
    """
    Search text files inside the project for a string.

    Returns matching file paths, line numbers, and matching lines.

    This tool is read-only and cannot search outside
    the personal-ai-agent project.
    """

    if not search_term.strip():
        return "Error: Search term cannot be empty."

    try:
        requested_path = _resolve_project_path(directory)
    except ValueError as error:
        return f"Error: {error}"

    if not requested_path.exists():
        return f"Error: Directory does not exist: {directory}"

    if not requested_path.is_dir():
        return f"Error: Path is not a directory: {directory}"

    matches = []

    try:
        for file_path in requested_path.rglob("*"):
            if not file_path.is_file():
                continue

            relative_parts = file_path.relative_to(PROJECT_ROOT).parts

            if any(
                part in EXCLUDED_DIRECTORIES
                for part in relative_parts
            ):
                continue

            try:
                if file_path.stat().st_size > MAX_SEARCH_FILE_SIZE:
                    continue

                contents = file_path.read_text(encoding="utf-8")

            except (UnicodeDecodeError, OSError):
                continue

            for line_number, line in enumerate(
                contents.splitlines(),
                start=1,
            ):
                if search_term.lower() in line.lower():
                    relative_path = file_path.relative_to(PROJECT_ROOT)

                    matches.append(
                        f"{relative_path}:{line_number}: {line.strip()}"
                    )

                    if len(matches) >= MAX_SEARCH_RESULTS:
                        matches.append(
                            "Search result limit reached."
                        )
                        return "\n".join(matches)

        if not matches:
            return (
                f"No matches found for '{search_term}' "
                f"in '{directory}'."
            )

        return "\n".join(matches)

    except OSError as error:
        return f"Error searching files: {error}"