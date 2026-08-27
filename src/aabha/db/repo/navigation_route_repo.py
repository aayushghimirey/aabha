from uuid import UUID

from aabha.db.conn_pool import get_cursor
from aabha.db.model.navigation_route import (
    NavigationRoute,
    NavigationRouteDraft,
    NavigationStatus,
)

_COLUMNS = (
    "id, user_id, mode, initial_coords, destination_coords, destination,"
    " status, created_at, updated_at, last_used_at"
)


async def register_navigation_route(draft: NavigationRouteDraft) -> NavigationRoute:
    """Writes down a navigation as it starts. The coordinate pairs go in as
    lists - a tuple would be adapted as a composite, not as the array the
    column holds."""
    async with get_cursor() as cursor:
        await cursor.execute(
            f"""
            INSERT INTO navigation_route
                (user_id, mode, initial_coords, destination_coords, destination)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING {_COLUMNS}
            """,
            (
                draft.user_id,
                draft.mode,
                list(draft.initial_coords),
                list(draft.destination_coords),
                draft.destination,
            ),
        )

        row = await cursor.fetchone()

        return NavigationRoute.model_validate(row)


async def change_navigation_status(
    navigation_route_id: UUID, status: NavigationStatus
) -> NavigationRoute | None:
    """Moves a navigation on. None when there is no such row - the caller may
    be finishing a navigation that was never written down."""
    async with get_cursor() as cursor:
        await cursor.execute(
            f"""
            UPDATE navigation_route
            SET status = %s, updated_at = now()
            WHERE id = %s
            RETURNING {_COLUMNS}
            """,
            (status, navigation_route_id),
        )

        row = await cursor.fetchone()

        return NavigationRoute.model_validate(row) if row else None


async def get_navigation_route(navigation_route_id: UUID) -> NavigationRoute | None:
    async with get_cursor() as cursor:
        await cursor.execute(
            f"SELECT {_COLUMNS} FROM navigation_route WHERE id = %s",
            (navigation_route_id,),
        )

        row = await cursor.fetchone()

        return NavigationRoute.model_validate(row) if row else None
