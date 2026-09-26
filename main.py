from agent import (
    build_messages,
    preload_model,
    run_agent_turn_with_metrics,
)
from config import (
    CHAT_MODEL,
    PRELOAD_MODEL,
    SHOW_TIMINGS,
)
from router import (
    history_limit_for_route,
    route_request,
)
from sessions import SessionStore


def _print_sessions(
    store: SessionStore,
) -> None:
    sessions = (
        store.list_sessions()
    )

    if not sessions:
        print(
            "\nNo saved sessions."
        )
        return

    print(
        "\nSaved sessions:"
    )

    for session in sessions:
        print(
            f"- {session.id[:8]}  "
            f"{session.title}  "
            f"({session.updated_at})"
        )


def _resolve_session(
    store: SessionStore,
    prefix: str,
):
    matches = [
        session
        for session in (
            store.list_sessions(
                limit=100
            )
        )
        if session.id.startswith(
            prefix
        )
    ]

    if len(matches) == 1:
        return matches[0]

    if not matches:
        print(
            f"\nNo session matches "
            f"'{prefix}'."
        )
    else:
        print(
            "\nMore than one session "
            f"matches '{prefix}'. "
            "Use a longer ID prefix."
        )

    return None


def main() -> None:
    store = SessionStore()
    session = (
        store
        .get_or_create_latest_session()
    )

    print(
        "Personal AI Agent"
    )
    print(
        f"Model: {CHAT_MODEL}"
    )
    print(
        f"Session: "
        f"{session.id[:8]} "
        f"({session.title})"
    )
    print(
        "Commands: /new, "
        "/sessions, "
        "/use <id>, "
        "/help, exit"
    )

    if PRELOAD_MODEL:
        print(
            preload_model()
        )

    while True:
        try:
            user_prompt = input(
                "\nYou: "
            ).strip()
        except (
            KeyboardInterrupt,
            EOFError,
        ):
            print(
                "\n\nAgent: Goodbye."
            )
            break

        if user_prompt.lower() in {
            "exit",
            "quit",
        }:
            print(
                "\nAgent: Goodbye."
            )
            break

        if not user_prompt:
            continue

        if user_prompt == "/help":
            print(
                "\n/new          "
                "Start a new conversation\n"
                "/sessions     "
                "List saved conversations\n"
                "/use <id>     "
                "Switch to a saved conversation\n"
                "exit          Quit"
            )
            continue

        if user_prompt == "/sessions":
            _print_sessions(
                store
            )
            continue

        if user_prompt == "/new":
            session = (
                store
                .create_session()
            )

            print(
                f"\nStarted session "
                f"{session.id[:8]}."
            )
            continue

        if user_prompt.startswith(
            "/use "
        ):
            prefix = (
                user_prompt[5:]
                .strip()
            )

            selected = (
                _resolve_session(
                    store,
                    prefix,
                )
            )

            if selected is None:
                continue

            session = selected

            print(
                f"\nSwitched to "
                f"{session.id[:8]} "
                f"({session.title})."
            )
            continue

        route = route_request(
            user_prompt
        )

        history = (
            store
            .load_context_messages(
                session.id,
                recent_limit=(
                    history_limit_for_route(
                        route
                    )
                ),
            )
        )

        messages = build_messages(
            history,
            route_name=route.name,
        )

        messages.append(
            {
                "role": "user",
                "content": user_prompt,
            }
        )

        try:
            result = (
                run_agent_turn_with_metrics(
                    messages=messages,
                    user_prompt=user_prompt,
                    route=route,
                )
            )
        except Exception as error:
            print(
                f"\nAgent error: "
                f"{error}"
            )
            continue

        store.update_title_from_prompt(
            session.id,
            user_prompt,
        )

        store.add_message(
            session.id,
            "user",
            user_prompt,
        )

        store.add_message(
            session.id,
            "assistant",
            result.content,
        )

        print(
            f"\nAgent: "
            f"{result.content}"
        )

        if SHOW_TIMINGS:
            print(
                "\n[Performance] "
                f"route={result.route} | "
                f"tools={result.tool_calls} | "
                f"model={result.model_ms:.0f}ms | "
                f"total={result.total_ms:.0f}ms"
            )


if __name__ == "__main__":
    main()
