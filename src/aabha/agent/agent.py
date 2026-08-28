from __future__ import annotations

import logging

from livekit.agents import (
    Agent,
    ChatContext,
    ChatMessage,
    ToolError,
    function_tool,
)

from aabha.agent.prompt import AGENT_PROMPT
from aabha.db.models import MemoryKind
from aabha.service.conversation_service import UserConversation
from aabha.service.google_service import PlaceResult, find_nearby_places
from aabha.service.location_service import LocationUnavailable, UserLocation
from aabha.service.memory_service import MemoryAction, UserMemory
from aabha.utils.goole_search_place_type import GooglePlaceType

logger = logging.getLogger("aabha.agent")

_SPOKEN_ROLES = ("user", "assistant")


class AabhaAgent(Agent):
    """The conversation itself. Everything it needs is handed to it: the
    memories are already in `chat_ctx`, and the conversation row is already
    open. It reads nothing at startup - the entrypoint does that work, so this
    stays a thing that talks."""

    def __init__(
        self,
        memory: UserMemory,
        conversation: UserConversation,
        location: UserLocation,
        chat_ctx: ChatContext | None = None,
    ) -> None:
        super().__init__(instructions=AGENT_PROMPT, chat_ctx=chat_ctx)

        # we keep the memories around for recall
        self._memory = memory
        # we summarize the user's conversation on exit, this object holds summarize_conversation and create_conversation
        # create_conversation is done
        self._conversation = conversation
        # asks the user's device where they are, and names the place for us
        self._location = location

    async def on_exit(self) -> None:
        await self.summarise()

    async def summarise(self) -> None:
        """Leaves the summary of this call behind. Called on the way out and
        again from the job's shutdown callback, because a dropped connection
        does not always unwind through on_exit - the conversation itself only
        writes once."""
        try:
            session = self.session
        except RuntimeError:
            # Shutdown reached us before the session ever started.
            return

        await self._conversation.summarise(session, self._spoken())

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

    @function_tool
    async def ask_current_coordinates(self) -> dict[str, float]:
        """Ask the user's device for their latitude and longitude.

        Use this when something has to be worked out from where they are
        rather than said about it: how far away something is, which way it is,
        anything you hand to a map or a search that wants numbers. Never read
        the numbers out - if you want to say where they are, ask for the
        address instead.
        """
        try:
            coordinates = await self._location.current_coordinates()
        except LocationUnavailable as e:
            raise ToolError(str(e))

        return coordinates.model_dump()

    @function_tool
    async def search_nearby_places(
        self,
        query: GooglePlaceType,
        radius: float = 500.0,
    ) -> list[dict]:
        """
        Find places of the specified type near the user's current location.

        Start with a 500-meter search radius. If suitable places are not found,
        increase the radius and search again.
        
        Among response place, suggest only best 3 places and ask the user to choose.
        """

        result = await find_nearby_places(
            query,
            await self._location.current_coordinates(),
            radius,
        )

        return [
            {
                "id": place.id,
                "name": place.displayName["text"],
                "address": place.formattedAddress,
                "latitude": place.location.latitude,
                "longitude": place.location.longitude,
                "type": place.primaryType,
            }
            for place in result.places
        ]

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
