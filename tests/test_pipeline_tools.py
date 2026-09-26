from tools import pipeline_tools


def test_latest_is_not_treated_as_status():
    assert (
        pipeline_tools._normalise_status(
            "latest"
        )
        == ""
    )


def test_failed_normalises_to_failure():
    assert (
        pipeline_tools._normalise_status(
            "failed"
        )
        == "failure"
    )


def test_invalid_status_is_ignored():
    assert (
        pipeline_tools._normalise_status(
            "definitely-not-valid"
        )
        == ""
    )


def test_short_repo_name_is_not_forced():
    assert (
        pipeline_tools._github_repo_arguments(
            "personal-ai-agent"
        )
        == []
    )


def test_owner_repo_is_accepted():
    assert (
        pipeline_tools._github_repo_arguments(
            "owner/repo"
        )
        == [
            "--repo",
            "owner/repo",
        ]
    )
