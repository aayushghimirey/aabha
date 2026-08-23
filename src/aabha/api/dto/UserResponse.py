from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class UserResponse(BaseModel):
    """Public view of a user - never carries the password hash."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: EmailStr
    dob: datetime
    created_at: datetime
    updated_at: datetime
