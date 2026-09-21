# Apollo

Django + React API Health Monitor (monolith).

## Stack

- **Backend:** Django 6 + DRF + httpx + Token auth + WhiteNoise + Gunicorn
- **Frontend:** React + Vite + Redux Toolkit + React Router (pnpm)
- **Data:** SQLite (local) or PostgreSQL (`DATABASE_URL`)
- **Ops:** Docker Compose (`db` + `web` + `worker`), GitHub Actions CI
- **Product:** multi-user ownership, advanced assertions, quiet hours, incident ack, charts, exports, Discord/Slack, status page, retention

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

- App: http://localhost:5173 — login **`apollo` / `apollo`** (or register if `APOLLO_ALLOW_REGISTER=true`)
- Public status: http://localhost:5173/status

## Docker

```bash
cp .env.example .env
docker compose up --build
```

- App: http://localhost:8000
- Status: http://localhost:8000/status
- Worker runs due checks + `prune_checks` on an interval

## Features

| Area | Details |
|------|---------|
| Auth | Login/logout/me + optional register; endpoints scoped by owner (staff sees all) |
| Endpoints | CRUD, tags, public, probe auth/headers/body, mute, quiet hours |
| Checks | Manual, due, history; body/header/JSON/latency/SSL assertions; failure threshold |
| Alerts | Webhook/email/Discord/Slack after N failures; muted by datetime or quiet hours |
| Incidents | Auto open/resolve; acknowledge via API/UI |
| Status page | Public `/status` + branding via `/api/status/config/` |
| Dashboard | Uptime, latency, charts, CSV export |
| Retention | Worker prunes checks older than `CHECK_RETENTION_DAYS` |

## Key API routes

| Method | Path | Auth |
|--------|------|------|
| GET | `/api/health/` | public |
| GET | `/api/status/public/` | public |
| GET/PATCH | `/api/status/config/` | token |
| GET | `/api/exports/{checks\|alerts\|incidents}.csv` | token |
| POST | `/api/auth/login/` | public |
| POST | `/api/auth/register/` | public (if enabled) |
| GET | `/api/dashboard/` | token |
| CRUD | `/api/endpoints/` | token |
| GET | `/api/incidents/?status=open` | token |
| POST | `/api/incidents/{id}/acknowledge/` | token |
| GET/POST | `/api/tags/` | token |
| GET | `/api/alerts/` | token |

## Env highlights

See `.env.example` (`DATABASE_URL`, `CHECK_INTERVAL_SECONDS`, `CHECK_RETENTION_DAYS`, `APOLLO_ALLOW_REGISTER`, `EMAIL_*`, demo user, etc.).

## Commands

```bash
poetry run pytest
poetry run python manage.py check_endpoints --due
poetry run python manage.py run_check_worker --once
poetry run python manage.py prune_checks --dry-run
pnpm --dir frontend build
docker compose up --build
```
