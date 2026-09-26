from dataclasses import dataclass
import re

from config import (
    SIMPLE_CHAT_HISTORY_LIMIT,
    TOOL_HISTORY_LIMIT,
)


@dataclass(frozen=True)
class RouteDecision:
    name: str
    reason: str


LATEST_FAILURE_PATTERNS = (
    "latest failed github actions",
    "most recent failed github actions",
    "latest github actions failure",
    "most recent github actions failure",
    "latest failed workflow",
    "most recent failed workflow",
)

DOMAIN_PATTERNS = {
    "knowledge": (
        "my knowledge",
        "knowledge base",
        "my notes",
        "my documents",
        "my documentation",
        "what have i documented",
        "what did i document",
        "uploaded document",
        "uploaded file",
        "my pdf",
        "my docx",
        "stored project",
        "search my knowledge",
    ),
    "pipeline": (
        "github actions",
        "workflow run",
        "workflow failure",
        "pipeline failure",
        "failed pipeline",
        "ci failure",
        "ci run",
    ),
    "aws": (
        "aws",
        "ec2",
        "ecs",
        "eks",
        "cloudwatch",
        "route 53",
        "route53",
        "s3 bucket",
        "s3 buckets",
    ),
    "terraform": (
        "terraform",
        ".tf",
        "tfplan",
    ),
    "git": (
        "git status",
        "git diff",
        "git log",
        "commit history",
        "staged changes",
        "unstaged changes",
    ),
    "files": (
        "read file",
        "open file",
        "list directory",
        "list files",
        "search files",
        "find in file",
        "repository file",
        "repo file",
        "log file",
    ),
    "documentation": (
        "write a readme",
        "create a readme",
        "draft a readme",
        "incident report",
        "root cause analysis",
        "rca",
        "jira update",
        "architecture document",
        "troubleshooting document",
        "save document",
        "save this",
        "export this",
    ),
    "research": (
        "search the web",
        "research",
        "look up",
        "find online",
        "official documentation",
        "official docs",
        "latest version",
        "current version",
    ),
}


def _normalise(
    prompt: str,
) -> str:
    return re.sub(
        r"\s+",
        " ",
        prompt.strip().lower(),
    )


def route_request(
    prompt: str,
) -> RouteDecision:
    """
    Deterministically route a request before the LLM sees tool schemas.
    """

    text = _normalise(
        prompt
    )

    if not text:
        return RouteDecision(
            name="simple_chat",
            reason="empty or whitespace-only input",
        )

    if any(
        pattern in text
        for pattern in LATEST_FAILURE_PATTERNS
    ):
        return RouteDecision(
            name="pipeline_latest_failure",
            reason=(
                "explicit latest failed pipeline investigation"
            ),
        )

    for route_name, patterns in DOMAIN_PATTERNS.items():
        if any(
            pattern in text
            for pattern in patterns
        ):
            return RouteDecision(
                name=route_name,
                reason=(
                    f"matched {route_name} intent"
                ),
            )

    word_count = len(
        text.split()
    )

    if word_count <= 24:
        return RouteDecision(
            name="simple_chat",
            reason=(
                "short request with no tool-domain indicators"
            ),
        )

    return RouteDecision(
        name="general",
        reason=(
            "general request with no tool-domain indicators"
        ),
    )


def history_limit_for_route(
    route: RouteDecision,
) -> int:
    if route.name in {
        "simple_chat",
        "general",
    }:
        return SIMPLE_CHAT_HISTORY_LIMIT

    return TOOL_HISTORY_LIMIT
