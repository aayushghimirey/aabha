from aabha.models.base import BaseEntity
from uuid import UUID


class Conversation(BaseEntity):
    user_id: UUID

    messages_count: int

    summary: str
