from __future__ import annotations

from contextlib import asynccontextmanager

import aiohttp
from livekit.agents.utils import http_context


@asynccontextmanager
async def session():
    """Reuse the job's shared session where there is one, so the agent is not
    opening a connection pool per question. Outside a job - a script, a test -
    fall back to a session of our own."""
    try:
        yield http_context.http_session()
    except RuntimeError:
        async with aiohttp.ClientSession() as own:
            yield own
