import io

import web_app
from sessions import SessionStore


def _client(
    tmp_path,
):
    store = SessionStore(
        tmp_path / "sessions.sqlite3"
    )

    app = web_app.create_app(
        store=store
    )
    app.config.update(
        TESTING=True
    )

    return app.test_client()


def test_home_loads(
    tmp_path,
):
    client = _client(
        tmp_path
    )

    response = client.get("/")

    assert response.status_code == 200
    assert (
        b"Personal AI Agent"
        in response.data
    )


def test_chat_persists_response(
    monkeypatch,
    tmp_path,
):
    store = SessionStore(
        tmp_path / "sessions.sqlite3"
    )
    session = store.create_session()

    monkeypatch.setattr(
        web_app,
        "run_agent_turn",
        lambda *args, **kwargs: "Test response",
    )

    app = web_app.create_app(
        store=store
    )
    app.config.update(
        TESTING=True
    )

    client = app.test_client()

    response = client.post(
        "/api/chat",
        json={
            "session_id": session.id,
            "prompt": "Hello",
            "approve_writes": False,
        },
    )

    assert response.status_code == 200
    assert (
        response.get_json()["response"]
        == "Test response"
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
            "content": "Test response",
        },
    ]


def test_upload_rejects_unsupported_extension(
    tmp_path,
):
    client = _client(
        tmp_path
    )

    response = client.post(
        "/api/knowledge/upload",
        data={
            "file": (
                io.BytesIO(b"data"),
                "payload.exe",
            )
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert (
        "Unsupported"
        in response.get_json()["error"]
    )


def test_upload_saves_supported_file_without_overwrite(
    monkeypatch,
    tmp_path,
):
    root = tmp_path / "knowledge"

    monkeypatch.setattr(
        web_app,
        "KNOWLEDGE_ROOT",
        root,
    )
    monkeypatch.setattr(
        web_app,
        "knowledge_status",
        lambda: "status",
    )

    client = _client(
        tmp_path
    )

    first = client.post(
        "/api/knowledge/upload",
        data={
            "file": (
                io.BytesIO(b"hello"),
                "notes.txt",
            )
        },
        content_type="multipart/form-data",
    )

    second = client.post(
        "/api/knowledge/upload",
        data={
            "file": (
                io.BytesIO(b"again"),
                "notes.txt",
            )
        },
        content_type="multipart/form-data",
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert (
        root / "inbox" / "notes.txt"
    ).read_bytes() == b"hello"


def test_reindex_requires_explicit_confirmation(
    tmp_path,
):
    client = _client(
        tmp_path
    )

    response = client.post(
        "/api/knowledge/reindex",
        json={
            "confirm": False,
        },
    )

    assert response.status_code == 400
    assert (
        "Explicit confirmation"
        in response.get_json()["error"]
    )
