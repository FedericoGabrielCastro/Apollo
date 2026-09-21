#!/bin/sh
set -eu

echo "Waiting for database..."
python /wait_for_db.py

echo "Starting check worker (interval=${CHECK_INTERVAL_SECONDS:-60}s)..."
exec python manage.py run_check_worker --interval "${CHECK_INTERVAL_SECONDS:-60}"
