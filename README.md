# Apollo

Django + React API Health Monitor (monolith).

## Stack

- **Backend:** Django 6 + DRF + httpx + Token auth + WhiteNoise + Gunicorn (Poetry)
- **Frontend:** React + Vite + Redux Toolkit (pnpm)
- **Ops:** Docker, docker-compose, GitHub Actions CI, `.env` configuration
- **Features:** scheduled checks, webhook alerts, uptime dashboard

## Quick start (local)

```bash
cp .env.example .env
poetry install
poetry run python manage.py migrate
poetry run python manage.py seed

pnpm --dir frontend install
```

Run API + Vite:

```bash
poetry run python manage.py runserver
pnpm --dir frontend dev
```

Open http://localhost:5173 and sign in with **`apollo` / `apollo`**.

## Docker

```bash
cp .env.example .env
# set DJANGO_SECRET_KEY and DJANGO_DEBUG=false for real deploys
docker compose up --build
```

App: http://localhost:8000 (SPA + API in one container)  
Login: `apollo` / `apollo` (seeded on startup when `APOLLO_SEED_ON_STARTUP=true`)

Useful:

```bash
docker compose logs -f web
docker compose down
```

## Environment

See [`.env.example`](.env.example). Important keys:

| Variable | Purpose |
|----------|---------|
| `DJANGO_SECRET_KEY` | Django secret |
| `DJANGO_DEBUG` | `true` / `false` |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hosts |
| `DJANGO_SQLITE_PATH` | SQLite file path (`/data/db.sqlite3` in Docker) |
| `CORS_ALLOWED_ORIGINS` | Browser origins allowed to call the API |
| `APOLLO_DEMO_USERNAME` / `APOLLO_DEMO_PASSWORD` | Seeded demo user |
| `APOLLO_SEED_ON_STARTUP` | Run `seed` on container boot |

## Auth

API uses **Token authentication** (`Authorization: Token <key>`).

| Method | Path | Auth |
|--------|------|------|
| POST | `/api/auth/login/` | public |
| POST | `/api/auth/logout/` | token |
| GET | `/api/auth/me/` | token |
| GET | `/api/health/` | public |
| GET | `/api/dashboard/` | token |
| * | `/api/endpoints/…` | token |

## Scheduling (cron / host)

```bash
* * * * * cd /path/to/Apollo && poetry run python manage.py check_endpoints --due
```

Inside Docker you can add a second service or host cron hitting the same volume/DB.

## CI

GitHub Actions (`.github/workflows/ci.yml`) runs:

1. Poetry + pytest
2. pnpm build
3. `docker build`

## Useful commands

```bash
poetry run pytest
poetry run python manage.py check_endpoints --due
pnpm --dir frontend build
poetry run python manage.py collectstatic --noinput
poetry run gunicorn config.wsgi:application --bind 0.0.0.0:8000
```
