from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from psycopg import AsyncCursor
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from aabha.config import config

_connection_pool: AsyncConnectionPool | None = None


def get_connection_pool() -> AsyncConnectionPool:
    global _connection_pool

    if _connection_pool is None:
        _connection_pool = AsyncConnectionPool(
            conninfo=config.DATABASE_URL,
            min_size=5,
            max_size=10,
            timeout=5,
        )

    return _connection_pool


async def open_connection_pool() -> None:
    global _connection_pool

    if _connection_pool is None:
        get_connection_pool()

    await _connection_pool.open()


async def close_connection_pool() -> None:
    global _connection_pool

    if _connection_pool is not None:
        await _connection_pool.close()
        _connection_pool = None


@asynccontextmanager
async def get_cursor() -> AsyncGenerator[AsyncCursor, None]:
    """Yields a cursor whose rows come back as dicts, so models validate directly."""
    async with get_connection_pool().connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cursor:
            yield cursor
