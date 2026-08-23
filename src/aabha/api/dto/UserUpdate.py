from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserUpdate(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    email: EmailStr
    dob: datetime
