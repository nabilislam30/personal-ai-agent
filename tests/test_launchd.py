from pathlib import Path

from scripts import install_launchd


def test_app_launchd_configuration_is_run_at_load():
    payload = (
        install_launchd
        .build_app_plist()
    )

    assert (
        payload["Label"]
        == "com.nabil.personal-ai-agent"
    )
    assert (
        payload["RunAtLoad"]
        is True
    )
    assert (
        payload["KeepAlive"]
        is True
    )
    assert (
        payload[
            "ProgramArguments"
        ][0]
        == "/bin/zsh"
    )
    assert (
        payload[
            "ProgramArguments"
        ][1]
        .endswith(
            "scripts/run_production.sh"
        )
    )


def test_backup_launchd_configuration_has_schedule(
    tmp_path,
):
    backup_root = (
        tmp_path
        / "backups"
    )

    payload = (
        install_launchd
        .build_backup_plist(
            backup_root=backup_root,
            hour=3,
            minute=15,
            keep=14,
        )
    )

    assert (
        payload[
            "StartCalendarInterval"
        ]
        == {
            "Hour": 3,
            "Minute": 15,
        }
    )

    arguments = payload[
        "ProgramArguments"
    ]

    assert "--output" in arguments
    assert (
        str(backup_root)
        in arguments
    )
    assert "--keep" in arguments
    assert "14" in arguments
