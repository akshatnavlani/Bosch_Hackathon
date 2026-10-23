"""Read-only Prometheus metrics query tool."""

from __future__ import annotations

import os
import re
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from agent.tools.base import MAX_ITEMS, tool_result

_DURATION_PART = re.compile(r"(\d+)(ms|s|m|h|d|w)")
_UNIT_SECONDS = {"ms": 0.001, "s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}


def _window_seconds(window: str | int | float | timedelta) -> float:
    if isinstance(window, timedelta):
        seconds = window.total_seconds()
    elif isinstance(window, (int, float)):
        seconds = float(window)
    elif isinstance(window, str):
        value = window.strip()
        matches = list(_DURATION_PART.finditer(value))
        if not matches or "".join(match.group() for match in matches) != value:
            raise ValueError("window must be seconds or a duration such as '5m'")
        seconds = sum(int(match[1]) * _UNIT_SECONDS[match[2]] for match in matches)
    else:
        raise ValueError("window must be seconds, timedelta, or a Prometheus duration")
    if seconds <= 0 or seconds > 31 * 86400:
        raise ValueError("window must be greater than zero and no longer than 31 days")
    return seconds


def _extract_items(data: dict[str, Any], promql: str) -> tuple[list[dict[str, str]], str | None]:
    items = []
    services = set()
    for series in data.get("result", []):
        labels = series.get("metric", {})
        service_name = labels.get("service") or labels.get("service_name")
        if service_name:
            services.add(str(service_name))
        values = series.get("values") or ([series["value"]] if series.get("value") else [])
        if not values:
            continue
        timestamp, value = values[-1]
        label_text = ",".join(f'{key}="{val}"' for key, val in sorted(labels.items()))
        pointer = f"{promql}{{{label_text}}} @ {timestamp}" if label_text else f"{promql} @ {timestamp}"
        items.append({"pointer": pointer, "snippet": f"value={value}"})
        if len(items) >= MAX_ITEMS:
            break
    return items, next(iter(services)) if len(services) == 1 else None


def query_metrics(
    promql: str,
    window: str | int | float | timedelta,
    *,
    service: str | None = None,
    base_url: str | None = None,
    timeout: float = 5.0,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Query Prometheus over ``window`` and return compact evidence.

    Window accepts seconds, ``timedelta``, or a duration such as ``5m``.
    ``PROMETHEUS_URL`` defaults to ``http://localhost:9090``.
    """
    query = promql.strip()
    if not query:
        return tool_result(kind="metric", service=service, summary="PromQL query is empty", ok=False)
    try:
        seconds = _window_seconds(window)
    except ValueError as exc:
        return tool_result(kind="metric", service=service, summary=str(exc), ok=False)

    end = datetime.now(UTC)
    start = end - timedelta(seconds=seconds)
    url = (base_url or os.getenv("PROMETHEUS_URL", "http://localhost:9090")).rstrip("/")
    params = {
        "query": query,
        "start": start.isoformat().replace("+00:00", "Z"),
        "end": end.isoformat().replace("+00:00", "Z"),
        "step": str(max(1, int(seconds / 120))),
    }
    try:
        if client is None:
            with httpx.Client(timeout=timeout) as http:
                response = http.get(f"{url}/api/v1/query_range", params=params)
        else:
            response = client.get(f"{url}/api/v1/query_range", params=params)
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != "success":
            return tool_result(
                kind="metric", service=service,
                summary=str(payload.get("error", "Prometheus returned a non-success status")), ok=False,
            )
        items, found_service = _extract_items(payload.get("data", {}), query)
        service = service or found_service
        return tool_result(
            kind="metric", service=service,
            summary=f"Prometheus returned {len(items)} series for the last {window}", items=items,
        )
    except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
        return tool_result(
            kind="metric", service=service,
            summary=f"Prometheus query failed: {str(exc)[:160]}", ok=False,
        )
