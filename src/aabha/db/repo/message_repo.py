from uuid import UUID

from aabha.db.pool import get_cursor
from aabha.models.message import ROLE_TYPES, Message

_COLUMNS = "id, conversation_id, role, content, created_at, updated_at"


async def create_message(
    conversation_id: UUID, role: ROLE_TYPES, content: str
) -> Message:
    """Inserts the message and bumps its conversation's counter in one statement,
    so the count can never drift from the rows it counts."""
    async with get_cursor() as cursor:
        await cursor.execute(
            f"WITH new_message AS ("
            f"    INSERT INTO messages (conversation_id, role, content)"
            f"    VALUES (%s, %s, %s) RETURNING {_COLUMNS}"
            f"), bumped AS ("
            f"    UPDATE conversations SET messages_count = messages_count + 1,"
            f"        updated_at = now() WHERE id = %s"
            f") SELECT {_COLUMNS} FROM new_message",
            (conversation_id, role, content, conversation_id),
        )
        row = await cursor.fetchone()
        return Message.model_validate(row)


async def get_messages(conversation_id: UUID, limit: int = 50) -> list[Message]:
    """Returns the most recent `limit` messages, oldest first."""
    async with get_cursor() as cursor:
        await cursor.execute(
            f"SELECT {_COLUMNS} FROM ("
            f"    SELECT {_COLUMNS} FROM messages WHERE conversation_id = %s"
            f"    ORDER BY created_at DESC LIMIT %s"
            f") AS recent ORDER BY created_at ASC",
            (conversation_id, limit),
        )
        rows = await cursor.fetchall()
        return [Message.model_validate(row) for row in rows]
