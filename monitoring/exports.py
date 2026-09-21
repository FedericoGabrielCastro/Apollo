from __future__ import annotations

import csv
from collections.abc import Iterable
from io import StringIO
from typing import Any

from django.http import HttpResponse


def csv_response(filename: str, headers: list[str], rows: Iterable[Iterable[Any]]) -> HttpResponse:
    """Build a downloadable CSV HttpResponse."""
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(list(row))
    response = HttpResponse(buffer.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
