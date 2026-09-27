import argparse
import os
import plistlib
import subprocess
from pathlib import Path


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

HOME = Path.home()
LAUNCH_AGENTS = (
    HOME
    / "Library"
    / "LaunchAgents"
)

APP_LABEL = (
    "com.nabil.personal-ai-agent"
)
BACKUP_LABEL = (
    "com.nabil.personal-ai-agent.backup"
)

APP_PLIST = (
    LAUNCH_AGENTS
    / f"{APP_LABEL}.plist"
)
BACKUP_PLIST = (
    LAUNCH_AGENTS
    / f"{BACKUP_LABEL}.plist"
)


def _write_plist(
    path: Path,
    payload: dict,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open("wb") as file_handle:
        plistlib.dump(
            payload,
            file_handle,
            sort_keys=False,
        )


def _launchctl(
    *arguments: str,
    check: bool = True,
) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            "/bin/launchctl",
            *arguments,
        ],
        capture_output=True,
        text=True,
        check=check,
    )


def build_app_plist() -> dict:
    log_dir = (
        PROJECT_ROOT
        / "workspace"
        / "logs"
    )

    return {
        "Label": APP_LABEL,
        "ProgramArguments": [
            "/bin/zsh",
            str(
                PROJECT_ROOT
                / "scripts"
                / "run_production.sh"
            ),
        ],
        "WorkingDirectory": (
            str(PROJECT_ROOT)
        ),
        "RunAtLoad": True,
        "KeepAlive": True,
        "ProcessType": "Interactive",
        "StandardOutPath": (
            str(
                log_dir
                / "launchd-app.out.log"
            )
        ),
        "StandardErrorPath": (
            str(
                log_dir
                / "launchd-app.err.log"
            )
        ),
    }


def build_backup_plist(
    backup_root: Path,
    hour: int,
    minute: int,
    keep: int,
) -> dict:
    log_dir = (
        PROJECT_ROOT
        / "workspace"
        / "logs"
    )

    python_path = (
        PROJECT_ROOT
        / ".venv"
        / "bin"
        / "python"
    )

    return {
        "Label": BACKUP_LABEL,
        "ProgramArguments": [
            str(python_path),
            str(
                PROJECT_ROOT
                / "scripts"
                / "backup.py"
            ),
            "--output",
            str(backup_root),
            "--keep",
            str(keep),
        ],
        "WorkingDirectory": (
            str(PROJECT_ROOT)
        ),
        "StartCalendarInterval": {
            "Hour": hour,
            "Minute": minute,
        },
        "ProcessType": "Background",
        "StandardOutPath": (
            str(
                log_dir
                / "launchd-backup.out.log"
            )
        ),
        "StandardErrorPath": (
            str(
                log_dir
                / "launchd-backup.err.log"
            )
        ),
    }


def _domain() -> str:
    return (
        f"gui/{os.getuid()}"
    )


def _bootout(
    plist_path: Path,
) -> None:
    _launchctl(
        "bootout",
        _domain(),
        str(plist_path),
        check=False,
    )


def _bootstrap(
    plist_path: Path,
) -> None:
    result = _launchctl(
        "bootstrap",
        _domain(),
        str(plist_path),
        check=False,
    )

    if result.returncode != 0:
        message = (
            result.stderr.strip()
            or result.stdout.strip()
            or "launchctl bootstrap failed"
        )
        raise RuntimeError(
            message
        )


def install(
    backup_root: Path,
    hour: int,
    minute: int,
    keep: int,
    start_now: bool,
) -> None:
    env_file = (
        PROJECT_ROOT
        / ".env.production"
    )
    gunicorn = (
        PROJECT_ROOT
        / ".venv"
        / "bin"
        / "gunicorn"
    )
    python_path = (
        PROJECT_ROOT
        / ".venv"
        / "bin"
        / "python"
    )
    runner = (
        PROJECT_ROOT
        / "scripts"
        / "run_production.sh"
    )

    missing = [
        str(path)
        for path in (
            env_file,
            gunicorn,
            python_path,
            runner,
        )
        if not path.exists()
    ]

    if missing:
        raise SystemExit(
            "Cannot install launch agents. Missing:\n- "
            + "\n- ".join(
                missing
            )
        )

    if not 0 <= hour <= 23:
        raise SystemExit(
            "Backup hour must be 0-23."
        )

    if not 0 <= minute <= 59:
        raise SystemExit(
            "Backup minute must be 0-59."
        )

    keep = max(
        1,
        int(keep),
    )

    backup_root = (
        backup_root
        .expanduser()
        .resolve()
    )

    (
        PROJECT_ROOT
        / "workspace"
        / "logs"
    ).mkdir(
        parents=True,
        exist_ok=True,
    )

    backup_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    _write_plist(
        APP_PLIST,
        build_app_plist(),
    )

    _write_plist(
        BACKUP_PLIST,
        build_backup_plist(
            backup_root=backup_root,
            hour=hour,
            minute=minute,
            keep=keep,
        ),
    )

    for plist_path in (
        APP_PLIST,
        BACKUP_PLIST,
    ):
        _bootout(
            plist_path
        )
        _bootstrap(
            plist_path
        )

    _launchctl(
        "enable",
        (
            f"{_domain()}/"
            f"{APP_LABEL}"
        ),
        check=False,
    )
    _launchctl(
        "enable",
        (
            f"{_domain()}/"
            f"{BACKUP_LABEL}"
        ),
        check=False,
    )

    if start_now:
        _launchctl(
            "kickstart",
            "-k",
            (
                f"{_domain()}/"
                f"{APP_LABEL}"
            ),
            check=False,
        )

    print(
        "Launch agents installed."
    )
    print(
        f"App: {APP_PLIST}"
    )
    print(
        f"Backup: {BACKUP_PLIST}"
    )
    print(
        "Daily backup schedule: "
        f"{hour:02d}:{minute:02d}"
    )
    print(
        f"Backup location: "
        f"{backup_root}"
    )

    if not start_now:
        print(
            "The app will start automatically "
            "at the next login/reboot."
        )
        print(
            "To start it now after stopping any "
            "manually running Gunicorn process:"
        )
        print(
            "launchctl kickstart -k "
            f"{_domain()}/{APP_LABEL}"
        )


def uninstall() -> None:
    for plist_path in (
        APP_PLIST,
        BACKUP_PLIST,
    ):
        _bootout(
            plist_path
        )
        plist_path.unlink(
            missing_ok=True
        )

    print(
        "Personal AI Agent launch agents removed."
    )


def status() -> None:
    for label in (
        APP_LABEL,
        BACKUP_LABEL,
    ):
        result = _launchctl(
            "print",
            f"{_domain()}/{label}",
            check=False,
        )

        state = (
            "loaded"
            if result.returncode == 0
            else "not loaded"
        )

        print(
            f"{label}: {state}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Install macOS LaunchAgents for "
            "automatic Personal AI Agent startup "
            "and scheduled local backups."
        )
    )

    parser.add_argument(
        "--uninstall",
        action="store_true",
    )
    parser.add_argument(
        "--status",
        action="store_true",
    )
    parser.add_argument(
        "--start-now",
        action="store_true",
        help=(
            "Kickstart the app LaunchAgent "
            "immediately after installation."
        ),
    )
    parser.add_argument(
        "--backup-hour",
        type=int,
        default=3,
    )
    parser.add_argument(
        "--backup-minute",
        type=int,
        default=15,
    )
    parser.add_argument(
        "--keep",
        type=int,
        default=14,
    )
    parser.add_argument(
        "--backup-root",
        type=Path,
        default=(
            HOME
            / "PersonalAIAgentBackups"
        ),
    )

    args = parser.parse_args()

    if args.uninstall:
        uninstall()
        return

    if args.status:
        status()
        return

    install(
        backup_root=(
            args.backup_root
        ),
        hour=(
            args.backup_hour
        ),
        minute=(
            args.backup_minute
        ),
        keep=args.keep,
        start_now=(
            args.start_now
        ),
    )


if __name__ == "__main__":
    main()
