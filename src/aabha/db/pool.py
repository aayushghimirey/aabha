from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from aabha.config.config import config
from contextlib import asynccontextmanager

_conn_pool: AsyncConnectionPool | None = None


def create_pool() -> AsyncConnectionPool:
    global _conn_pool

    if _conn_pool is None:
        _conn_pool = AsyncConnectionPool(
            conninfo=config.DATABASE_URL,
            min_size=5,
            max_size=20,
            timeout=30,
            open=False,
        )

    return _conn_pool


async def open_pool():
    pool = create_pool()
    await pool.open()
    await pool.wait()


async def close_pool():
    global _conn_pool

    if _conn_pool is not None:
        await _conn_pool.close()
        _conn_pool = None


@asynccontextmanager
async def get_cursor():
    """Yields a cursor whose rows come back as dicts, so models validate directly."""
    pool = create_pool()

    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cursor:
            yield cursor
