from __future__ import annotations

import asyncio
import logging
from typing import get_args

from livekit.agents import (
    Agent,
    ChatContext,
    ChatMessage,
    ConversationItemAddedEvent,
    ToolError,
    function_tool,
    get_job_context,
    llm,
)

from aabha.agent.prompts import (
    GREETING_INSTRUCTIONS,
    SUMMARY_INSTRUCTIONS,
    SYSTEM_PROMPT,
)
from aabha.agent.user_location_lkrpc import LocationUnavailable, ask_user_location
from aabha.agent.user_session import UserSession
from aabha.db.repo.conversation_repo import update_conversation_summary
from aabha.db.repo.memory_repo import upsert_memory
from aabha.db.repo.message_repo import create_message
from aabha.services.geocoding import describe_location
from aabha.models.memory import MEMORY_KINDS
from aabha.models.message import ROLE_TYPES

logger = logging.getLogger("aabha.agent")

# A Literal is not a container - get_args() is what actually yields the roles.
_PERSISTED_ROLES = frozenset(get_args(ROLE_TYPES))

# The tail of a long conversation is the part worth summarising, and it keeps
# the summary request inside the model's context window.
_MAX_TRANSCRIPT_CHARS = 8000


class AssistantAgent(Agent):
    def __init__(self, chat_ctx: ChatContext | None = None) -> None:
        super().__init__(instructions=SYSTEM_PROMPT, chat_ctx=chat_ctx)

        self._writes: set[asyncio.Task[object]] = set()

        # Writes run off the voice loop, but one at a time: a message's
        # created_at is set when the row lands, so letting two turns race
        # would order the stored transcript by write, not by what was said.
        self._write_lock = asyncio.Lock()

        self._finalised = False

    @property
    def userdata(self) -> UserSession:
        return self.session.userdata

    async def on_enter(self) -> None:
        self.session.on("conversation_item_added", self._on_conversation_item_added)
        self.session.generate_reply(instructions=GREETING_INSTRUCTIONS)

    async def on_exit(self) -> None:
        await self.finalise()

    # -- persistence ------------------------------------------------------

    def _on_conversation_item_added(self, ev: ConversationItemAddedEvent) -> None:
        """Persist every user and assistant turn as it lands in the history."""
        item = ev.item

        if not isinstance(item, ChatMessage) or item.role not in _PERSISTED_ROLES:
            return

        content = item.text_content

        if not content:
            return

        self._spawn(
            create_message(self.userdata.conversation.id, item.role, content),
            "persist message",
        )

    def _spawn(self, coro, what: str) -> None:
        """Run a write in the background without blocking the voice loop, and
        keep a strong reference until it finishes so it cannot be GC'd."""

        async def run() -> None:
            try:
                async with self._write_lock:
                    await coro
            except Exception:
                logger.exception("failed to %s", what)

        task = asyncio.create_task(run())
        self._writes.add(task)
        task.add_done_callback(self._writes.discard)

    async def finalise(self) -> None:
        """Flush pending writes and store a summary of the conversation.

        Called from on_exit and again as a job shutdown callback, since a
        dropped connection does not always unwind through on_exit. Runs once.
        """
        if self._finalised:
            return

        self._finalised = True

        if self._writes:
            await asyncio.gather(*self._writes, return_exceptions=True)

        try:
            summary = await self._summarise()

            if summary:
                await update_conversation_summary(
                    self.userdata.conversation.id, summary
                )
        except Exception:
            logger.exception("failed to summarise conversation")

    # -- summarising ------------------------------------------------------

    def _transcript(self) -> str:
        lines = [
            f"{item.role}: {item.text_content}"
            for item in self.chat_ctx.items
            if isinstance(item, ChatMessage)
            and item.role in _PERSISTED_ROLES
            and item.text_content
        ]

        return "\n".join(lines)[-_MAX_TRANSCRIPT_CHARS:]

    async def _summarise(self) -> str | None:
        transcript = self._transcript()

        if not transcript or not isinstance(self.session.llm, llm.LLM):
            return None

        chat_ctx = ChatContext.empty()
        chat_ctx.add_message(role="system", content=SUMMARY_INSTRUCTIONS)
        chat_ctx.add_message(role="user", content=transcript)

        response = await self.session.llm.chat(chat_ctx=chat_ctx).collect()

        return response.text or None

    # -- tools ------------------------------------------------------------

    @function_tool
    async def save_memory(self, kind: MEMORY_KINDS, key: str, content: str) -> str:
        """Remember something about the user for future conversations.

        Use this for anything durable - a preference, a habit, a goal, a person
        who matters to them, a place they go. Do not use it for passing remarks
        or for anything that is only true today.

        Args:
            kind: What sort of thing this is.
            key: A short stable handle for the fact, lowercase, such as
                "coffee_order" or "commute". Saving a key that already exists
                replaces what was stored under it, so reuse the same key when
                a fact changes.
            content: The fact itself, in one sentence, written so it still
                makes sense read back months later.
        """
        await upsert_memory(self.userdata.user.id, kind, key, content)
        logger.info("saved memory %r for user %s", key, self.userdata.user.id)

        return f"Saved: {content}"

    @function_tool
    async def get_current_location(self) -> dict[str, str | float | None]:
        """Get the user's CURRENT physical location from their device.

        MANDATORY TOOL USAGE:
        - ALWAYS call this tool when the user asks "Where am I?", "What's my location?",
        "Where am I right now?", or any equivalent question about their current location.
        - ALWAYS call this tool when the user asks how far away a place/destination is
        and they have NOT explicitly provided a starting location.
        - ALWAYS call this tool for "near me", "nearby", "around me", "close to me",
        "closest", or similar location-relative requests.
        - ALWAYS call this tool when calculating distance, travel time, or directions
        FROM the user's current location.
        - Do NOT assume, remember, or invent the user's current location.
        - A previously mentioned place is NOT the user's current location unless the user
        explicitly says they are currently there.

        EXAMPLES:
        User: "Where am I?"
        → MUST call this tool.

        User: "What's my current location?"
        → MUST call this tool.

        User: "How far is the airport?"
        → MUST call this tool first, then use the returned coordinates to calculate
        distance/travel time to the airport.

        User: "How far is Thamel from me?"
        → MUST call this tool first.

        User: "Find a restaurant near me."
        → MUST call this tool first.

        User: "How far is Thamel from Kathmandu?"
        → Do NOT call this tool because both locations are explicitly provided.

        User: "What's the weather here?"
        → Call this tool if "here" refers to the user's current physical location.

        The tool returns the user's current place name, latitude, and longitude.
        Use the place name when speaking to the user. NEVER read latitude or longitude
        aloud. Use latitude/longitude internally for maps, distance, weather, and other
        location-based tools.

        This tool accesses the user's device location and may cause the device/browser
        to ask for location permission, so briefly tell the user when appropriate.
        """
        try:
            location = await ask_user_location(get_job_context().room)
        except LocationUnavailable as err:
            # The message is written to be said out loud, so hand it to the
            # model rather than failing the turn.
            raise ToolError(f"I could not get their location: {err}") from err

        # A name is the half worth saying, but the lookup is a third party and
        # can be slow or down - so it is allowed to come back empty, and the
        # coordinates go out either way.
        place = await describe_location(location.latitude, location.longitude)

        logger.info("located user %s: %s", self.userdata.user.id, place or "unnamed")

        return {
            "place": place,
            "latitude": location.latitude,
            "longitude": location.longitude,
            "accuracy_m": location.accuracy_m,
        }
