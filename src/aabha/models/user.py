from aabha.models.base import BaseEntity
from datetime import datetime

from pydantic import EmailStr


class User(BaseEntity):
    username: str
    password: str
    email: EmailStr
    dob: datetime
