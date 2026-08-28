from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegister(BaseModel):
    """What POST /users/register takes."""

    username: str = Field(min_length=3, max_length=32)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    dob: date


class AuthRequest(BaseModel):
    """The credentials POST /auth/login and POST /auth/token both take.

    The API issues no session of its own, so the password is presented once per
    call rather than exchanged for a cookie.
    """

    username: str
    password: str


class UserResponse(BaseModel):
    """The public view of a user. Declared field by field rather than built
    from the row, so the password hash has no way of reaching a response body."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: EmailStr
    dob: date
    created_at: datetime
    updated_at: datetime | None = None


class TokenResponse(BaseModel):
    """Everything a client needs to open a LiveKit connection."""

    token: str
    server_url: str
    room: str
    identity: str
