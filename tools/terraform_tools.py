from pathlib import Path
import shutil
import subprocess


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MAX_OUTPUT = 25_000


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


def _run_terraform(
    arguments: list[str],
    directory: str,
) -> str:
    if shutil.which("terraform") is None:
        return (
            "Error: Terraform is not installed "
            "or is not available in PATH."
        )

    try:
        working_directory = _resolve_directory(directory)
    except ValueError as error:
        return f"Error: {error}"

    try:
        result = subprocess.run(
            ["terraform", *arguments],
            cwd=working_directory,
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return "Error: Terraform command timed out."

    output = result.stdout.strip()

    if result.stderr.strip():
        output += f"\n{result.stderr.strip()}"

    if not output:
        output = "(No output)"

    if len(output) > MAX_OUTPUT:
        output = output[:MAX_OUTPUT] + "\n[Output truncated]"

    return (
        f"Exit code: {result.returncode}\n"
        f"{output}"
    )


def terraform_version() -> str:
    """
    Show the installed Terraform version.

    Returns:
        Terraform version information.
    """

    return _run_terraform(
        ["version"],
        ".",
    )


def terraform_validate(directory: str = ".") -> str:
    """
    Validate Terraform configuration without applying infrastructure.

    Args:
        directory: Project-relative Terraform directory.

    Returns:
        Terraform validation output.
    """

    return _run_terraform(
        ["validate", "-no-color"],
        directory,
    )


def terraform_fmt_check(directory: str = ".") -> str:
    """
    Check Terraform formatting without rewriting files.

    Args:
        directory: Project-relative Terraform directory.

    Returns:
        Formatting check output.
    """

    return _run_terraform(
        [
            "fmt",
            "-check",
            "-recursive",
            "-diff",
        ],
        directory,
    )


def terraform_show(
    file_path: str,
    directory: str = ".",
) -> str:
    """
    Inspect an existing Terraform plan or state file.

    Args:
        file_path: Project-relative plan or state file.
        directory: Project-relative Terraform directory.

    Returns:
        Terraform show output.

    Note:
        Terraform state and plan files may contain sensitive information.
    """

    try:
        working_directory = _resolve_directory(directory)
    except ValueError as error:
        return f"Error: {error}"

    requested_file = (
        working_directory / file_path
    ).resolve()

    try:
        requested_file.relative_to(PROJECT_ROOT)
    except ValueError:
        return (
            "Error: Access outside the project "
            "directory is not allowed."
        )

    if not requested_file.is_file():
        return f"Error: File does not exist: {file_path}"

    return (
        "Warning: Terraform plan/state output may contain "
        "sensitive information.\n\n"
        + _run_terraform(
            [
                "show",
                "-no-color",
                str(requested_file),
            ],
            directory,
        )
    )