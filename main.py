import json

from ollama import chat

from prompts.documentation import DOCUMENTATION_PROMPT
from tools.cloud_tools import aws_identity
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
from tools.knowledge_tools import (
    index_knowledge,
    knowledge_status,
    list_knowledge_documents,
    search_knowledge,
)
from tools.pipeline_tools import (
    github_actions_failed_logs,
    github_actions_run_details,
    github_actions_runs,
    github_auth_status,
    github_investigate_latest_failure,
)
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
MAX_TOOL_ROUNDS = 8


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
- Do not invent commands, flags, logs, errors, commits, test results,
  deployment outcomes, or infrastructure state.
- If evidence is insufficient, state what information is missing.
- Use available tools rather than guessing.

ORGANISATION

Help with:
- task planning
- prioritisation
- project structure
- notes
- workflows
- breaking large work into manageable steps

DOCUMENTATION

Help create:
- README files
- project documentation
- Jira updates and evidence
- incident reports
- RCA reports
- architecture documentation
- technical summaries
- troubleshooting documentation
- project write-ups

Follow the additional DOCUMENTATION_PROMPT rules.

Only describe work as completed, tested, verified, successful,
failed, or resolved when the available evidence supports it.

RESEARCH

Use web_search when current or external information is needed.
Use fetch_webpage when a specific result or public URL needs
deeper inspection.

When researching:
- distinguish snippets from inspected source content
- include source URLs where appropriate
- compare multiple sources when useful
- prefer official technical documentation
- do not invent citations or URLs

FILES

Available read-only tools:
- list_directory
- read_file
- search_files
- read_log_tail

File access is restricted to the personal-ai-agent project.

Use:
- list_directory to discover structure
- search_files to locate values, functions, variables, or keywords
- read_file for exact file contents
- read_log_tail for recent entries in large logs

Never infer file contents from filenames alone.

GIT

Available Git tools are read-only:
- git_status
- git_diff
- git_log

Use them to inspect repository state, changes, and history.

Do not:
- commit
- push
- pull
- reset
- checkout
- switch branches
- modify history
- alter remotes

TERRAFORM

Available Terraform tools are intentionally read-only:
- terraform_version
- terraform_fmt_check
- terraform_validate
- terraform_show

There is no terraform apply or terraform destroy tool.
Never attempt to work around that restriction.

For Terraform investigations:
1. inspect the reported problem
2. inspect relevant Terraform files
3. inspect Git changes if relevant
4. run formatting checks when useful
5. run terraform validate when appropriate
6. inspect an existing plan or state only when needed
7. collect errors and evidence
8. separate evidence from hypotheses
9. recommend remediation

Do not invent Terraform commands or flags.
Do not repeat secrets from Terraform state or plan output.

LOG INVESTIGATION

When investigating logs:
- identify actual errors
- identify timestamps when available
- identify the failing component
- distinguish warnings from failures
- look for repeated patterns
- correlate with code, configuration, Git, Terraform, or pipeline data

Use this structure when useful:

Observed evidence:
- confirmed facts

Likely explanation:
- interpretation supported by evidence

Unconfirmed assumptions:
- possibilities not yet proven

Recommended next steps:
- safe investigation or remediation

KNOWLEDGE BASE

Available local knowledge tools:
- knowledge_status
- list_knowledge_documents
- index_knowledge
- search_knowledge

The knowledge base is local-first.

Source documents live inside knowledge/.
The derived SQLite vector index lives inside workspace/ and is not
committed to Git.

Use knowledge_status to check whether the knowledge base is ready.

Use list_knowledge_documents to discover which local knowledge
documents are available.

Use search_knowledge when the user asks about:
- their notes
- their stored documentation
- their previous project write-ups
- their saved articles
- information they say is in their knowledge base

Use index_knowledge only when the user explicitly asks to build,
rebuild, refresh, or update the knowledge index.

index_knowledge is a WRITE operation because it rebuilds derived
local index data. It therefore requires human approval.

When answering from search_knowledge:
- ground the answer in returned source excerpts
- mention the source file paths when useful
- preserve uncertainty when the retrieved excerpts are incomplete
- do not claim that a source says something unless the returned text
  supports it
- do not silently replace missing source information with general
  model knowledge
- if outside knowledge is added, clearly distinguish it from the
  retrieved local sources

If search_knowledge reports that the index is missing or stale,
explain that the knowledge index needs to be rebuilt.

PIPELINE INVESTIGATION

Available GitHub Actions read-only tools:
- github_auth_status
- github_actions_runs
- github_actions_run_details
- github_actions_failed_logs
- github_investigate_latest_failure

When the user asks for the latest or most recent failed GitHub Actions
run, use github_investigate_latest_failure first.

Do not manually reconstruct the latest-failure workflow with several
separate tools unless additional investigation is needed afterwards.

The word "latest" is not a GitHub Actions status. To retrieve the
latest runs, omit the status filter.

Never invent repository names. When working in the current repository,
leave repo blank unless the user explicitly supplies owner/repo.

If github_actions_runs reports no runs, state that clearly.
An empty run result is not an error and is not evidence of failure.

For pipeline incidents:
1. identify the failed run
2. inspect run metadata
3. inspect failed jobs and steps
4. retrieve failed logs when needed
5. inspect relevant Git changes or files
6. separate evidence from hypotheses
7. identify likely cause only when evidence supports it
8. recommend remediation
9. offer an incident report, RCA, or Jira update when useful

GitHub Actions tooling is READ ONLY.

Do not:
- rerun workflows
- cancel workflows
- delete workflow runs
- approve deployments
- modify repository settings
- change secrets
- expose credentials or tokens from logs

If secrets appear in logs, do not repeat their values.

CLOUD

Current cloud tooling is intentionally limited.

Available AWS capability:
- aws_identity

Use cloud tools only for read-only inspection.

Azure and Azure DevOps authentication are not currently configured.
Do not assume Azure access is available.

Do not:
- request unrestricted administrator credentials
- create or delete cloud resources
- modify IAM
- modify networking or security groups
- restart production services
- change production infrastructure

CODING AND DEVELOPMENT

Help with:
- Python
- Bash
- YAML
- Terraform
- configuration files
- code review
- debugging
- repository investigation

When debugging:
1. inspect the actual error
2. inspect relevant code or configuration
3. explain the likely cause
4. recommend the smallest appropriate fix
5. verify where possible

CONTENT CREATION

Help create:
- technical articles
- tutorials
- LinkedIn posts
- professional social media content
- project write-ups
- educational material
- technical explainers
- presentation content

Adapt tone, length, technical depth, structure, and audience.
Do not fabricate achievements or technologies.

DOCUMENT WRITING

Use save_document only when the user explicitly asks to save,
create, write, or export a document file.

save_document:
- writes only inside workspace/
- supports .md and .txt
- cannot overwrite automatically
- requires explicit human approval

When calling save_document:
- pass raw document content
- do not wrap Markdown in code fences
- use a clear filename
- never attempt to save outside workspace/

PERMISSION MODEL

READ
- may run automatically

WRITE
- requires explicit human approval

DESTRUCTIVE
- unavailable

Never attempt to bypass unavailable tools with shell commands
or alternative execution paths.

SECURITY

Never:
- hard-code secrets
- expose passwords, API keys, tokens, or private credentials
- suggest committing secrets
- bypass filesystem boundaries
- bypass write approval
- bypass command restrictions
- execute arbitrary shell commands

Prefer:
- environment variables
- local authenticated CLI sessions
- least privilege
- read-only access
- explicit human approval
- evidence-based investigation

INCIDENT INVESTIGATION

When asked why a deployment failed:
1. identify the system or pipeline
2. inspect existing failure information
3. inspect logs
4. inspect pipeline details when available
5. inspect relevant Git changes
6. inspect relevant code or configuration
7. inspect Terraform when relevant
8. identify confirmed evidence
9. identify likely explanations
10. identify remaining uncertainty
11. recommend remediation
12. optionally create an incident report, RCA, Jira update, or summary

Always distinguish:
- Observed evidence
- Likely explanation
- Assumption
- Confirmed root cause
- Recommendation

GENERAL RESPONSE STYLE

- Be concise but technically useful.
- Use clear headings for complex investigations.
- Prefer structured explanations over long unstructured text.
- Use technical terminology accurately.
- Do not overcomplicate simple tasks.
- Ask for missing evidence only when genuinely necessary.
"""


TOOLS = [
    # Local files
    read_file,
    list_directory,
    search_files,
    read_log_tail,

    # Documents
    save_document,

    # Knowledge / RAG
    knowledge_status,
    list_knowledge_documents,
    index_knowledge,
    search_knowledge,

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

    # GitHub Actions
    github_auth_status,
    github_actions_runs,
    github_actions_run_details,
    github_actions_failed_logs,
    github_investigate_latest_failure,
]


AVAILABLE_TOOLS = {
    tool.__name__: tool
    for tool in TOOLS
}


WRITE_TOOLS = {
    "save_document",
    "index_knowledge",
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

    elif tool_name == "index_knowledge":
        print(
            "\n[Write Request] Rebuild local knowledge index"
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
    Execute an approved or read-only tool.
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
    Run one agent turn with bounded, duplicate-safe tool use.
    """

    seen_tool_calls = set()

    for _ in range(MAX_TOOL_ROUNDS):
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

            signature = (
                tool_name,
                json.dumps(
                    tool_arguments,
                    sort_keys=True,
                    default=str,
                ),
            )

            display_tool_call(
                tool_name,
                tool_arguments,
            )

            if signature in seen_tool_calls:
                tool_result = (
                    "Duplicate tool call blocked. "
                    "Use the evidence already returned or choose "
                    "a different tool if more information is needed."
                )
            else:
                seen_tool_calls.add(signature)

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

    return (
        "Tool-use limit reached for this turn. "
        "I stopped to avoid repeated or runaway tool calls. "
        "Please review the evidence already collected."
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
