#!/usr/bin/env python
"""Wait until the configured database accepts connections."""

from __future__ import annotations

import os
import sys
import time


def main() -> int:
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        print("No DATABASE_URL set; skipping DB wait (sqlite mode).")
        return 0

    import dj_database_url
    import psycopg

    config = dj_database_url.parse(database_url)
    if not config.get("ENGINE", "").endswith("postgresql"):
        print(f"DATABASE_URL engine is {config.get('ENGINE')}; skipping wait.")
        return 0

    retries = int(os.environ.get("DB_WAIT_RETRIES", "30"))
    delay = float(os.environ.get("DB_WAIT_DELAY", "2"))

    conninfo = (
        f"host={config['HOST']} port={config.get('PORT') or 5432} "
        f"dbname={config['NAME']} user={config['USER']} "
        f"password={config.get('PASSWORD') or ''}"
    )

    for attempt in range(1, retries + 1):
        try:
            with psycopg.connect(conninfo, connect_timeout=3) as connection:
                connection.execute("SELECT 1")
            print(f"Database is ready (attempt {attempt}).")
            return 0
        except Exception as exc:  # noqa: BLE001 - retry until timeout
            print(f"Waiting for database ({attempt}/{retries}): {exc}")
            time.sleep(delay)

    print("Database did not become ready in time.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
