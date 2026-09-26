from agent import (
    build_messages,
    run_agent_turn,
)


TEST_PROMPTS = [
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
    (
        "Inspect this project and summarise the main capabilities "
        "that are currently implemented."
    ),
]


def run_test(
    number: int,
    prompt: str,
) -> None:
    print("\n" + "=" * 80)
    print(f"TEST {number}")
    print("=" * 80)
    print(f"\nPrompt:\n{prompt}\n")

    messages = build_messages(
        [
            {
                "role": "user",
                "content": prompt,
            }
        ]
    )

    try:
        response = run_agent_turn(
            messages
        )

        print("\nResponse:")
        print(response)

    except Exception as error:
        print(
            f"\nTEST FAILED: {error}"
        )


def main():
    print(
        "Personal AI Agent - Smoke Test"
    )
    print(
        f"Running {len(TEST_PROMPTS)} tests..."
    )

    for number, prompt in enumerate(
        TEST_PROMPTS,
        start=1,
    ):
        run_test(
            number,
            prompt,
        )

    print("\n" + "=" * 80)
    print("SMOKE TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
