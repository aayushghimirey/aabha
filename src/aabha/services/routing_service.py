from __future__ import annotations

import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Literal

import aiohttp

from aabha.config import config
from aabha.models.navigation import NavigationPoint
from aabha.services.geo import distance_m
from aabha.services.http import session

logger = logging.getLogger("aabha.agent")

# How the user is travelling, in the words they would use. Everything below
# is written in these terms; the openrouteservice profile is an implementation
# detail that stops at the edge of this module.
TRAVEL_MODE = Literal["walk", "drive", "cycle"]

# A route on foot goes the wrong way up one-way streets and down alleys no car
# fits through, so the profile is not a preference - the wrong one is a
# different set of turns.
_PROFILES: dict[str, str] = {
    "walk": "foot-walking",
    "drive": "driving-car",
    "cycle": "cycling-regular",
}

# The geojson flavour of /v2/directions/{profile}. The bare endpoint answers
# with the line as an encoded polyline string; this one hands the coordinates
# back already decoded, and every metre of guidance below is arithmetic on
# those coordinates.
_DIRECTIONS_URL = "https://api.openrouteservice.org/v2/directions/{profile}/geojson"

# Someone is standing on a street corner waiting for this, so a slow answer is
# worth less than "I could not work out a route - say that again".
_TIMEOUT = aiohttp.ClientTimeout(total=12)

_LANGUAGE = "en"

# What openrouteservice's own error codes mean to someone being spoken to.
# Anything not listed here gets the generic reply, which is the honest one.
_ERRORS: dict[int, str] = {
    2004: "that is too far away for me to route",
    2009: "I could not find a way there by that means of travel",
    2010: "I could not find a road near there",
}

# A route between two fixed points does not change, and the free tier allows
# 40 requests a minute. Between a reroute, a reconnect and someone asking
# twice how far it is, the same route gets wanted more than once.
_CACHE_TTL_S = 30 * 60.0
_CACHE_MAX = 64

# Coordinates are rounded to this many decimals before they become a cache
# key - four is about eleven metres, which is a step and a half. Any closer
# and every location update would plan its own route; any further and a
# reroute would be answered with the route it just came off.
_KEY_DECIMALS = 4


class RoutingError(Exception):
    """No route could be worked out - no key, no road, no network.

    The message is meant to be read aloud, so it says what happened in the
    user's terms rather than the API's.
    """


@dataclass(frozen=True)
class RouteStep:
    """One instruction, and the stretch of the line it covers.

    openrouteservice describes the manoeuvre at the *start* of a step, so
    `start_index` is where the turn happens and the rest of the step is the
    road walked or driven afterwards.
    """

    instruction: str
    maneuver: int
    name: str | None
    distance_m: float
    duration_s: float
    start_index: int
    end_index: int

    # Which exit to take, when the manoeuvre is a roundabout.
    exit_number: int | None = None


@dataclass(frozen=True)
class Route:
    """A planned way there: the line on the ground, and what to do along it."""

    mode: str
    profile: str
    distance_m: float
    duration_s: float

    # Every coordinate of the line, in order.
    points: list[NavigationPoint]

    # How far along the line each of those points sits. Kept beside the points
    # because working out where someone is means asking "how far in is this",
    # and summing the line each time is the one thing that would make matching
    # a position expensive.
    cumulative_m: list[float]

    steps: list[RouteStep] = field(default_factory=list)

    @property
    def destination(self) -> NavigationPoint:
        return self.points[-1]


async def plan_route(
    origin: NavigationPoint,
    destination: NavigationPoint,
    mode: TRAVEL_MODE = "walk",
) -> Route:
    """Work out how to get from one point to the other.

    Answers from cache when the same trip has been planned recently, so
    rerouting and re-asking cost nothing.

    Raises RoutingError when no route could be had, with a reason that can be
    said out loud.
    """
    profile = _PROFILES.get(mode)

    if profile is None:
        raise RoutingError(f"I do not know how to route for {mode}")

    if not config.OPEN_ROUTE_API_KEY:
        raise RoutingError("directions are not configured on my side")

    key = _cache_key(profile, origin, destination)
    cached = _cached(key)

    if cached is not None:
        logger.info("route for %s served from cache", profile)

        return cached

    body = await _request(profile, origin, destination)
    route = _build(body, mode, profile)

    _store(key, route)

    logger.info(
        "planned a %s route: %.0fm, %.0fs, %d step(s)",
        profile,
        route.distance_m,
        route.duration_s,
        len(route.steps),
    )

    return route


async def _request(
    profile: str, origin: NavigationPoint, destination: NavigationPoint
) -> dict:
    payload = {
        "coordinates": [
            [round(origin.longitude, 6), round(origin.latitude, 6)],
            [round(destination.longitude, 6), round(destination.latitude, 6)],
        ],
        "instructions": True,
        "units": "m",
        "language": _LANGUAGE,
        # The default simplifies the line for drawing, which loses exactly the
        # corners a position has to be matched against.
        "geometry_simplify": False,
    }

    try:
        async with session() as http:
            async with http.post(
                _DIRECTIONS_URL.format(profile=profile),
                json=payload,
                headers={
                    "Authorization": config.OPEN_ROUTE_API_KEY,
                    "Content-Type": "application/json",
                },
                timeout=_TIMEOUT,
            ) as response:
                # A refused route explains itself in the body, and
                # raise_for_status would throw that away.
                body = await response.json(content_type=None)

                if response.status >= 400:
                    raise RoutingError(_reason(body, response.status))
    except (aiohttp.ClientError, TimeoutError, ValueError) as err:
        logger.warning("routing request failed: %s", err)

        raise RoutingError("the directions service is not answering") from err

    return body if isinstance(body, dict) else {}


def _reason(body: object, status: int) -> str:
    """Turn a rejection into something worth saying."""
    error = body.get("error") if isinstance(body, dict) else None

    if isinstance(error, dict):
        code = error.get("code")

        if isinstance(code, int) and code in _ERRORS:
            logger.info("openrouteservice refused the route (%s)", code)

            return _ERRORS[code]

        logger.warning("openrouteservice error: %s", error.get("message") or error)
    else:
        logger.warning("openrouteservice returned %s: %s", status, error or body)

    if status in (401, 403):
        return "my directions key is not being accepted"

    return "I could not work out a route there"


def _build(body: dict, mode: str, profile: str) -> Route:
    features = body.get("features")
    feature = features[0] if isinstance(features, list) and features else None

    if not isinstance(feature, dict):
        raise RoutingError("I could not work out a route there")

    geometry = feature.get("geometry")
    coordinates = geometry.get("coordinates") if isinstance(geometry, dict) else None

    points = _points(coordinates)

    # One point is a place, not a way to get anywhere, and everything below
    # measures progress between pairs of them.
    if len(points) < 2:
        raise RoutingError("the route that came back was empty")

    properties = feature.get("properties")
    properties = properties if isinstance(properties, dict) else {}
    summary = properties.get("summary")
    summary = summary if isinstance(summary, dict) else {}

    cumulative = _cumulative(points)

    return Route(
        mode=mode,
        profile=profile,
        # A route with one leg reports no summary of its own; the line is
        # still there to be measured.
        distance_m=float(summary.get("distance") or cumulative[-1]),
        duration_s=float(summary.get("duration") or 0.0),
        points=points,
        cumulative_m=cumulative,
        steps=_steps(properties.get("segments"), len(points)),
    )


def _points(coordinates: object) -> list[NavigationPoint]:
    """GeoJSON puts longitude first; everything else here does not."""
    if not isinstance(coordinates, list):
        return []

    points: list[NavigationPoint] = []

    for pair in coordinates:
        if not isinstance(pair, list) or len(pair) < 2:
            continue

        try:
            points.append(
                NavigationPoint(latitude=float(pair[1]), longitude=float(pair[0]))
            )
        except (TypeError, ValueError):
            continue

    return points


def _cumulative(points: list[NavigationPoint]) -> list[float]:
    """How far into the route each point is, in metres."""
    totals = [0.0]

    for previous, point in zip(points, points[1:]):
        totals.append(totals[-1] + distance_m(previous, point))

    return totals


def _steps(segments: object, point_count: int) -> list[RouteStep]:
    """Flatten the legs into one list of instructions.

    A two-point request comes back as a single segment, but the waypoint
    indices are into the whole line either way, so the legs can be run
    together without renumbering anything.
    """
    if not isinstance(segments, list):
        return []

    steps: list[RouteStep] = []

    for segment in segments:
        if not isinstance(segment, dict):
            continue

        for raw in segment.get("steps") or []:
            step = _step(raw, point_count)

            if step is not None:
                steps.append(step)

    return steps


def _step(raw: object, point_count: int) -> RouteStep | None:
    if not isinstance(raw, dict):
        return None

    waypoints = raw.get("way_points")

    if not isinstance(waypoints, list) or len(waypoints) < 2:
        return None

    try:
        start_index = int(waypoints[0])
        end_index = int(waypoints[1])
    except (TypeError, ValueError):
        return None

    # A step pointing past the end of the line would send every distance
    # measured from it off into nothing.
    if not 0 <= start_index <= end_index < point_count:
        return None

    name = raw.get("name")

    # openrouteservice writes an unnamed road as "-", which is not a name and
    # must never be read out as one.
    name = name.strip() if isinstance(name, str) else ""
    name = name if name and name != "-" else None

    exit_number = raw.get("exit_number")

    return RouteStep(
        instruction=str(raw.get("instruction") or "").strip(),
        maneuver=int(raw.get("type") or 0),
        name=name,
        distance_m=float(raw.get("distance") or 0.0),
        duration_s=float(raw.get("duration") or 0.0),
        start_index=start_index,
        end_index=end_index,
        exit_number=int(exit_number) if isinstance(exit_number, int) else None,
    )


# -- cache ----------------------------------------------------------------

# Oldest first, so trimming is a matter of dropping from the front.
_CACHE: "OrderedDict[tuple, tuple[float, Route]]" = OrderedDict()


def _cache_key(
    profile: str, origin: NavigationPoint, destination: NavigationPoint
) -> tuple:
    return (
        profile,
        round(origin.latitude, _KEY_DECIMALS),
        round(origin.longitude, _KEY_DECIMALS),
        round(destination.latitude, _KEY_DECIMALS),
        round(destination.longitude, _KEY_DECIMALS),
    )


def _cached(key: tuple) -> Route | None:
    entry = _CACHE.get(key)

    if entry is None:
        return None

    stored_at, route = entry

    if time.monotonic() - stored_at > _CACHE_TTL_S:
        del _CACHE[key]

        return None

    _CACHE.move_to_end(key)

    return route


def _store(key: tuple, route: Route) -> None:
    _CACHE[key] = (time.monotonic(), route)
    _CACHE.move_to_end(key)

    while len(_CACHE) > _CACHE_MAX:
        _CACHE.popitem(last=False)
