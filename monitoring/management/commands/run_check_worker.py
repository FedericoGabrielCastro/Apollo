from __future__ import annotations

import time

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Continuously run due endpoint health checks."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--interval",
            type=int,
            default=None,
            help="Seconds between due-check passes (default: CHECK_INTERVAL_SECONDS).",
        )
        parser.add_argument(
            "--once",
            action="store_true",
            help="Run a single due-check pass and exit.",
        )

    def handle(self, *args, **options) -> None:
        interval = options["interval"] or getattr(settings, "CHECK_INTERVAL_SECONDS", 60)
        interval = max(5, int(interval))

        self.stdout.write(
            self.style.NOTICE(f"Check worker interval: {interval}s (due endpoints only)")
        )

        while True:
            started = time.monotonic()
            try:
                call_command("check_endpoints", due=True)
            except Exception as exc:  # noqa: BLE001 - keep worker alive
                self.stderr.write(self.style.ERROR(f"Check pass failed: {exc}"))

            if options["once"]:
                break

            elapsed = time.monotonic() - started
            sleep_for = max(1.0, interval - elapsed)
            time.sleep(sleep_for)
