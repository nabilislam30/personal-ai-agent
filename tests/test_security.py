import pytest

import security


def test_production_requires_auth(
    monkeypatch,
):
    monkeypatch.setattr(
        security,
        "PRODUCTION_MODE",
        True,
    )
    monkeypatch.setattr(
        security,
        "WEB_REQUIRE_AUTH",
        False,
    )

    with pytest.raises(
        RuntimeError
    ):
        (
            security
            .validate_security_configuration(
                "127.0.0.1"
            )
        )


def test_non_loopback_requires_auth(
    monkeypatch,
):
    monkeypatch.setattr(
        security,
        "PRODUCTION_MODE",
        False,
    )
    monkeypatch.setattr(
        security,
        "WEB_REQUIRE_AUTH",
        False,
    )

    with pytest.raises(
        RuntimeError
    ):
        (
            security
            .validate_security_configuration(
                "0.0.0.0"
            )
        )


def test_auth_requires_hash_and_secret(
    monkeypatch,
):
    monkeypatch.setattr(
        security,
        "PRODUCTION_MODE",
        False,
    )
    monkeypatch.setattr(
        security,
        "WEB_REQUIRE_AUTH",
        True,
    )
    monkeypatch.setattr(
        security,
        "WEB_PASSWORD_HASH",
        "",
    )
    monkeypatch.setattr(
        security,
        "WEB_SECRET_KEY",
        "",
    )

    with pytest.raises(
        RuntimeError
    ):
        (
            security
            .validate_security_configuration(
                "127.0.0.1"
            )
        )


def test_rate_limiter_blocks_after_limit():
    limiter = security.RateLimiter(
        window_seconds=60
    )

    assert limiter.allow(
        "user",
        2,
    )
    assert limiter.allow(
        "user",
        2,
    )
    assert not limiter.allow(
        "user",
        2,
    )
