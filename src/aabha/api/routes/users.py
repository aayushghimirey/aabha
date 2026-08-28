from fastapi import APIRouter, HTTPException, status

from aabha.api.schemas import UserRegister, UserResponse
from aabha.service import user_service
from aabha.service.user_service import UsernameOrEmailTaken

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(payload: UserRegister) -> UserResponse:
    """Registers a user and hands back their public view.

    Registering does not sign anyone in - there is no session to hand back.
    A client that wants to start talking goes on to /auth/token with the same
    credentials.
    """
    try:
        user = await user_service.sign_up(
            username=payload.username,
            email=payload.email,
            password=payload.password,
            dob=payload.dob,
        )
    except UsernameOrEmailTaken:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already taken",
        )

    return UserResponse.model_validate(user)
