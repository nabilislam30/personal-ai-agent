import getpass
import secrets
import shlex

from werkzeug.security import (
    generate_password_hash,
)


def main() -> None:
    password = getpass.getpass(
        "Choose a strong web password: "
    )
    confirm = getpass.getpass(
        "Confirm password: "
    )

    if not password:
        raise SystemExit(
            "Password cannot be empty."
        )

    if password != confirm:
        raise SystemExit(
            "Passwords do not match."
        )

    password_hash = (
        generate_password_hash(
            password
        )
    )
    secret_key = (
        secrets.token_hex(32)
    )

    print(
        "\nAdd these to "
        ".env.production:\n"
    )
    print(
        "PAI_PASSWORD_HASH="
        + shlex.quote(
            password_hash
        )
    )
    print(
        "PAI_SECRET_KEY="
        + shlex.quote(
            secret_key
        )
    )


if __name__ == "__main__":
    main()
