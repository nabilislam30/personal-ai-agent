import agent


def test_unknown_tool_is_rejected():
    result = agent.execute_tool(
        "does_not_exist",
        {},
    )

    assert "Unknown tool" in result


def test_write_tool_can_be_denied():
    result = agent.execute_tool(
        "save_document",
        {
            "file_path": "blocked.md",
            "content": "blocked",
        },
        approval_callback=lambda *_: False,
    )

    assert result == "Write cancelled by user."


def test_messages_start_with_system_prompt():
    messages = agent.build_messages(
        [
            {
                "role": "user",
                "content": "hello",
            }
        ]
    )

    assert messages[0]["role"] == "system"
    assert messages[1] == {
        "role": "user",
        "content": "hello",
    }
