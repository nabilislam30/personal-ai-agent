import shutil
import subprocess


MAX_OUTPUT = 15_000


def _run_command(command: list[str]) -> str:
    executable = command[0]

    if shutil.which(executable) is None:
        return (
            f"Error: {executable} CLI is not installed "
            "or is not available in PATH."
        )

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return f"Error: {executable} command timed out."

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


def aws_identity() -> str:
    """
    Show the current AWS CLI identity without changing resources.

    Returns:
        AWS STS caller identity.
    """

    return _run_command(
        [
            "aws",
            "sts",
            "get-caller-identity",
            "--output",
            "json",
        ]
    )


def azure_account_show() -> str:
    """
    Show the active Azure CLI account without changing resources.

    Returns:
        Active Azure account information.
    """

    return _run_command(
        [
            "az",
            "account",
            "show",
            "--output",
            "json",
        ]
    )


def azure_resource_list() -> str:
    """
    List up to 50 Azure resources without changing anything.

    Returns:
        Azure resource information.
    """

    return _run_command(
        [
            "az",
            "resource",
            "list",
            "--query",
            "[0:50].{name:name,type:type,"
            "resourceGroup:resourceGroup,location:location}",
            "--output",
            "json",
        ]
    )