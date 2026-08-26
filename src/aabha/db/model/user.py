from datetime import date

from pydantic import EmailStr

from aabha.db.model.base_model import CoreEntity


class User(CoreEntity):
    """A row from users.

    Carries the password hash, so it must never be handed back from a route -
    api/dto/user.py has UserResponse for that.
    """

    username: str

    email: EmailStr

    password_hash: str

    dob: date
