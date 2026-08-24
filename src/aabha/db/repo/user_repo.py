from datetime import datetime
from uuid import UUID

from aabha.db.pool import get_cursor
from aabha.models.user import User
from aabha.services.security import hash_password

_COLUMNS = "id, username, email, password, dob, created_at, updated_at"


async def create_user(
    *, username: str, email: str, password: str, dob: datetime
) -> User:
    """Store a new user, hashing the password on the way in.

    `password` is the plaintext the caller was given: hashing belongs here so
    that storing one unhashed is not something a caller can forget to prevent.

    Keyword-only, because three of the four arguments are strings and getting
    a username into the email column is not the kind of mistake that announces
    itself.
    """
    async with get_cursor() as cursor:
        await cursor.execute(
            f"INSERT INTO users (username, email, password, dob)"
            f" VALUES (%s, %s, %s, %s) RETURNING {_COLUMNS}",
            (username, email, hash_password(password), dob),
        )
        row = await cursor.fetchone()
        return User.model_validate(row)


async def update_user(
    user_id: UUID, *, username: str, email: str, dob: datetime
) -> User | None:
    """Overwrite a user's profile. The password is not touched here."""
    async with get_cursor() as cursor:
        await cursor.execute(
            f"UPDATE users SET username = %s, email = %s, dob = %s, updated_at = now()"
            f" WHERE id = %s RETURNING {_COLUMNS}",
            (username, email, dob, user_id),
        )
        row = await cursor.fetchone()
        return User.model_validate(row) if row else None


async def find_user_by_id(user_id: UUID) -> User | None:
    async with get_cursor() as cursor:
        await cursor.execute(f"SELECT {_COLUMNS} FROM users WHERE id = %s", (user_id,))
        row = await cursor.fetchone()
        return User.model_validate(row) if row else None


async def find_user_by_username(username: str) -> User | None:
    async with get_cursor() as cursor:
        await cursor.execute(
            f"SELECT {_COLUMNS} FROM users WHERE username = %s", (username,)
        )
        row = await cursor.fetchone()
        return User.model_validate(row) if row else None


async def find_user_by_email(email: str) -> User | None:
    async with get_cursor() as cursor:
        await cursor.execute(f"SELECT {_COLUMNS} FROM users WHERE email = %s", (email,))
        row = await cursor.fetchone()
        return User.model_validate(row) if row else None
