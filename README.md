# Apollo

Django + React API Health Monitor (monolith).

## Stack

- **Backend:** Django 6 + Django REST Framework + httpx (Poetry)
- **Frontend:** React + Vite + Redux Toolkit (pnpm)
- **Data helpers:** Factory Boy + `seed` / `check_endpoints` commands
- **Alerting:** webhook notifications on failure / recovery transitions

## Setup

```bash
# Backend
poetry install
poetry run python manage.py migrate
poetry run python manage.py seed

# Frontend
pnpm --dir frontend install
```

## Development

Run both processes:

```bash
# Terminal 1 — API on :8000
poetry run python manage.py runserver

# Terminal 2 — Vite on :5173 (proxies /api to Django)
pnpm --dir frontend dev
```

Open http://localhost:5173 to manage endpoints, run checks, inspect history, and configure webhooks.

## Scheduling (cron)

Each endpoint has `check_interval_minutes`. Run due probes every minute from cron:

```bash
# Every minute — only endpoints whose interval elapsed
* * * * * cd /path/to/Apollo && poetry run python manage.py check_endpoints --due
```

Or trigger the same logic from the UI / API with `POST /api/endpoints/check-due/`.

## Alerting

Alerts fire only on **status transitions**:

- healthy / never-checked → `down` or `error` → **failure** alert
- `down` / `error` → `up` → **recovery** alert
- consecutive failures do **not** re-alert

Configure per endpoint:

- `webhook_url` — POST JSON payload destination
- `alert_on_failure` — enable / disable alerting

Useful for local testing: [webhook.site](https://webhook.site) or `POST /api/endpoints/:id/test-webhook/`.

## Useful commands

```bash
# Seed curated sample endpoints (optional extra Factory Boy rows)
poetry run python manage.py seed
poetry run python manage.py seed --count 5

# Replace existing seed data
poetry run python manage.py seed --flush

# Probe all active endpoints
poetry run python manage.py check_endpoints

# Probe only due endpoints (for cron)
poetry run python manage.py check_endpoints --due

# Backend tests
poetry run pytest

# Frontend build (for monolith static serving when DEBUG=False)
pnpm --dir frontend build
```

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health/` | Apollo liveness |
| GET/POST | `/api/endpoints/` | List / create monitored endpoints |
| GET/PUT/PATCH/DELETE | `/api/endpoints/:id/` | Endpoint detail (`last_check`, `last_alert`, `is_due`) |
| POST | `/api/endpoints/:id/check/` | Run a health check now (may dispatch alerts) |
| POST | `/api/endpoints/check-due/` | Run checks for all due endpoints |
| GET | `/api/endpoints/:id/checks/` | Recent checks for one endpoint |
| GET | `/api/endpoints/:id/alerts/` | Recent alert events for one endpoint |
| POST | `/api/endpoints/:id/test-webhook/` | Send a test webhook payload |
| GET | `/api/checks/` | List all check results |
| GET | `/api/alerts/` | List all alert events |
