from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from livekit import rtc

logger = logging.getLogger("aabha.agent")

# The name the browser registers its handler under; both sides have to agree,
# so it lives here rather than being spelled out at the call site.
LOCATION_RPC_METHOD = "get_current_location"

# The first ask puts a permission prompt in front of the user, and the wait is
# then a human's rather than a network's - the 10s default is far too short.
_RESPONSE_TIMEOUT = 30.0

# What each failure means to someone speaking to the agent. The LLM reads
# these, so they are written as something it can say back.
_RPC_REASONS = {
    rtc.RpcError.ErrorCode.UNSUPPORTED_METHOD: (
        "their app cannot share a location - it may need reloading"
    ),
    rtc.RpcError.ErrorCode.RECIPIENT_NOT_FOUND: "they are no longer connected",
    rtc.RpcError.ErrorCode.RECIPIENT_DISCONNECTED: "they left the call",
    rtc.RpcError.ErrorCode.RESPONSE_TIMEOUT: (
        "they did not answer the permission prompt in time"
    ),
    rtc.RpcError.ErrorCode.CONNECTION_TIMEOUT: "the connection to their app stalled",
}


class LocationUnavailable(Exception):
    """The user's client could not, or would not, hand over a position.

    The message is meant to be read aloud by the agent, so it says what
    happened in the user's terms and never in RPC's.
    """


@dataclass(frozen=True)
class Location:
    latitude: float
    longitude: float
    accuracy_m: float | None = None


async def ask_user_location(room: rtc.Room) -> Location:
    """Ask the participant's browser for a GPS fix over LiveKit RPC.

    Raises LocationUnavailable for anything the user could plausibly fix -
    a denied prompt, a stale tab, a client that never registered the method.
    """
    # A room with an agent in it normally holds exactly one other participant,
    # but an empty dict is reachable on a reconnect and must not raise
    # StopIteration out of a coroutine.
    participant = next(iter(room.remote_participants.values()), None)

    if participant is None:
        raise LocationUnavailable("there is nobody in the call to ask")

    try:
        payload = await room.local_participant.perform_rpc(
            destination_identity=participant.identity,
            method=LOCATION_RPC_METHOD,
            payload="",
            response_timeout=_RESPONSE_TIMEOUT,
        )
    except rtc.RpcError as err:
        # A handler that raised on the browser side reports APPLICATION_ERROR
        # and carries its own message - "location permission was denied" and
        # the like - which is more use than anything written here.
        reason = _RPC_REASONS.get(err.code) or err.message
        logger.info("location request failed (%s): %s", err.code, err.message)

        raise LocationUnavailable(reason) from err

    return _parse(payload)


def _parse(payload: str) -> Location:
    """RPC answers with a string; the browser puts JSON in it."""
    try:
        data = json.loads(payload)
        return Location(
            latitude=float(data["latitude"]),
            longitude=float(data["longitude"]),
            accuracy_m=(
                float(data["accuracy"]) if data.get("accuracy") is not None else None
            ),
        )
    except (ValueError, TypeError, KeyError) as err:
        logger.warning("unreadable location payload: %r", payload)

        raise LocationUnavailable(
            "their app sent back a location I could not read"
        ) from err
