from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from aabha.api.routes import auth, user
from aabha.db.pool import close_pool, get_cursor, open_pool

_SCHEMA = Path(__file__).resolve().parents[1] / "db" / "schema.sql"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await open_pool()
    async with get_cursor() as cursor:
        await cursor.execute(_SCHEMA.read_text())
    yield
    await close_pool()


app = FastAPI(title="aabha", lifespan=lifespan)

app.include_router(user.router)
app.include_router(auth.router)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
