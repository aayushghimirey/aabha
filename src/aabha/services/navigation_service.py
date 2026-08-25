from __future__ import annotations

import logging
from dataclasses import dataclass, field

import aiohttp

from aabha.config import config
from aabha.models.navigation import NavigationPoint
from aabha.services.geo import distance_m
from aabha.services.http import session
from aabha.services.place_categories import PlaceCategory, resolve

logger = logging.getLogger("aabha.agent")

# Two endpoints, because there are two questions. The geocoder answers "where
# is this place called X"; Places answers "what shops of this kind are near
# here". Asking the geocoder the second question is how "mobile shops" once
# came back as a shop of that name 1,200km away.
_GEOCODE_URL = "https://api.geoapify.com/v1/geocode/search"
_PLACES_URL = "https://api.geoapify.com/v2/places"

# Someone is waiting mid-sentence for this, so a slow answer is worth less
# than a quick "I could not find it - say that again for me".
_TIMEOUT = aiohttp.ClientTimeout(total=8)

# Ask for more than we show: places arrive with duplicates - the same shop
# indexed twice, a building and its address - and those collapse below.
_FETCH_LIMIT = 20

# More than a handful of options cannot be read out loud, and a question that
# lists six things is not a question anyone can answer.
_MAX_CANDIDATES = 5

# Two hits this close together are the same place under two records, whatever
# their names say. ~11m, which is inside a single building.
_SAME_PLACE_DEGREES = 1e-4

_LANGUAGE = "en"

# How far out a category search reaches, in steps. It stops at the first ring
# that has anything, so a town centre answers with what is on the next street
# and a village still gets an answer rather than silence. The last ring is
# wide because OpenStreetMap coverage outside cities is thin - the honest
# answer there is often "the nearest one is 12km away".
_RADIUS_STEPS_M = (3_000, 10_000, 30_000)

# Where "nearby" stops for a named place the user asked to be kept close.
_NEARBY_RADIUS_M = 15_000


class DestinationLookupError(Exception):
    """The search could not be run at all - no key, no network, a bad reply.

    The message is meant to be read aloud, so it says what happened in the
    user's terms rather than the API's.
    """


@dataclass(frozen=True)
class DestinationCandidate:
    """One place the user might have meant."""

    name: str
    address: str
    point: NavigationPoint

    # Both optional: the category is missing for plain addresses, and the
    # distance needs an origin we do not always have.
    category: str | None = None
    distance_m: float | None = None

    def summary(self) -> dict[str, str | float | None]:
        """The shape handed to the model - what tells one candidate from
        another when the names are identical."""
        return {
            "name": self.name,
            "address": self.address,
            "category": self.category,
            "distance_km": (
                round(self.distance_m / 1000, 1) if self.distance_m is not None else None
            ),
        }


@dataclass(frozen=True)
class DestinationSearch:
    """What a search found, and how hard it had to look.

    The radius matters as much as the results: "nothing in the three
    kilometres around you, and the nearest is twelve away" is a true answer,
    and it is not one the candidate list alone can give.
    """

    candidates: list[DestinationCandidate] = field(default_factory=list)

    # What kind of place was searched for, when the request named a kind
    # rather than a place. None means the geocoder answered.
    category_label: str | None = None

    # How far out the search reached, when it was bounded.
    radius_m: int | None = None


async def find_destinations(
    query: str,
    origin: NavigationPoint | None = None,
    nearby_only: bool = False,
    limit: int = _MAX_CANDIDATES,
) -> DestinationSearch:
    """Search for the place the user described, nearest match first.

    Which search runs depends on what was asked. A kind of place - "a
    pharmacy", "mobile shops near me" - is looked up by category within a
    radius that widens until something is found, so the answer is always
    genuinely near the user. A named place - "Ananya Mobile & Electronics",
    "Pokhara" - goes to the geocoder, biased towards the user but not fenced
    in, so a place in the next city still resolves.

    Returns an empty search when nothing matched; raises DestinationLookupError
    when the search itself could not run.
    """
    query = query.strip()

    if not query:
        raise DestinationLookupError("I did not catch where they want to go")

    if not config.GEOAPIFY_API_KEY:
        raise DestinationLookupError("place search is not configured on my side")

    # The model's own read of the request counts as a nearby signal.
    category = resolve(query, nearby_hint=nearby_only)

    # A category search needs somewhere to search around. Without a fix on the
    # user there is nothing to do but read the words as a name.
    if category is not None and origin is not None:
        return await _search_category(category, origin, limit)

    return await _search_name(query, origin, nearby_only, limit)


async def _search_category(
    category: PlaceCategory, origin: NavigationPoint, limit: int
) -> DestinationSearch:
    """Find places of a kind, widening the circle until some turn up."""
    for radius_m in _RADIUS_STEPS_M:
        params = {
            "categories": category.categories,
            "filter": (
                f"circle:{origin.longitude:.6f},{origin.latitude:.6f},{radius_m}"
            ),
            "bias": f"proximity:{origin.longitude:.6f},{origin.latitude:.6f}",
            "limit": str(_FETCH_LIMIT),
            "lang": _LANGUAGE,
            "apiKey": config.GEOAPIFY_API_KEY,
        }

        body = await _get(_PLACES_URL, params, category.label)
        candidates = _rank(_collect(_properties(body), origin, category.label), category)

        if candidates:
            logger.info(
                "found %d %s within %dm",
                len(candidates),
                category.label,
                radius_m,
            )

            return DestinationSearch(
                candidates=candidates[:limit],
                category_label=category.label,
                radius_m=radius_m,
            )

    logger.info(
        "no %s within %dm of the user", category.label, _RADIUS_STEPS_M[-1]
    )

    return DestinationSearch(
        category_label=category.label, radius_m=_RADIUS_STEPS_M[-1]
    )


def _rank(
    candidates: list[DestinationCandidate], category: PlaceCategory
) -> list[DestinationCandidate]:
    """Put the places that are actually the thing asked for first.

    Geoapify's categories are coarse: a phone shop, a printer repair desk and
    a fridge showroom share `commercial.elektronics`. Asked for a mobile shop,
    the phone shop goes first even when the printer desk is closer - the
    nearest wrong answer is not a better answer. The rest are kept, in
    distance order, because a thin map is still worth reading out.
    """
    if not category.prefers:
        return candidates

    wanted = {kind.replace("_", " ") for kind in category.prefers}

    return sorted(candidates, key=lambda item: item.category not in wanted)


async def _search_name(
    query: str,
    origin: NavigationPoint | None,
    nearby_only: bool,
    limit: int,
) -> DestinationSearch:
    """Resolve a place the user named, nearest first where we know where they
    are."""
    params: dict[str, str] = {
        "text": query,
        "format": "json",
        "limit": str(_FETCH_LIMIT),
        "lang": _LANGUAGE,
        "apiKey": config.GEOAPIFY_API_KEY,
    }

    radius_m: int | None = None

    if origin is not None:
        params["bias"] = f"proximity:{origin.longitude:.6f},{origin.latitude:.6f}"

        if nearby_only:
            radius_m = _NEARBY_RADIUS_M
            params["filter"] = (
                f"circle:{origin.longitude:.6f},{origin.latitude:.6f},{radius_m}"
            )

    results = _results(await _get(_GEOCODE_URL, params, query))

    # Geoapify's proximity bias sometimes answers a perfectly good query with
    # nothing at all - "Pokhara" from Dharan comes back empty biased and finds
    # the city unbiased. A place the user named is worth having even when it
    # is not close, so drop the bias and ask again rather than say no.
    if not results and "bias" in params and not nearby_only:
        logger.info("retrying %r without proximity bias", query)

        del params["bias"]
        results = _results(await _get(_GEOCODE_URL, params, query))

    candidates = _collect(results, origin)

    if origin is not None:
        candidates = [item for item in candidates if not _too_far(item, results)]

    # Still nothing worth saying. Before giving up, ask whether the words were
    # a town: the geocoder answers "Pokhara" with five businesses in Kathmandu
    # called Pokhara Something and never the city, until it is asked for a
    # city specifically.
    if not candidates and not nearby_only:
        params["type"] = "city"
        results = _results(await _get(_GEOCODE_URL, params, query))
        candidates = _collect(results, origin)

    return DestinationSearch(candidates=candidates[:limit], radius_m=radius_m)


# Past this, a shop the geocoder matched by name is not the shop the user
# meant. Asked for "movie theater" it offers ones in India, Qatar and the
# United States, all scored full confidence - distance is the only thing that
# gives them away. Towns and regions are exempt: "Pokhara" really is 219km
# from Dharan, and is still the right answer.
_ABSURD_M = 150_000

_PLACE_TYPES = frozenset(
    {"city", "town", "village", "suburb", "populated_place", "state", "county", "country", "postcode"}
)


def _too_far(candidate: DestinationCandidate, results: list[object]) -> bool:
    if candidate.distance_m is None or candidate.distance_m < _ABSURD_M:
        return False

    for result in results:
        if not isinstance(result, dict) or _text(result, "name") != candidate.name:
            continue

        # A distant town is a real answer; a distant shop of the same name is
        # a coincidence of spelling.
        if _text(result, "result_type") in _PLACE_TYPES:
            return False

    logger.info(
        "dropping %r - %.0fkm away and matched on name alone",
        candidate.name,
        candidate.distance_m / 1000,
    )

    return True


def _results(body: dict) -> list[object]:
    results = body.get("results")

    if not isinstance(results, list):
        logger.warning("unexpected geocoder reply: %s", body.get("message") or body)

        return []

    return results


async def _get(url: str, params: dict[str, str], what: str) -> dict:
    try:
        async with session() as http:
            async with http.get(url, params=params, timeout=_TIMEOUT) as response:
                # Geoapify explains a rejected key or a malformed filter in the
                # body, which is worth logging before raise_for_status eats it.
                body = await response.json(content_type=None)
                response.raise_for_status()
    except (aiohttp.ClientError, TimeoutError, ValueError) as err:
        logger.warning("place search for %r failed: %s", what, err)

        raise DestinationLookupError(
            "the place search is not answering right now"
        ) from err

    return body if isinstance(body, dict) else {}


def _properties(body: dict) -> list[object]:
    """The Places API answers in GeoJSON; everything worth reading sits under
    each feature's `properties`, in the same shape the geocoder returns."""
    features = body.get("features")

    if not isinstance(features, list):
        logger.warning("unexpected places reply: %s", body.get("message") or body)

        return []

    return [
        feature.get("properties")
        for feature in features
        if isinstance(feature, dict)
    ]


def _collect(
    results: list[object],
    origin: NavigationPoint | None,
    label: str | None = None,
) -> list[DestinationCandidate]:
    candidates: list[DestinationCandidate] = []

    for result in results:
        candidate = _candidate(result, origin, label)

        if candidate is None or _is_duplicate(candidate, candidates):
            continue

        candidates.append(candidate)

    # Nearest first when we know where the user is; otherwise Geoapify's own
    # relevance order is the best signal available.
    if origin is not None:
        candidates.sort(key=lambda item: item.distance_m or 0.0)

    return candidates


def _candidate(
    result: object, origin: NavigationPoint | None, label: str | None = None
) -> DestinationCandidate | None:
    if not isinstance(result, dict) or _is_junk(result):
        return None

    try:
        point = NavigationPoint(
            latitude=float(result["lat"]), longitude=float(result["lon"])
        )
    except (KeyError, TypeError, ValueError):
        return None

    # A shop has a name; a house is only ever its address line. Plenty of
    # real places have no name in OpenStreetMap at all - most ATMs, half the
    # bus stops - and for those the kind of place is the honest thing to call
    # it. "An ATM on Adarsha Marg" beats reading the street name twice as
    # though it were two different shops.
    named = _text(result, "name")
    name = named or label or _text(result, "address_line1") or _text(
        result, "formatted"
    )

    if not name:
        return None

    # address_line2 is the part that separates the two Himalayan Java Coffees -
    # street, ward, city - and drops the name we just used. An unnamed place
    # never had a name in line 1, so its whole address is worth saying.
    address = (
        _text(result, "address_line2")
        if named
        else _text(result, "formatted") or _text(result, "address_line1")
    ) or _text(result, "formatted") or ""

    # Measured here rather than read off the reply. The geocoder's own
    # `distance` is from whatever region it matched, not from the user - it
    # calls a Kathmandu bank 1km away when the user is in Dharan, 219km off -
    # and a distance that is wrong is worse than one that is missing.
    distance = distance_m(origin, point) if origin is not None else None

    return DestinationCandidate(
        name=name,
        address=address,
        point=point,
        category=_category(result) or label,
        distance_m=float(distance) if distance is not None else None,
    )


def _category(result: dict) -> str | None:
    """What the place actually is, in words that can be said out loud.

    OpenStreetMap's own tag is the specific one - a shop tagged `mobile_phone`
    sits under Geoapify's broad `commercial.elektronics`, and only the tag
    tells a phone shop from a fridge showroom.
    """
    for key in ("commercial", "catering", "healthcare", "service", "accommodation"):
        section = result.get(key)

        if isinstance(section, dict):
            kind = section.get("type")

            if isinstance(kind, str) and kind:
                return kind.replace("_", " ")

    # The geocoder answers with a single flat category instead.
    return _text(result, "category")


def _is_junk(result: dict) -> bool:
    """Whether the geocoder matched on the words rather than the place.

    Asked for "Dharan bus park" it offers school bus parks in England, and
    scores every one of them zero. Its own confidence is the only thing that
    separates those from a real answer, so a zero is taken at its word.
    """
    rank = result.get("rank")

    if not isinstance(rank, dict):
        # The Places API does not rank - it answered a category, not a name.
        return False

    confidence = rank.get("confidence")

    return isinstance(confidence, (int, float)) and confidence <= 0


def _text(result: dict, key: str) -> str | None:
    value = result.get(key)

    return value.strip() if isinstance(value, str) and value.strip() else None


def _is_duplicate(
    candidate: DestinationCandidate, seen: list[DestinationCandidate]
) -> bool:
    """Whether this is a place we already have.

    Two records within ~11m are one place indexed twice. Two that read out
    identically - the same name at the same address, which is what unnamed
    places on one street come to - are worth collapsing too, since offering a
    choice nobody can tell apart is not offering a choice.
    """
    return any(
        (
            abs(candidate.point.latitude - other.point.latitude) < _SAME_PLACE_DEGREES
            and abs(candidate.point.longitude - other.point.longitude)
            < _SAME_PLACE_DEGREES
        )
        or (candidate.name == other.name and candidate.address == other.address)
        for other in seen
    )
