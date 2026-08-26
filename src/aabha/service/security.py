from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """False rather than an exception for a wrong password: at the call site a
    mismatch and a corrupt hash both mean the same thing - do not sign them in."""
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError, VerificationError, InvalidHashError:
        return False


def needs_rehash(password_hash: str) -> bool:
    """True when the hash was made with weaker parameters than we use now."""
    return _hasher.check_needs_rehash(password_hash)
