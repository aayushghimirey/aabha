from aabha.models.base import BaseEntity
from uuid import UUID
from typing import Literal

ROLE_TYPES = Literal["user", "assistant"]


class Message(BaseEntity):
    conversation_id: UUID

    role: ROLE_TYPES

    content: str
