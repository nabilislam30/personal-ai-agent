import secrets
import threading
from collections import defaultdict, deque
from time import monotonic

from flask import session

from config import (
    PRODUCTION_MODE,
    WEB_PASSWORD_HASH,
    WEB_REQUIRE_AUTH,
    WEB_SECRET_KEY,
)


SAFE_METHODS = {
    "GET",
    "HEAD",
    "OPTIONS",
}


class RateLimiter:
    """
    Lightweight in-process sliding-window limiter.

    Production uses one Gunicorn worker so the limiter remains consistent
    for this single-user deployment.
    """

    def __init__(
        self,
        window_seconds: int = 60,
    ) -> None:
        self.window_seconds = (
            window_seconds
        )
        self._events = defaultdict(
            deque
        )
        self._lock = (
            threading.Lock()
        )

    def allow(
        self,
        key: str,
        limit: int,
    ) -> bool:
        now = monotonic()
        cutoff = (
            now
            - self.window_seconds
        )

        with self._lock:
            events = self._events[
                key
            ]

            while (
                events
                and events[0] < cutoff
            ):
                events.popleft()

            if len(events) >= limit:
                return False

            events.append(now)
            return True


def csrf_token() -> str:
    token = session.get(
        "_csrf_token"
    )

    if not token:
        token = (
            secrets.token_urlsafe(
                32
            )
        )
        session[
            "_csrf_token"
        ] = token

    return token


def valid_csrf_token(
    supplied: str,
) -> bool:
    expected = session.get(
        "_csrf_token",
        "",
    )

    return bool(
        expected
        and supplied
        and secrets.compare_digest(
            expected,
            supplied,
        )
    )


def validate_security_configuration(
    host: str,
) -> None:
    """
    Refuse unsafe production configurations before serving traffic.
    """

    if (
        host
        not in {
            "127.0.0.1",
            "localhost",
            "::1",
        }
        and not WEB_REQUIRE_AUTH
    ):
        raise RuntimeError(
            "Refusing to bind to a non-loopback host "
            "without authentication enabled."
        )

    if (
        PRODUCTION_MODE
        and not WEB_REQUIRE_AUTH
    ):
        raise RuntimeError(
            "Production mode requires PAI_REQUIRE_AUTH=true."
        )

    if (
        WEB_REQUIRE_AUTH
        and not WEB_PASSWORD_HASH
    ):
        raise RuntimeError(
            "Authentication is enabled but PAI_PASSWORD_HASH is missing."
        )

    if (
        WEB_REQUIRE_AUTH
        and not WEB_SECRET_KEY
    ):
        raise RuntimeError(
            "Authentication is enabled but PAI_SECRET_KEY is missing."
        )
