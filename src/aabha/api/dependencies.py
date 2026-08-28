from fastapi import Header, HTTPException, status

from aabha.api.schemas import AuthRequest
from aabha.db.models import User
from aabha.service import livekit_service, user_service

INVALID_CREDENTIALS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid username or password",
)


async def authenticate(payload: AuthRequest) -> User:
    """The user behind a username and password, or 401."""
    user = await user_service.sign_in(payload.username, payload.password)

    if user is None:
        raise INVALID_CREDENTIALS

    return user


def room_from_token(authorization: str | None = Header(default=None)) -> str:
    """The room a bearer LiveKit token actually grants.

    Read from the token rather than taken from the request body, so a caller
    cannot act on a room the token does not let them into.
    """
    # Optional so that a missing header is answered as 401 rather than as the
    # 422 FastAPI gives a required header that was not sent.
    if not authorization:
        raise INVALID_CREDENTIALS

    scheme, _, token = authorization.partition(" ")

    if scheme.lower() != "bearer" or not token:
        raise INVALID_CREDENTIALS

    try:
        claims = livekit_service.claims_for(token)
    except Exception:
        raise INVALID_CREDENTIALS

    room = claims.video.room if claims.video else None

    if not room:
        raise INVALID_CREDENTIALS

    return room
