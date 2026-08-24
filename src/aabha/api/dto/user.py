from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    dob: datetime


class UserUpdate(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    email: EmailStr
    dob: datetime


class UserResponse(BaseModel):
    """Public view of a user - never carries the password hash."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: EmailStr
    dob: datetime
    created_at: datetime
    updated_at: datetime
