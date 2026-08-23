from uuid import UUID

from aabha.api.dto.UserRegister import UserRegister
from aabha.api.dto.UserUpdate import UserUpdate
from aabha.db.pool import get_cursor
from aabha.models.user import User
from aabha.services.security import hash_password

_COLUMNS = "id, username, email, password, dob, created_at, updated_at"


async def create_user(user: UserRegister) -> User:
    async with get_cursor() as cursor:
        await cursor.execute(
            f"INSERT INTO users (username, email, password, dob)"
            f" VALUES (%s, %s, %s, %s) RETURNING {_COLUMNS}",
            (user.username, user.email, hash_password(user.password), user.dob),
        )
        row = await cursor.fetchone()
        return User.model_validate(row)


async def update_user(user_id: UUID, user: UserUpdate) -> User | None:
    async with get_cursor() as cursor:
        await cursor.execute(
            f"UPDATE users SET username = %s, email = %s, dob = %s, updated_at = now()"
            f" WHERE id = %s RETURNING {_COLUMNS}",
            (user.username, user.email, user.dob, user_id),
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
