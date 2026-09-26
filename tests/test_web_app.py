import io
import json

from werkzeug.security import (
    generate_password_hash,
)

import web_app
from sessions import SessionStore


def _client(
    tmp_path,
):
    store = SessionStore(
        tmp_path
        / "sessions.sqlite3"
    )

    app = web_app.create_app(
        store=store
    )
    app.config.update(
        TESTING=True
    )

    return (
        app.test_client(),
        store,
    )


def _csrf(
    client,
) -> str:
    client.get("/")

    with (
        client
        .session_transaction()
    ) as flask_session:
        return flask_session[
            "_csrf_token"
        ]


def test_home_loads(
    tmp_path,
):
    client, _ = _client(
        tmp_path
    )

    response = client.get("/")

    assert (
        response.status_code
        == 200
    )
    assert (
        b"Personal AI Agent"
        in response.data
    )


def test_chat_stream_persists_response(
    monkeypatch,
    tmp_path,
):
    client, store = _client(
        tmp_path
    )
    selected = (
        store.create_session()
    )

    def fake_stream(
        **_kwargs,
    ):
        yield {
            "type": "meta",
            "route": "simple_chat",
            "route_reason": "test",
        }
        yield {
            "type": "token",
            "content": "Test ",
        }
        yield {
            "type": "token",
            "content": "response",
        }
        yield {
            "type": "done",
            "route": "simple_chat",
            "tool_calls": 0,
            "first_token_ms": 10.0,
            "model_ms": 20.0,
            "total_ms": 25.0,
        }

    monkeypatch.setattr(
        web_app,
        "stream_agent_turn",
        fake_stream,
    )

    token = _csrf(
        client
    )

    response = client.post(
        "/api/chat/stream",
        json={
            "session_id": (
                selected.id
            ),
            "prompt": "Hello",
            "approve_writes": False,
        },
        headers={
            "X-CSRF-Token": token,
        },
    )

    assert (
        response.status_code
        == 200
    )

    events = [
        json.loads(line)
        for line in (
            response
            .get_data(
                as_text=True
            )
            .splitlines()
        )
        if line
    ]

    assert any(
        event.get("type")
        == "done"
        for event in events
    )

    assert (
        store.load_messages(
            selected.id
        )
        == [
            {
                "role": "user",
                "content": "Hello",
            },
            {
                "role": "assistant",
                "content": (
                    "Test response"
                ),
            },
        ]
    )


def test_post_requires_csrf(
    tmp_path,
):
    client, _ = _client(
        tmp_path
    )

    response = client.post(
        "/api/sessions"
    )

    assert (
        response.status_code
        == 400
    )
    assert (
        "CSRF"
        in response.get_json()[
            "error"
        ]
    )


def test_upload_rejects_unsupported_extension(
    tmp_path,
):
    client, _ = _client(
        tmp_path
    )
    token = _csrf(
        client
    )

    response = client.post(
        "/api/knowledge/upload",
        data={
            "file": (
                io.BytesIO(b"data"),
                "payload.exe",
            )
        },
        content_type=(
            "multipart/form-data"
        ),
        headers={
            "X-CSRF-Token": token,
        },
    )

    assert (
        response.status_code
        == 400
    )
    assert (
        "Unsupported"
        in response.get_json()[
            "error"
        ]
    )


def test_upload_saves_supported_file_without_overwrite(
    monkeypatch,
    tmp_path,
):
    root = (
        tmp_path
        / "knowledge"
    )

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

    client, _ = _client(
        tmp_path
    )
    token = _csrf(
        client
    )

    first = client.post(
        "/api/knowledge/upload",
        data={
            "file": (
                io.BytesIO(
                    b"hello"
                ),
                "notes.txt",
            )
        },
        content_type=(
            "multipart/form-data"
        ),
        headers={
            "X-CSRF-Token": token,
        },
    )

    second = client.post(
        "/api/knowledge/upload",
        data={
            "file": (
                io.BytesIO(
                    b"again"
                ),
                "notes.txt",
            )
        },
        content_type=(
            "multipart/form-data"
        ),
        headers={
            "X-CSRF-Token": token,
        },
    )

    assert (
        first.status_code
        == 201
    )
    assert (
        second.status_code
        == 409
    )
    assert (
        root
        / "inbox"
        / "notes.txt"
    ).read_bytes() == b"hello"


def test_reindex_requires_explicit_confirmation(
    tmp_path,
):
    client, _ = _client(
        tmp_path
    )
    token = _csrf(
        client
    )

    response = client.post(
        "/api/knowledge/reindex",
        json={
            "confirm": False,
        },
        headers={
            "X-CSRF-Token": token,
        },
    )

    assert (
        response.status_code
        == 400
    )
    assert (
        "Explicit confirmation"
        in response.get_json()[
            "error"
        ]
    )


def test_authentication_can_protect_home(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        web_app,
        "WEB_REQUIRE_AUTH",
        True,
    )
    monkeypatch.setattr(
        web_app,
        "WEB_PASSWORD_HASH",
        generate_password_hash(
            "test-password"
        ),
    )
    monkeypatch.setattr(
        web_app,
        "WEB_SECRET_KEY",
        "test-secret",
    )

    store = SessionStore(
        tmp_path
        / "sessions.sqlite3"
    )
    app = web_app.create_app(
        store=store
    )
    app.config.update(
        TESTING=True
    )

    client = app.test_client()

    protected = client.get(
        "/"
    )

    assert (
        protected.status_code
        == 302
    )
    assert (
        "/login"
        in protected.headers[
            "Location"
        ]
    )

    client.get(
        "/login"
    )

    with (
        client
        .session_transaction()
    ) as flask_session:
        token = flask_session[
            "_csrf_token"
        ]

    logged_in = client.post(
        "/login",
        data={
            "password": (
                "test-password"
            ),
            "csrf_token": token,
        },
    )

    assert (
        logged_in.status_code
        == 302
    )

    home = client.get(
        "/"
    )

    assert (
        home.status_code
        == 200
    )
