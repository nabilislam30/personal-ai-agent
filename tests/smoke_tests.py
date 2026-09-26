from agent import (
    build_messages,
    run_agent_turn_with_metrics,
)
from router import (
    route_request,
)


TEST_PROMPTS = [
    "What is your name?",
    "Show me the current Git status.",
    (
        "Find references to qwen3 in this repository "
        "and tell me where the model is configured."
    ),
    "Check whether Terraform is installed on this Mac.",
    (
        "Search the web for the official Terraform validate "
        "documentation and give me the sources."
    ),
]


def run_test(
    number: int,
    prompt: str,
) -> None:
    print(
        "\n"
        + "=" * 80
    )
    print(
        f"TEST {number}"
    )
    print(
        "=" * 80
    )
    print(
        f"\nPrompt:\n"
        f"{prompt}\n"
    )

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

    try:
        result = (
            run_agent_turn_with_metrics(
                messages=messages,
                user_prompt=prompt,
                route=route,
            )
        )

        print(
            f"Route: "
            f"{result.route}"
        )
        print(
            "\nResponse:"
        )
        print(
            result.content
        )
        print(
            "\nPerformance: "
            f"tools={result.tool_calls}, "
            f"model={result.model_ms:.0f}ms, "
            f"total={result.total_ms:.0f}ms"
        )

    except Exception as error:
        print(
            f"\nTEST FAILED: "
            f"{error}"
        )


def main() -> None:
    print(
        "Personal AI Agent - "
        "Performance Smoke Test"
    )
    print(
        f"Running "
        f"{len(TEST_PROMPTS)} "
        "tests..."
    )

    for number, prompt in enumerate(
        TEST_PROMPTS,
        start=1,
    ):
        run_test(
            number,
            prompt,
        )

    print(
        "\n"
        + "=" * 80
    )
    print(
        "SMOKE TEST COMPLETE"
    )
    print(
        "=" * 80
    )


if __name__ == "__main__":
    main()
