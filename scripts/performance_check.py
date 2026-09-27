import argparse
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
import sys


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

sys.path.insert(
    0,
    str(PROJECT_ROOT),
)

from agent import (  # noqa: E402
    build_messages,
    preload_model,
    stream_agent_turn,
)
from router import (  # noqa: E402
    route_request,
)


DEFAULT_OUTPUT_ROOT = (
    PROJECT_ROOT
    / "workspace"
    / "performance"
)

CASES = [
    {
        "name": "simple_name",
        "category": "simple",
        "prompt": (
            "What is your name? "
            "Answer in one short sentence."
        ),
    },
    {
        "name": "simple_capabilities",
        "category": "simple",
        "prompt": (
            "In one sentence, what can you help me with?"
        ),
    },
    {
        "name": "complex_pipeline",
        "category": "complex",
        "prompt": (
            "Investigate the most recent failed "
            "GitHub Actions run. Separate observed "
            "evidence, likely cause, uncertainty, "
            "and recommended remediation."
        ),
    },
    {
        "name": "complex_knowledge",
        "category": "complex",
        "prompt": (
            "Search my knowledge base for the agent "
            "architecture and security model, then "
            "summarise the most relevant evidence."
        ),
    },
]


def run_case(
    case: dict,
) -> dict:
    prompt = case[
        "prompt"
    ]

    route = route_request(
        prompt
    )

    messages = build_messages(
        route_name=route.name
    )
    messages.append(
        {
            "role": "user",
            "content": prompt,
        }
    )

    first_token_ms = None
    total_ms = None
    model_ms = None
    tool_calls = 0
    response_parts = []
    error = None

    try:
        for event in stream_agent_turn(
            messages=messages,
            user_prompt=prompt,
            route=route,
        ):
            event_type = (
                event.get(
                    "type"
                )
            )

            if event_type == "token":
                response_parts.append(
                    event.get(
                        "content",
                        "",
                    )
                )

            if event_type == "done":
                first_token_ms = (
                    event.get(
                        "first_token_ms"
                    )
                )
                total_ms = (
                    event.get(
                        "total_ms"
                    )
                )
                model_ms = (
                    event.get(
                        "model_ms"
                    )
                )
                tool_calls = (
                    event.get(
                        "tool_calls",
                        0,
                    )
                )

            if event_type == "error":
                error = event.get(
                    "error"
                )

    except Exception as exc:
        error = str(exc)

    return {
        "name": case[
            "name"
        ],
        "category": case[
            "category"
        ],
        "prompt": prompt,
        "route": route.name,
        "first_token_ms": (
            first_token_ms
        ),
        "model_ms": model_ms,
        "total_ms": total_ms,
        "tool_calls": (
            tool_calls
        ),
        "response_chars": len(
            "".join(
                response_parts
            )
        ),
        "error": error,
    }


def _median(
    values: list,
):
    numeric = [
        value
        for value in values
        if isinstance(
            value,
            (
                int,
                float,
            ),
        )
    ]

    if not numeric:
        return None

    return round(
        statistics.median(
            numeric
        ),
        1,
    )


def build_summary(
    results: list[dict],
) -> dict:
    summary = {}

    for category in (
        "simple",
        "complex",
    ):
        rows = [
            row
            for row in results
            if row[
                "category"
            ] == category
        ]

        summary[category] = {
            "cases": len(rows),
            "successful": sum(
                1
                for row in rows
                if not row[
                    "error"
                ]
            ),
            "median_first_token_ms": (
                _median(
                    [
                        row[
                            "first_token_ms"
                        ]
                        for row in rows
                    ]
                )
            ),
            "median_total_ms": (
                _median(
                    [
                        row[
                            "total_ms"
                        ]
                        for row in rows
                    ]
                )
            ),
        }

    return summary


def write_markdown(
    output_path: Path,
    created_at: str,
    preload_result: str,
    results: list[dict],
    summary: dict,
) -> None:
    lines = [
        "# Personal AI Agent Performance Check",
        "",
        f"Recorded: {created_at}",
        "",
        "## Model preload",
        "",
        preload_result,
        "",
        "## Results",
        "",
        (
            "| Case | Category | Route | "
            "First token | Total | Tools | Result |"
        ),
        (
            "| --- | --- | --- | ---: | ---: | ---: | --- |"
        ),
    ]

    for row in results:
        first = (
            f"{row['first_token_ms']:.0f} ms"
            if isinstance(
                row[
                    "first_token_ms"
                ],
                (
                    int,
                    float,
                ),
            )
            else "—"
        )

        total = (
            f"{row['total_ms'] / 1000:.2f} s"
            if isinstance(
                row[
                    "total_ms"
                ],
                (
                    int,
                    float,
                ),
            )
            else "—"
        )

        result = (
            "OK"
            if not row[
                "error"
            ]
            else (
                "Error: "
                + row[
                    "error"
                ].replace(
                    "|",
                    "\\|",
                )
            )
        )

        lines.append(
            (
                f"| {row['name']} "
                f"| {row['category']} "
                f"| {row['route']} "
                f"| {first} "
                f"| {total} "
                f"| {row['tool_calls']} "
                f"| {result} |"
            )
        )

    lines.extend(
        [
            "",
            "## Summary",
            "",
        ]
    )

    for category in (
        "simple",
        "complex",
    ):
        data = summary[
            category
        ]

        lines.append(
            f"### {category.title()}"
        )
        lines.append("")
        lines.append(
            (
                f"- Successful: "
                f"{data['successful']}/"
                f"{data['cases']}"
            )
        )

        first = data[
            "median_first_token_ms"
        ]
        total = data[
            "median_total_ms"
        ]

        lines.append(
            (
                "- Median first-token latency: "
                + (
                    f"{first:.0f} ms"
                    if first
                    is not None
                    else "n/a"
                )
            )
        )

        lines.append(
            (
                "- Median total latency: "
                + (
                    f"{total / 1000:.2f} s"
                    if total
                    is not None
                    else "n/a"
                )
            )
        )
        lines.append("")

    output_path.write_text(
        "\n".join(lines)
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Record first-token and total latency "
            "for representative simple and complex prompts."
        )
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
    )

    args = parser.parse_args()

    output_root = (
        args.output
        .expanduser()
        .resolve()
    )
    output_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        "Preloading model..."
    )
    preload_result = (
        preload_model()
    )
    print(
        preload_result
    )

    results = []

    for case in CASES:
        print(
            (
                f"Running "
                f"{case['name']}..."
            )
        )

        result = run_case(
            case
        )
        results.append(
            result
        )

        if result[
            "error"
        ]:
            print(
                (
                    "  ERROR: "
                    + result[
                        "error"
                    ]
                )
            )
        else:
            print(
                (
                    "  route="
                    f"{result['route']} "
                    "first="
                    f"{result['first_token_ms']}ms "
                    "total="
                    f"{result['total_ms']}ms"
                )
            )

    created_at = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    summary = build_summary(
        results
    )

    stamp = (
        datetime.now(
            timezone.utc
        ).strftime(
            "%Y%m%dT%H%M%SZ"
        )
    )

    json_path = (
        output_root
        / f"performance-{stamp}.json"
    )
    md_path = (
        output_root
        / f"performance-{stamp}.md"
    )

    payload = {
        "created_at": (
            created_at
        ),
        "preload": (
            preload_result
        ),
        "summary": summary,
        "results": results,
    }

    json_path.write_text(
        json.dumps(
            payload,
            indent=2,
        ),
        encoding="utf-8",
    )

    write_markdown(
        output_path=md_path,
        created_at=created_at,
        preload_result=(
            preload_result
        ),
        results=results,
        summary=summary,
    )

    print("")
    print(
        f"JSON report: {json_path}"
    )
    print(
        f"Markdown report: {md_path}"
    )


if __name__ == "__main__":
    main()
