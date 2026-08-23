from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

# The frontend (index.html) is opened straight from disk, so its origin is
# "null" and every call is cross-origin. Wide open is fine while the API is
# unauthenticated and local; it needs narrowing before this is deployed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user.router)
app.include_router(auth.router)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
