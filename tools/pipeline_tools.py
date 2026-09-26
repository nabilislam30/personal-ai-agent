import json
import shutil
import subprocess


MAX_OUTPUT = 30_000

_ALLOWED_STATUSES = {
    "completed",
    "in_progress",
    "queued",
    "requested",
    "waiting",
    "pending",
    "action_required",
    "cancelled",
    "failure",
    "neutral",
    "skipped",
    "stale",
    "startup_failure",
    "success",
    "timed_out",
}


def _run_command(
    command: list[str],
    timeout: int = 60,
) -> tuple[int, str, str]:
    """
    Run an explicitly allowed read-only command.

    Returns:
        exit_code
        stdout
        stderr
    """

    executable = command[0]

    if shutil.which(executable) is None:
        return (
            127,
            "",
            (
                f"{executable} is not installed "
                "or is not available in PATH."
            ),
        )

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

    except subprocess.TimeoutExpired:
        return (
            124,
            "",
            f"{executable} command timed out.",
        )

    stdout = result.stdout.strip()
    stderr = result.stderr.strip()

    if len(stdout) > MAX_OUTPUT:
        stdout = (
            stdout[:MAX_OUTPUT]
            + "\n\n[Output truncated]"
        )

    if len(stderr) > MAX_OUTPUT:
        stderr = (
            stderr[:MAX_OUTPUT]
            + "\n\n[Error output truncated]"
        )

    return (
        result.returncode,
        stdout,
        stderr,
    )


def _github_repo_arguments(
    repo: str,
) -> list[str]:
    """
    Add --repo only for an owner/repo value.

    A short repository name is ignored so the GitHub CLI can
    safely detect the current repository from the working tree.
    """

    cleaned_repo = repo.strip()

    if not cleaned_repo:
        return []

    if "/" not in cleaned_repo:
        return []

    return [
        "--repo",
        cleaned_repo,
    ]


def _normalise_status(status: str) -> str:
    """
    Convert natural-language status values into supported gh values.
    """

    cleaned_status = status.strip().lower()

    if cleaned_status in {
        "",
        "latest",
        "recent",
        "all",
    }:
        return ""

    if cleaned_status == "failed":
        return "failure"

    if cleaned_status == "successful":
        return "success"

    if cleaned_status not in _ALLOWED_STATUSES:
        return ""

    return cleaned_status


def github_auth_status() -> str:
    """
    Check GitHub CLI authentication status.

    This is read-only.
    """

    exit_code, stdout, stderr = _run_command(
        [
            "gh",
            "auth",
            "status",
        ]
    )

    if exit_code == 0:
        details = stdout or stderr or "Authenticated."

        return (
            "GitHub authentication check succeeded.\n\n"
            f"{details}"
        )

    details = stderr or stdout or "Unknown authentication error."

    return (
        "GitHub authentication check failed.\n\n"
        f"{details}"
    )


def github_actions_runs(
    repo: str = "",
    limit: int = 10,
    status: str = "",
) -> str:
    """
    List recent GitHub Actions workflow runs.

    Args:
        repo:
            Optional repository in owner/repo format.
            Leave blank to use the current Git repository.

        limit:
            Number of workflow runs to return, from 1 to 30.

        status:
            Optional status filter such as failure, success,
            completed, or in_progress. Values such as latest,
            recent, or all are treated as no status filter.
    """

    limit = max(
        1,
        min(int(limit), 30),
    )

    normalised_status = _normalise_status(status)

    command = [
        "gh",
        "run",
        "list",
        "--limit",
        str(limit),
        "--json",
        (
            "databaseId,displayTitle,workflowName,"
            "status,conclusion,event,headBranch,"
            "headSha,createdAt,updatedAt,url"
        ),
    ]

    if normalised_status:
        command.extend(
            [
                "--status",
                normalised_status,
            ]
        )

    command.extend(
        _github_repo_arguments(repo)
    )

    exit_code, stdout, stderr = _run_command(
        command
    )

    if exit_code != 0:
        details = stderr or stdout or "Unknown GitHub CLI error."

        return (
            "GitHub Actions run query failed.\n\n"
            f"{details}"
        )

    try:
        runs = json.loads(
            stdout or "[]"
        )
    except json.JSONDecodeError:
        return (
            "GitHub Actions run query succeeded, "
            "but the response could not be parsed.\n\n"
            f"Raw output:\n{stdout}"
        )

    if not runs:
        if normalised_status:
            return (
                "GitHub Actions run query succeeded.\n\n"
                f"No workflow runs with status "
                f"'{normalised_status}' were found."
            )

        return (
            "GitHub Actions run query succeeded.\n\n"
            "No workflow runs were found for this repository."
        )

    return (
        "GitHub Actions run query succeeded.\n\n"
        + json.dumps(
            runs,
            indent=2,
        )
    )


def github_actions_run_details(
    run_id: int,
    repo: str = "",
) -> str:
    """
    Inspect a specific GitHub Actions workflow run.

    This is read-only.
    """

    command = [
        "gh",
        "run",
        "view",
        str(run_id),
        "--json",
        (
            "attempt,conclusion,createdAt,databaseId,"
            "displayTitle,event,headBranch,headSha,jobs,"
            "name,number,startedAt,status,updatedAt,url,"
            "workflowName"
        ),
    ]

    command.extend(
        _github_repo_arguments(repo)
    )

    exit_code, stdout, stderr = _run_command(
        command
    )

    if exit_code != 0:
        details = stderr or stdout or "Unknown GitHub CLI error."

        return (
            f"Unable to inspect GitHub Actions run {run_id}.\n\n"
            f"{details}"
        )

    try:
        run = json.loads(stdout)
    except json.JSONDecodeError:
        return (
            f"GitHub Actions run {run_id} was retrieved, "
            "but the response could not be parsed.\n\n"
            f"Raw output:\n{stdout}"
        )

    return (
        f"GitHub Actions run {run_id} details:\n\n"
        + json.dumps(
            run,
            indent=2,
        )
    )


def github_actions_failed_logs(
    run_id: int,
    repo: str = "",
) -> str:
    """
    Retrieve logs from failed steps in a GitHub Actions run.

    This is read-only.
    """

    command = [
        "gh",
        "run",
        "view",
        str(run_id),
        "--log-failed",
    ]

    command.extend(
        _github_repo_arguments(repo)
    )

    exit_code, stdout, stderr = _run_command(
        command,
        timeout=120,
    )

    if exit_code != 0:
        details = stderr or stdout or "Unknown GitHub CLI error."

        return (
            f"Unable to retrieve failed logs "
            f"for GitHub Actions run {run_id}.\n\n"
            f"{details}"
        )

    if not stdout:
        return (
            f"GitHub Actions run {run_id} was inspected successfully, "
            "but no failed-step logs were returned."
        )

    return (
        f"Failed-step logs for GitHub Actions run {run_id}:\n\n"
        f"{stdout}"
    )


def github_investigate_latest_failure(
    repo: str = "",
) -> str:
    """
    Investigate the most recent failed GitHub Actions workflow run.

    This performs a deterministic read-only investigation:
    1. find the latest failed run
    2. inspect the run details
    3. retrieve failed-step logs

    Args:
        repo:
            Optional repository in owner/repo format.
            Leave blank to use the current Git repository.

    Returns:
        Structured evidence for the latest failed workflow run.
    """

    repo_arguments = _github_repo_arguments(repo)

    list_command = [
        "gh",
        "run",
        "list",
        "--status",
        "failure",
        "--limit",
        "1",
        "--json",
        (
            "databaseId,displayTitle,workflowName,"
            "status,conclusion,event,headBranch,"
            "headSha,createdAt,updatedAt,url"
        ),
    ]

    list_command.extend(repo_arguments)

    exit_code, stdout, stderr = _run_command(
        list_command
    )

    if exit_code != 0:
        details = stderr or stdout or "Unknown GitHub CLI error."

        return (
            "Failed to search for GitHub Actions failures.\n\n"
            f"{details}"
        )

    try:
        runs = json.loads(
            stdout or "[]"
        )
    except json.JSONDecodeError:
        return (
            "GitHub returned workflow-run data that "
            "could not be parsed."
        )

    if not runs:
        return (
            "No failed GitHub Actions workflow runs were found."
        )

    failed_run = runs[0]
    run_id = failed_run["databaseId"]

    details_command = [
        "gh",
        "run",
        "view",
        str(run_id),
        "--json",
        (
            "attempt,conclusion,createdAt,databaseId,"
            "displayTitle,event,headBranch,headSha,jobs,"
            "name,number,startedAt,status,updatedAt,url,"
            "workflowName"
        ),
    ]

    details_command.extend(repo_arguments)

    (
        details_exit_code,
        details_stdout,
        details_stderr,
    ) = _run_command(details_command)

    if details_exit_code != 0:
        run_details = (
            "Unable to retrieve run details.\n"
            + (
                details_stderr
                or details_stdout
                or "Unknown error."
            )
        )
    else:
        run_details = details_stdout

    logs_command = [
        "gh",
        "run",
        "view",
        str(run_id),
        "--log-failed",
    ]

    logs_command.extend(repo_arguments)

    (
        logs_exit_code,
        logs_stdout,
        logs_stderr,
    ) = _run_command(
        logs_command,
        timeout=120,
    )

    if logs_exit_code != 0:
        failed_logs = (
            "Unable to retrieve failed-step logs.\n"
            + (
                logs_stderr
                or logs_stdout
                or "Unknown error."
            )
        )
    elif not logs_stdout:
        failed_logs = "No failed-step logs were returned."
    else:
        failed_logs = logs_stdout

    return (
        "LATEST FAILED GITHUB ACTIONS RUN\n"
        "================================\n\n"
        f"Run ID: {run_id}\n"
        f"Workflow: {failed_run.get('workflowName')}\n"
        f"Title: {failed_run.get('displayTitle')}\n"
        f"Event: {failed_run.get('event')}\n"
        f"Branch: {failed_run.get('headBranch')}\n"
        f"Conclusion: {failed_run.get('conclusion')}\n"
        f"URL: {failed_run.get('url')}\n\n"
        "RUN DETAILS\n"
        "===========\n"
        f"{run_details}\n\n"
        "FAILED STEP LOGS\n"
        "================\n"
        f"{failed_logs}"
    )
