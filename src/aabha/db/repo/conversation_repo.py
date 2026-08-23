from uuid import UUID

from aabha.db.pool import get_cursor
from aabha.models.conversation import Conversation

_COLUMNS = "id, user_id, messages_count, summary, created_at, updated_at"


async def create_conversation(user_id: UUID) -> Conversation:
    async with get_cursor() as cursor:
        await cursor.execute(
            f"INSERT INTO conversations (user_id) VALUES (%s) RETURNING {_COLUMNS}",
            (user_id,),
        )
        row = await cursor.fetchone()
        return Conversation.model_validate(row)


async def update_conversation_summary(
    conversation_id: UUID, summary: str
) -> Conversation | None:
    async with get_cursor() as cursor:
        await cursor.execute(
            f"UPDATE conversations SET summary = %s, updated_at = now()"
            f" WHERE id = %s RETURNING {_COLUMNS}",
            (summary, conversation_id),
        )
        row = await cursor.fetchone()
        return Conversation.model_validate(row) if row else None


async def get_latest_conversation(user_id: UUID) -> Conversation | None:
    async with get_cursor() as cursor:
        await cursor.execute(
            f"SELECT {_COLUMNS} FROM conversations WHERE user_id = %s"
            f" ORDER BY updated_at DESC LIMIT 1",
            (user_id,),
        )
        row = await cursor.fetchone()
        return Conversation.model_validate(row) if row else None


async def get_conversations(user_id: UUID, limit: int = 10) -> list[Conversation]:
    async with get_cursor() as cursor:
        await cursor.execute(
            f"SELECT {_COLUMNS} FROM conversations WHERE user_id = %s"
            f" ORDER BY updated_at DESC LIMIT %s",
            (user_id, limit),
        )
        rows = await cursor.fetchall()
        return [Conversation.model_validate(row) for row in rows]
