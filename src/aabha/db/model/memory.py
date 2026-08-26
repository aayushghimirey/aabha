from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from aabha.db.model.base_model import CoreEntity

MemoryKind = Literal[
    "preference",
    "habit",
    "fact",
]

MemorySource = Literal[
    "user",
    "agent",
    "conversation",
    "system",
]


class MemoryDraft(BaseModel):
    """A memory before it is a row - everything a writer supplies. Kept apart
    from Memory so writing one does not mean inventing an id and a created_at."""

    key: str = Field(
        min_length=1,
        max_length=64,
        description="Short stable handle, such as coffee_order or commute."
        " Saving under a key that is taken overwrites it.",
    )

    kind: MemoryKind = "fact"

    content: str = Field(
        min_length=1, max_length=2000, description="The actual memory content"
    )

    source: MemorySource = "conversation"

    importance: int = Field(
        default=5, ge=1, le=10, description="How important this memory is"
    )


class Memory(CoreEntity, MemoryDraft):
    user_id: UUID
