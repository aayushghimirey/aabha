from __future__ import annotations

from livekit.agents import Agent, ChatContext, ChatMessage, function_tool, llm

from aabha.agent.prompt import AGENT_PROMPT, SUMMARY_INSTRUCTIONS
from aabha.db.model.memory import MemoryKind
from aabha.service.conversation_service import UserConversation
from aabha.service.memory_service import MemoryAction, UserMemory

# The tail of a long call is the part worth summarising, and it keeps the
# request inside the model's context window.
_MAX_TRANSCRIPT_CHARS = 8000

_SPOKEN_ROLES = ("user", "assistant")


class AabhaAgent(Agent):
    """The conversation itself. Everything it needs is handed to it: the
    memories are already in `chat_ctx`, and the conversation row is already
    open. It reads nothing at startup and knows no user id - the entrypoint
    does that work, so this stays a thing that talks."""

    def __init__(
        self,
        memory: UserMemory,
        conversation: UserConversation,
        chat_ctx: ChatContext | None = None,
    ) -> None:
        super().__init__(instructions=AGENT_PROMPT, chat_ctx=chat_ctx)

        # we keep the memories around for recall
        self._memory = memory
        # we summarize the user's conversation on exit, this object holds summarize_conversation and create_conversation
        # create_conversation is done
        self._conversation = conversation

    async def on_exit(self) -> None:
        await self.summarise()

    @function_tool
    async def manage_memory(
        self,
        action: MemoryAction,
        key: str,
        content: str | None = None,
        kind: MemoryKind | None = None,
        importance: int | None = None,
    ) -> str:
        """Keep what you know about the user up to date.

        Args:
            action: save to remember something or change something you
                already know, delete to forget it.
            key: A short lowercase handle for the fact, such as coffee_order
                or commute. To change something you already know, save under
                the key it is listed with - that overwrites it. To remember
                something new, make up a key that describes it.
            content: For save - the fact itself, one sentence in the third
                person, written so it still makes sense months from now. Not
                needed to delete.
            kind: For save - whether this is a preference, a habit, or a plain
                fact about them.
            importance: 1 to 10. Everyday preferences sit around 3 to 5;
                things that matter to them for a long time sit at 8 or above.
        """
        return await self._memory.handle(
            action=action,
            key=key,
            content=content,
            kind=kind,
            importance=importance,
        )

    async def summarise(self) -> None:
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
            model = self.session.llm
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

    def _spoken(self) -> list[str]:
        """What was actually said, as transcript lines. The memories handed in
        at startup are a system message, so they are left out."""
        return [
            f"{item.role}: {item.text_content}"
            for item in self.chat_ctx.items
            if isinstance(item, ChatMessage)
            and item.role in _SPOKEN_ROLES
            and item.text_content
        ]
