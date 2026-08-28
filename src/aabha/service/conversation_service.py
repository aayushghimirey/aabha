from uuid import UUID

from livekit.agents import AgentSession, ChatContext, llm

from aabha.agent.prompt import SUMMARY_INSTRUCTIONS
from aabha.db.models import Conversation
from aabha.db.repo import conversation_repo

_MAX_TRANSCRIPT_CHARS = 8000

# Two calls back is enough to pick up a thread the user left hanging. More than
# that and the model starts answering out of the past instead of the present.
_RECALL_LIMIT = 2


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

    async def summarise(self, session: AgentSession, spoken: list[str]) -> None:
        """Sum the call up and leave it on the conversation the entrypoint
        opened.

        The transcript is handed in - the agent is the one holding it. Safe to
        call twice, and the job's shutdown callback should call it too: a
        dropped connection does not always unwind through on_exit.
        """
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

        await self.summarize_conversation(response.text, len(spoken))

    async def get_conversations(self) -> list[Conversation]:
        """The calls worth reading back - summarised, and not this one."""
        return await conversation_repo.get_summarised_conversations(
            user_id=self.user_id,
            limit=_RECALL_LIMIT,
            exclude_id=self.conversation_id,
        )

    async def recall(self) -> str | None:
        """What the agent is told about calls that already happened, or None
        when there are none.

        Deliberately framed as background rather than as an agenda: the user
        starts a call to talk about something now, and an assistant that opens
        by picking up where it left off is answering a question nobody asked.
        """
        conversations = await self.get_conversations()

        if not conversations:
            return None

        # Oldest first, so the list reads forwards to the present.
        lines = "\n".join(
            f"- {conversation.summary}" for conversation in reversed(conversations)
        )

        return (
            "Notes from this user's last few calls, oldest first. This is"
            " background only. Treat this call as a fresh start: do not greet"
            " them with it, do not bring any of it up, and do not ask how"
            " something from it turned out. Use it only when it answers"
            " something they have actually asked about now.\n" + lines
        )
