from django.core.management.base import BaseCommand

from monitoring.retention import prune_old_checks


class Command(BaseCommand):
    help = "Delete health check results older than CHECK_RETENTION_DAYS (or --days)."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--days",
            type=int,
            default=None,
            help="Override retention window in days (0 disables).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print how many rows would be deleted without deleting.",
        )

    def handle(self, *args, **options) -> None:
        days = options["days"]
        if options["dry_run"]:
            from datetime import timedelta

            from django.conf import settings
            from django.utils import timezone

            from monitoring.models import HealthCheckResult

            effective = days
            if effective is None:
                effective = int(getattr(settings, "CHECK_RETENTION_DAYS", 30) or 0)
            if effective <= 0:
                self.stdout.write("Retention disabled; nothing to prune.")
                return
            cutoff = timezone.now() - timedelta(days=effective)
            count = HealthCheckResult.objects.filter(checked_at__lt=cutoff).count()
            self.stdout.write(
                self.style.WARNING(f"Would delete {count} check(s) older than {effective} day(s).")
            )
            return

        deleted = prune_old_checks(days=days)
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} old check result(s)."))
