import aiohttp
from pydantic import BaseModel, ConfigDict, Field

from aabha.config import config

_GEOAPIFY_URL = "https://api.geoapify.com/v1/geocode/reverse"
_GEOAPIFY_API_KEY = config.GEOAPIFY_API_KEY


class Timezone(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str | None = None
    # Geoapify sends standard and daylight offsets separately, and they are the
    # same number nearly everywhere. One is enough to say what time it is.
    offset: str | None = Field(default=None, alias="offset_STD")


class Location(BaseModel):
    """What Geoapify says is at a set of coordinates.

    The parts a person could be answered with, and no more - the response also
    carries licensing, ranking and place-id fields that are of no use in a
    conversation. Anything Geoapify does not know is left unset.
    """

    # The name of the thing the fix landed on, when it landed on one at all -
    # a cafe, a school. Absent in the middle of a residential street.
    name: str | None = None
    # Geoapify's own one-line rendering, largest last. The readiest thing to
    # say out loud.
    formatted: str | None = None

    address_line1: str | None = None
    address_line2: str | None = None

    street: str | None = None
    suburb: str | None = None
    district: str | None = None
    city: str | None = None
    county: str | None = None
    state: str | None = None
    postcode: str | None = None
    country: str | None = None

    # What kind of place it is, as OSM tags: "commercial;service.travel_agency".
    category: str | None = None

    timezone: Timezone | None = None


async def reverse_geocode(lat: float, lon: float) -> Location | None:
    """What is at these coordinates, or None when Geoapify knows of nothing
    there."""
    if not _GEOAPIFY_API_KEY:
        raise RuntimeError("GEOAPIFY_API_KEY is not set")

    params = {
        "lat": lat,
        "lon": lon,
        "apiKey": _GEOAPIFY_API_KEY,
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(_GEOAPIFY_URL, params=params) as response:
            response.raise_for_status()
            data = await response.json()

    features = data.get("features")

    if not features:
        return None

    properties = features[0]["properties"]

    return Location.model_validate(properties)
