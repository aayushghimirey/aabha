from uuid import UUID

from livekit.agents import AgentSession, ChatContext

from aabha.agent.prompt import SUMMARY_INSTRUCTIONS
from aabha.db.repo import conversation_repo
from livekit.agents import llm

_MAX_TRANSCRIPT_CHARS = 8000


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

    async def summarise(self, session: AgentSession) -> None:
        """Sum the call up and leave it on the conversation the entrypoint
        opened.

        Safe to call twice, and the job's shutdown callback should call it too:
        a dropped connection does not always unwind through on_exit.
        """
        spoken = self._spoken()

        if not spoken:
            return

        # That same shutdown callback can fire before the session ever started,
        # and reaching for the model then is what raises.
        try:
            model = session.llm
        except RuntimeError:
            return

        if not isinstance(model, llm.LLM):
            return

        chat_ctx = ChatContext.empty()
        chat_ctx.add_message(role="system", content=SUMMARY_INSTRUCTIONS)
        chat_ctx.add_message(
            role="user", content="\n".join(spoken)[-_MAX_TRANSCRIPT_CHARS:]
        )

        response = await model.chat(chat_ctx=chat_ctx).collect()

        # A model that answers with nothing would otherwise overwrite the NULL
        # that marks a call as never summarised.
        if not response.text:
            return

        await self._conversation.summarize_conversation(response.text, len(spoken))
