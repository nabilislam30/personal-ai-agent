import json
from collections.abc import Callable

from ollama import chat

from config import CHAT_MODEL, MAX_TOOL_ROUNDS
from permissions import (
    request_write_approval,
    requires_write_approval,
)
from prompts.documentation import DOCUMENTATION_PROMPT
from prompts.system import SYSTEM_PROMPT
from tools.cloud_tools import (
    aws_cloudwatch_alarms,
    aws_ec2_instances,
    aws_ecs_clusters,
    aws_ecs_services,
    aws_eks_clusters,
    aws_identity,
    aws_region,
    aws_route53_hosted_zones,
    aws_s3_buckets,
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
from tools.knowledge_tools import (
    index_knowledge,
    knowledge_status,
    list_knowledge_documents,
    search_knowledge,
)
from tools.log_tools import read_log_tail
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


TOOLS = [
    read_file,
    list_directory,
    search_files,
    read_log_tail,
    save_document,
    knowledge_status,
    list_knowledge_documents,
    index_knowledge,
    search_knowledge,
    web_search,
    fetch_webpage,
    git_status,
    git_diff,
    git_log,
    terraform_version,
    terraform_fmt_check,
    terraform_validate,
    terraform_show,
    aws_identity,
    aws_region,
    aws_ec2_instances,
    aws_ecs_clusters,
    aws_ecs_services,
    aws_eks_clusters,
    aws_cloudwatch_alarms,
    aws_route53_hosted_zones,
    aws_s3_buckets,
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


def build_system_message() -> dict[str, str]:
    return {
        "role": "system",
        "content": (
            SYSTEM_PROMPT
            + "\n\n"
            + DOCUMENTATION_PROMPT
        ),
    }


def build_messages(
    history: list[dict[str, str]] | None = None,
) -> list:
    messages: list = [
        build_system_message(),
    ]

    if history:
        messages.extend(history)

    return messages


def display_tool_call(
    tool_name: str,
    tool_arguments: dict,
) -> None:
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
    approval_callback: Callable[
        [str, dict],
        bool,
    ] = request_write_approval,
) -> str:
    function_to_call = AVAILABLE_TOOLS.get(
        tool_name
    )

    if function_to_call is None:
        return (
            f"Error: Unknown tool requested: {tool_name}"
        )

    if requires_write_approval(tool_name):
        approved = approval_callback(
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


def run_agent_turn(
    messages: list,
    approval_callback: Callable[
        [str, dict],
        bool,
    ] = request_write_approval,
) -> str:
    seen_tool_calls = set()

    for _ in range(MAX_TOOL_ROUNDS):
        response = chat(
            model=CHAT_MODEL,
            messages=messages,
            tools=TOOLS,
        )

        messages.append(response.message)

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
                    approval_callback,
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
