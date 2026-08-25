from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from livekit import rtc

logger = logging.getLogger("aabha.agent")

# The names the browser registers its handlers under; both sides have to
# agree, so they live here rather than being spelled out at the call sites.
# The first asks once. The other two turn a running stream of positions on
# and off, for when the user is being guided somewhere and standing still is
# no longer the interesting case.
LOCATION_RPC_METHOD = "get_current_location"
LOCATION_STREAM_START = "start_location_stream"
LOCATION_STREAM_STOP = "stop_location_stream"

# The topic those streamed positions arrive on. Data messages rather than
# RPC: nothing is being asked of the agent, and a fix that goes missing is
# replaced by the next one a few steps later.
LOCATION_TOPIC = "aabha.location"

# How far the user has to move before their app sends another position.
# Close enough that a turn is never missed between two fixes, far enough that
# a phone sitting on a table says nothing at all.
LOCATION_STEP_M = 10.0

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
    return _parse(await _call(room, LOCATION_RPC_METHOD, ""))


async def start_location_stream(
    room: rtc.Room, step_m: float = LOCATION_STEP_M
) -> None:
    """Ask the user's app to report where they are as they move.

    From here until it is stopped, every `step_m` of travel arrives as a data
    message on LOCATION_TOPIC. The browser will not do this without an open
    permission, so the same refusals apply as for a single fix.
    """
    await _call(room, LOCATION_STREAM_START, json.dumps({"step_m": step_m}))

    logger.info("asked the user's app for a position every %.0fm", step_m)


async def stop_location_stream(room: rtc.Room) -> None:
    """Let the user's app put the GPS down.

    Best effort on purpose: this runs when a trip ends, and a trip that ends
    because the user hung up has nobody left to tell.
    """
    try:
        await _call(room, LOCATION_STREAM_STOP, "")
    except LocationUnavailable as err:
        logger.info("could not stop the location stream: %s", err)


def read_location(data: bytes) -> Location:
    """Read a position off the stream."""
    return _parse(data.decode("utf-8", errors="replace"))


async def _call(room: rtc.Room, method: str, payload: str) -> str:
    # A room with an agent in it normally holds exactly one other participant,
    # but an empty dict is reachable on a reconnect and must not raise
    # StopIteration out of a coroutine.
    participant = next(iter(room.remote_participants.values()), None)

    if participant is None:
        raise LocationUnavailable("there is nobody in the call to ask")

    try:
        return await room.local_participant.perform_rpc(
            destination_identity=participant.identity,
            method=method,
            payload=payload,
            response_timeout=_RESPONSE_TIMEOUT,
        )
    except rtc.RpcError as err:
        # A handler that raised on the browser side reports APPLICATION_ERROR
        # and carries its own message - "location permission was denied" and
        # the like - which is more use than anything written here.
        reason = _RPC_REASONS.get(err.code) or err.message
        logger.info("%s failed (%s): %s", method, err.code, err.message)

        raise LocationUnavailable(reason) from err


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
