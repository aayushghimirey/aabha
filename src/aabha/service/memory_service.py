from typing import Literal
from uuid import UUID

from aabha.db.model.memory import Memory, MemoryDraft, MemoryKind
from aabha.db.repo import memory_repo

MemoryAction = Literal["save", "delete"]


def normalise_key(key: str) -> str:
    """The assistant may say "Coffee Order" one turn and "coffee_order" the
    next. Both should land on the same memory."""
    return "_".join(key.strip().lower().split())


class UserMemory:

    def __init__(self, user_id: UUID) -> None:
        self._user_id = user_id

    async def handle(
        self,
        action: MemoryAction,
        key: str,
        content: str | None = None,
        kind: MemoryKind | None = None,
        importance: int | None = None,
    ) -> str:
        key = normalise_key(key)

        if action == "save":
            if not content:
                return "Content is required to save a memory."

            await memory_repo.upsert_memory(
                user_id=self._user_id,
                draft=MemoryDraft(
                    key=key,
                    kind=kind or "fact",
                    content=content,
                    source="user",
                    importance=importance or 5,
                ),
            )
            return f"Saved under {key}."

        if action == "delete":
            deleted = await memory_repo.delete_memory(
                user_id=self._user_id,
                key=key,
            )

            if not deleted:
                return f"There is nothing saved under {key}."

            return f"Forgotten {key}."

        raise ValueError(f"Unknown action: {action}")

    async def get_memories(self) -> list[Memory]:
        return await memory_repo.get_memories(user_id=self._user_id)

    async def recall(self) -> str | None:
        """What goes into the prompt at the start of a conversation, or None
        when there is nothing known yet.

        Every line leads with its key, because that key is how the assistant
        names a memory it wants to change or forget.
        """
        memories = await self.get_memories()

        if not memories:
            return None

        lines = "\n".join(
            f"- {memory.key} ({memory.kind}): {memory.content}" for memory in memories
        )

        return (
            "What you already know about this user. Save under the same key to"
            f" change one, or forget it by that key:\n{lines}"
        )
