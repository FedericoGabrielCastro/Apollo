# syntax=docker/dockerfile:1

FROM node:22-alpine AS frontend
WORKDIR /app/frontend
RUN corepack enable
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir poetry==2.2.1

COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-ansi --no-root

COPY manage.py ./
COPY config ./config
COPY monitoring ./monitoring
COPY --from=frontend /app/frontend/dist ./frontend/dist
COPY docker/entrypoint.sh /entrypoint.sh
COPY docker/worker.sh /worker.sh
COPY docker/wait_for_db.py /wait_for_db.py

RUN chmod +x /entrypoint.sh /worker.sh \
    && mkdir -p /data

ENV DJANGO_DEBUG=false \
    DJANGO_ALLOWED_HOSTS=* \
    APOLLO_SEED_ON_STARTUP=true \
    CHECK_INTERVAL_SECONDS=60

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/api/health/ || exit 1

ENTRYPOINT ["/entrypoint.sh"]
