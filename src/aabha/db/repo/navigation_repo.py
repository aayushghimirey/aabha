from uuid import UUID

from aabha.db.pool import get_cursor
from aabha.models.navigation import NAVIGATION_STATUS, Navigation, NavigationPoint

_COLUMNS = (
    "id, user_id, destination_name, destination_address,"
    " start_latitude, start_longitude,"
    " destination_latitude, destination_longitude,"
    " status, created_at, updated_at"
)


def _to_navigation(row: dict) -> Navigation:
    """The table keeps each coordinate in its own column - a point is two
    numbers to postgres and one thing to everyone else."""
    return Navigation(
        id=row["id"],
        user_id=row["user_id"],
        start=NavigationPoint(
            latitude=row["start_latitude"], longitude=row["start_longitude"]
        ),
        destination=NavigationPoint(
            latitude=row["destination_latitude"],
            longitude=row["destination_longitude"],
        ),
        destination_name=row["destination_name"],
        destination_address=row["destination_address"],
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def create_navigation(
    user_id: UUID,
    start: NavigationPoint,
    destination: NavigationPoint,
    destination_name: str,
    destination_address: str = "",
) -> Navigation:
    async with get_cursor() as cursor:
        await cursor.execute(
            f"INSERT INTO navigations"
            f" (user_id, destination_name, destination_address,"
            f"  start_latitude, start_longitude,"
            f"  destination_latitude, destination_longitude)"
            f" VALUES (%s, %s, %s, %s, %s, %s, %s)"
            f" RETURNING {_COLUMNS}",
            (
                user_id,
                destination_name,
                destination_address,
                start.latitude,
                start.longitude,
                destination.latitude,
                destination.longitude,
            ),
        )
        row = await cursor.fetchone()
        return _to_navigation(row)


async def change_navigation_status(
    navigation_id: UUID, status: NAVIGATION_STATUS
) -> Navigation | None:
    async with get_cursor() as cursor:
        await cursor.execute(
            f"UPDATE navigations SET status = %s, updated_at = now()"
            f" WHERE id = %s RETURNING {_COLUMNS}",
            (status, navigation_id),
        )
        row = await cursor.fetchone()
        return _to_navigation(row) if row else None


async def get_navigation(navigation_id: UUID) -> Navigation | None:
    async with get_cursor() as cursor:
        await cursor.execute(
            f"SELECT {_COLUMNS} FROM navigations WHERE id = %s", (navigation_id,)
        )
        row = await cursor.fetchone()
        return _to_navigation(row) if row else None


async def get_active_navigation(user_id: UUID) -> Navigation | None:
    """The trip the user is on, or the one they just saved.

    A navigation stops being active once it is completed or abandoned, so the
    two live statuses are the whole of what "where am I going" can mean.
    """
    async with get_cursor() as cursor:
        await cursor.execute(
            f"SELECT {_COLUMNS} FROM navigations"
            f" WHERE user_id = %s AND status IN ('pending', 'started')"
            f" ORDER BY created_at DESC LIMIT 1",
            (user_id,),
        )
        row = await cursor.fetchone()
        return _to_navigation(row) if row else None


async def get_navigations(
    user_id: UUID, status: NAVIGATION_STATUS | None = None, limit: int = 10
) -> list[Navigation]:
    async with get_cursor() as cursor:
        await cursor.execute(
            f"SELECT {_COLUMNS} FROM navigations"
            f" WHERE user_id = %s AND (%s::TEXT IS NULL OR status = %s)"
            f" ORDER BY created_at DESC LIMIT %s",
            (user_id, status, status, limit),
        )
        rows = await cursor.fetchall()
        return [_to_navigation(row) for row in rows]
