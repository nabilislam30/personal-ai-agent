from pathlib import Path
import subprocess


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MAX_OUTPUT = 20_000


def _resolve_directory(directory: str) -> Path:
    path = (PROJECT_ROOT / directory).resolve()

    try:
        path.relative_to(PROJECT_ROOT)
    except ValueError as error:
        raise ValueError(
            "Access outside the project directory is not allowed."
        ) from error

    if not path.exists():
        raise ValueError(
            f"Directory does not exist: {directory}"
        )

    if not path.is_dir():
        raise ValueError(
            f"Path is not a directory: {directory}"
        )

    return path


def _run_git(arguments: list[str], directory: str) -> str:
    try:
        working_directory = _resolve_directory(directory)
    except ValueError as error:
        return f"Error: {error}"

    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=working_directory,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except FileNotFoundError:
        return "Error: Git is not installed or is not available in PATH."
    except subprocess.TimeoutExpired:
        return "Error: Git command timed out."

    output = result.stdout.strip()

    if result.stderr.strip():
        output += f"\n{result.stderr.strip()}"

    if not output:
        output = "(No output)"

    if len(output) > MAX_OUTPUT:
        output = output[:MAX_OUTPUT] + "\n[Output truncated]"

    return output


def git_status(directory: str = ".") -> str:
    """
    Show Git repository status without changing anything.

    Args:
        directory: Project-relative repository directory.

    Returns:
        Git status output.
    """

    return _run_git(
        ["status", "--short", "--branch"],
        directory,
    )


def git_diff(directory: str = ".", staged: bool = False) -> str:
    """
    Show Git changes without modifying the repository.

    Args:
        directory: Project-relative repository directory.
        staged: Show staged changes when true.

    Returns:
        Git diff output.
    """

    arguments = ["diff"]

    if staged:
        arguments.append("--staged")

    return _run_git(arguments, directory)


def git_log(directory: str = ".", max_entries: int = 10) -> str:
    """
    Show recent Git commit history.

    Args:
        directory: Project-relative repository directory.
        max_entries: Maximum number of commits, from 1 to 30.

    Returns:
        Recent Git history.
    """

    max_entries = max(1, min(int(max_entries), 30))

    return _run_git(
        [
            "log",
            f"-{max_entries}",
            "--date=short",
            "--pretty=format:%h | %ad | %an | %s",
        ],
        directory,
    )