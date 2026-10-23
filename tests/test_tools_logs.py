"""Unit tests for query_logs (D1-08) — mocked OpenSearch, no live backend required."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
from agent.tools.logs import DEFAULT_LIMIT, MAX_LIMIT, query_logs


def _hit(
    *,
    body: str,
    level: str = "INFO",
    service: str = "payment",
    ts: str = "2026-10-23T12:00:00Z",
    hit_id: str = "abc123",
) -> dict[str, Any]:
    return {
        "_id": hit_id,
        "_source": {
            "body": body,
            "severity.text": level,
            "resource.service.name": service,
            "observedTimestamp": ts,
        },
    }


class _FakeTransport(httpx.BaseTransport):
    """Capture last request and return a canned OpenSearch JSON body."""

    def __init__(
        self,
        response_json: dict[str, Any] | None = None,
        *,
        error: Exception | None = None,
    ):
        self.response_json = response_json
        self.error = error
        self.last_request: httpx.Request | None = None

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.last_request = request
        if self.error is not None:
            raise self.error
        assert self.response_json is not None
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            content=json.dumps(self.response_json).encode(),
            request=request,
        )


def test_query_logs_filters_and_maps_snippets() -> None:
    transport = _FakeTransport(
        {
            "hits": {
                "hits": [
                    _hit(body="payment timeout to bank", level="ERROR", hit_id="h1"),
                    _hit(
                        body="retry scheduled",
                        level="WARN",
                        hit_id="h2",
                        ts="2026-10-23T11:59:00Z",
                    ),
                ]
            }
        }
    )
    with httpx.Client(transport=transport) as client:
        result = query_logs(
            "payment",
            level="ERROR",
            query="timeout",
            limit=10,
            base_url="http://opensearch.test:9200",
            client=client,
        )

    assert result["ok"] is True
    assert result["kind"] == "log"
    assert result["service"] == "payment"
    assert len(result["items"]) == 2
    assert result["items"][0]["pointer"] == "log:payment:h1"
    assert "payment timeout to bank" in result["items"][0]["snippet"]
    assert "ERROR" in result["items"][0]["snippet"]
    assert result["items"][0]["snippet"]  # Evidence-suitable non-empty

    assert transport.last_request is not None
    assert transport.last_request.url.path.endswith("/otel-logs-*/_search")
    body = json.loads(transport.last_request.content.decode())
    assert body["size"] == 10
    must = body["query"]["bool"]["must"]
    assert {"term": {"resource.service.name.keyword": "payment"}} in must
    assert {"term": {"severity.text.keyword": "ERROR"}} in must
    assert {"match": {"body": "timeout"}} in must


def test_query_logs_hard_limit_clamp() -> None:
    transport = _FakeTransport({"hits": {"hits": []}})
    with httpx.Client(transport=transport) as client:
        query_logs("cart", limit=999, base_url="http://os:9200", client=client)

    body = json.loads(transport.last_request.content.decode())  # type: ignore[union-attr]
    assert body["size"] == MAX_LIMIT

    transport2 = _FakeTransport({"hits": {"hits": []}})
    with httpx.Client(transport=transport2) as client:
        query_logs("cart", limit=0, base_url="http://os:9200", client=client)
    body2 = json.loads(transport2.last_request.content.decode())  # type: ignore[union-attr]
    assert body2["size"] == 1


def test_query_logs_default_limit() -> None:
    transport = _FakeTransport({"hits": {"hits": []}})
    with httpx.Client(transport=transport) as client:
        query_logs("frontend", base_url="http://os:9200", client=client)
    body = json.loads(transport.last_request.content.decode())  # type: ignore[union-attr]
    assert body["size"] == DEFAULT_LIMIT


def test_query_logs_empty_hits_ok() -> None:
    transport = _FakeTransport({"hits": {"hits": []}})
    with httpx.Client(transport=transport) as client:
        result = query_logs("payment", base_url="http://os:9200", client=client)
    assert result["ok"] is True
    assert result["items"] == []
    assert "no matching logs" in result["summary"]


def test_query_logs_backend_missing_connection_error() -> None:
    transport = _FakeTransport(
        error=httpx.ConnectError(
            "Connection refused", request=httpx.Request("POST", "http://os:9200/x")
        ),
    )
    with httpx.Client(transport=transport) as client:
        result = query_logs("payment", base_url="http://os:9200", client=client)

    assert result["ok"] is False
    assert result["items"] == []
    assert "OpenSearch unreachable" in result["summary"]
    assert result.get("error")


def test_query_logs_backend_http_error() -> None:
    class StatusTransport(httpx.BaseTransport):
        def handle_request(self, request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, text="unavailable", request=request)

    with httpx.Client(transport=StatusTransport()) as client:
        result = query_logs("payment", base_url="http://os:9200", client=client)

    assert result["ok"] is False
    assert "OpenSearch unreachable" in result["summary"] or "error" in result["summary"].lower()
    assert result["items"] == []


def test_query_logs_missing_service() -> None:
    result = query_logs("")
    assert result["ok"] is False
    assert "service" in result["summary"].lower()


def test_query_logs_snippet_truncated() -> None:
    long_body = "x" * 500
    transport = _FakeTransport({"hits": {"hits": [_hit(body=long_body, hit_id="long1")]}})
    with httpx.Client(transport=transport) as client:
        result = query_logs("payment", base_url="http://os:9200", client=client)
    snippet = result["items"][0]["snippet"]
    assert len(snippet) < 400
    assert "…" in snippet


@pytest.mark.skipif(
    True,
    reason="SKIPPED: live OpenSearch smoke not required for D1-08 CI; mock tests cover acceptance",
)
def test_live_opensearch_smoke_optional() -> None:
    result = query_logs("frontend", limit=1)
    assert "ok" in result
