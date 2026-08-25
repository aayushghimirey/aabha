from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

from aabha.models.navigation import NavigationPoint

_EARTH_RADIUS_M = 6_371_000.0

# Metres in a degree of latitude. A degree of longitude is this shrunk by the
# cosine of the latitude, which is what the projection below corrects for.
_M_PER_DEGREE = 111_320.0


def distance_m(origin: NavigationPoint, point: NavigationPoint) -> float:
    """Great-circle distance in metres.

    Not the walk, but enough to tell "the one across the street" from "the one
    in the next district".
    """
    lat1, lon1 = radians(origin.latitude), radians(origin.longitude)
    lat2, lon2 = radians(point.latitude), radians(point.longitude)

    haversine = (
        sin((lat2 - lat1) / 2) ** 2
        + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    )

    return 2 * _EARTH_RADIUS_M * asin(sqrt(haversine))


def project(
    point: NavigationPoint, start: NavigationPoint, end: NavigationPoint
) -> tuple[float, float]:
    """Drop a point onto the line between two others.

    Returns how far along that line the foot of the perpendicular falls, as a
    fraction from 0 at `start` to 1 at `end`, and how far the point sits off
    the line in metres. A point beyond either end clamps to that end, so the
    fraction never leaves the segment it was asked about.

    Flat-earth arithmetic on purpose. Over the tens of metres between two
    points of a route the curvature is far smaller than the error on the GPS
    fix being matched against it, and the closed form is cheap enough to run
    over every segment of a route on every update.
    """
    to_x = _M_PER_DEGREE * cos(radians(start.latitude))
    to_y = _M_PER_DEGREE

    line_x = (end.longitude - start.longitude) * to_x
    line_y = (end.latitude - start.latitude) * to_y

    point_x = (point.longitude - start.longitude) * to_x
    point_y = (point.latitude - start.latitude) * to_y

    length_sq = line_x * line_x + line_y * line_y

    # A route can repeat a coordinate; there is no direction to project onto,
    # and the distance to the segment is the distance to the point itself.
    if length_sq == 0.0:
        return 0.0, sqrt(point_x * point_x + point_y * point_y)

    along = (point_x * line_x + point_y * line_y) / length_sq
    along = 0.0 if along < 0.0 else 1.0 if along > 1.0 else along

    off_x = point_x - along * line_x
    off_y = point_y - along * line_y

    return along, sqrt(off_x * off_x + off_y * off_y)
