from uuid import UUID

from aabha.db.repo import conversation_repo


class UserConversation:
    """One conversation, from the user joining the room to the summary left
    behind when they go."""

    def __init__(self, user_id: UUID):
        self.user_id = user_id
        self.conversation_id: UUID | None = None

        self._summarised = False

    async def create_conversation(self) -> None:
        """Opens the row this call will be written onto. Called once, when the
        user joins."""
        if self.conversation_id is not None:
            return

        conversation = await conversation_repo.create_conversation(user_id=self.user_id)

        self.conversation_id = conversation.id

    async def summarize_conversation(self, summary: str, message_count: int) -> None:
        """Writes the summary onto that row.

        Runs once, and does nothing without a conversation to write onto: a
        dropped call can reach here twice, through the agent's on_exit and
        through the job's shutdown callback.
        """
        if self.conversation_id is None or self._summarised or not summary:
            return

        self._summarised = True

        await conversation_repo.insert_conversation_summary(
            conversation_id=self.conversation_id,
            summary=summary,
            message_count=message_count,
        )
