from fastapi import APIRouter, Depends, status

from aabha.api.dependencies import authenticate, room_from_token
from aabha.api.schemas import TokenResponse, UserResponse
from aabha.config import config
from aabha.db.models import User
from aabha.service import livekit_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=UserResponse)
async def login(user: User = Depends(authenticate)) -> UserResponse:
    """Confirms a username and password and says who they belong to.

    Hands back no credential of its own - the LiveKit token from /auth/token
    is the only one this API issues.
    """
    return UserResponse.model_validate(user)


@router.post("/token", response_model=TokenResponse)
async def issue_token(user: User = Depends(authenticate)) -> TokenResponse:
    """Exchanges a username and password for a LiveKit access token.

    Tokens expire (LIVEKIT_TOKEN_TTL_MINUTES), so a long session comes back
    here for another one rather than holding one forever.
    """
    return TokenResponse(
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
