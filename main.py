from ollama import chat


MODEL = "qwen3:8b"


def main():
    messages = []

    print("Personal AI Agent")
    print("Type 'exit' to quit.")

    while True:
        user_prompt = input("\nYou: ").strip()

        if user_prompt.lower() in {"exit", "quit"}:
            print("\nAgent: Goodbye.")
            break

        if not user_prompt:
            continue

        messages.append(
            {
                "role": "user",
                "content": user_prompt,
            }
        )

        response = chat(
            model=MODEL,
            messages=messages,
        )

        assistant_response = response.message.content

        messages.append(
            {
                "role": "assistant",
                "content": assistant_response,
            }
        )

        print(f"\nAgent: {assistant_response}")


if __name__ == "__main__":
    main()