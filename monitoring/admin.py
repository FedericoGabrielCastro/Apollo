from django.contrib import admin

from monitoring.models import MonitoredEndpoint


@admin.register(MonitoredEndpoint)
class MonitoredEndpointAdmin(admin.ModelAdmin):
    list_display = ("name", "url", "method", "expected_status", "is_active")
    list_filter = ("is_active", "method")
    search_fields = ("name", "url")
