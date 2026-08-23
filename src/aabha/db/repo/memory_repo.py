from uuid import UUID

from aabha.db.pool import get_cursor
from aabha.models.memory import MEMORY_KINDS, Memory

_COLUMNS = "id, user_id, kind, key, content, created_at, updated_at"


async def upsert_memory(
    user_id: UUID, kind: MEMORY_KINDS, key: str, content: str
) -> Memory:
    """Records a memory, overwriting whatever was previously stored under `key`
    for this user (the table is unique on (user_id, key))."""
    async with get_cursor() as cursor:
        await cursor.execute(
            f"INSERT INTO memories (user_id, kind, key, content)"
            f" VALUES (%s, %s, %s, %s)"
            f" ON CONFLICT (user_id, key) DO UPDATE"
            f" SET kind = EXCLUDED.kind, content = EXCLUDED.content,"
            f"     updated_at = now()"
            f" RETURNING {_COLUMNS}",
            (user_id, kind, key, content),
        )
        row = await cursor.fetchone()
        return Memory.model_validate(row)


async def get_memories(
    user_id: UUID, kind: MEMORY_KINDS | None = None, limit: int = 20
) -> list[Memory]:
    async with get_cursor() as cursor:
        await cursor.execute(
            f"SELECT {_COLUMNS} FROM memories"
            f" WHERE user_id = %s AND (%s::TEXT IS NULL OR kind = %s)"
            f" ORDER BY updated_at DESC LIMIT %s",
            (user_id, kind, kind, limit),
        )
        rows = await cursor.fetchall()
        return [Memory.model_validate(row) for row in rows]
