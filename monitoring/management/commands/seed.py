from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from rest_framework.authtoken.models import Token

from monitoring.factories import MonitoredEndpointFactory
from monitoring.models import MonitoredEndpoint


SEED_ENDPOINTS = [
    {
        "name": "Apollo self",
        "url": "http://127.0.0.1:8000/api/health/",
        "method": "GET",
        "expected_status": 200,
    },
    {
        "name": "Example.com",
        "url": "https://example.com/",
        "method": "GET",
        "expected_status": 200,
    },
    {
        "name": "HTTPBin status 200",
        "url": "https://httpbin.org/status/200",
        "method": "GET",
        "expected_status": 200,
    },
]


class Command(BaseCommand):
    help = "Seed demo user, token, and sample monitored endpoints."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--count",
            type=int,
            default=None,
            help="Extra random endpoints to create via Factory Boy.",
        )
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete existing monitored endpoints before seeding.",
        )

    def handle(self, *args, **options) -> None:
        username = settings.APOLLO_DEMO_USERNAME
        password = settings.APOLLO_DEMO_PASSWORD
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"is_staff": True, "is_superuser": True},
        )
        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Created demo user `{username}`."))
        else:
            self.stdout.write(f"Demo user `{username}` already exists.")

        token, _ = Token.objects.get_or_create(user=user)
        self.stdout.write(self.style.SUCCESS(f"API token: {token.key}"))

        if options["flush"]:
            deleted, _ = MonitoredEndpoint.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted {deleted} endpoint(s)."))

        created_endpoints = []
        for payload in SEED_ENDPOINTS:
            endpoint, was_created = MonitoredEndpoint.objects.get_or_create(
                name=payload["name"],
                defaults=payload,
            )
            if was_created:
                created_endpoints.append(endpoint)

        extra = options["count"]
        if extra:
            created_endpoints.extend(MonitoredEndpointFactory.create_batch(extra))

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(created_endpoints)} new endpoint(s) "
                f"({MonitoredEndpoint.objects.count()} total)."
            )
        )
        self.stdout.write(
            self.style.NOTICE(
                f"Login with username=`{username}` password=`{password}`."
            )
        )
