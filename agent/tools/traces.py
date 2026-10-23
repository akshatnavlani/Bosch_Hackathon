"""Read-only Jaeger trace query tool."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

from agent.tools.base import MAX_ITEMS, tool_result

DEFAULT_LIMIT = 10
MAX_LIMIT = MAX_ITEMS
DEFAULT_LOOKBACK = "1h"
DEFAULT_JAEGER_URL = "http://localhost:8080/jaeger/ui"
HTTP_TIMEOUT = 10.0
OBSERVABILITY_HINT = (
    "Start the demo with docker compose -f compose.yaml -f compose.observability.yaml up -d "
    "from ../opentelemetry-demo."
)


def _clamp_limit(limit: int) -> int:
    return max(1, min(int(limit), MAX_LIMIT))


def _span_value(span: dict[str, Any], key: str) -> str:
    for tag in span.get("tags") or []:
        if tag.get("key") == key:
            return str(tag.get("value", ""))
    return ""


def _is_error(span: dict[str, Any]) -> bool:
    value = _span_value(span, "error").lower()
    return value in {"true", "1"}


def _extract_error_spans(
    payload: dict[str, Any], service: str, error_only: bool, limit: int
) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for trace in payload.get("data") or []:
        trace_id = str(trace.get("traceID") or "")
        processes = trace.get("processes") or {}
        for span in trace.get("spans") or []:
            process = processes.get(span.get("processID"), {})
            span_service = str(process.get("serviceName") or "")
            if span_service and span_service != service:
                continue
            if error_only and not _is_error(span):
                continue

            span_id = str(span.get("spanID") or "")
            operation = str(span.get("operationName") or "(unnamed operation)")
            duration = span.get("duration")
            detail = f"service={span_service or service}; operation={operation}"
            if duration is not None:
                detail += f"; duration={duration}μs"
            items.append(
                {
                    "pointer": f"trace:{trace_id}" + (f":span:{span_id}" if span_id else ""),
                    "snippet": detail,
                }
            )
            if len(items) >= limit:
                return items
    return items


def query_traces(
    service: str,
    error: bool = True,
    limit: int = DEFAULT_LIMIT,
    *,
    lookback: str = DEFAULT_LOOKBACK,
    base_url: str | None = None,
    timeout: float = HTTP_TIMEOUT,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Query Jaeger for recent spans from ``service`` and return compact evidence.

    By default only error spans are returned. ``JAEGER_URL`` can override the
    demo proxy URL; set it to a Jaeger query base URL if using a direct port.
    """
    if not service or not str(service).strip():
        return tool_result(
            kind="trace", service=service or "", summary="service is required", ok=False
        )
    service = str(service).strip()
    limit = _clamp_limit(limit if limit is not None else DEFAULT_LIMIT)
    if not lookback or not str(lookback).strip():
        return tool_result(
            kind="trace", service=service, summary="lookback is required", ok=False
        )

    url = (base_url or os.getenv("JAEGER_URL") or DEFAULT_JAEGER_URL).rstrip("/")
    params: dict[str, str | int] = {
        "service": service,
        "limit": limit,
        "lookback": str(lookback).strip(),
    }
    if error:
        params["tags"] = json.dumps({"error": "true"}, separators=(",", ":"))

    owns_client = client is None
    http = client or httpx.Client(timeout=timeout)
    try:
        try:
            response = http.get(f"{url}/api/traces", params=params)
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError as exc:
            return tool_result(
                kind="trace",
                service=service,
                summary=f"Jaeger unavailable at {url}: {type(exc).__name__}. {OBSERVABILITY_HINT}",
                ok=False,
            )
        except ValueError as exc:
            return tool_result(
                kind="trace",
                service=service,
                summary=f"Jaeger returned invalid JSON: {exc}",
                ok=False,
            )
    finally:
        if owns_client:
            http.close()

    items = _extract_error_spans(payload, service, error, limit)
    qualifier = "error span(s)" if error else "span(s)"
    summary = f"{len(items)} {qualifier} for service={service} in the last {lookback} (limit={limit})"
    return tool_result(kind="trace", service=service, summary=summary, items=items)
