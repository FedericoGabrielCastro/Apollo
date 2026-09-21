# Apollo

Django + React API Health Monitor (monolith).

## Stack

- **Backend:** Django 6 + Django REST Framework + httpx + Token auth (Poetry)
- **Frontend:** React + Vite + Redux Toolkit (pnpm)
- **Data helpers:** Factory Boy + `seed` / `check_endpoints` commands
- **Alerting:** webhook notifications on failure / recovery transitions
- **Dashboard:** uptime %, latency, due endpoints, recent failures

## Setup

```bash
# Backend
poetry install
poetry run python manage.py migrate
poetry run python manage.py seed

# Frontend
pnpm --dir frontend install
```

`seed` creates demo user **`apollo` / `apollo`** plus an API token and sample endpoints.

## Development

Run both processes:

```bash
# Terminal 1 — API on :8000
poetry run python manage.py runserver

# Terminal 2 — Vite on :5173 (proxies /api to Django)
pnpm --dir frontend dev
```

Open http://localhost:5173 and sign in with `apollo` / `apollo`.

## Auth

API defaults to **Token authentication** (`Authorization: Token <key>`).

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/login/` | Exchange username/password for token |
| POST | `/api/auth/logout/` | Delete current token |
| GET | `/api/auth/me/` | Current user |
| GET | `/api/health/` | Public liveness (no auth) |

All other API routes require authentication.

## Scheduling (cron)

```bash
* * * * * cd /path/to/Apollo && poetry run python manage.py check_endpoints --due
```

## Alerting

Alerts fire only on **status transitions** (failure / recovery). Consecutive failures do not re-alert.

## Dashboard

`GET /api/dashboard/?hours=24` returns aggregate uptime, latency, per-endpoint rows, recent failures, and recent alerts.

## Useful commands

```bash
poetry run python manage.py seed
poetry run python manage.py check_endpoints --due
poetry run pytest
pnpm --dir frontend build
```

## API (authenticated unless noted)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health/` | Public liveness |
| GET | `/api/dashboard/` | Uptime / ops dashboard |
| GET/POST | `/api/endpoints/` | List / create |
| GET/PUT/PATCH/DELETE | `/api/endpoints/:id/` | Detail |
| POST | `/api/endpoints/:id/check/` | Run check |
| POST | `/api/endpoints/check-due/` | Check due endpoints |
| GET | `/api/endpoints/:id/checks/` | Check history |
| GET | `/api/endpoints/:id/alerts/` | Alert history |
| POST | `/api/endpoints/:id/test-webhook/` | Test webhook |
| GET | `/api/checks/` | All checks |
| GET | `/api/alerts/` | All alerts |
