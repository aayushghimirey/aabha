import logging
from uuid import UUID

from geopy.distance import geodesic
from pydantic import BaseModel

from aabha.db.model.navigation_route import (
    NavigationRouteDraft,
    NavigationStatus,
)
from aabha.db.repo.navigation_route_repo import (
    change_navigation_status,
    register_navigation_route,
)
from aabha.service.location_service import Coordinates
from aabha.service.route_service import Route, RouteRequest, get_route

logger = logging.getLogger("aabha.agent")

# How far ahead a turn is called out, and how close to it the turn itself is
# given. Both in meters, and both sized for someone walking or driving slowly -
# a fix arrives every few seconds, so a shorter window would be stepped over.
_APPROACH_METERS = 50
_MANEUVER_METERS = 10

# Close enough to the last point of the route to call it arrived.
_ARRIVAL_METERS = 20


def distance_meters(current: Coordinates, target: Coordinates) -> float:
    return geodesic(
        (current.latitude, current.longitude),
        (target.latitude, target.longitude),
    ).meters


class NavigationSession(BaseModel):
    """Where the user is along a route right now.

    Only the live state - what has been said and which step is being walked -
    lives here. Nothing in it is written to the database; the engine owns that.
    """

    route: Route

    current_step_index: int = 0

    current_location: Coordinates | None = None

    approach_announced: bool = False
    maneuver_announced: bool = False

    arrived: bool = False

    def next_step(self) -> None:
        self.current_step_index += 1
        self.approach_announced = False
        self.maneuver_announced = False

    def update_location(self, location: Coordinates) -> None:
        self.current_location = location


def process(session: NavigationSession) -> str | None:
    """What there is to say about the fix the session is sitting on, or None
    when the user is between announcements and there is nothing to say.

    The near case is checked first: a fix that lands right on top of the turn
    should be given as the turn, not as an approach to it.
    """
    if session.current_location is None or session.arrived:
        return None

    # No next step means the last leg is being walked, and the only thing left
    # to announce is arriving.
    if session.current_step_index + 1 >= len(session.route.steps):
        remaining = distance_meters(
            session.current_location,
            session.route.coordinates[-1],
        )

        if remaining > _ARRIVAL_METERS:
            return None

        session.arrived = True

        return "Arrived"

    next_step = session.route.steps[session.current_step_index + 1]

    # Where the next maneuver happens.
    maneuver_index = next_step.way_points[0]

    maneuver_location = session.route.coordinates[maneuver_index]

    distance = distance_meters(session.current_location, maneuver_location)

    instruction = next_step.instruction.lower()

    if distance <= _MANEUVER_METERS:
        if session.maneuver_announced:
            return None

        session.maneuver_announced = True

        # The turn has been given, so the step it belongs to is the one being
        # walked from here on.
        session.next_step()

        return f"Now, {instruction}"

    if distance <= _APPROACH_METERS and not session.approach_announced:
        session.approach_announced = True

        return f"In about {round(distance)} meters, {instruction}"

    return None


class NavigationEngine:
    """One user's navigation, from asking for a route to arriving.

    Holds the live session and the row it was written to, so the route is
    saved once when it is new and only moved along after that.
    """

    def __init__(self, user_id: UUID) -> None:
        self.user_id = user_id

        self.session: NavigationSession | None = None
        self.navigation_route_id: UUID | None = None
        self.status: NavigationStatus = "pending"

    @property
    def navigating(self) -> bool:
        return self.session is not None and not self.session.arrived

    async def start(self, request: RouteRequest) -> Route:
        """Fetches the route, opens a session on it, and writes it down.

        Asking for a new route replaces whatever was being navigated - the old
        one is left cancelled rather than hanging about as active.
        """
        if self.navigating:
            await self.cancel()

        route = await get_route(request)

        self.session = NavigationSession(route=route)

        await self._register(request)

        return route

    async def _register(self, request: RouteRequest) -> None:
        """Saves the navigation, once. A session already carrying a row is one
        that has been saved, and re-registering it would leave two rows for the
        same trip."""
        if self.navigation_route_id is not None:
            return

        draft = NavigationRouteDraft(
            user_id=self.user_id,
            mode=request.travel_mode,
            initial_coords=(request.initial_lat, request.initial_lon),
            destination_coords=(request.destination_lat, request.destination_lon),
            destination=request.destination,
        )

        try:
            saved = await register_navigation_route(draft)
        except Exception:
            # A trip that could not be written down is still a trip the user
            # can be walked through, so this is not raised at them.
            logger.exception("could not register navigation route")
            return

        self.navigation_route_id = saved.id
        self.status = saved.status

        await self.set_status("active")

    async def set_status(self, status: NavigationStatus) -> None:
        """Moves the saved navigation on. Does nothing when there is no row to
        move, or when it is already where it is being moved to."""
        if self.navigation_route_id is None or self.status == status:
            return

        try:
            updated = await change_navigation_status(
                self.navigation_route_id, status
            )
        except Exception:
            logger.exception("could not set navigation status to %s", status)
            return

        if updated is not None:
            self.status = updated.status

    async def update_location(self, location: Coordinates) -> str | None:
        """Feeds a fix in and gives back what should be said about it, if
        anything. Arriving closes the navigation off."""
        if self.session is None:
            return None

        self.session.update_location(location)

        announcement = process(self.session)

        if self.session.arrived:
            await self.set_status("completed")

        return announcement

    async def cancel(self) -> None:
        """The user gave up on it, or asked for somewhere else instead."""
        await self.set_status("cancelled")

        self.session = None
        self.navigation_route_id = None
        self.status = "pending"
