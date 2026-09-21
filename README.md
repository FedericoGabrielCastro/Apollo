# Apollo

Django + React API Health Monitor (monolith).

## Stack

- **Backend:** Django 6 + DRF + httpx + Token auth + WhiteNoise + Gunicorn (Poetry)
- **Frontend:** React + Vite + Redux Toolkit (pnpm)
- **Data:** SQLite (local default) or **PostgreSQL** via `DATABASE_URL`
- **Ops:** Docker Compose (`db` + `web` + `worker`), GitHub Actions CI
- **Features:** due checks, webhook alerts, uptime dashboard, background check worker

## Quick start (local / SQLite)

```bash
cp .env.example .env
poetry install
poetry run python manage.py migrate
poetry run python manage.py seed

pnpm --dir frontend install
poetry run python manage.py runserver
pnpm --dir frontend dev
```

Open http://localhost:5173 — login **`apollo` / `apollo`**.

## Docker (Postgres + web + worker)

```bash
cp .env.example .env
# set a real DJANGO_SECRET_KEY for deploys
docker compose up --build
```

Services:

| Service | Role |
|---------|------|
| `db` | PostgreSQL 16 |
| `web` | Gunicorn API + SPA |
| `worker` | Loop: `check_endpoints --due` every `CHECK_INTERVAL_SECONDS` |

App: http://localhost:8000  
Login: `apollo` / `apollo` (seeded by web when `APOLLO_SEED_ON_STARTUP=true`)

```bash
docker compose logs -f worker
docker compose down
```

## Environment

See [`.env.example`](.env.example).

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Postgres URL (empty = SQLite) |
| `DJANGO_SQLITE_PATH` | SQLite path when `DATABASE_URL` is empty |
| `CHECK_INTERVAL_SECONDS` | Worker loop interval (default 60) |
| `APOLLO_SEED_ON_STARTUP` | Seed demo user/endpoints on web boot |
| `DJANGO_SECRET_KEY` / `DJANGO_DEBUG` / `DJANGO_ALLOWED_HOSTS` | Django core |

## Auth

Token auth (`Authorization: Token <key>`). Public: `/api/health/`, `/api/auth/login/`.

## Scheduling

**Docker:** the `worker` service runs due checks automatically.

**Host cron (SQLite/Poetry):**

```bash
* * * * * cd /path/to/Apollo && poetry run python manage.py check_endpoints --due
```

**One-shot / debug:**

```bash
poetry run python manage.py run_check_worker --once
poetry run python manage.py run_check_worker --interval 30
```

## CI

`.github/workflows/ci.yml`:

1. Pytest against Postgres service
2. pnpm build
3. `docker build` + `docker compose config`

## Useful commands

```bash
poetry run pytest
poetry run python manage.py check_endpoints --due
pnpm --dir frontend build
docker compose up --build
```
