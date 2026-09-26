from pathlib import Path

from flask import (
    Flask,
    jsonify,
    render_template,
    request,
)
from werkzeug.utils import secure_filename

from agent import (
    build_messages,
    run_agent_turn,
)
from config import (
    CHAT_MODEL,
    KNOWLEDGE_ROOT,
    SESSION_HISTORY_LIMIT,
    WEB_HOST,
    WEB_MAX_UPLOAD_BYTES,
    WEB_PORT,
)
from sessions import SessionStore
from tools.knowledge_tools import (
    index_knowledge,
    knowledge_status,
)


ALLOWED_UPLOAD_EXTENSIONS = {
    ".md",
    ".txt",
    ".pdf",
    ".docx",
}


def _session_payload(
    session,
) -> dict:
    return {
        "id": session.id,
        "short_id": session.id[:8],
        "title": session.title,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
    }


def _knowledge_destination(
    filename: str,
) -> Path:
    safe_name = secure_filename(
        filename
    )

    if not safe_name:
        raise ValueError(
            "Filename is invalid."
        )

    extension = Path(
        safe_name
    ).suffix.lower()

    if (
        extension
        not in ALLOWED_UPLOAD_EXTENSIONS
    ):
        raise ValueError(
            "Unsupported knowledge file type. "
            "Allowed: .md, .txt, .pdf, .docx"
        )

    inbox = (
        KNOWLEDGE_ROOT
        / "inbox"
    ).resolve()

    destination = (
        inbox
        / safe_name
    ).resolve()

    try:
        destination.relative_to(
            inbox
        )
    except ValueError as error:
        raise ValueError(
            "Invalid upload destination."
        ) from error

    return destination


def create_app(
    store: SessionStore | None = None,
) -> Flask:
    app = Flask(__name__)
    app.config[
        "MAX_CONTENT_LENGTH"
    ] = WEB_MAX_UPLOAD_BYTES

    session_store = (
        store
        or SessionStore()
    )

    @app.get("/")
    def home():
        return render_template(
            "index.html",
            model=CHAT_MODEL,
        )

    @app.get("/api/bootstrap")
    def bootstrap():
        active = (
            session_store
            .get_or_create_latest_session()
        )

        sessions = (
            session_store
            .list_sessions()
        )

        messages = (
            session_store
            .load_messages(
                active.id,
                limit=SESSION_HISTORY_LIMIT,
            )
        )

        return jsonify(
            {
                "model": CHAT_MODEL,
                "active_session": (
                    _session_payload(
                        active
                    )
                ),
                "sessions": [
                    _session_payload(
                        session
                    )
                    for session in sessions
                ],
                "messages": messages,
                "knowledge_status": (
                    knowledge_status()
                ),
            }
        )

    @app.post("/api/sessions")
    def create_session():
        session = (
            session_store
            .create_session()
        )

        return jsonify(
            {
                "session": (
                    _session_payload(
                        session
                    )
                ),
                "messages": [],
            }
        ), 201

    @app.get(
        "/api/sessions/<session_id>"
    )
    def get_session(
        session_id: str,
    ):
        session = (
            session_store
            .get_session(
                session_id
            )
        )

        if session is None:
            return jsonify(
                {
                    "error": (
                        "Session not found."
                    )
                }
            ), 404

        messages = (
            session_store
            .load_messages(
                session.id,
                limit=SESSION_HISTORY_LIMIT,
            )
        )

        return jsonify(
            {
                "session": (
                    _session_payload(
                        session
                    )
                ),
                "messages": messages,
            }
        )

    @app.post("/api/chat")
    def chat():
        payload = (
            request.get_json(
                silent=True
            )
            or {}
        )

        prompt = str(
            payload.get(
                "prompt",
                "",
            )
        ).strip()

        session_id = str(
            payload.get(
                "session_id",
                "",
            )
        ).strip()

        approve_writes = (
            payload.get(
                "approve_writes"
            )
            is True
        )

        if not prompt:
            return jsonify(
                {
                    "error": (
                        "Prompt cannot "
                        "be empty."
                    )
                }
            ), 400

        session = (
            session_store
            .get_session(
                session_id
            )
            if session_id
            else None
        )

        if session is None:
            session = (
                session_store
                .create_session()
            )

        history = (
            session_store
            .load_messages(
                session.id,
                limit=SESSION_HISTORY_LIMIT,
            )
        )

        messages = build_messages(
            history
        )

        messages.append(
            {
                "role": "user",
                "content": prompt,
            }
        )

        def web_approval(
            _tool_name: str,
            _tool_arguments: dict,
        ) -> bool:
            return approve_writes

        try:
            response = run_agent_turn(
                messages,
                approval_callback=(
                    web_approval
                ),
            )
        except Exception as error:
            return jsonify(
                {
                    "error": (
                        "Agent request failed: "
                        f"{error}"
                    )
                }
            ), 500

        session_store.update_title_from_prompt(
            session.id,
            prompt,
        )

        session_store.add_message(
            session.id,
            "user",
            prompt,
        )

        session_store.add_message(
            session.id,
            "assistant",
            response,
        )

        updated_session = (
            session_store
            .get_session(
                session.id
            )
        )

        return jsonify(
            {
                "session": (
                    _session_payload(
                        updated_session
                    )
                ),
                "response": response,
                "write_approval": (
                    approve_writes
                ),
            }
        )

    @app.get(
        "/api/knowledge/status"
    )
    def get_knowledge_status():
        return jsonify(
            {
                "status": (
                    knowledge_status()
                )
            }
        )

    @app.post(
        "/api/knowledge/upload"
    )
    def upload_knowledge():
        uploaded = (
            request.files.get(
                "file"
            )
        )

        if (
            uploaded is None
            or not uploaded.filename
        ):
            return jsonify(
                {
                    "error": (
                        "No file was selected."
                    )
                }
            ), 400

        try:
            destination = (
                _knowledge_destination(
                    uploaded.filename
                )
            )
        except ValueError as error:
            return jsonify(
                {
                    "error": str(error)
                }
            ), 400

        if destination.exists():
            return jsonify(
                {
                    "error": (
                        "A knowledge file with "
                        "that name already exists. "
                        "Overwriting is not allowed."
                    )
                }
            ), 409

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        uploaded.save(
            destination
        )

        relative = (
            destination
            .relative_to(
                KNOWLEDGE_ROOT
            )
        )

        return jsonify(
            {
                "message": (
                    "Knowledge file "
                    f"uploaded: {relative}"
                ),
                "status": (
                    knowledge_status()
                ),
            }
        ), 201

    @app.post(
        "/api/knowledge/reindex"
    )
    def rebuild_knowledge():
        payload = (
            request.get_json(
                silent=True
            )
            or {}
        )

        if (
            payload.get(
                "confirm"
            )
            is not True
        ):
            return jsonify(
                {
                    "error": (
                        "Explicit confirmation "
                        "is required to rebuild "
                        "the knowledge index."
                    )
                }
            ), 400

        result = index_knowledge()

        return jsonify(
            {
                "result": result,
                "status": (
                    knowledge_status()
                ),
            }
        )

    return app


app = create_app()


if __name__ == "__main__":
    print(
        "Personal AI Agent Web UI"
    )
    print(
        f"Model: {CHAT_MODEL}"
    )
    print(
        f"Open: http://{WEB_HOST}:{WEB_PORT}"
    )

    app.run(
        host=WEB_HOST,
        port=WEB_PORT,
        debug=False,
        use_reloader=False,
    )
