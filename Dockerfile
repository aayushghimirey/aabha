FROM python:3.14-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Dependencies before the source, so editing a file doesn't reinstall the world.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-dev --no-install-project --no-editable

COPY pyproject.toml uv.lock README.md ./
COPY src ./src

# --no-editable copies the package into the venv rather than pointing at
# /app/src, so the runtime stage below needs nothing but the venv. schema.sql
# rides along in the wheel.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable


FROM python:3.14-slim AS runtime

RUN useradd --create-home --uid 10001 aabha

COPY --from=builder --chown=aabha:aabha /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

USER aabha
WORKDIR /app

EXPOSE 8080

CMD ["uvicorn", "aabha.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
