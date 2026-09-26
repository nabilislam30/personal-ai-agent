import json
import logging
import secrets
import sqlite3
import uuid
from pathlib import Path
from time import perf_counter

from flask import (
    Flask,
    Response,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    stream_with_context,
    url_for,
)
from ollama import list as ollama_list
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename

from agent import (
    build_messages,
    preload_model,
    stream_agent_turn,
)
from config import (
    CHAT_MODEL,
    KNOWLEDGE_ROOT,
    PRELOAD_MODEL,
    SESSION_DB_PATH,
    WEB_CHAT_RATE_LIMIT,
    WEB_COOKIE_SECURE,
    WEB_HOST,
    WEB_LOGIN_RATE_LIMIT,
    WEB_MAX_UPLOAD_BYTES,
    WEB_PASSWORD_HASH,
    WEB_PORT,
    WEB_REQUIRE_AUTH,
    WEB_SECRET_KEY,
)
from observability import configure_logging
from router import (
    history_limit_for_route,
    route_request,
)
from security import (
    RateLimiter,
    csrf_token,
    valid_csrf_token,
    validate_security_configuration,
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

PUBLIC_PATHS = {
    "/health",
    "/ready",
    "/login",
}

configure_logging()
logger = logging.getLogger(
    "personal_ai_agent.web"
)

chat_limiter = RateLimiter()
login_limiter = RateLimiter()


def _session_payload(
    session_record,
) -> dict:
    return {
        "id": session_record.id,
        "short_id": (
            session_record.id[:8]
        ),
        "title": (
            session_record.title
        ),
        "created_at": (
            session_record.created_at
        ),
        "updated_at": (
            session_record.updated_at
        ),
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

    extension = (
        Path(safe_name)
        .suffix
        .lower()
    )

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


def _csrf_from_request() -> str:
    return (
        request.headers.get(
            "X-CSRF-Token",
            "",
        )
        or request.form.get(
            "csrf_token",
            "",
        )
    )


def _is_authenticated() -> bool:
    if not WEB_REQUIRE_AUTH:
        return True

    return (
        session.get(
            "authenticated"
        )
        is True
    )


def _request_key(
    prefix: str,
) -> str:
    address = (
        request.remote_addr
        or "unknown"
    )

    return (
        f"{prefix}:{address}"
    )


def _readiness_status() -> bool:
    try:
        result = ollama_list()
        models = getattr(
            result,
            "models",
            [],
        )

        if not models:
            return False
    except Exception:
        return False

    try:
        connection = sqlite3.connect(
            SESSION_DB_PATH
        )
        connection.execute(
            "SELECT 1"
        ).fetchone()
        connection.close()
    except sqlite3.Error:
        return False

    return True


def create_app(
    store: SessionStore | None = None,
) -> Flask:
    app = Flask(__name__)

    app.config[
        "MAX_CONTENT_LENGTH"
    ] = WEB_MAX_UPLOAD_BYTES

    app.secret_key = (
        WEB_SECRET_KEY
        or secrets.token_hex(32)
    )

    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Strict",
        SESSION_COOKIE_SECURE=(
            WEB_COOKIE_SECURE
        ),
    )

    session_store = (
        store
        or SessionStore()
    )

    @app.before_request
    def before_request():
        g.request_started = (
            perf_counter()
        )
        g.request_id = (
            uuid.uuid4().hex[:12]
        )

        if (
            request.path == "/login"
            and request.method == "POST"
        ):
            allowed = (
                login_limiter.allow(
                    _request_key(
                        "login"
                    ),
                    WEB_LOGIN_RATE_LIMIT,
                )
            )

            if not allowed:
                return (
                    "Too many login attempts.",
                    429,
                )

        if (
            request.path.startswith(
                "/api/chat"
            )
        ):
            allowed = (
                chat_limiter.allow(
                    _request_key(
                        "chat"
                    ),
                    WEB_CHAT_RATE_LIMIT,
                )
            )

            if not allowed:
                return jsonify(
                    {
                        "error": (
                            "Chat rate limit "
                            "exceeded."
                        )
                    }
                ), 429

        if (
            request.path
            not in PUBLIC_PATHS
            and not _is_authenticated()
        ):
            if request.path.startswith(
                "/api/"
            ):
                return jsonify(
                    {
                        "error": (
                            "Authentication "
                            "required."
                        )
                    }
                ), 401

            return redirect(
                url_for("login")
            )

        if (
            request.method
            not in {
                "GET",
                "HEAD",
                "OPTIONS",
            }
            and request.path
            != "/login"
        ):
            supplied = (
                _csrf_from_request()
            )

            if not valid_csrf_token(
                supplied
            ):
                if request.path.startswith(
                    "/api/"
                ):
                    return jsonify(
                        {
                            "error": (
                                "Invalid CSRF "
                                "token."
                            )
                        }
                    ), 400

                return (
                    "Invalid CSRF token.",
                    400,
                )

        return None

    @app.after_request
    def after_request(
        response,
    ):
        response.headers[
            "X-Content-Type-Options"
        ] = "nosniff"
        response.headers[
            "X-Frame-Options"
        ] = "DENY"
        response.headers[
            "Referrer-Policy"
        ] = "no-referrer"
        response.headers[
            "Permissions-Policy"
        ] = (
            "camera=(), microphone=(), "
            "geolocation=()"
        )
        response.headers[
            "Cache-Control"
        ] = "no-store"

        response.headers[
            "Content-Security-Policy"
        ] = (
            "default-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )

        duration_ms = (
            perf_counter()
            - getattr(
                g,
                "request_started",
                perf_counter(),
            )
        ) * 1000

        logger.info(
            "request_complete",
            extra={
                "event": (
                    "request_complete"
                ),
                "request_id": (
                    getattr(
                        g,
                        "request_id",
                        None,
                    )
                ),
                "method": (
                    request.method
                ),
                "path": request.path,
                "status": (
                    response.status_code
                ),
                "duration_ms": (
                    round(
                        duration_ms,
                        1,
                    )
                ),
            },
        )

        return response

    @app.errorhandler(413)
    def payload_too_large(
        _error,
    ):
        if request.path.startswith(
            "/api/"
        ):
            return jsonify(
                {
                    "error": (
                        "Upload exceeds the "
                        "configured size limit."
                    )
                }
            ), 413

        return (
            "Request too large.",
            413,
        )

    @app.route(
        "/login",
        methods=[
            "GET",
            "POST",
        ],
    )
    def login():
        if not WEB_REQUIRE_AUTH:
            return redirect(
                url_for("home")
            )

        error = None
        token = csrf_token()

        if request.method == "POST":
            supplied = request.form.get(
                "csrf_token",
                "",
            )

            if not valid_csrf_token(
                supplied
            ):
                error = (
                    "Invalid request token."
                )
            else:
                password = (
                    request.form.get(
                        "password",
                        "",
                    )
                )

                valid = (
                    bool(
                        WEB_PASSWORD_HASH
                    )
                    and check_password_hash(
                        WEB_PASSWORD_HASH,
                        password,
                    )
                )

                if valid:
                    session.clear()
                    session[
                        "authenticated"
                    ] = True
                    csrf_token()

                    logger.info(
                        "login_success",
                        extra={
                            "event": (
                                "login_success"
                            ),
                        },
                    )

                    return redirect(
                        url_for("home")
                    )

                error = (
                    "Invalid password."
                )

                logger.warning(
                    "login_failure",
                    extra={
                        "event": (
                            "login_failure"
                        ),
                    },
                )

        return render_template(
            "login.html",
            error=error,
            csrf_token=token,
        )

    @app.post(
        "/logout"
    )
    def logout():
        session.clear()

        return redirect(
            url_for("login")
        )

    @app.get(
        "/health"
    )
    def health():
        return jsonify(
            {
                "status": "ok",
            }
        )

    @app.get(
        "/ready"
    )
    def ready():
        ready_state = (
            _readiness_status()
        )

        return jsonify(
            {
                "status": (
                    "ready"
                    if ready_state
                    else "not_ready"
                )
            }
        ), (
            200
            if ready_state
            else 503
        )

    @app.get("/")
    def home():
        return render_template(
            "index.html",
            model=CHAT_MODEL,
            csrf_token=csrf_token(),
            auth_enabled=(
                WEB_REQUIRE_AUTH
            ),
        )

    @app.get(
        "/api/bootstrap"
    )
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
                limit=200,
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
                        item
                    )
                    for item in sessions
                ],
                "messages": messages,
                "knowledge_status": (
                    knowledge_status()
                ),
            }
        )

    @app.post(
        "/api/sessions"
    )
    def create_session():
        new_session = (
            session_store
            .create_session()
        )

        return jsonify(
            {
                "session": (
                    _session_payload(
                        new_session
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
        selected = (
            session_store
            .get_session(
                session_id
            )
        )

        if selected is None:
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
                selected.id,
                limit=200,
            )
        )

        return jsonify(
            {
                "session": (
                    _session_payload(
                        selected
                    )
                ),
                "messages": messages,
            }
        )

    @app.post(
        "/api/chat/stream"
    )
    def chat_stream():
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

        selected = (
            session_store
            .get_session(
                session_id
            )
            if session_id
            else None
        )

        if selected is None:
            selected = (
                session_store
                .create_session()
            )

        route = route_request(
            prompt
        )

        history = (
            session_store
            .load_context_messages(
                selected.id,
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
                "content": prompt,
            }
        )

        session_store.update_title_from_prompt(
            selected.id,
            prompt,
        )

        session_store.add_message(
            selected.id,
            "user",
            prompt,
        )

        def web_approval(
            _tool_name: str,
            _tool_arguments: dict,
        ) -> bool:
            return approve_writes

        @stream_with_context
        def generate_stream():
            response_parts = []
            done_event = None

            try:
                for event in (
                    stream_agent_turn(
                        messages=messages,
                        user_prompt=prompt,
                        route=route,
                        approval_callback=(
                            web_approval
                        ),
                    )
                ):
                    if (
                        event.get(
                            "type"
                        )
                        == "token"
                    ):
                        response_parts.append(
                            event.get(
                                "content",
                                "",
                            )
                        )

                    if (
                        event.get(
                            "type"
                        )
                        == "done"
                    ):
                        done_event = event

                    yield (
                        json.dumps(
                            event,
                            ensure_ascii=False,
                        )
                        + "\n"
                    )

                full_response = "".join(
                    response_parts
                ).strip()

                if full_response:
                    session_store.add_message(
                        selected.id,
                        "assistant",
                        full_response,
                    )

                if done_event:
                    logger.info(
                        "agent_turn_complete",
                        extra={
                            "event": (
                                "agent_turn_complete"
                            ),
                            "request_id": (
                                getattr(
                                    g,
                                    "request_id",
                                    None,
                                )
                            ),
                            "route_name": (
                                done_event.get(
                                    "route"
                                )
                            ),
                            "tool_calls": (
                                done_event.get(
                                    "tool_calls"
                                )
                            ),
                            "first_token_ms": (
                                done_event.get(
                                    "first_token_ms"
                                )
                            ),
                            "model_ms": (
                                done_event.get(
                                    "model_ms"
                                )
                            ),
                            "total_ms": (
                                done_event.get(
                                    "total_ms"
                                )
                            ),
                        },
                    )

            except Exception as error:
                logger.exception(
                    "agent_stream_error",
                    extra={
                        "event": (
                            "agent_stream_error"
                        ),
                    },
                )

                yield (
                    json.dumps(
                        {
                            "type": "error",
                            "error": str(error),
                        }
                    )
                    + "\n"
                )

        response = Response(
            generate_stream(),
            mimetype=(
                "application/x-ndjson"
            ),
        )

        response.headers[
            "X-Accel-Buffering"
        ] = "no"

        return response

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


def run_server() -> None:
    validate_security_configuration(
        WEB_HOST
    )

    if PRELOAD_MODEL:
        logger.info(
            preload_model(),
            extra={
                "event": (
                    "model_preload"
                ),
            },
        )

    print(
        "Personal AI Agent Web UI"
    )
    print(
        f"Model: {CHAT_MODEL}"
    )
    print(
        f"Open: "
        f"http://{WEB_HOST}:{WEB_PORT}"
    )

    app.run(
        host=WEB_HOST,
        port=WEB_PORT,
        debug=False,
        use_reloader=False,
        threaded=True,
    )


if __name__ == "__main__":
    run_server()
