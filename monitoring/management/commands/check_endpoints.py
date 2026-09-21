from django.core.management.base import BaseCommand

from monitoring.models import MonitoredEndpoint
from monitoring.services import run_health_check


class Command(BaseCommand):
    help = "Run health checks against all active monitored endpoints."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--all",
            action="store_true",
            help="Include inactive endpoints.",
        )

    def handle(self, *args, **options) -> None:
        queryset = MonitoredEndpoint.objects.all()
        if not options["all"]:
            queryset = queryset.filter(is_active=True)

        if not queryset.exists():
            self.stdout.write(self.style.WARNING("No endpoints to check."))
            return

        for endpoint in queryset:
            result = run_health_check(endpoint)
            style = (
                self.style.SUCCESS
                if result.status == "up"
                else self.style.ERROR
            )
            latency = f"{result.latency_ms}ms" if result.latency_ms is not None else "n/a"
            self.stdout.write(
                style(
                    f"{endpoint.name}: {result.status} "
                    f"(code={result.status_code}, latency={latency})"
                )
            )
