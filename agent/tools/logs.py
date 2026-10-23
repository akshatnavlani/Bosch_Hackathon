"""Log query tool (query_logs) against demo OpenSearch."""

from __future__ import annotations

import os
from typing import Any

import httpx

DEFAULT_LIMIT = 20
MAX_LIMIT = 50
DEFAULT_OPENSEARCH_URL = "http://127.0.0.1:9200"
LOGS_INDEX = "otel-logs-*"
SNIPPET_BODY_MAX = 240
HTTP_TIMEOUT = 10.0


def _clamp_limit(limit: int) -> int:
    return max(1, min(int(limit), MAX_LIMIT))


def _opensearch_url(base_url: str | None) -> str:
    url = (base_url or os.environ.get("OPENSEARCH_URL") or DEFAULT_OPENSEARCH_URL).rstrip("/")
    return url


def _envelope(
    *,
    ok: bool,
    service: str,
    summary: str,
    items: list[dict[str, str]] | None = None,
    raw_refs: list[str] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "ok": ok,
        "kind": "log",
        "service": service,
        "summary": summary,
        "items": items or [],
        "raw_refs": raw_refs or [],
    }
    if error is not None:
        out["error"] = error
    return out


def _build_query(
    service: str,
    level: str | None,
    query: str | None,
    size: int,
) -> dict[str, Any]:
    must: list[dict[str, Any]] = [
        {"term": {"resource.service.name.keyword": service}},
    ]
    if level:
        must.append({"term": {"severity.text.keyword": level}})
    if query:
        must.append({"match": {"body": query}})

    return {
        "size": size,
        "sort": [{"observedTimestamp": {"order": "desc", "unmapped_type": "date"}}],
        "query": {"bool": {"must": must}},
        "_source": [
            "body",
            "severity.text",
            "resource.service.name",
            "observedTimestamp",
            "time",
        ],
    }


def _field(source: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in source and source[key] is not None:
            return source[key]
    # Nested resource.service.name may already be flattened in _source keys
    return None


def _hit_to_item(hit: dict[str, Any], service: str) -> dict[str, str]:
    source = hit.get("_source") or {}
    body = str(_field(source, "body") or "")
    level = str(_field(source, "severity.text") or "")
    ts = str(_field(source, "observedTimestamp", "time") or "")
    hit_id = str(hit.get("_id") or "")

    body_snip = body if len(body) <= SNIPPET_BODY_MAX else body[: SNIPPET_BODY_MAX - 1] + "…"
    parts = [p for p in (f"[{ts}]" if ts else None, level or None, body_snip or None) if p]
    snippet = " ".join(parts) if parts else "(empty log line)"

    if hit_id:
        pointer = f"log:{service}:{hit_id}"
    elif ts:
        pointer = f"log:{service}:{ts}"
    else:
        pointer = f"log:{service}:{abs(hash(snippet)) % 10_000_000}"

    return {"pointer": pointer, "snippet": snippet}


def query_logs(
    service: str,
    level: str | None = None,
    query: str | None = None,
    limit: int = DEFAULT_LIMIT,
    *,
    base_url: str | None = None,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Query OpenSearch for compact log evidence by service / level / keyword.

    Returns the shared Day-1 tool envelope. On backend failure, ``ok`` is False
    with a clear summary (never invents log lines).
    """
    if not service or not str(service).strip():
        return _envelope(
            ok=False,
            service=service or "",
            summary="service is required for query_logs",
            error="missing_service",
        )

    service = str(service).strip()
    size = _clamp_limit(limit if limit is not None else DEFAULT_LIMIT)
    url = _opensearch_url(base_url)
    search_url = f"{url}/{LOGS_INDEX}/_search"
    payload = _build_query(service, level, query, size)

    owns_client = client is None
    http = client or httpx.Client(timeout=HTTP_TIMEOUT)
    try:
        try:
            resp = http.post(search_url, json=payload)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as exc:
            detail = f"HTTP {exc.response.status_code}"
            return _envelope(
                ok=False,
                service=service,
                summary=f"OpenSearch unreachable or error at {url}: {detail}",
                error=detail,
                raw_refs=[search_url],
            )
        except httpx.RequestError as exc:
            detail = f"{type(exc).__name__}: {exc}"
            return _envelope(
                ok=False,
                service=service,
                summary=f"OpenSearch unreachable at {url}: {detail}",
                error=detail,
                raw_refs=[search_url],
            )
        except ValueError as exc:
            return _envelope(
                ok=False,
                service=service,
                summary=f"OpenSearch returned invalid JSON from {url}: {exc}",
                error=str(exc),
                raw_refs=[search_url],
            )
    finally:
        if owns_client:
            http.close()

    hits = (data.get("hits") or {}).get("hits") or []
    items = [_hit_to_item(h, service) for h in hits[:size]]

    filters: list[str] = [f"service={service}"]
    if level:
        filters.append(f"level={level}")
    if query:
        filters.append(f"keyword={query!r}")
    filter_desc = ", ".join(filters)

    if not items:
        summary = f"no matching logs ({filter_desc}, limit={size})"
    else:
        summary = f"{len(items)} log line(s) ({filter_desc}, limit={size})"

    return _envelope(
        ok=True,
        service=service,
        summary=summary,
        items=items,
        raw_refs=[search_url],
    )
