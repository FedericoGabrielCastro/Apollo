from django.core.management.base import BaseCommand

from monitoring.factories import MonitoredEndpointFactory
from monitoring.models import MonitoredEndpoint


class Command(BaseCommand):
    help = "Seed the database with sample monitored endpoints."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--count",
            type=int,
            default=5,
            help="Number of endpoints to create (default: 5).",
        )
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete existing monitored endpoints before seeding.",
        )

    def handle(self, *args, **options) -> None:
        count: int = options["count"]

        if options["flush"]:
            deleted, _ = MonitoredEndpoint.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted {deleted} endpoint(s)."))

        endpoints = MonitoredEndpointFactory.create_batch(count)
        self.stdout.write(
            self.style.SUCCESS(f"Seeded {len(endpoints)} monitored endpoint(s).")
        )
