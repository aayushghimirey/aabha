from datetime import timedelta
from uuid import UUID

from livekit import api

from aabha.config import config
from aabha.db.model.user import User

# The name the agent worker registers under. Naming the agent switches LiveKit
# from automatic to explicit dispatch, so a job is created per connect rather
# than once per room - see create_dispatch below.
AGENT_NAME = "aabha"


def room_for(user_id: UUID) -> str:
    """One room per user, so nobody lands in a stranger's conversation."""
    return f"assistant-{user_id}"


def create_token(user: User) -> str:
    """Mints an access token letting this user join their own room, and only
    their own room."""
    return (
        api.AccessToken(
            api_key=config.LIVEKIT_API_KEY,
            api_secret=config.LIVEKIT_API_SECRET,
        )
        .with_identity(str(user.id))
        .with_name(user.username)
        .with_ttl(timedelta(minutes=config.LIVEKIT_TOKEN_TTL_MINUTES))
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room=room_for(user.id),
                # The room is made on demand, when the user first connects.
                room_create=True,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True,
            )
        )
        .to_jwt()
    )


def claims_for(token: str) -> api.access_token.Claims:
    """Verifies a token this service minted, so a caller holding one can act as
    that user without presenting their password again."""
    verifier = api.TokenVerifier(
        api_key=config.LIVEKIT_API_KEY,
        api_secret=config.LIVEKIT_API_SECRET,
    )

    return verifier.verify(token)


async def create_dispatch(room: str) -> None:
    """Asks LiveKit to start an agent job for `room`.

    Automatic dispatch fires when a room is created, so a user who leaves and
    rejoins before the room is torn down lands in a live room that will never
    get an agent. Tying the dispatch to the connect instead means a reused room
    still gets a job.
    """
    lkapi = api.LiveKitAPI(
        url=config.LIVEKIT_URL,
        api_key=config.LIVEKIT_API_KEY,
        api_secret=config.LIVEKIT_API_SECRET,
    )

    try:
        await lkapi.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(agent_name=AGENT_NAME, room=room)
        )
    finally:
        await lkapi.aclose()
