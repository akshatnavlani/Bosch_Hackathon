"""Unit tests for query_traces (D1-07); Jaeger is mocked."""

from __future__ import annotations

import httpx
import json

from agent.tools.base import MAX_ITEMS
from agent.tools.traces import DEFAULT_LIMIT, MAX_LIMIT, query_traces


def _span(
    *,
    trace_id: str = "trace-1",
    span_id: str = "span-1",
    service: str = "payment",
    error: bool = True,
) -> dict:
    return {
        "traceID": trace_id,
        "spans": [
            {
                "spanID": span_id,
                "operationName": "AuthorizePayment",
                "processID": "p1",
                "duration": 1234,
                "tags": [{"key": "error", "type": "bool", "value": error}],
            }
        ],
        "processes": {"p1": {"serviceName": service}},
    }


def test_query_traces_filters_errors_and_maps_trace_ids() -> None:
    requests: list[httpx.Request] = []
    payload = {
        "data": [
            _span(trace_id="error-trace"),
            _span(trace_id="ok-trace", span_id="span-2", error=False),
            _span(trace_id="other-service", service="cart"),
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=payload)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = query_traces(
            "payment", limit=5, lookback="30m", base_url="http://jaeger.test", client=client
        )

    assert result == {
        "ok": True,
        "kind": "trace",
        "service": "payment",
        "summary": "1 error span(s) for service=payment in the last 30m (limit=5)",
        "items": [
            {
                "pointer": "trace:error-trace:span:span-1",
                "snippet": "service=payment; operation=AuthorizePayment; duration=1234μs",
            }
        ],
    }
    request = requests[0]
    assert request.url.path == "/api/traces"
    assert request.url.params["service"] == "payment"
    assert request.url.params["limit"] == "5"
    assert request.url.params["lookback"] == "30m"
    assert json.loads(request.url.params["tags"]) == {"error": "true"}


def test_query_traces_can_return_non_error_spans() -> None:
    payload = {"data": [_span(), _span(trace_id="trace-2", error=False)]}
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ) as client:
        result = query_traces("payment", error=False, client=client)

    assert len(result["items"]) == 2
    assert "tags" not in str(result)


def test_query_traces_caps_top_k_to_shared_compact_limit() -> None:
    payload = {"data": [_span(trace_id=f"trace-{i}", span_id=f"span-{i}") for i in range(25)]}
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=payload)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = query_traces("payment", error=False, limit=999, client=client)

    assert len(result["items"]) == MAX_ITEMS
    assert requests[0].url.params["limit"] == str(MAX_LIMIT)


def test_query_traces_empty_and_missing_service() -> None:
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"data": []}))
    ) as client:
        empty = query_traces("payment", client=client)

    assert empty["ok"] is True
    assert empty["items"] == []
    assert empty["service"] == "payment"
    assert query_traces("")["ok"] is False
    assert "service" in query_traces("")["summary"]


def test_query_traces_backend_unavailable_mentions_compose_fix() -> None:
    def fail(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused", request=request)

    with httpx.Client(transport=httpx.MockTransport(fail)) as client:
        result = query_traces("payment", client=client)

    assert result["ok"] is False
    assert result["kind"] == "trace"
    assert result["items"] == []
    assert "Jaeger unavailable" in result["summary"]
    assert "compose.observability.yaml" in result["summary"]


def test_query_traces_default_limit() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"data": []})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        query_traces("payment", client=client)

    assert requests[0].url.params["limit"] == str(DEFAULT_LIMIT)
