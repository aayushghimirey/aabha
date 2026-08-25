from __future__ import annotations

import asyncio
import logging
from typing import get_args
from uuid import UUID

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
from aabha.agent.user_location_lkrpc import (
    Location,
    LocationUnavailable,
    ask_user_location,
)
from aabha.agent.user_session import UserSession
from aabha.db.repo.conversation_repo import update_conversation_summary
from aabha.db.repo.memory_repo import upsert_memory
from aabha.db.repo.message_repo import create_message
from aabha.db.repo.navigation_repo import (
    change_navigation_status,
    create_navigation,
    get_active_navigation,
    get_navigation,
)
from aabha.services.geocoding import describe_location
from aabha.services.navigation_service import (
    DestinationCandidate,
    DestinationLookupError,
    find_destinations,
)
from aabha.models.memory import MEMORY_KINDS
from aabha.models.message import ROLE_TYPES
from aabha.models.navigation import NAVIGATION_UPDATE, Navigation, NavigationPoint

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

        # The last search's results, numbered as they were read to the user.
        # save_navigation works off these rather than off coordinates the
        # model repeats back, which it is free to get wrong.
        self._candidates: list[DestinationCandidate] = []

        # Where the user was when that search ran - the start point the
        # navigation is saved with.
        self._search_origin: NavigationPoint | None = None

        # The trip this call saved, if it saved one. A conversation that starts
        # after the trip did leaves this empty, and the row is looked up
        # instead - so "I have arrived" works on a fresh call too.
        self._navigation_id: UUID | None = None

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
            location: Location = await ask_user_location(get_job_context().room)
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

    # -- navigation -------------------------------------------------------

    async def _origin(self) -> NavigationPoint:
        """Where the user is standing, asked for fresh.

        A trip is planned from where someone is now, not from where they were
        when the call started, so this never reuses an older fix.
        """
        try:
            location: Location = await ask_user_location(get_job_context().room)
        except LocationUnavailable as err:
            raise ToolError(f"I could not get their location: {err}") from err

        return NavigationPoint(latitude=location.latitude, longitude=location.longitude)

    @function_tool
    async def find_destination(
        self, query: str, nearby_only: bool = False
    ) -> dict[str, object]:
        """Find a place, or the nearest places of some kind, around the user.

        Call this both when the user wants to GO somewhere and when they are
        only ASKING what is around - "are there any mobile shops near me",
        "where is the closest pharmacy". It looks things up; it saves nothing.

        Pass what they called it, in their words, plus any detail they added -
        "the German bakery in Jhamsikhel" finds far more than "bakery". A kind
        of place ("mobile shops", "a pharmacy") is searched by category near
        them; a named place is looked up by name.

        This tool asks their device for their location, so the search is
        anchored where they actually are.

        HOW TO ANSWER FROM WHAT COMES BACK

        Every match is a real place near them, and `distance_km` is a
        straight-line distance from where they are standing right now. Say it.
        "The nearest one is Ananya Mobile and Electronics, about twelve
        kilometres away in Barahaksetra" is a good answer even though twelve
        kilometres is far - it is true, and they can decide.

        `category` is what each place actually is, and results are ordered so
        the ones that really are what they asked for come first. Use that
        word. An "electronics" shop is not a "mobile" shop, and a customer
        centre is not a shop at all - if the only matches are near misses, say
        what they are and that they may not be what was wanted.

        You know a place's name, kind, rough location and distance. You do NOT
        know what it sells, its prices, its hours, or whether it is any good -
        never say or imply otherwise.

        - Read out the nearest one or two, with the distance and the area. Name
          at most three, ever.
        - `searched_radius_km` is how far out the search had to reach. If it is
          large, lead with that: "there is nothing in the few kilometres around
          you - the closest is about twelve kilometres away". Do not let a far
          result stand as though it were nearby.
        - Nothing found: say so plainly and ask them to describe it another way
          or name a landmark. Do not offer something else instead.
        - Only ask "which one" when the options are genuinely hard to tell
          apart and they have to choose - not when they simply asked what is
          nearby.
        - If they are only asking what is around, answer the question. Do not
          push them to set a destination; offer that only if they sound like
          they want to go.

        Never read out coordinates. Never name a place that is not in the
        list, and never present a place of a different kind as an answer. Once
        they choose one, call save_navigation with that option's number.

        Args:
            query: The destination or kind of place, in the user's own words.
            nearby_only: True when they clearly mean somewhere close by -
                "the nearest pharmacy", "a cafe around here". Leave False for
                a named place that could be any distance away.
        """
        origin = await self._origin()

        try:
            search = await find_destinations(
                query, origin=origin, nearby_only=nearby_only
            )
        except DestinationLookupError as err:
            raise ToolError(f"I could not search for that: {err}") from err

        # Held for save_navigation, and cleared first so a failed search cannot
        # leave the previous one's options answerable.
        self._candidates = search.candidates
        self._search_origin = origin

        logger.info(
            "destination search %r for user %s: %d match(es)",
            query,
            self.userdata.user.id,
            len(search.candidates),
        )

        found: dict[str, object] = {
            "searched_for": search.category_label or query,
            "searched_radius_km": (
                round(search.radius_m / 1000, 1) if search.radius_m else None
            ),
        }

        if not search.candidates:
            return {
                **found,
                "matches": [],
                "instruction": (
                    "Nothing of that kind was found. Say so plainly - including"
                    " how far out you looked, if that is known - and ask them"
                    " to describe it another way or name a landmark near it."
                    " Do not offer a different kind of place instead."
                ),
            }

        matches = [
            {"option": number, **candidate.summary()}
            for number, candidate in enumerate(search.candidates, start=1)
        ]

        nearest_km = matches[0]["distance_km"]

        if isinstance(nearest_km, (int, float)) and nearest_km >= 5:
            instruction = (
                f"Everything found is some way off - the closest is about"
                f" {nearest_km} kilometres away. Lead with that, so they are"
                " not told a distant place is nearby, then name it and where"
                " it is. Ask whether they want to go there before saving."
            )
        elif len(matches) == 1:
            instruction = (
                "One match. Say what it is, where it is and how far, and ask"
                " them to confirm before you save it."
            )
        else:
            instruction = (
                "Give the nearest one or two with their distance and area."
                " Ask which they want only if they have to choose - if they"
                " were just asking what is nearby, answering is enough."
            )

        return {**found, "matches": matches, "instruction": instruction}

    @function_tool
    async def save_navigation(self, option: int) -> str:
        """Save the destination the user settled on, so the trip is ready to go.

        Only call this after find_destination has returned options and the user
        has confirmed which one they mean. If they have not confirmed, ask them
        first - saving the wrong place is worse than one more question.

        This records where they are going. It does not start guiding them.

        Args:
            option: The number of the chosen match from find_destination.
        """
        if not self._candidates or self._search_origin is None:
            raise ToolError(
                "There are no destination options yet - call find_destination" " first."
            )

        if not 1 <= option <= len(self._candidates):
            raise ToolError(
                f"There is no option {option}; there are"
                f" {len(self._candidates)}. Ask them which one they meant."
            )

        candidate = self._candidates[option - 1]

        navigation = await create_navigation(
            user_id=self.userdata.user.id,
            start=self._search_origin,
            destination=candidate.point,
            destination_name=candidate.name,
            destination_address=candidate.address,
        )

        logger.info(
            "saved navigation %s for user %s: %s",
            navigation.id,
            self.userdata.user.id,
            candidate.name,
        )

        self._navigation_id = navigation.id

        # The options are spent: anything said next is a new destination, not
        # another pick from this list.
        self._candidates = []
        self._search_origin = None

        return f"Saved {candidate.name} as their destination."

    async def _active_navigation(self) -> Navigation | None:
        """The trip being talked about: the one saved in this call, or failing
        that whatever the user last left unfinished."""
        if self._navigation_id is not None:
            navigation = await get_navigation(self._navigation_id)

            if navigation is not None:
                return navigation

        return await get_active_navigation(self.userdata.user.id)

    @function_tool
    async def get_saved_destination(self) -> dict[str, object]:
        """Check where the user is currently headed, if anywhere.

        Call this when they ask where they are going, whether they are still on
        their way, or say something that only makes sense if a trip is already
        under way - "am I nearly there", "how much further", "I have arrived".
        A trip saved in an earlier conversation is still theirs, so check here
        rather than assuming there is nothing.

        Returns the destination and its status, or nothing when they have no
        trip open.
        """
        navigation = await self._active_navigation()

        if navigation is None:
            return {"destination": None, "instruction": "They have no trip saved."}

        self._navigation_id = navigation.id

        return {
            "destination": {
                "name": navigation.destination_name,
                "address": navigation.destination_address,
                "status": navigation.status,
                "saved_at": navigation.created_at.isoformat(),
            },
            "instruction": (
                "Only mention this if it is what they asked about. Never read"
                " out coordinates."
            ),
        }

    @function_tool
    async def update_navigation_status(self, status: NAVIGATION_UPDATE) -> str:
        """Move the user's saved trip on when they say what is happening with it.

        Call this as soon as they tell you, and do not ask permission first -
        this is bookkeeping, not a decision.

        When to use which:
        - "started": they have set off - "I'm on my way", "heading there now",
          "just left".
        - "completed": they got there - "I've arrived", "I'm here", "made it".
        - "failed": the trip is off - "it was closed", "I gave up", "never
          mind", "we turned back".

        If they are simply changing their mind about where to go, find the new
        place with find_destination instead; mark the old trip "failed" first
        only if they say they are abandoning it.

        Args:
            status: What has happened to the trip.
        """
        navigation = await self._active_navigation()

        if navigation is None:
            raise ToolError(
                "They have no trip saved, so there is nothing to update. Ask"
                " where they want to go."
            )

        if navigation.status == status:
            return f"Their trip to {navigation.destination_name} is already {status}."

        updated = await change_navigation_status(navigation.id, status)

        if updated is None:
            raise ToolError("I could not update their trip just now.")

        logger.info(
            "navigation %s for user %s is now %s",
            updated.id,
            self.userdata.user.id,
            status,
        )

        # A finished trip is not the one a later "I've arrived" refers to.
        self._navigation_id = None if status in ("completed", "failed") else updated.id

        return f"Marked their trip to {updated.destination_name} as {status}."
