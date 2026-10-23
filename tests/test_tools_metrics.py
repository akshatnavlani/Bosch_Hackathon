import json
from pathlib import Path

import httpx
from agent.tools.metrics import query_metrics

FIXTURE = Path(__file__).parent / "fixtures" / "prometheus_range.json"


def test_query_metrics_returns_compact_fixture_evidence():
    payload = json.loads(FIXTURE.read_text())
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=payload)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = query_metrics(
        'sum(rate(http_requests_total{status_code="500"}[5m]))', "5m", client=client
    )

    assert result["ok"] is True
    assert result["kind"] == "metric"
    assert result["service"] == "checkout"
    assert len(result["items"]) == 1
    assert "@ 1792760060" in result["items"][0]["pointer"]
    assert result["items"][0]["snippet"] == "value=7"
    assert requests[0].url.path == "/api/v1/query_range"
    assert requests[0].url.params["query"].startswith("sum(rate(")
    client.close()


def test_query_metrics_rejects_invalid_window_without_request():
    result = query_metrics("up", "not-a-window")

    assert result["ok"] is False
    assert result["kind"] == "metric"
    assert result["items"] == []


def test_query_metrics_caps_number_of_items():
    payload = {
        "status": "success",
        "data": {
            "result": [
                {"metric": {"instance": str(index)}, "values": [[1, "1"]]} for index in range(30)
            ]
        },
    }
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    )
    result = query_metrics("up", "1m", client=client)
    assert result["ok"] is True
    assert len(result["items"]) == 20
    client.close()
