from ollama import chat


MODEL = "qwen3:8b"


def main():
    user_prompt = input("You: ")

    response = chat(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": user_prompt,
            }
        ],
    )

    print(f"\nAgent: {response.message.content}")


if __name__ == "__main__":
    main()