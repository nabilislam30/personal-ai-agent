from ollama import chat

from prompts.documentation import DOCUMENTATION_PROMPT
from tools.cloud_tools import (
    aws_identity,
    azure_account_show,
    azure_resource_list,
)
from tools.document_tools import save_document
from tools.file_tools import (
    list_directory,
    read_file,
    search_files,
)
from tools.git_tools import (
    git_diff,
    git_log,
    git_status,
)
from tools.log_tools import read_log_tail
from tools.research_tools import (
    fetch_webpage,
    web_search,
)
from tools.terraform_tools import (
    terraform_fmt_check,
    terraform_show,
    terraform_validate,
    terraform_version,
)


MODEL = "qwen3:8b"


SYSTEM_PROMPT = """
You are a personal AI assistant supporting technical work,
DevOps, documentation, research, organisation, coding,
content creation, and general professional work.

CORE PRINCIPLES

- Do not invent evidence.
- Distinguish observed facts from assumptions.
- Distinguish likely explanations from confirmed root causes.
- State uncertainty clearly.
- Prefer evidence before conclusions.
- Prefer read-only investigation before changes.
- Never claim a tool was run unless a tool result confirms it.
- Never claim a file was inspected unless a tool returned its content.
- Never claim a document was saved unless save_document confirms success.

ORGANISATION

Help with:
- task planning
- prioritisation
- project structure
- notes
- workflows
- breaking large tasks into manageable steps

DOCUMENTATION

Help create:
- README files
- project documentation
- Jira updates
- incident reports
- RCA reports
- architecture documentation
- technical summaries

Follow the additional DOCUMENTATION_PROMPT rules.

RESEARCH

Use web_search when current or external information is needed.

Use fetch_webpage when a specific search result or URL needs
to be inspected in more detail.

When researching:
- distinguish search-result snippets from inspected source content
- include source URLs in the answer
- compare multiple sources when appropriate
- prefer primary technical documentation where possible
- do not present unsourced model knowledge as newly verified research

FILES

Available read-only tools:
- list_directory
- read_file
- search_files
- read_log_tail

File access is restricted to the personal-ai-agent project.

Use list_directory to discover structure.
Use search_files to locate information.
Use read_file for specific file contents.
Use read_log_tail for large logs.

Never infer file contents from a filename alone.

GIT

Available Git tools are read-only:
- git_status
- git_diff
- git_log

They may inspect repository state but cannot modify Git history,
branches, commits, or remotes.

Do not claim a change has been committed or pushed unless evidence
supports that statement.

TERRAFORM

Available Terraform tools are intentionally read-only:
- terraform_version
- terraform_fmt_check
- terraform_validate
- terraform_show

There is no terraform apply or terraform destroy tool.

Never attempt to work around that restriction.

For Terraform incidents:
1. inspect existing evidence
2. inspect relevant configuration
3. validate where appropriate
4. inspect existing plan/state only when needed
5. distinguish errors from hypotheses
6. recommend remediation

Do not invent Terraform flags or command behaviour.

CLOUD

Cloud tooling is intentionally restricted.

Available AWS capability:
- aws_identity

Available Azure capabilities:
- azure_account_show
- azure_resource_list

These tools are for read-only inspection only.

Do not request unrestricted administrator credentials.
Do not suggest weakening IAM or security controls merely to
make an investigation easier.

CONTENT CREATION

Help create:
- technical articles
- tutorials
- LinkedIn posts
- professional social media content
- project write-ups
- educational material
- presentation content

Adapt:
- tone
- length
- technical depth
- format
- audience

Do not fabricate project achievements or technical evidence.

DOCUMENT WRITING

Use save_document only when the user explicitly asks to save
or create a document file.

save_document:
- writes only inside workspace/
- supports .md and .txt
- cannot overwrite automatically
- requires human approval from the application

When calling save_document:
- pass raw document content
- do not wrap Markdown content in code fences

SECURITY

READ operations may run automatically.

WRITE operations require explicit human approval.

DESTRUCTIVE operations are not available.

Never attempt to bypass:
- filesystem boundaries
- write approval
- command restrictions
- cloud permission restrictions
"""


TOOLS = [
    # Local files
    read_file,
    list_directory,
    search_files,
    read_log_tail,

    # Documents
    save_document,

    # Research
    web_search,
    fetch_webpage,

    # Git
    git_status,
    git_diff,
    git_log,

    # Terraform
    terraform_version,
    terraform_fmt_check,
    terraform_validate,
    terraform_show,

    # Cloud
    aws_identity,
    azure_account_show,
    azure_resource_list,
]


AVAILABLE_TOOLS = {
    tool.__name__: tool
    for tool in TOOLS
}


WRITE_TOOLS = {
    "save_document",
}


def request_write_approval(
    tool_name: str,
    tool_arguments: dict,
) -> bool:
    """
    Request explicit user approval before a write tool runs.
    """

    if tool_name == "save_document":
        file_path = tool_arguments.get(
            "file_path",
            "unknown file",
        )

        print(
            f"\n[Write Request] Save document: {file_path}"
        )

    else:
        print(
            f"\n[Write Request] Tool: {tool_name}"
        )

    approval = input(
        "Approve this write? [y/N]: "
    ).strip().lower()

    return approval in {"y", "yes"}


def display_tool_call(
    tool_name: str,
    tool_arguments: dict,
) -> None:
    """
    Display tool activity without dumping large document content.
    """

    if tool_name == "save_document":
        file_path = tool_arguments.get(
            "file_path",
            "unknown file",
        )

        content = str(
            tool_arguments.get("content", "")
        )

        print(
            f"\n[Tool] save_document("
            f"file_path='{file_path}', "
            f"content={len(content)} chars)"
        )

        return

    print(
        f"\n[Tool] {tool_name}({tool_arguments})"
    )


def execute_tool(
    tool_name: str,
    tool_arguments: dict,
) -> str:
    """
    Execute an approved/allowed tool.
    """

    function_to_call = AVAILABLE_TOOLS.get(
        tool_name
    )

    if function_to_call is None:
        return (
            f"Error: Unknown tool requested: {tool_name}"
        )

    if tool_name in WRITE_TOOLS:
        approved = request_write_approval(
            tool_name,
            tool_arguments,
        )

        if not approved:
            return "Write cancelled by user."

    try:
        return str(
            function_to_call(
                **tool_arguments
            )
        )

    except Exception as error:
        return (
            f"Error executing tool "
            f"'{tool_name}': {error}"
        )


def run_agent_turn(messages):
    """
    Run one agent turn.

    The model may perform multiple tool calls before returning
    a final response.
    """

    while True:
        response = chat(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
        )

        messages.append(
            response.message
        )

        if not response.message.tool_calls:
            return (
                response.message.content
                or "(No response returned.)"
            )

        for tool_call in response.message.tool_calls:
            tool_name = tool_call.function.name
            tool_arguments = dict(
                tool_call.function.arguments
            )

            display_tool_call(
                tool_name,
                tool_arguments,
            )

            tool_result = execute_tool(
                tool_name,
                tool_arguments,
            )

            messages.append(
                {
                    "role": "tool",
                    "tool_name": tool_name,
                    "content": tool_result,
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
    print(f"Model: {MODEL}")
    print("Type 'exit' to quit.")

    while True:
        try:
            user_prompt = input(
                "\nYou: "
            ).strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nAgent: Goodbye.")
            break

        if user_prompt.lower() in {
            "exit",
            "quit",
        }:
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

        try:
            assistant_response = run_agent_turn(
                messages
            )

        except Exception as error:
            print(
                f"\nAgent error: {error}"
            )
            continue

        print(
            f"\nAgent: {assistant_response}"
        )


if __name__ == "__main__":
    main()