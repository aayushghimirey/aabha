from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Literal

from aabha.models.navigation import NavigationPoint
from aabha.services.geo import distance_m, project
from aabha.services.routing_service import Route, RouteStep

logger = logging.getLogger("aabha.agent")

CUE_KIND = Literal["approach", "turn", "arrive", "off_route"]

# How far ahead of a turn it is worth mentioning, per means of travel: early
# enough to prepare, and again at the corner. The distances are longer by car
# because the same warning has to survive being given at fifteen metres a
# second, and a driver gets the middle warning a walker does not - missing a
# turn costs a walker a few steps and a driver the next junction.
#
# The count matters as much as the distances. This is a voice in someone's
# ear that also holds conversations, and three warnings a corner through a
# street of alleys is forty interruptions in twenty minutes.
_ANNOUNCE_M: dict[str, tuple[float, ...]] = {
    "walk": (100.0, 12.0),
    "cycle": (200.0, 25.0),
    "drive": (500.0, 150.0, 40.0),
}

# How far off the line someone has to be before it stops being GPS drift and
# starts being a wrong turn. A phone in a street of tall buildings is
# routinely twenty metres out while standing still.
_OFF_ROUTE_M: dict[str, float] = {"walk": 35.0, "cycle": 45.0, "drive": 60.0}

# Two fixes in a row, so one bad reading off a wall does not send the route
# back to openrouteservice.
_OFF_ROUTE_STRIKES = 2

# Close enough to call it arrived. A door is not a coordinate, and a walker
# who is twenty metres away can see the place.
_ARRIVED_M: dict[str, float] = {"walk": 25.0, "cycle": 30.0, "drive": 40.0}

# Two turns can fall within a few metres of each other in an old town, and a
# voice that reads out both at once is worse than one that reads out neither.
# The last call before a corner is exempt: that one cannot wait.
_MIN_GAP_S = 6.0

# Where a manoeuvre stops being ahead and starts being behind.
_PASSED_M = 2.0

# How far back and forward of the last known position to look when matching a
# fix to the line. Far enough that a fast car cannot outrun the window between
# updates, near enough that a route which doubles back on itself does not
# match the wrong half.
_LOOK_BACK = 2
_LOOK_AHEAD = 60

# openrouteservice's manoeuvre codes, as something to say and the same thing
# with a road name in it. Written the way it would be said out loud - "carry
# straight on onto Pragya Marg" is what a naive template produces, and not
# what anybody says.
_MANEUVERS: dict[int, tuple[str, str]] = {
    0: ("turn left", "turn left onto {name}"),
    1: ("turn right", "turn right onto {name}"),
    2: ("take a sharp left", "take a sharp left onto {name}"),
    3: ("take a sharp right", "take a sharp right onto {name}"),
    4: ("bear left", "bear left onto {name}"),
    5: ("bear right", "bear right onto {name}"),
    6: ("carry straight on", "carry on along {name}"),
    7: ("go round the roundabout", "go round the roundabout onto {name}"),
    8: ("come off the roundabout", "come off the roundabout onto {name}"),
    9: ("turn back the way you came", "turn back onto {name}"),
    11: ("set off", "set off along {name}"),
    12: ("keep left", "keep left onto {name}"),
    13: ("keep right", "keep right onto {name}"),
}

_DEPART = 11
_ARRIVE = 10
_ROUNDABOUT = 7

# Openrouteservice raises one of these wherever a road changes name or a
# junction is passed without turning. There is nothing to do about them - the
# instruction is to keep doing what you are already doing - and announcing
# them buries the turns that do need acting on. Skipping them also means the
# countdown runs to the next real corner instead of stopping at a name change
# fifty metres short of it.
_STRAIGHT_ON = 6

_ORDINALS = (
    "first",
    "second",
    "third",
    "fourth",
    "fifth",
    "sixth",
    "seventh",
    "eighth",
    "ninth",
)


@dataclass(frozen=True)
class Cue:
    """Something worth saying out loud, now, without being asked."""

    text: str
    kind: CUE_KIND


@dataclass(frozen=True)
class Progress:
    """Where they have got to, for when they ask rather than are told."""

    remaining_m: float
    remaining_s: float
    travelled_m: float
    off_route: bool
    arrived: bool

    # What to do next, and how far off it is. Both empty at the last step,
    # where the only thing left is to arrive.
    next_instruction: str | None
    next_turn_m: float | None


class RouteTracker:
    """Follows a planned route as the fixes come in.

    Holds one route and the last place the user was matched to on it, and
    answers each new position with the one thing worth saying at that moment,
    or with nothing at all - which is the usual answer, and the reason this
    is worth having. A voice that spoke on every update would be unusable.
    """

    def __init__(self, route: Route, destination_name: str) -> None:
        self.route = route
        self.destination_name = destination_name

        self._announce = _ANNOUNCE_M.get(route.mode, _ANNOUNCE_M["walk"])
        self._off_route_m = _OFF_ROUTE_M.get(route.mode, _OFF_ROUTE_M["walk"])
        self._arrived_m = _ARRIVED_M.get(route.mode, _ARRIVED_M["walk"])

        # Every turn on the route, in order, with how far into the line it
        # happens. openrouteservice describes a manoeuvre at the start of the
        # step it begins, so this is the point the distances count down to.
        self._turns: list[tuple[int, RouteStep, float]] = [
            (index, step, route.cumulative_m[step.start_index])
            for index, step in enumerate(route.steps)
            if step.maneuver not in (_DEPART, _STRAIGHT_ON)
        ]

        # How many fixes have been matched against this route. Nought means
        # nothing has been heard from the user's app yet, which is a different
        # thing from their not having moved.
        self.updates = 0

        self._segment = 0
        self._along_m = 0.0
        self._off_m = 0.0

        # (turn, how urgent) pairs already said, so nothing is said twice and
        # a warning is never repeated once a nearer one has been given.
        self._spoken: set[tuple[int, int]] = set()

        self._strikes = 0
        self._off_route = False
        self._arrived = False
        self._spoke_at = 0.0

    # -- being told -------------------------------------------------------

    def update(self, point: NavigationPoint, accuracy_m: float | None = None) -> Cue | None:
        """Take a fix and answer with what should be said about it, if anything."""
        self.updates += 1

        self._segment, self._along_m, self._off_m = self._snap(point)

        if self._arrived:
            return None

        if distance_m(point, self.route.destination) <= self._arrived_m:
            self._arrived = True

            logger.info("arrived at %s", self.destination_name)

            return Cue(text=self._arrival_line(), kind="arrive")

        # A fix that is only accurate to fifty metres cannot show that someone
        # is thirty-five metres off course. Believing it would send the route
        # back to be planned again on the strength of nothing.
        tolerance = max(self._off_route_m, accuracy_m or 0.0)

        if self._off_m > tolerance:
            self._strikes += 1

            if self._strikes >= _OFF_ROUTE_STRIKES and not self._off_route:
                self._off_route = True

                logger.info("off route by %.0fm", self._off_m)

                return Cue(
                    text=(
                        "It looks like you have come off the route. Give me a"
                        " moment and I will work out the way from here."
                    ),
                    kind="off_route",
                )

            return None

        self._strikes = 0
        self._off_route = False

        return self._turn_cue()

    def _turn_cue(self) -> Cue | None:
        turn = self._upcoming()

        if turn is None:
            return None

        index, step, at_m = turn
        away_m = at_m - self._along_m

        urgency = self._urgency(away_m)

        if urgency is None or (index, urgency) in self._spoken:
            return None

        last = len(self._announce) - 1

        # Everything less urgent than what is about to be said is now moot:
        # "in a hundred and fifty metres" after "turn left now" is noise.
        if urgency < last and time.monotonic() - self._spoke_at < _MIN_GAP_S:
            return None

        for level in range(urgency + 1):
            self._spoken.add((index, level))

        self._spoke_at = time.monotonic()

        return Cue(
            text=self._phrase(step, away_m, urgent=urgency == last),
            kind="turn" if urgency == last else "approach",
        )

    def _upcoming(self) -> tuple[int, RouteStep, float] | None:
        """The next thing they have to do, and how far into the route it is."""
        for turn in self._turns:
            if turn[2] - self._along_m > -_PASSED_M:
                return turn

        return None

    def _urgency(self, away_m: float) -> int | None:
        """Which warning a distance has earned - the nearest one that fits."""
        urgency: int | None = None

        for level, threshold in enumerate(self._announce):
            if away_m <= threshold:
                urgency = level

        return urgency

    # -- being asked ------------------------------------------------------

    def progress(self) -> Progress:
        remaining_m = max(0.0, self.route.distance_m - self._along_m)

        # The route's own estimate, scaled by how much of it is left. Not a
        # fresh estimate - it does not know they have been standing still -
        # but it is the same clock the trip was described with.
        share = remaining_m / self.route.distance_m if self.route.distance_m else 0.0

        turn = self._upcoming()

        return Progress(
            remaining_m=remaining_m,
            remaining_s=self.route.duration_s * share,
            travelled_m=self._along_m,
            off_route=self._off_route,
            arrived=self._arrived,
            next_instruction=(
                self._phrase(turn[1], turn[2] - self._along_m, urgent=False)
                if turn is not None
                else None
            ),
            next_turn_m=turn[2] - self._along_m if turn is not None else None,
        )

    def opening(self) -> str:
        """How the trip is described before a step of it has been taken."""
        first = self.route.steps[0] if self.route.steps else None

        start = (
            self._movement(first)
            if first is not None and first.maneuver == _DEPART
            else None
        )

        line = (
            f"It is about {say_distance(self.route.distance_m)} to"
            f" {self.destination_name}, roughly"
            f" {say_duration(self.route.duration_s)} {_BY[self.route.mode]}."
        )

        return f"{line} To start, {start}." if start else line

    # -- matching a fix to the line ---------------------------------------

    def _snap(self, point: NavigationPoint) -> tuple[int, float, float]:
        """Find where on the route a position belongs.

        Looks around where they were last seen first, which is what keeps a
        route that passes the same corner twice from jumping between the two.
        Only when nothing near fits does it consider the whole line - which is
        the case where they really have gone somewhere else.
        """
        segments = len(self.route.points) - 1

        first = max(0, self._segment - _LOOK_BACK)
        last = min(segments, self._segment + _LOOK_AHEAD)

        near = self._scan(point, first, last)

        if near[2] > self._off_route_m and (first > 0 or last < segments):
            whole = self._scan(point, 0, segments)

            if whole[2] < near[2]:
                return whole

        return near

    def _scan(
        self, point: NavigationPoint, first: int, last: int
    ) -> tuple[int, float, float]:
        points = self.route.points
        cumulative = self.route.cumulative_m

        best_segment = first
        best_along = cumulative[first]
        best_off = float("inf")

        for index in range(first, max(first + 1, last)):
            share, off_m = project(point, points[index], points[index + 1])

            if off_m < best_off:
                best_segment = index
                best_off = off_m
                best_along = cumulative[index] + share * (
                    cumulative[index + 1] - cumulative[index]
                )

        return best_segment, best_along, best_off

    # -- putting it into words --------------------------------------------

    def _phrase(self, step: RouteStep, away_m: float, urgent: bool) -> str:
        if step.maneuver == _ARRIVE:
            if urgent:
                return self._arrival_line()

            return (
                f"{self.destination_name} is about {say_distance(away_m)} ahead"
                f"{self._side(step)}."
            )

        movement = self._movement(step)

        if urgent:
            return f"{movement[0].upper()}{movement[1:]} now."

        return f"In {say_distance(away_m)}, {movement}."

    def _movement(self, step: RouteStep) -> str:
        """What to do, in words, with the road named where naming it helps."""
        plain, named = _MANEUVERS.get(step.maneuver, ("carry on", "carry on along {name}"))

        if step.maneuver == _ROUNDABOUT and step.exit_number:
            exit_name = (
                _ORDINALS[step.exit_number - 1]
                if 1 <= step.exit_number <= len(_ORDINALS)
                else None
            )

            if exit_name:
                plain = f"take the {exit_name} exit at the roundabout"
                named = plain + " onto {name}"

        name = _speakable(step.name)

        return named.format(name=name) if name else plain

    def _arrival_line(self) -> str:
        arrive = self.route.steps[-1] if self.route.steps else None
        side = self._side(arrive) if arrive is not None else ""

        return f"You have arrived at {self.destination_name}{side}."

    def _side(self, step: RouteStep | None) -> str:
        """openrouteservice says which side of the road the place is on inside
        the arrival wording, and nowhere else. It is the one part of that
        sentence worth keeping."""
        instruction = (step.instruction if step else "").lower()

        if "on the right" in instruction:
            return ", on your right"

        if "on the left" in instruction:
            return ", on your left"

        return ""


# -- words for numbers ----------------------------------------------------

_BY = {"walk": "on foot", "drive": "by car", "cycle": "on a bike"}


def _speakable(name: str | None) -> str | None:
    """Whether a road name can be read out by an English voice.

    Half the streets on this map are named in Devanagari, and the voice makes
    noise rather than words out of them. "Turn left" on its own is a real
    instruction; "turn left onto" followed by mangled syllables is not.
    """
    if not name or not name.isascii():
        return None

    return name


def say_distance(metres: float) -> str:
    """A distance as it would be said, rounded to what can be acted on.

    Nobody turns left in thirty-seven metres.
    """
    if metres >= 1000:
        kilometres = f"{metres / 1000:.1f}".removesuffix(".0")

        return f"{kilometres} kilometre{'' if kilometres == '1' else 's'}"

    if metres >= 100:
        return f"{int(round(metres / 50.0) * 50)} metres"

    return f"{max(10, int(round(metres / 10.0) * 10))} metres"


def say_duration(seconds: float) -> str:
    if seconds < 60:
        return "under a minute"

    minutes = int(round(seconds / 60.0))

    if minutes < 60:
        return "a minute" if minutes == 1 else f"{minutes} minutes"

    hours, minutes = divmod(minutes, 60)
    hour_text = "an hour" if hours == 1 else f"{hours} hours"

    return hour_text if not minutes else f"{hour_text} and {minutes} minutes"
