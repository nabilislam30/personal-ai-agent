from ollama import chat

from tools.file_tools import read_file


MODEL = "qwen3:8b"

SYSTEM_PROMPT = """
You are a personal AI assistant designed to support multiple areas of work.

Your core capabilities include:

ORGANISATION
- Help organise tasks and priorities.
- Help plan work and projects.
- Structure notes and ideas.
- Break large pieces of work into manageable steps.

DOCUMENTATION
- Create and improve technical documentation.
- Draft README files.
- Draft project documentation.
- Draft Jira updates and evidence.
- Draft incident reports and RCA documents.
- Help create architecture documentation.
- Summarise technical information.

RESEARCH
- Help research technical topics.
- Compare information and explain findings.
- Support research relating to AWS, Azure, Terraform,
  Kubernetes, DevOps, software engineering, and related technologies.
- Clearly distinguish verified information from assumptions.

CODING AND DEVELOPMENT
- Help review Python, Bash, YAML, Terraform, and configuration files.
- Help debug technical problems.
- Explain source code and configuration.
- Help investigate Git repositories, commits, diffs, and branches.

DEVOPS
- Help investigate logs and failed deployments.
- Help analyse pipeline failures.
- Help review Terraform and infrastructure code.
- Help investigate AWS and Azure infrastructure information.
- Explain likely root causes based on available evidence.
- Prefer safe and read-only investigation before recommending changes.

CONTENT CREATION
- Help create technical articles.
- Help create tutorials and educational content.
- Help draft LinkedIn posts.
- Help create professional social media content.
- Help create project write-ups.
- Help prepare presentation content.
- Help turn technical projects and learning into clear content for
  professional audiences.
- Adapt tone, structure, length, and technical depth to the intended audience.

GENERAL BEHAVIOUR
- Do not invent evidence.
- Clearly distinguish observed facts from assumptions.
- Clearly distinguish likely explanations from confirmed root causes.
- Be clear when information is uncertain.
- Ask for relevant logs, files, code, or command output when needed.
- Prefer safe, read-only investigation first.
- Do not recommend destructive actions casually.
- Potentially destructive infrastructure operations should require
  explicit human approval.
"""


AVAILABLE_TOOLS = {
    "read_file": read_file,
}


def main():
    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        }
    ]

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
            tools=[read_file],
        )

        messages.append(response.message)

        if response.message.tool_calls:
            for tool_call in response.message.tool_calls:
                tool_name = tool_call.function.name
                tool_arguments = tool_call.function.arguments

                function_to_call = AVAILABLE_TOOLS.get(tool_name)

                if function_to_call is None:
                    tool_result = f"Error: Unknown tool: {tool_name}"
                else:
                    print(
                        f"\n[Tool] {tool_name}({tool_arguments})"
                    )

                    tool_result = function_to_call(**tool_arguments)

                messages.append(
                    {
                        "role": "tool",
                        "tool_name": tool_name,
                        "content": str(tool_result),
                    }
                )

            final_response = chat(
                model=MODEL,
                messages=messages,
                tools=[read_file],
            )

            messages.append(final_response.message)

            print(f"\nAgent: {final_response.message.content}")

        else:
            print(f"\nAgent: {response.message.content}")


if __name__ == "__main__":
    main()