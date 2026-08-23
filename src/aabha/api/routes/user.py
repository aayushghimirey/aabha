from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from psycopg.errors import UniqueViolation

from aabha.api.dto.UserRegister import UserRegister
from aabha.api.dto.UserResponse import UserResponse
from aabha.api.dto.UserUpdate import UserUpdate
from aabha.db.repo.user_repo import (
    create_user,
    find_user_by_id,
    update_user,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister) -> UserResponse:
    try:
        user = await create_user(payload)
    except UniqueViolation:
        # The unique indexes are the source of truth: a pre-check would still race.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already taken",
        )

    return UserResponse.model_validate(user, from_attributes=True)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: UUID) -> UserResponse:
    user = await find_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return UserResponse.model_validate(user, from_attributes=True)


@router.put("/{user_id}", response_model=UserResponse)
async def update(user_id: UUID, payload: UserUpdate) -> UserResponse:
    try:
        user = await update_user(user_id, payload)
    except UniqueViolation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already taken",
        )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return UserResponse.model_validate(user, from_attributes=True)
