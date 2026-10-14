"""Password hashing and opaque session tokens.

Uses only the Python standard library so that the SQLite fallback and the
Supabase/Postgres deployment share the exact same credential format without
adding a runtime dependency.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

_ALGORITHM = "pbkdf2_sha256"
_ITERATIONS = 200_000
_SALT_BYTES = 16


def hash_password(password: str) -> str:
    """Return a salted PBKDF2 hash encoded as ``algorithm$iterations$salt$hash``."""
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return f"{_ALGORITHM}${_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    """Constant-time verification of a password against a stored hash."""
    try:
        algorithm, iterations, salt_hex, digest_hex = encoded.split("$")
        if algorithm != _ALGORITHM:
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest.hex(), digest_hex)


def new_token() -> str:
    """Create a high-entropy opaque bearer token."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Return the SHA-256 digest stored for a session token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
