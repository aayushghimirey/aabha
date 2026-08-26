from __future__ import annotations

import asyncio
import json
import logging
from time import monotonic

from livekit import rtc
from livekit.agents import get_job_context
from pydantic import BaseModel

from aabha.service.geoapify_service import Location, reverse_geocode

logger = logging.getLogger("aabha.agent")

# The name the client registers its handler under. Both sides have to agree on
# it, so it lives here rather than inline - see dev/index.html.
COORDINATES_RPC_METHOD = "get_current_coordinates"

# The client has to ask the browser for a fix, and the user may have to answer a
# permission prompt first. The default is too short for that.
_RPC_TIMEOUT = 20.0

# How long a fix is worth reusing. Asking the device costs a round trip and, on
# the web client, can put a permission prompt in front of the user - so the two
# things that want a fix in the same breath should not each ask for one. Short
# enough that someone on the move is not placed where they were.
_FIX_TTL = 30.0


class Coordinates(BaseModel):
    """What the device sends back. The field names are the contract with the
    client - see the RPC handler in dev/index.html."""

    latitude: float
    longitude: float


class LocationUnavailable(Exception):
    """Where the user is could not be established: the device never answered,
    refused, or the lookup fell over. The message is written to be read out by
    the assistant as it is."""


class UserLocation:
    """Where the user is right now.

    Two separate questions, because they are wanted separately: the fix itself,
    for anything that measures or gets handed to a map, and what is at it, for
    anything that gets spoken. Neither is made to go through the other.
    """

    def __init__(self, user_identity: str) -> None:
        # Who to address an RPC to. The room has the agent in it too, so the
        # user's identity has to be carried rather than guessed at.
        self._user_identity = user_identity

        self._fix: Coordinates | None = None
        self._fix_at = 0.0
        # Both questions can be asked at once - the model is free to call both
        # tools in the same turn - and without this they would race into two
        # device prompts.
        self._lock = asyncio.Lock()

    async def current_coordinates(self, max_age: float = _FIX_TTL) -> Coordinates:
        """The fix itself. Reused for a moment after it is taken, so asking
        twice in a row does not prompt the user twice."""
        fresh = self._fresh_fix(max_age)

        if fresh is not None:
            return fresh

        async with self._lock:
            # Whoever held the lock may have just taken one.
            fresh = self._fresh_fix(max_age)

            if fresh is not None:
                return fresh

            fix = await self._ask_device()

            self._fix = fix
            self._fix_at = monotonic()

            return fix

    async def current_address(self) -> Location:
        """What is where the user is, in words.

        Raises LocationUnavailable when the device will not say where it is, or
        when the fix is somewhere nothing is known about.
        """
        return await self.describe(await self.current_coordinates())

    async def describe(self, coordinates: Coordinates) -> Location:
        """What is at a fix. Works on any coordinates, not only the user's."""
        try:
            location = await reverse_geocode(
                coordinates.latitude, coordinates.longitude
            )
        except Exception:
            logger.exception("reverse geocode failed")
            raise LocationUnavailable(
                "I could not look up what is at the user's location."
            )

        if location is None:
            logger.info("nothing known at %s", coordinates)
            raise LocationUnavailable(
                "The user's location is not anywhere I can put a name to."
            )

        return location

    def _fresh_fix(self, max_age: float) -> Coordinates | None:
        if self._fix is None or monotonic() - self._fix_at > max_age:
            return None

        return self._fix

    async def _ask_device(self) -> Coordinates:
        try:
            payload = await get_job_context().room.local_participant.perform_rpc(
                destination_identity=self._user_identity,
                method=COORDINATES_RPC_METHOD,
                payload="{}",
                response_timeout=_RPC_TIMEOUT,
            )
        except rtc.RpcError as e:
            # The device answered, and what it said is worth passing on: a
            # refused permission is not the same as a device that never
            # replied, and the assistant should say so.
            logger.info("coordinates rpc refused: %s", e.message)
            raise LocationUnavailable(
                f"The user's device would not share a location: {e.message}"
            )
        except Exception:
            logger.exception("coordinates rpc failed")
            raise LocationUnavailable(
                "The user's device did not answer with a location."
            )

        try:
            return Coordinates.model_validate(json.loads(payload))
        except Exception:
            logger.exception("coordinates rpc returned %r", payload)
            raise LocationUnavailable(
                "The user's device sent back a location I could not read."
            )
