from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from aabha.db.model.base_model import CoreEntity

# The same names the routing provider takes, so nothing has to be mapped
# between what was asked for and what was stored - see route_service.TravelMode.
NavigationMode = Literal[
    "driving-car",
    "cycling-regular",
    "foot-walking",
]

NavigationStatus = Literal["pending", "active", "completed", "cancelled"]


class NavigationRouteDraft(BaseModel):
    """A navigation the user has asked for, before it is written down."""

    user_id: UUID
    mode: NavigationMode

    initial_coords: tuple[float, float]
    destination_coords: tuple[float, float]
    destination: str


class NavigationRoute(NavigationRouteDraft, CoreEntity):
    status: NavigationStatus = "pending"
