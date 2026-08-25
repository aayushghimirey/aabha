# aabha
An intelligent voice companion that understands context, remembers what matters, and helps you navigate everyday life.

## Running the stack

    cp .env.example .env      # first time only, then fill in the keys
    docker compose up -d --build

That brings up three containers: `postgres` (the agent's memory), `api` on
127.0.0.1:8080, and `agent` - the LiveKit worker, registered under the name
`aabha`. Open dev/index.html from disk to talk to it.

The schema in src/aabha/db/schema.sql is applied when the database volume is
first created, and again by the API on every startup. Data lives in the
`pgdata` volume, so `docker compose down` keeps it - `docker compose down -v`
wipes it.

Postgres publishes no port at all - the api and agent reach it over the
compose network at `postgres:5432`, and nothing outside the stack can. Only
`api` is on the host, and `API_PORT` in .env moves it if 8080 is taken.

## Running a piece on the host

The containers are independent, so any one of them can be left out and run
locally instead - useful for the agent, where `lk agent dev` reloads on save
and the container's `start` does not. A host process cannot see the database
through the compose network, so publish the port for that case only, in a
docker-compose.override.yml compose picks up on its own:

    services:
      postgres:
        ports:
          - "127.0.0.1:5432:5432"

Then point DATABASE_URL at localhost and:

    docker compose up -d postgres

    lk agent dev src/aabha/agent/entrypoint.py

    uvicorn src.aabha.api.main:app --host 0.0.0.0 --port 8080
