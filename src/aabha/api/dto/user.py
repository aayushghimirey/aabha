from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SignUpRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    dob: date


class UserResponse(BaseModel):
    """The public view of a user. Built field by field rather than from the
    row, so the password hash has no way of reaching a response body."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: EmailStr
    dob: date
    created_at: datetime
    updated_at: datetime | None = None
