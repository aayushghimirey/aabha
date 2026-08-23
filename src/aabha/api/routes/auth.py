from fastapi import APIRouter, HTTPException, status

from aabha.api.dto.AuthRequest import AuthRequest
from aabha.api.dto.TokenResponse import TokenResponse
from aabha.api.dto.UserResponse import UserResponse
from aabha.config.config import config
from aabha.db.repo.user_repo import find_user_by_username
from aabha.models.user import User
from aabha.services.livekit_service import create_token, room_for
from aabha.services.security import verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

_INVALID_CREDENTIALS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid username or password",
)


async def check_credentials(payload: AuthRequest) -> User:
    user = await find_user_by_username(payload.username)
    if user is None:
        raise _INVALID_CREDENTIALS

    if not verify_password(user.password, payload.password):
        raise _INVALID_CREDENTIALS

    return user


@router.post("/login", response_model=UserResponse)
async def login(payload: AuthRequest) -> UserResponse:
    user = await check_credentials(payload)
    return UserResponse.model_validate(user, from_attributes=True)


@router.post("/token", response_model=TokenResponse)
async def issue_token(payload: AuthRequest) -> TokenResponse:
    """Exchange username + password for a LiveKit access token."""
    user = await check_credentials(payload)

    return TokenResponse(
        token=create_token(user.id, user.username),
        server_url=config.LIVEKIT_URL,
        room=room_for(user.id),
        identity=str(user.id),
    )
