import hashlib
import secrets

import bcrypt


MAX_BCRYPT_PASSWORD_BYTES = 72


def _validate_password(password: str) -> bytes:
    """
    Convert a password to UTF-8 bytes and enforce bcrypt's
    maximum password length.
    """

    if not password:
        raise ValueError("Password cannot be empty.")

    password_bytes = password.encode("utf-8")

    if len(password_bytes) > MAX_BCRYPT_PASSWORD_BYTES:
        raise ValueError(
            "Password is too long. "
            "Please use a password of 72 UTF-8 bytes or fewer."
        )

    return password_bytes


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.
    """

    password_bytes = _validate_password(password)

    password_hash = bcrypt.hashpw(
        password_bytes,
        bcrypt.gensalt(),
    )

    return password_hash.decode("utf-8")


def verify_password(
    password: str,
    password_hash: str,
) -> bool:
    """
    Verify a plaintext password against a stored bcrypt hash.
    """

    try:
        password_bytes = _validate_password(password)

        return bcrypt.checkpw(
            password_bytes,
            password_hash.encode("utf-8"),
        )

    except (ValueError, TypeError):
        return False


def generate_session_token() -> str:
    """
    Generate a cryptographically secure session token.

    The raw token is sent to the browser through an HttpOnly cookie.
    Only its hash is stored in the database.
    """

    return secrets.token_urlsafe(48)


def hash_session_token(token: str) -> str:
    """
    Hash a session token before storing/comparing it.
    """

    if not token:
        raise ValueError("Session token cannot be empty.")

    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


def generate_csrf_token() -> str:
    """
    Generate a CSRF token for future state-changing browser requests.
    """

    return secrets.token_urlsafe(32)