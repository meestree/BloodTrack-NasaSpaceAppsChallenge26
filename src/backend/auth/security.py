"""Password hashing and opaque session tokens."""

from hashlib import sha256
from secrets import token_urlsafe

from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

password_hasher = PasswordHash.recommended()
# Perform a real verification even when a username does not exist.
dummy_hash = password_hasher.hash(token_urlsafe(32))
SESSION_SECONDS = 3600


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        return password_hasher.verify(password, stored_hash)
    except (UnknownHashError, ValueError):
        return False


def hash_token(token: str) -> str:
    # Session tokens have high entropy; fast hashing is appropriate here.
    return sha256(token.encode()).hexdigest()
