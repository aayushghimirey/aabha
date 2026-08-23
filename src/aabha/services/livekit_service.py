from datetime import timedelta
from uuid import UUID

from livekit import api

from aabha.config.config import config


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
