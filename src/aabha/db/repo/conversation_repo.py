from uuid import UUID

from aabha.db.conn_pool import get_cursor
from aabha.db.models import Conversation

_COLUMNS = "id, user_id, summary, message_count, created_at, updated_at"


async def create_conversation(user_id: UUID) -> Conversation:
    async with get_cursor() as cursor:
        await cursor.execute(
            f"""
            INSERT INTO conversation (user_id)
            VALUES (%s)
            RETURNING {_COLUMNS}
            """,
            (user_id,),
        )

        row = await cursor.fetchone()

        return Conversation.model_validate(row)


async def insert_conversation_summary(
    conversation_id: UUID, summary: str, message_count: int
) -> Conversation | None:
    """Writes the summary onto a conversation already opened. None when there
    is no such row - fetchone needs the RETURNING clause to have something to
    hand back."""
    async with get_cursor() as cursor:
        await cursor.execute(
            f"""
            UPDATE conversation
            SET summary = %s, message_count = %s, updated_at = now()
            WHERE id = %s
            RETURNING {_COLUMNS}
            """,
            (summary, message_count, conversation_id),
        )

        row = await cursor.fetchone()

        return Conversation.model_validate(row) if row else None


async def get_summarised_conversations(
    user_id: UUID, limit: int = 5, exclude_id: UUID | None = None
) -> list[Conversation]:
    """The user's most recently summarised conversations, newest first.

    A NULL summary means the call is still open or was cut off before it could
    be written up, and there is nothing to read back from it. `exclude_id`
    leaves out the call being had right now, which is opened before the context
    is built and so would otherwise come back as the newest row.
    """
    async with get_cursor() as cursor:
        await cursor.execute(
            f"""
            SELECT {_COLUMNS} FROM conversation
            WHERE user_id = %s
              AND summary IS NOT NULL
              AND id IS DISTINCT FROM %s::uuid
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (user_id, exclude_id, limit),
        )

        rows = await cursor.fetchall()

        return [Conversation.model_validate(row) for row in rows]
