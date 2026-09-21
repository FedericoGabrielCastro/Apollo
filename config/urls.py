from django.conf import settings
from django.contrib import admin
from django.http import HttpRequest, HttpResponse
from django.urls import include, path, re_path
from django.views.generic import TemplateView


def spa_fallback(request: HttpRequest) -> HttpResponse:
    """Serve the Vite build for non-API routes when the frontend is built."""
    index = settings.BASE_DIR / "frontend" / "dist" / "index.html"
    if not index.exists():
        return HttpResponse(
            "Frontend build not found. Run `pnpm --dir frontend build` "
            "or use the Vite dev server on :5173.",
            status=503,
            content_type="text/plain",
        )
    return TemplateView.as_view(template_name="index.html")(request)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("monitoring.urls")),
]

if not settings.DEBUG:
    urlpatterns += [
        re_path(r"^(?!api/|admin/|static/).*$", spa_fallback),
    ]
