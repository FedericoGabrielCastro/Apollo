from __future__ import annotations

from typing import Any

from django.core.paginator import Paginator
from rest_framework.request import Request


def paginate_queryset(
    request: Request,
    queryset,
    *,
    default_page_size: int = 20,
    max_page_size: int = 100,
) -> dict[str, Any]:
    """Return a page payload for list endpoints."""
    try:
        page = int(request.query_params.get("page", 1))
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = int(request.query_params.get("page_size", default_page_size))
    except (TypeError, ValueError):
        page_size = default_page_size

    page = max(1, page)
    page_size = max(1, min(page_size, max_page_size))

    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)
    return {
        "count": paginator.count,
        "page": page_obj.number,
        "page_size": page_size,
        "total_pages": paginator.num_pages,
        "results": list(page_obj.object_list),
    }
