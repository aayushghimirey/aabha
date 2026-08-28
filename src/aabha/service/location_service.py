from __future__ import annotations

import json
import logging

from livekit import rtc
from livekit.agents import get_job_context
from pydantic import BaseModel

logger = logging.getLogger("aabha.agent")

# The name the client registers its handler under. Both sides have to agree on
# it - see LocationRpc in the mobile app and the handler in dev/index.html.
LOCATION_RPC_METHOD = "get_current_location"

# The client has to ask the device for a fix, and the user may have to answer a
# permission prompt first. The default is too short for that.
_RPC_TIMEOUT = 30.0


class Coordinate(BaseModel):
    """What the device sends back. The field names are the contract with the
    client, which may send more than this - anything extra is dropped."""

    latitude: float
    longitude: float


class LocationUnavailable(Exception):
    """Where the user is could not be established: the device never answered or
    refused. The message is written to be read out by the assistant as it is."""


class UserLocation:
    """Where the user is right now.

    Asks their device for a fix over LiveKit RPC. Nothing is stored and nothing
    is looked up - the numbers go straight back to whoever asked.
    """

    def __init__(self, user_identity: str) -> None:
        # Who to address an RPC to. The room has the agent in it too, so the
        # user's identity has to be carried rather than guessed at.
        self._user_identity = user_identity

    async def current_coordinates(self) -> Coordinate:
        """The device's latitude and longitude.

        Raises LocationUnavailable when the device will not say where it is.
        """
        print("ask current coordinates")
        try:
            payload = await get_job_context().room.local_participant.perform_rpc(
            destination_identity=self._user_identity,
                method=LOCATION_RPC_METHOD,
                payload="{}",
                response_timeout=_RPC_TIMEOUT,
            )
        except rtc.RpcError as e:
            # The device answered, and what it said is worth passing on: a
            # refused permission is not the same as a device that never
            # replied, and the assistant should say so.
            logger.info("location rpc refused: %s", e.message)
            raise LocationUnavailable(
                f"The user's device would not share a location: {e.message}"
            )
        except Exception:
            logger.exception("location rpc failed")
            raise LocationUnavailable(
                "The user's device did not answer with a location."
            )

        try:
            return Coordinate.model_validate(json.loads(payload))
        except Exception:
            logger.exception("location rpc returned %r", payload)
            raise LocationUnavailable(
                "The user's device sent back a location I could not read."
            )
