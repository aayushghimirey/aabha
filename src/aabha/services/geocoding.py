from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import aiohttp
from livekit.agents.utils import http_context

from aabha.config import config

logger = logging.getLogger("aabha.agent")

# Nominatim asks every caller to identify itself and to stay under one request
# a second. Both are conditions of the public instance, not suggestions - point
# NOMINATIM_URL at your own instance if aabha ever gets busy enough to matter.
_USER_AGENT = "aabha-voice-companion (https://github.com/aayushghimirey/aabha)"

# A place name is a nicety: the agent already has coordinates, so waiting long
# for the prettier version only leaves the user listening to silence.
_TIMEOUT = aiohttp.ClientTimeout(total=5)

# Without this Nominatim answers in the local script - "ठमेल, नेपाल" rather
# than "Thamel, Nepal" - which the TTS voice then has to read. Keep it in step
# with whatever language that voice speaks.
_LANGUAGE = "en"

# Nominatim's zoom levels run from 0 (country) to 18 (building). 16 lands on
# the street or neighbourhood - close enough to say aloud, vague enough not to
# read back someone's house number.
_ZOOM = 16

# Most specific first; the first two that exist become the name. OSM fills in
# whichever of these its data has, and it is never the same set twice.
_LOCALITY_KEYS = (
    "neighbourhood",
    "suburb",
    "village",
    "town",
    "city_district",
    "city",
    "county",
    "state",
)


async def describe_location(latitude: float, longitude: float) -> str | None:
    """Turn coordinates into something speakable, such as "Thamel, Kathmandu".

    Returns None if the lookup fails for any reason - the caller still has the
    coordinates, and a missing place name is not worth failing a turn over.
    """
    params = {
        "lat": f"{latitude:.6f}",
        "lon": f"{longitude:.6f}",
        "format": "jsonv2",
        "zoom": str(_ZOOM),
        "addressdetails": "1",
        "accept-language": _LANGUAGE,
    }

    try:
        async with _session() as session:
            async with session.get(
                config.NOMINATIM_URL,
                params=params,
                headers={"User-Agent": _USER_AGENT},
                timeout=_TIMEOUT,
            ) as response:
                response.raise_for_status()
                # Nominatim answers errors with 200 and a JSON body, and
                # labels the body text/html while doing it.
                body = await response.json(content_type=None)
    except (aiohttp.ClientError, TimeoutError, ValueError) as err:
        # Expected often enough - a rate limit, a flaky network - that a
        # traceback would only be noise. The caller copes without a name.
        logger.warning("reverse geocoding failed: %s", err)
        return None

    return _name(body)


@asynccontextmanager
async def _session():
    """Reuse the job's shared session where there is one, so the agent is not
    opening a connection pool per question. Outside a job - a script, a test -
    fall back to a session of our own."""
    try:
        yield http_context.http_session()
    except RuntimeError:
        async with aiohttp.ClientSession() as session:
            yield session


def _name(body: object) -> str | None:
    if not isinstance(body, dict) or "error" in body:
        return None

    address = body.get("address")

    if not isinstance(address, dict):
        display = body.get("display_name")
        return display if isinstance(display, str) and display else None

    parts: list[str] = []

    for key in _LOCALITY_KEYS:
        value = address.get(key)

        if isinstance(value, str) and value not in parts:
            parts.append(value)

        if len(parts) == 2:
            break

    country = address.get("country")

    if isinstance(country, str) and country not in parts:
        parts.append(country)

    return ", ".join(parts) or None
