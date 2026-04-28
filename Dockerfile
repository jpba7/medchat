# syntax=docker/dockerfile:1.7

FROM python:3.13-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

# Binário do uv copiado da imagem oficial (cravado em versão).
COPY --from=ghcr.io/astral-sh/uv:0.11.8 /uv /uvx /usr/local/bin/

WORKDIR /app

# Camada 1 — instala dependências usando o lockfile (cacheada quando deps não mudam).
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

# Camada 2 — copia o código.
COPY . .

# Camada 3 — instala o próprio projeto (rápido, deps já estão).
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "config.asgi:application", "--host", "0.0.0.0", "--port", "8000"]
