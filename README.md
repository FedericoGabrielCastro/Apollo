# Apollo

Django + React API Health Monitor (monolith).

## Stack

- **Backend:** Django 6 + Django REST Framework + httpx (Poetry)
- **Frontend:** React + Vite + Redux Toolkit (pnpm)
- **Data helpers:** Factory Boy + `seed` / `check_endpoints` commands

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

Open http://localhost:5173

## Useful commands

```bash
# Seed curated sample endpoints (optional extra Factory Boy rows)
poetry run python manage.py seed
poetry run python manage.py seed --count 5

# Replace existing seed data
poetry run python manage.py seed --flush

# Probe all active endpoints
poetry run python manage.py check_endpoints

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
| GET/PUT/PATCH/DELETE | `/api/endpoints/:id/` | Endpoint detail (includes `last_check`) |
| POST | `/api/endpoints/:id/check/` | Run a health check now |
| GET | `/api/endpoints/:id/checks/` | Recent checks for one endpoint |
| GET | `/api/checks/` | List all check results |
