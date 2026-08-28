from datetime import date

from psycopg.errors import UniqueViolation

from aabha.db.models import User
from aabha.db.repo import user_repo
from aabha.service import security


class UsernameOrEmailTaken(Exception):
    """Raised by sign_up when the name or the address is already registered."""


async def sign_up(*, username: str, email: str, password: str, dob: date) -> User:
    """Registers a user and returns them.

    The unique indexes are the source of truth rather than a lookup first: two
    sign-ups for the same name arriving together would both pass a pre-check
    and one would still fail at the insert.
    """
    try:
        return await user_repo.insert_user(
            username=username,
            email=email,
            password_hash=security.hash_password(password),
            dob=dob,
        )
    except UniqueViolation as error:
        raise UsernameOrEmailTaken from error


async def sign_in(username: str, password: str) -> User | None:
    """The user, or None when either the name or the password is wrong.

    One answer for both, so the caller cannot tell a registered name from an
    unregistered one by asking.
    """
    user = await user_repo.find_user_by_username(username)

    if user is None:
        return None

    if not security.verify_password(user.password_hash, password):
        return None

    # The cost parameters change as hardware does. Signing in is the only
    # moment the plaintext is in hand, so it is the only chance to upgrade.
    if security.needs_rehash(user.password_hash):
        await user_repo.update_password_hash(user.id, security.hash_password(password))

    return user
