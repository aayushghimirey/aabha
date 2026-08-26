from datetime import date
from uuid import UUID

from aabha.db.conn_pool import get_cursor
from aabha.db.model.user import User

_COLUMNS = "id, username, email, password_hash, dob, created_at, updated_at"


async def insert_user(
    *, username: str, email: str, password_hash: str, dob: date
) -> User:
    """Stores a new user. The password arrives already hashed - hashing is the
    service's job, and a repo that took plaintext could be handed it by mistake.

    Keyword-only: three of the four arguments are strings, and a username in
    the email column is not a mistake that announces itself.
    """
    async with get_cursor() as cursor:
        await cursor.execute(
            f"""
            INSERT INTO users (username, email, password_hash, dob)
            VALUES (%s, %s, %s, %s)
            RETURNING {_COLUMNS}
            """,
            (username, email, password_hash, dob),
        )

        row = await cursor.fetchone()

        return User.model_validate(row)


async def update_password_hash(user_id: UUID, password_hash: str) -> None:
    async with get_cursor() as cursor:
        await cursor.execute(
            "UPDATE users SET password_hash = %s, updated_at = now() WHERE id = %s",
            (password_hash, user_id),
        )


async def find_user_by_id(user_id: UUID) -> User | None:
    async with get_cursor() as cursor:
        await cursor.execute(
            f"SELECT {_COLUMNS} FROM users WHERE id = %s",
            (user_id,),
        )

        row = await cursor.fetchone()

        return User.model_validate(row) if row else None


async def find_user_by_username(username: str) -> User | None:
    """Case-folded, to match the unique index that let this name be taken."""
    async with get_cursor() as cursor:
        await cursor.execute(
            f"SELECT {_COLUMNS} FROM users WHERE lower(username) = lower(%s)",
            (username,),
        )

        row = await cursor.fetchone()

        return User.model_validate(row) if row else None


async def find_user_by_email(email: str) -> User | None:
    async with get_cursor() as cursor:
        await cursor.execute(
            f"SELECT {_COLUMNS} FROM users WHERE lower(email) = lower(%s)",
            (email,),
        )

        row = await cursor.fetchone()

        return User.model_validate(row) if row else None
