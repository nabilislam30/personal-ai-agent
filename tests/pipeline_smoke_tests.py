from tools.pipeline_tools import (
    github_actions_runs,
    github_auth_status,
    github_investigate_latest_failure,
)


def main():
    print("=" * 72)
    print("GITHUB AUTH")
    print("=" * 72)
    print(github_auth_status())

    print()
    print("=" * 72)
    print("RECENT GITHUB ACTIONS RUNS")
    print("=" * 72)
    print(
        github_actions_runs(
            limit=5,
        )
    )

    print()
    print("=" * 72)
    print("LATEST FAILED GITHUB ACTIONS RUN")
    print("=" * 72)
    print(
        github_investigate_latest_failure()
    )

    print()
    print("=" * 72)
    print("PIPELINE SMOKE TEST COMPLETE")
    print("=" * 72)


if __name__ == "__main__":
    main()
