from sessions import SessionStore


def test_session_round_trip(
    tmp_path,
):
    store = SessionStore(
        tmp_path
        / "sessions.sqlite3"
    )

    session = (
        store.create_session()
    )

    store.add_message(
        session.id,
        "user",
        "Hello",
    )
    store.add_message(
        session.id,
        "assistant",
        "Hi",
    )

    assert (
        store.load_messages(
            session.id
        )
        == [
            {
                "role": "user",
                "content": "Hello",
            },
            {
                "role": "assistant",
                "content": "Hi",
            },
        ]
    )


def test_session_title_updates_from_first_prompt(
    tmp_path,
):
    store = SessionStore(
        tmp_path
        / "sessions.sqlite3"
    )
    session = (
        store.create_session()
    )

    store.update_title_from_prompt(
        session.id,
        (
            "Investigate the latest "
            "failed GitHub Actions run"
        ),
    )

    updated = (
        store.get_session(
            session.id
        )
    )

    assert updated is not None
    assert updated.title.startswith(
        "Investigate the latest failed"
    )


def test_latest_session_returns_most_recent(
    tmp_path,
):
    store = SessionStore(
        tmp_path
        / "sessions.sqlite3"
    )

    first = store.create_session(
        "first"
    )
    second = store.create_session(
        "second"
    )

    store.add_message(
        first.id,
        "user",
        "make first newest",
    )

    latest = (
        store.latest_session()
    )

    assert latest is not None
    assert latest.id == first.id
    assert second.id != latest.id


def test_context_compacts_older_messages(
    tmp_path,
):
    store = SessionStore(
        tmp_path
        / "sessions.sqlite3"
    )

    session = (
        store.create_session()
    )

    for number in range(6):
        store.add_message(
            session.id,
            (
                "user"
                if number % 2 == 0
                else "assistant"
            ),
            f"message {number}",
        )

    context = (
        store.load_context_messages(
            session.id,
            recent_limit=2,
        )
    )

    assert (
        context[0]["role"]
        == "system"
    )
    assert (
        "message 0"
        in context[0]["content"]
    )
    assert len(context) == 3
    assert (
        context[-1]["content"]
        == "message 5"
    )
