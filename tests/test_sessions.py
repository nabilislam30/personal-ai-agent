from sessions import SessionStore


def test_session_round_trip(tmp_path):
    store = SessionStore(
        tmp_path / "sessions.sqlite3"
    )

    session = store.create_session()

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

    assert store.load_messages(
        session.id
    ) == [
        {
            "role": "user",
            "content": "Hello",
        },
        {
            "role": "assistant",
            "content": "Hi",
        },
    ]


def test_session_title_updates_from_first_prompt(tmp_path):
    store = SessionStore(
        tmp_path / "sessions.sqlite3"
    )
    session = store.create_session()

    store.update_title_from_prompt(
        session.id,
        "Investigate the latest failed GitHub Actions run",
    )

    updated = store.get_session(
        session.id
    )

    assert updated is not None
    assert updated.title.startswith(
        "Investigate the latest failed"
    )


def test_latest_session_returns_most_recent(tmp_path):
    store = SessionStore(
        tmp_path / "sessions.sqlite3"
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

    latest = store.latest_session()

    assert latest is not None
    assert latest.id == first.id
    assert second.id != latest.id
