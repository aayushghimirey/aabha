from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from aabha.models.base import BaseEntity

NAVIGATION_STATUS = Literal["pending", "started", "completed", "failed"]

# What a saved navigation can be moved to. "pending" is where every trip
# begins, so nothing ever moves back to it.
NAVIGATION_UPDATE = Literal["started", "completed", "failed"]


class NavigationPoint(BaseModel):
    latitude: float
    longitude: float


class Navigation(BaseEntity):
    user_id: UUID

    # Where the user was standing when they asked. Kept because a saved
    # navigation is only meaningful next to the trip it was planned from.
    start: NavigationPoint

    destination: NavigationPoint

    # What the user would call the place, and the postal-style line that tells
    # two places of the same name apart.
    destination_name: str
    destination_address: str = ""

    status: NAVIGATION_STATUS = "pending"
