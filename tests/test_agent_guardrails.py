import agent
from router import RouteDecision


def test_unknown_tool_is_rejected():
    result = agent.execute_tool(
        "does_not_exist",
        {},
    )

    assert (
        "Unknown or unavailable tool"
        in result
    )


def test_write_tool_can_be_denied():
    result = agent.execute_tool(
        "save_document",
        {
            "file_path": "blocked.md",
            "content": "blocked",
        },
        approval_callback=lambda *_: False,
    )

    assert (
        result
        == "Write cancelled by user."
    )


def test_simple_route_has_no_tools():
    assert (
        agent.tools_for_route(
            "simple_chat"
        )
        == []
    )


def test_aws_route_does_not_receive_git_or_terraform_tools():
    names = {
        tool.__name__
        for tool in agent.tools_for_route(
            "aws"
        )
    }

    assert "aws_identity" in names
    assert "git_status" not in names
    assert "terraform_validate" not in names
    assert "web_search" not in names


def test_documentation_prompt_only_added_for_documentation_route():
    normal = (
        agent.build_system_message(
            "simple_chat"
        )["content"]
    )
    documentation = (
        agent.build_system_message(
            "documentation"
        )["content"]
    )

    assert (
        len(documentation)
        > len(normal)
    )
    assert (
        "DOCUMENTATION WORKFLOW"
        not in normal
    )


def test_simple_chat_disables_thinking(
    monkeypatch,
):
    captured = {}

    class Message:
        content = "Personal AI Agent"
        tool_calls = None

    class Response:
        message = Message()

    def fake_chat(**kwargs):
        captured.update(kwargs)
        return Response()

    monkeypatch.setattr(
        agent,
        "chat",
        fake_chat,
    )

    messages = (
        agent.build_messages(
            route_name="simple_chat"
        )
    )
    messages.append(
        {
            "role": "user",
            "content": (
                "What is your name?"
            ),
        }
    )

    result = (
        agent.run_agent_turn_with_metrics(
            messages=messages,
            user_prompt=(
                "What is your name?"
            ),
            route=RouteDecision(
                name="simple_chat",
                reason="test",
            ),
        )
    )

    assert (
        result.content
        == "Personal AI Agent"
    )
    assert (
        captured["think"]
        is False
    )
    assert (
        "tools"
        not in captured
    )
