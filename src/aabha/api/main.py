from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aabha.api.routes import auth, users
from aabha.db.conn_pool import close_connection_pool, get_cursor, open_connection_pool

_SCHEMA = Path(__file__).resolve().parents[1] / "db" / "schema.sql"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await open_connection_pool()

    # Every statement is IF NOT EXISTS, so this is safe on every boot and
    # saves a separate migration step while the schema is still moving.
    async with get_cursor() as cursor:
        await cursor.execute(_SCHEMA.read_text())

    yield

    await close_connection_pool()


def create_app() -> FastAPI:
    app = FastAPI(title="aabha", lifespan=lifespan)

    # The dev frontend is opened straight from disk, so its origin is "null"
    # and every call is cross-origin. Wide open is fine while this is local;
    # it needs narrowing before it is deployed anywhere.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(users.router)
    app.include_router(auth.router)

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
