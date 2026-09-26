from agent import build_messages, run_agent_turn
from config import CHAT_MODEL, SESSION_HISTORY_LIMIT
from sessions import SessionStore


def _print_sessions(
    store: SessionStore,
) -> None:
    sessions = store.list_sessions()

    if not sessions:
        print("\nNo saved sessions.")
        return

    print("\nSaved sessions:")

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
        for session in store.list_sessions(limit=100)
        if session.id.startswith(prefix)
    ]

    if len(matches) == 1:
        return matches[0]

    if not matches:
        print(
            f"\nNo session matches '{prefix}'."
        )
    else:
        print(
            f"\nMore than one session matches '{prefix}'. "
            "Use a longer ID prefix."
        )

    return None


def main() -> None:
    store = SessionStore()
    session = store.get_or_create_latest_session()
    history = store.load_messages(
        session.id,
        limit=SESSION_HISTORY_LIMIT,
    )
    messages = build_messages(history)

    print("Personal AI Agent")
    print(f"Model: {CHAT_MODEL}")
    print(
        f"Session: {session.id[:8]} "
        f"({session.title})"
    )
    print(
        "Commands: /new, /sessions, /use <id>, /help, exit"
    )

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

        if user_prompt == "/help":
            print(
                "\n/new          Start a new conversation\n"
                "/sessions     List saved conversations\n"
                "/use <id>     Switch to a saved conversation\n"
                "exit          Quit"
            )
            continue

        if user_prompt == "/sessions":
            _print_sessions(store)
            continue

        if user_prompt == "/new":
            session = store.create_session()
            messages = build_messages()
            print(
                f"\nStarted session {session.id[:8]}."
            )
            continue

        if user_prompt.startswith("/use "):
            prefix = user_prompt[5:].strip()
            selected = _resolve_session(
                store,
                prefix,
            )

            if selected is None:
                continue

            session = selected
            history = store.load_messages(
                session.id,
                limit=SESSION_HISTORY_LIMIT,
            )
            messages = build_messages(history)

            print(
                f"\nSwitched to {session.id[:8]} "
                f"({session.title})."
            )
            continue

        store.update_title_from_prompt(
            session.id,
            user_prompt,
        )

        messages.append(
            {
                "role": "user",
                "content": user_prompt,
            }
        )
        store.add_message(
            session.id,
            "user",
            user_prompt,
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

        store.add_message(
            session.id,
            "assistant",
            assistant_response,
        )

        print(
            f"\nAgent: {assistant_response}"
        )


if __name__ == "__main__":
    main()
