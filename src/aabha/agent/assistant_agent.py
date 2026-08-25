from __future__ import annotations

import asyncio
import logging
from typing import get_args
from uuid import UUID

from livekit import rtc
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
    LOCATION_TOPIC,
    Location,
    LocationUnavailable,
    ask_user_location,
    read_location,
    start_location_stream,
    stop_location_stream,
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
from aabha.services.route_guidance import RouteTracker, say_distance, say_duration
from aabha.services.routing_service import TRAVEL_MODE, RoutingError, plan_route
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

        # The trip in progress, if one is being guided: the planned route and
        # how far along it the user was last seen. None means nobody is being
        # guided anywhere, and the positions their app sends are ignored.
        self._tracker: RouteTracker | None = None

        # How they said they were travelling, kept for the reroute - a walker
        # who wanders off is put back on a walking route.
        self._travel_mode: TRAVEL_MODE | None = None

        # One reroute at a time. Coming off a route takes several fixes to
        # notice and only one to fix, and asking twice would leave two routes
        # racing to become the one being followed.
        self._rerouting = False

        # Background work that is not a database write - rerouting, closing a
        # trip off - held only so the tasks are not collected mid-flight.
        self._tasks: set[asyncio.Task[object]] = set()

    @property
    def userdata(self) -> UserSession:
        return self.session.userdata

    async def on_enter(self) -> None:
        self.session.on("conversation_item_added", self._on_conversation_item_added)

        # Registered for the whole call, not just for a trip: the positions
        # only start arriving once a trip asks for them, and a handler that
        # was added when guidance began would miss the first of them.
        get_job_context().room.on("data_received", self._on_location)

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

        # A reroute or a trip being closed off has nothing left to say to a
        # call that is already over.
        for task in self._tasks:
            task.cancel()

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

        This records where they are going. Guiding them there is a separate
        step: ask whether they are walking or driving, then call
        start_navigation.

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

        return (
            f"Saved {candidate.name} as their destination. Ask whether they"
            " are walking, driving or cycling there, then call"
            " start_navigation to take them."
        )

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

        # A finished trip is not the one a later "I've arrived" refers to,
        # and it is not one to keep calling turns for either.
        self._navigation_id = None if status in ("completed", "failed") else updated.id

        if status in ("completed", "failed"):
            self._stop_guidance()

        return f"Marked their trip to {updated.destination_name} as {status}."

    # -- live guidance ----------------------------------------------------

    @function_tool
    async def start_navigation(self, travel_mode: TRAVEL_MODE) -> dict[str, object]:
        """Start guiding the user to the destination they have already chosen.

        Call this once they have saved a destination and have said how they
        are travelling. If they have not said, ask - "are you walking or
        driving?" - because a route on foot and a route by car are different
        turns, not the same turns at a different speed.

        This works out the way there, asks their app to report their position
        as they move, and from then on the turns are spoken to them
        automatically as each one comes up. You do not have to do anything to
        make that happen, and you must not do it yourself.

        HOW TO ANSWER FROM WHAT COMES BACK

        `say` is the whole answer. Read it out more or less word for word -
        how far it is, how long it should take, and the first thing they do -
        then stop. Do not add turns of your own, do not list the route, and do
        not offer to read the directions out: you have not been given them,
        and the ones that matter will be said at the moment they are needed.

        If `live_guidance` is false their app is not sharing their position,
        so nothing further will be spoken as they go. Tell them that plainly -
        they can hear the distance and the first step, but you will not be
        able to call the turns - and suggest they reload the page and allow
        location.

        Args:
            travel_mode: How they are getting there. "walk" for on foot,
                "drive" for a car, motorbike or taxi, "cycle" for a bicycle.
        """
        navigation = await self._active_navigation()

        if navigation is None:
            raise ToolError(
                "They have no destination saved. Find one with"
                " find_destination and save it first."
            )

        origin = await self._origin()

        try:
            route = await plan_route(origin, navigation.destination, travel_mode)
        except RoutingError as err:
            raise ToolError(f"I could not work out the way there: {err}") from err

        tracker = RouteTracker(route, navigation.destination_name)

        self._tracker = tracker
        self._travel_mode = travel_mode
        self._navigation_id = navigation.id

        if navigation.status != "started":
            await change_navigation_status(navigation.id, "started")

        # The route is worth having even if their phone will not follow them -
        # the distance and the first step still tell them something.
        live_guidance = True

        try:
            await start_location_stream(get_job_context().room)
        except LocationUnavailable as err:
            live_guidance = False

            logger.info("no live guidance for this trip: %s", err)

        logger.info(
            "guiding user %s to %s by %s: %.0fm",
            self.userdata.user.id,
            navigation.destination_name,
            travel_mode,
            route.distance_m,
        )

        return {
            "destination": navigation.destination_name,
            "travelling": travel_mode,
            "distance": say_distance(route.distance_m),
            "time": say_duration(route.duration_s),
            "turns": len(route.steps),
            "live_guidance": live_guidance,
            "say": tracker.opening(),
            "instruction": (
                "Say what is in `say`, near enough word for word, and nothing"
                " more. The turns will be spoken to them as they reach them -"
                " never invent one, never read the route out, and never"
                " promise to tell them when to turn as though it were"
                " something you had to remember to do."
                if live_guidance
                else "Say what is in `say`, then tell them their app is not"
                " sharing where they are, so you cannot call the turns as"
                " they go. Suggest reloading the page and allowing location."
            ),
        }

    @function_tool
    async def check_route_progress(self) -> dict[str, object]:
        """How much further the user has to go on the trip being guided.

        Call this when they ask how far is left, how long it will take, where
        they are up to, or what they do next - "how much further", "am I
        nearly there", "which way now".

        Answer with what comes back and nothing else. The distance and time
        are what is left from where they were last seen, which is within ten
        metres of where they are. If `off_route` is true they have wandered
        off it and a new route is already being worked out - say so, and that
        you will have the way in a moment.
        """
        tracker = self._tracker

        if tracker is None:
            raise ToolError(
                "Nobody is being guided anywhere just now. If they have a"
                " destination saved, start_navigation begins the trip."
            )

        # Nothing has come in yet - either they have not moved since setting
        # off, or their app never started reporting. One fix settles it, and
        # answering "how far is left" with the whole route would be a lie if
        # they had already walked half of it.
        if tracker.updates == 0:
            try:
                tracker.update(await self._origin())
            except ToolError:
                logger.info("no fix to answer the progress question with")

        progress = tracker.progress()

        return {
            "destination": tracker.destination_name,
            "remaining": say_distance(progress.remaining_m),
            "time_left": say_duration(progress.remaining_s),
            "next": progress.next_instruction,
            "off_route": progress.off_route,
            "arrived": progress.arrived,
            "instruction": (
                "Give them the distance and the time left in a sentence. Only"
                " mention the next turn if they asked which way to go."
            ),
        }

    def _on_location(self, packet: rtc.DataPacket) -> None:
        """A position from the user's app, arriving every ten metres they move.

        This runs on the room's event loop rather than inside a turn, so it
        waits for nothing: matching a fix to the route is arithmetic, and the
        two things that are not - re-planning, closing the trip off - are
        handed to a task.
        """
        tracker = self._tracker

        if packet.topic != LOCATION_TOPIC or tracker is None:
            return

        try:
            fix = read_location(packet.data)
        except LocationUnavailable:
            logger.warning("unreadable position on %s", LOCATION_TOPIC)

            return

        point = NavigationPoint(latitude=fix.latitude, longitude=fix.longitude)
        cue = tracker.update(point, fix.accuracy_m)

        if cue is None:
            return

        self._speak(cue.text)

        if cue.kind == "arrive":
            self._run(self._finish_trip(), "close the trip off")
        elif cue.kind == "off_route":
            self._run(self._reroute(point), "re-plan the route")

    def _speak(self, text: str) -> None:
        """Say something out loud that nobody asked for.

        Guidance is spoken word for word rather than handed to the model to
        phrase. "Turn left onto Pragya Marg now" has to reach the user at the
        corner rather than after a round trip through an LLM, and it has to be
        the turn the route says rather than one that sounded plausible.
        """
        try:
            self.session.say(text, allow_interruptions=True)
        except RuntimeError:
            # The call ended between the fix arriving and this being said.
            logger.info("could not say %r - the session is not running", text)

    async def _reroute(self, point: NavigationPoint) -> None:
        """Work out the way again from where the user actually is."""
        if self._rerouting or self._travel_mode is None:
            return

        self._rerouting = True

        try:
            navigation = await self._active_navigation()

            if navigation is None:
                return

            try:
                route = await plan_route(
                    point, navigation.destination, self._travel_mode
                )
            except RoutingError as err:
                # Better to stop guiding than to keep counting down turns from
                # a route they are no longer on.
                self._tracker = None

                self._speak(
                    f"I am sorry - {err}, so I cannot put you back on track"
                    " from here."
                )

                return

            tracker = RouteTracker(route, navigation.destination_name)
            self._tracker = tracker

            logger.info(
                "re-planned the way to %s for user %s",
                navigation.destination_name,
                self.userdata.user.id,
            )

            self._speak(f"I have the way from where you are now. {tracker.opening()}")
        finally:
            self._rerouting = False

    async def _finish_trip(self) -> None:
        """Close a trip off the moment the user reaches the door."""
        navigation = await self._active_navigation()

        self._stop_guidance()
        self._navigation_id = None

        if navigation is not None and navigation.status != "completed":
            await change_navigation_status(navigation.id, "completed")

            logger.info("navigation %s completed on arrival", navigation.id)

    def _stop_guidance(self) -> None:
        """Put the trip down, and let their phone stop watching the GPS."""
        self._tracker = None
        self._travel_mode = None

        try:
            room = get_job_context().room
        except RuntimeError:
            return

        self._run(stop_location_stream(room), "stop the location stream")

    def _run(self, coro, what: str) -> None:
        """Background work that is not a database write, so it does not queue
        behind the transcript."""

        async def run() -> None:
            try:
                await coro
            except Exception:
                logger.exception("failed to %s", what)

        task = asyncio.create_task(run())
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
