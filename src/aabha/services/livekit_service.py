from datetime import timedelta
from uuid import UUID

from livekit import api

from aabha.config.config import config

# The name the worker registers under. Naming the agent switches LiveKit from
# automatic dispatch to explicit dispatch, so a job is created per connect
# rather than once per room - see create_dispatch below.
AGENT_NAME = "aabha"


def room_for(user_id: UUID) -> str:
    """One room per user, so participants never land in a stranger's session."""
    return f"assistant-{user_id}"


def create_token(user_id: UUID, username: str) -> str:
    return (
        api.AccessToken(
            api_key=config.LIVEKIT_API_KEY,
            api_secret=config.LIVEKIT_API_SECRET,
        )
        .with_identity(str(user_id))
        .with_name(username)
        .with_ttl(timedelta(minutes=config.LIVEKIT_TOKEN_TTL_MINUTES))
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room=room_for(user_id),
                # The room is created on demand when the user first connects.
                room_create=True,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True,
            )
        )
        .to_jwt()
    )


def _lkapi() -> api.LiveKitAPI:
    return api.LiveKitAPI(
        url=config.LIVEKIT_URL,
        api_key=config.LIVEKIT_API_KEY,
        api_secret=config.LIVEKIT_API_SECRET,
    )


def claims_for(token: str) -> api.access_token.Claims:
    """Verify a token this service minted, so a caller holding one can act as
    that user without presenting the password again."""
    verifier = api.TokenVerifier(
        api_key=config.LIVEKIT_API_KEY,
        api_secret=config.LIVEKIT_API_SECRET,
    )
    return verifier.verify(token)


async def create_dispatch(room: str) -> None:
    """Ask LiveKit to start a job for `room`.

    Automatic dispatch fires when a room is created, so a user who leaves and
    rejoins before the room is torn down lands in a live room that will never
    get an agent. An explicit dispatch is tied to the connect instead, so a
    reused room still gets a job.
    """
    lkapi = _lkapi()
    try:
        await lkapi.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(agent_name=AGENT_NAME, room=room)
        )
    finally:
        await lkapi.aclose()
