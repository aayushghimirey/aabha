from aabha.models.base import BaseEntity
from uuid import UUID
from typing import Literal

MEMORY_KINDS = Literal["preference", "fact", "habit", "goal", "contact", "navigation"]


class Memory(BaseEntity):
    user_id: UUID

    kind: MEMORY_KINDS = "preference"
    key: str
    content: str
