from ollama import chat

from prompts.documentation import DOCUMENTATION_PROMPT
from tools.document_tools import save_document
from tools.file_tools import (
    list_directory,
    read_file,
    search_files,
)


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

FILE TOOLS
- Use the available file tools whenever the user asks about project files,
  project configuration, code, or information stored in the repository.
- Use list_directory when you need to discover the project structure.
- Use search_files when you need to find where a value, setting, function,
  variable, keyword, configuration, or piece of information is defined.
- Use read_file after locating the relevant file when you need its contents
  or surrounding context.
- For questions asking where something is defined, prefer search_files
  before guessing which file contains it.
- Search from the project root "." unless the user explicitly limits the
  request to a particular subdirectory.
- If a search result identifies a relevant file, inspect that file before
  drawing conclusions about its contents.
- Never claim that something does not exist in the project unless you have
  performed an appropriate project-wide search.
- Never pretend you have inspected a file that a tool has not returned.
- Never infer missing file contents from filenames alone.
- Base answers about project files on actual tool results.
- If a tool rejects access, report the actual restriction accurately.
- File read access is restricted to the personal-ai-agent project directory.

DOCUMENT WRITING
- Use save_document only when the user explicitly asks to save or create
  a document file.
- Documents may only be saved inside the workspace directory.
- Document writes require human approval before they are executed.
- Never claim that a document was saved unless the save_document tool
  reports that it was saved successfully.
- Do not attempt to overwrite existing files automatically.
- When calling save_document, pass the raw document content only.
- Do not wrap saved Markdown content in code fences.

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


TOOLS = [
    read_file,
    list_directory,
    search_files,
    save_document,
]


AVAILABLE_TOOLS = {
    "read_file": read_file,
    "list_directory": list_directory,
    "search_files": search_files,
    "save_document": save_document,
}


def run_agent_turn(messages):
    """
    Run one conversation turn.

    The model may call one or more tools before producing
    its final response.
    """

    while True:
        response = chat(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
        )

        messages.append(response.message)

        if not response.message.tool_calls:
            return response.message.content

        for tool_call in response.message.tool_calls:
            tool_name = tool_call.function.name
            tool_arguments = tool_call.function.arguments

            function_to_call = AVAILABLE_TOOLS.get(tool_name)

            print(
                f"\n[Tool] {tool_name}({tool_arguments})"
            )

            if function_to_call is None:
                tool_result = (
                    f"Error: Unknown tool requested: {tool_name}"
                )

            elif tool_name == "save_document":
                file_path = tool_arguments.get(
                    "file_path",
                    "unknown file",
                )

                print(
                    f"\n[Write Request] Save document: {file_path}"
                )

                approval = input(
                    "Approve this write? [y/N]: "
                ).strip().lower()

                if approval not in {"y", "yes"}:
                    tool_result = "Write cancelled by user."

                else:
                    try:
                        tool_result = function_to_call(
                            **tool_arguments
                        )
                    except Exception as error:
                        tool_result = (
                            f"Error executing tool "
                            f"'{tool_name}': {error}"
                        )

            else:
                try:
                    tool_result = function_to_call(
                        **tool_arguments
                    )
                except Exception as error:
                    tool_result = (
                        f"Error executing tool "
                        f"'{tool_name}': {error}"
                    )

            messages.append(
                {
                    "role": "tool",
                    "tool_name": tool_name,
                    "content": str(tool_result),
                }
            )


def main():
    messages = [
        {
            "role": "system",
            "content": (
                SYSTEM_PROMPT
                + "\n\n"
                + DOCUMENTATION_PROMPT
            ),
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

        assistant_response = run_agent_turn(messages)

        print(f"\nAgent: {assistant_response}")


if __name__ == "__main__":
    main()