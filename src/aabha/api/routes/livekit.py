from fastapi import APIRouter, Depends, status

from aabha.api.dependencies import authenticate, room_from_token
from aabha.api.dto.livekit import LiveKitTokenResponse
from aabha.config import config
from aabha.db.model.user import User
from aabha.service import livekit_service

router = APIRouter(prefix="/livekit", tags=["livekit"])


@router.post("/token", response_model=LiveKitTokenResponse)
async def issue_token(user: User = Depends(authenticate)) -> LiveKitTokenResponse:
    """Exchanges a username and password for a LiveKit access token.

    Tokens expire (LIVEKIT_TOKEN_TTL_MINUTES), so a long session comes back
    here for another one rather than holding one forever.
    """
    return LiveKitTokenResponse(
        token=livekit_service.create_token(user),
        server_url=config.LIVEKIT_URL,
        room=livekit_service.room_for(user.id),
        identity=str(user.id),
    )


@router.post("/dispatch", status_code=status.HTTP_204_NO_CONTENT)
async def dispatch(room: str = Depends(room_from_token)) -> None:
    """Starts an agent job for the caller's room.

    Called on every connect, not just at sign-in: the room name is stable per
    user, so a reconnect can reuse a room LiveKit already created and would
    otherwise never dispatch into. The LiveKit token is the credential here,
    which keeps the password out of the reconnect path.
    """
    await livekit_service.create_dispatch(room)
