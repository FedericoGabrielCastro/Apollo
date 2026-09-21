# Apollo

Django + React API Health Monitor (monolith).

## Stack

- **Backend:** Django 6 + DRF + httpx + Token auth + WhiteNoise + Gunicorn
- **Frontend:** React + Vite + Redux Toolkit + React Router (pnpm)
- **Data:** SQLite (local) or PostgreSQL (`DATABASE_URL`)
- **Ops:** Docker Compose (`db` + `web` + `worker`), GitHub Actions CI
- **Product:** due checks, assertions, SSL, mute windows, probe auth, failure threshold, Discord/Slack, status branding, incidents, tags, dashboard

## Quick start (local)

```bash
cp .env.example .env
poetry install
poetry run python manage.py migrate
poetry run python manage.py seed
pnpm --dir frontend install

poetry run python manage.py runserver
pnpm --dir frontend dev
```

- App: http://localhost:5173 — login **`apollo` / `apollo`**
- Public status: http://localhost:5173/status

## Docker

```bash
cp .env.example .env
docker compose up --build
```

- App: http://localhost:8000
- Status: http://localhost:8000/status
- Worker runs `check_endpoints --due` on an interval

## Features

| Area | Details |
|------|---------|
| Auth | Token login/logout/me; API protected except health + public status |
| Endpoints | CRUD, tags, public, interval, webhook/email/Discord/Slack, mute, probe auth/headers |
| Checks | Manual, due, history; body/latency assertions; SSL expiry; failure threshold |
| Alerts | Transition after N failures; muted while `mute_alerts_until` is future |
| Incidents | Auto-open after threshold, auto-resolve on recovery |
| Status page | Public `/status` + branding via `/api/status/config/` |
| Dashboard | Uptime, latency, due, open incidents |

## Key API routes

| Method | Path | Auth |
|--------|------|------|
| GET | `/api/health/` | public |
| GET | `/api/status/public/` | public |
| GET/PATCH | `/api/status/config/` | token |
| POST | `/api/auth/login/` | public |
| GET | `/api/dashboard/` | token |
| CRUD | `/api/endpoints/` | token |
| GET | `/api/incidents/?status=open` | token |
| GET/POST | `/api/tags/` | token |
| GET | `/api/alerts/` | token |

## Env highlights

See `.env.example` for full list (`DATABASE_URL`, `CHECK_INTERVAL_SECONDS`, `EMAIL_*` / mailer settings, demo user, etc.).

## Commands

```bash
poetry run pytest
poetry run python manage.py check_endpoints --due
poetry run python manage.py run_check_worker --once
pnpm --dir frontend build
docker compose up --build
```
