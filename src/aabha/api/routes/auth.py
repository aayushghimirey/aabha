from fastapi import APIRouter, Depends, HTTPException, status

from aabha.api.dependencies import authenticate
from aabha.api.dto.user import SignUpRequest, UserResponse
from aabha.db.model.user import User
from aabha.service import user_service
from aabha.service.user_service import UsernameOrEmailTaken

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def sign_up(payload: SignUpRequest) -> UserResponse:
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


@router.post("/signin", response_model=UserResponse)
async def sign_in(user: User = Depends(authenticate)) -> UserResponse:
    return UserResponse.model_validate(user)
