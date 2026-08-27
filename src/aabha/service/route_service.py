from typing import Literal

import aiohttp
from pydantic import BaseModel

from aabha.config import config
from aabha.service.location_service import Coordinates

_OPEN_ROUTE_API = "https://api.openrouteservice.org/v2/directions"
_OPEN_ROUTE_API_KEY = config.OPEN_ROUTE_API_KEY

TravelMode = Literal[
    "driving-car",
    "cycling-regular",
    "foot-walking",
]


class RouteRequest(BaseModel):
    initial_lat: float
    initial_lon: float

    travel_mode: TravelMode

    destination_lat: float
    destination_lon: float
    destination: str


class RouteStep(BaseModel):
    distance: float
    duration: float

    type: int
    instruction: str
    name: str

    way_points: tuple[int, int]


class RouteSummary(BaseModel):
    distance: float
    duration: float


class Route(BaseModel):
    coordinates: list[Coordinates]

    steps: list[RouteStep]

    summary: RouteSummary


async def get_route(route: RouteRequest) -> Route:
    url = f"{_OPEN_ROUTE_API}/{route.travel_mode}"

    params = {
        "api_key": _OPEN_ROUTE_API_KEY,
        "start": f"{route.initial_lon},{route.initial_lat}",
        "end": f"{route.destination_lon},{route.destination_lat}",
        "instructions": "true",
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            response.raise_for_status()

            data = await response.json()

    feature = data["features"][0]

    summary = feature["properties"]["summary"]
    segments = feature["properties"]["segments"]

    steps = []

    for segment in segments:
        for step in segment["steps"]:
            steps.append(
                {
                    "instruction": step.get("instruction"),
                    "name": step.get("name"),
                    "distance": step.get("distance"),
                    "duration": step.get("duration"),
                    "type": step.get("type"),
                    "way_points": step.get("way_points"),
                }
            )

    return Route(
        destination=route.destination,
        distance_meters=summary["distance"],
        duration_seconds=summary["duration"],
        geometry=feature["geometry"],
        steps=steps,
    )
