import aiohttp
from pydantic import BaseModel

from aabha.config import config
from aabha.service.location_service import Coordinate
from aabha.utils.goole_search_place_type import GooglePlaceType

_GOOGLE_NEARBY_API = "https://places.googleapis.com/v1/places:searchNearby"
_GOOGLE_MAP_API_KEY = config.GOOGLE_MAP_API_KEY


class PlaceResult(BaseModel):
    places: list["Place"]


class Place(BaseModel):
    id: str
    formattedAddress: str
    location: Coordinate
    displayName: dict[str, str]
    primaryType: str | None = None


async def find_nearby_places(
    query: GooglePlaceType,
    user_location: Coordinate,
    radius: float = 500.0,
) -> PlaceResult:
    """
    Find places near the user, increasing the radius if no results are found.
    """
    if not _GOOGLE_MAP_API_KEY:
        raise ValueError("GOOGLE_MAP_API_KEY is not set")

    async with aiohttp.ClientSession() as session:
        async with session.post(
            _GOOGLE_NEARBY_API,
            headers=_headers(),
            json=_body(query, user_location, radius),
        ) as response:

            response.raise_for_status()

            data = await response.json()

            return PlaceResult.model_validate(data)


def _headers() -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": _GOOGLE_MAP_API_KEY,
        "X-Goog-FieldMask": (
            "places.id,"
            "places.displayName,"
            "places.location,"
            "places.formattedAddress,"
            "places.primaryType"
        ),
    }


def _body(
    query: str,
    location: Coordinate,
    radius: float,
) -> dict:

    return {
        "includedTypes": [query],
        "maxResultCount": 5,
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": location.latitude,
                    "longitude": location.longitude,
                },
                "radius": radius,
            }
        },
    }
