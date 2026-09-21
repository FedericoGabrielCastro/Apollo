from django.core.management.base import BaseCommand

from monitoring.models import MonitoredEndpoint
from monitoring.services import due_endpoints, run_health_check


class Command(BaseCommand):
    help = "Run health checks against monitored endpoints."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--all",
            action="store_true",
            help="Include inactive endpoints.",
        )
        parser.add_argument(
            "--due",
            action="store_true",
            help="Only check endpoints whose interval has elapsed (for cron).",
        )

    def handle(self, *args, **options) -> None:
        if options["due"]:
            endpoints = due_endpoints(include_inactive=options["all"])
        else:
            queryset = MonitoredEndpoint.objects.all()
            if not options["all"]:
                queryset = queryset.filter(is_active=True)
            endpoints = list(queryset)

        if not endpoints:
            self.stdout.write(self.style.WARNING("No endpoints to check."))
            return

        for endpoint in endpoints:
            result = run_health_check(endpoint)
            style = self.style.SUCCESS if result.status == "up" else self.style.ERROR
            latency = f"{result.latency_ms}ms" if result.latency_ms is not None else "n/a"
            self.stdout.write(
                style(
                    f"{endpoint.name}: {result.status} "
                    f"(code={result.status_code}, latency={latency})"
                )
            )
