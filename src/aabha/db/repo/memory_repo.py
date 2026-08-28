from uuid import UUID

from aabha.db.conn_pool import get_cursor
from aabha.db.models import Memory, MemoryDraft

_COLUMNS = (
    "id, user_id, key, kind, content, source, importance, created_at, updated_at"
)


async def upsert_memory(user_id: UUID, draft: MemoryDraft) -> Memory:
    """Stores a memory under its key, overwriting whatever this user already
    had under that key. One key, one fact - which is what stops the same thing
    being remembered three ways."""
    async with get_cursor() as cursor:
        await cursor.execute(
            f"""
            INSERT INTO memory (user_id, key, kind, content, source, importance)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id, key) DO UPDATE
                SET kind = EXCLUDED.kind,
                    content = EXCLUDED.content,
                    source = EXCLUDED.source,
                    importance = EXCLUDED.importance,
                    updated_at = now()
            RETURNING {_COLUMNS}
            """,
            (
                user_id,
                draft.key,
                draft.kind,
                draft.content,
                draft.source,
                draft.importance,
            ),
        )

        row = await cursor.fetchone()

        return Memory.model_validate(row)


async def delete_memory(user_id: UUID, key: str) -> bool:
    """False when this user has nothing under that key, so a key the assistant
    guessed at is a miss rather than a reach into someone else's memories."""
    async with get_cursor() as cursor:
        await cursor.execute(
            "DELETE FROM memory WHERE user_id = %s AND key = %s",
            (user_id, key),
        )

        return cursor.rowcount > 0


async def get_memories(user_id: UUID, limit: int = 50) -> list[Memory]:
    """The user's memories, the ones worth knowing first."""
    async with get_cursor() as cursor:
        await cursor.execute(
            f"""
            SELECT {_COLUMNS} FROM memory
            WHERE user_id = %s
            ORDER BY importance DESC, updated_at DESC
            LIMIT %s
            """,
            (user_id, limit),
        )

        rows = await cursor.fetchall()

        return [Memory.model_validate(row) for row in rows]
