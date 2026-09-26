import json
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from time import perf_counter

from ollama import chat, generate

from config import (
    CHAT_MODEL,
    MAX_TOOL_ROUNDS,
    OLLAMA_KEEP_ALIVE,
)
from permissions import (
    request_write_approval,
    requires_write_approval,
)
from prompts.documentation import DOCUMENTATION_PROMPT
from prompts.system import system_prompt_for_route
from router import (
    RouteDecision,
    route_request,
)
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


FILE_TOOLS = [
    read_file,
    list_directory,
    search_files,
    read_log_tail,
]

KNOWLEDGE_TOOLS = [
    knowledge_status,
    list_knowledge_documents,
    index_knowledge,
    search_knowledge,
]

RESEARCH_TOOLS = [
    web_search,
    fetch_webpage,
]

GIT_TOOLS = [
    git_status,
    git_diff,
    git_log,
]

TERRAFORM_TOOLS = [
    terraform_version,
    terraform_fmt_check,
    terraform_validate,
    terraform_show,
]

AWS_TOOLS = [
    aws_identity,
    aws_region,
    aws_ec2_instances,
    aws_ecs_clusters,
    aws_ecs_services,
    aws_eks_clusters,
    aws_cloudwatch_alarms,
    aws_route53_hosted_zones,
    aws_s3_buckets,
]

PIPELINE_TOOLS = [
    github_auth_status,
    github_actions_runs,
    github_actions_run_details,
    github_actions_failed_logs,
    github_investigate_latest_failure,
]

TOOLS_BY_ROUTE = {
    "simple_chat": [],
    "general": [],
    "knowledge": KNOWLEDGE_TOOLS,
    "pipeline": PIPELINE_TOOLS + GIT_TOOLS,
    "pipeline_latest_failure": [],
    "aws": AWS_TOOLS,
    "terraform": (
        TERRAFORM_TOOLS
        + FILE_TOOLS
        + GIT_TOOLS
    ),
    "git": GIT_TOOLS + FILE_TOOLS,
    "files": FILE_TOOLS,
    "research": RESEARCH_TOOLS,
    "documentation": (
        [save_document]
        + FILE_TOOLS
        + KNOWLEDGE_TOOLS
    ),
}

ALL_TOOLS = []
for tool_group in TOOLS_BY_ROUTE.values():
    for tool in tool_group:
        if tool not in ALL_TOOLS:
            ALL_TOOLS.append(tool)

AVAILABLE_TOOLS = {
    tool.__name__: tool
    for tool in ALL_TOOLS
}


@dataclass(frozen=True)
class AgentResult:
    content: str
    route: str
    route_reason: str
    tool_calls: int
    model_ms: float
    total_ms: float


def preload_model() -> str:
    """
    Ask Ollama to load the chat model and keep it resident.

    Failure is returned as text so application startup can continue.
    """

    started = perf_counter()

    try:
        generate(
            model=CHAT_MODEL,
            prompt="",
            think=False,
            keep_alive=OLLAMA_KEEP_ALIVE,
        )
    except Exception as error:
        return (
            "Model preload failed: "
            f"{error}"
        )

    elapsed_ms = (
        perf_counter()
        - started
    ) * 1000

    return (
        f"Model preloaded in "
        f"{elapsed_ms:.0f} ms."
    )


def build_system_message(
    route_name: str = "general",
) -> dict[str, str]:
    prompt = system_prompt_for_route(
        route_name
    )

    if route_name == "documentation":
        prompt = (
            prompt
            + "\n\n"
            + DOCUMENTATION_PROMPT
        )

    return {
        "role": "system",
        "content": prompt,
    }


def build_messages(
    history: list[dict[str, str]] | None = None,
    route_name: str = "general",
) -> list:
    messages: list = [
        build_system_message(
            route_name
        ),
    ]

    if history:
        messages.extend(history)

    return messages


def tools_for_route(
    route_name: str,
) -> list:
    return list(
        TOOLS_BY_ROUTE.get(
            route_name,
            [],
        )
    )


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
            tool_arguments.get(
                "content",
                "",
            )
        )

        print(
            f"\n[Tool] save_document("
            f"file_path='{file_path}', "
            f"content={len(content)} chars)"
        )
        return

    print(
        f"\n[Tool] "
        f"{tool_name}({tool_arguments})"
    )


def execute_tool(
    tool_name: str,
    tool_arguments: dict,
    approval_callback: Callable[
        [str, dict],
        bool,
    ] = request_write_approval,
) -> str:
    function_to_call = (
        AVAILABLE_TOOLS.get(
            tool_name
        )
    )

    if function_to_call is None:
        return (
            "Error: Unknown or unavailable "
            f"tool requested: {tool_name}"
        )

    if requires_write_approval(
        tool_name
    ):
        approved = approval_callback(
            tool_name,
            tool_arguments,
        )

        if not approved:
            return (
                "Write cancelled by user."
            )

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


def _add_direct_evidence(
    messages: list,
    route: RouteDecision,
    user_prompt: str,
) -> bool:
    """
    Gather evidence deterministically for predictable high-value routes.
    """

    if (
        route.name
        == "pipeline_latest_failure"
    ):
        evidence = (
            github_investigate_latest_failure()
        )

        messages.append(
            {
                "role": "system",
                "content": (
                    "Current read-only GitHub "
                    "Actions evidence:\n"
                    + evidence
                ),
            }
        )
        return True

    if route.name == "knowledge":
        lowered = user_prompt.lower()

        if any(
            phrase in lowered
            for phrase in (
                "rebuild my knowledge",
                "rebuild the knowledge",
                "refresh my knowledge",
                "refresh the knowledge",
                "update my knowledge index",
                "update the knowledge index",
                "index my knowledge",
            )
        ):
            return False

        if (
            "knowledge status"
            in lowered
            or "status of my knowledge"
            in lowered
        ):
            evidence = knowledge_status()
        elif any(
            phrase in lowered
            for phrase in (
                "list my knowledge",
                "list knowledge documents",
                "what documents are in my knowledge",
                "what files are in my knowledge",
            )
        ):
            evidence = list_knowledge_documents()
        else:
            evidence = search_knowledge(
                user_prompt,
                top_k=5,
            )

        messages.append(
            {
                "role": "system",
                "content": (
                    "Current local knowledge "
                    "evidence:\n"
                    + evidence
                ),
            }
        )
        return True

    return False


def _chat_once(
    messages: list,
    tools: list | None = None,
    think: bool | str | None = None,
):
    arguments = {
        "model": CHAT_MODEL,
        "messages": messages,
        "keep_alive": OLLAMA_KEEP_ALIVE,
    }

    if tools:
        arguments["tools"] = tools

    if think is not None:
        arguments["think"] = think

    return chat(
        **arguments
    )


def _run_tool_loop(
    messages: list,
    tools: list,
    approval_callback: Callable[
        [str, dict],
        bool,
    ],
) -> tuple[str, int, float]:
    seen_tool_calls = set()
    tool_call_count = 0
    model_ms = 0.0

    for _ in range(
        MAX_TOOL_ROUNDS
    ):
        model_started = (
            perf_counter()
        )

        response = _chat_once(
            messages,
            tools=tools,
        )

        model_ms += (
            perf_counter()
            - model_started
        ) * 1000

        messages.append(
            response.message
        )

        if not response.message.tool_calls:
            return (
                response.message.content
                or "(No response returned.)",
                tool_call_count,
                model_ms,
            )

        for tool_call in (
            response.message.tool_calls
        ):
            tool_name = (
                tool_call.function.name
            )
            tool_arguments = dict(
                tool_call
                .function
                .arguments
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
                    "Use evidence already returned "
                    "or choose a different tool."
                )
            else:
                seen_tool_calls.add(
                    signature
                )
                tool_call_count += 1

                tool_result = execute_tool(
                    tool_name,
                    tool_arguments,
                    approval_callback,
                )

            messages.append(
                {
                    "role": "tool",
                    "tool_name": (
                        tool_name
                    ),
                    "content": (
                        tool_result
                    ),
                }
            )

    return (
        "Tool-use limit reached for this turn. "
        "I stopped to avoid repeated or runaway "
        "tool calls.",
        tool_call_count,
        model_ms,
    )


def run_agent_turn_with_metrics(
    messages: list,
    user_prompt: str,
    route: RouteDecision | None = None,
    approval_callback: Callable[
        [str, dict],
        bool,
    ] = request_write_approval,
) -> AgentResult:
    started = perf_counter()

    route = (
        route
        or route_request(
            user_prompt
        )
    )

    direct_evidence = (
        _add_direct_evidence(
            messages,
            route,
            user_prompt,
        )
    )

    tools = (
        []
        if direct_evidence
        else tools_for_route(
            route.name
        )
    )

    model_started = (
        perf_counter()
    )

    if tools:
        (
            content,
            tool_calls,
            model_ms,
        ) = _run_tool_loop(
            messages,
            tools,
            approval_callback,
        )
    else:
        response = _chat_once(
            messages,
            think=False,
        )

        model_ms = (
            perf_counter()
            - model_started
        ) * 1000

        content = (
            response.message.content
            or "(No response returned.)"
        )

        messages.append(
            response.message
        )
        tool_calls = 0

    total_ms = (
        perf_counter()
        - started
    ) * 1000

    return AgentResult(
        content=content,
        route=route.name,
        route_reason=route.reason,
        tool_calls=tool_calls,
        model_ms=model_ms,
        total_ms=total_ms,
    )


def run_agent_turn(
    messages: list,
    user_prompt: str = "",
    route: RouteDecision | None = None,
    approval_callback: Callable[
        [str, dict],
        bool,
    ] = request_write_approval,
) -> str:
    if not user_prompt:
        user_prompt = (
            str(
                messages[-1].get(
                    "content",
                    "",
                )
            )
            if messages
            and isinstance(
                messages[-1],
                dict,
            )
            else ""
        )

    result = (
        run_agent_turn_with_metrics(
            messages=messages,
            user_prompt=user_prompt,
            route=route,
            approval_callback=(
                approval_callback
            ),
        )
    )

    return result.content


def stream_agent_turn(
    messages: list,
    user_prompt: str,
    route: RouteDecision | None = None,
    approval_callback: Callable[
        [str, dict],
        bool,
    ] = request_write_approval,
) -> Iterator[dict]:
    """
    Stream low-latency routes token-by-token.

    Tool-heavy routes fall back to the bounded non-streaming tool loop
    because Ollama tool selection requires complete structured calls.
    """

    started = perf_counter()

    route = (
        route
        or route_request(
            user_prompt
        )
    )

    yield {
        "type": "meta",
        "route": route.name,
        "route_reason": route.reason,
    }

    direct_evidence = (
        _add_direct_evidence(
            messages,
            route,
            user_prompt,
        )
    )

    tools = (
        []
        if direct_evidence
        else tools_for_route(
            route.name
        )
    )

    if tools:
        result = (
            run_agent_turn_with_metrics(
                messages=messages,
                user_prompt=user_prompt,
                route=route,
                approval_callback=approval_callback,
            )
        )

        yield {
            "type": "token",
            "content": result.content,
        }
        yield {
            "type": "done",
            "route": result.route,
            "tool_calls": (
                result.tool_calls
            ),
            "first_token_ms": None,
            "model_ms": (
                round(
                    result.model_ms,
                    1,
                )
            ),
            "total_ms": (
                round(
                    result.total_ms,
                    1,
                )
            ),
        }
        return

    first_token_ms = None
    model_started = perf_counter()
    content_parts = []

    try:
        stream = chat(
            model=CHAT_MODEL,
            messages=messages,
            stream=True,
            think=False,
            keep_alive=(
                OLLAMA_KEEP_ALIVE
            ),
        )

        for chunk in stream:
            content = (
                chunk.message.content
                or ""
            )

            if not content:
                continue

            if first_token_ms is None:
                first_token_ms = (
                    perf_counter()
                    - model_started
                ) * 1000

            content_parts.append(
                content
            )

            yield {
                "type": "token",
                "content": content,
            }

    except Exception as error:
        yield {
            "type": "error",
            "error": str(error),
        }
        return

    full_content = "".join(
        content_parts
    )

    messages.append(
        {
            "role": "assistant",
            "content": full_content,
        }
    )

    model_ms = (
        perf_counter()
        - model_started
    ) * 1000

    total_ms = (
        perf_counter()
        - started
    ) * 1000

    yield {
        "type": "done",
        "route": route.name,
        "tool_calls": 0,
        "first_token_ms": (
            round(
                first_token_ms,
                1,
            )
            if first_token_ms
            is not None
            else None
        ),
        "model_ms": (
            round(
                model_ms,
                1,
            )
        ),
        "total_ms": (
            round(
                total_ms,
                1,
            )
        ),
    }
