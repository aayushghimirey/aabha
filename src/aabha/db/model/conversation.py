from uuid import UUID


from aabha.db.model.base_model import CoreEntity


class Conversation(CoreEntity):
    user_id: UUID
    message_count: int = 0
    summary: str | None = None
