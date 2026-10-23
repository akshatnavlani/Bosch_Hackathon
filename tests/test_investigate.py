from agent.graph import investigate
from agent.state import IncidentState


def test_investigate_uses_prior_results_and_preserves_evidence():
    calls = []
    result_items = {
        "query_metrics": {"pointer": "promql:payment @ 123", "snippet": "value=7"},
        "query_traces": {"pointer": "trace:abc:span:def", "snippet": "payment failed"},
        "query_logs": {"pointer": "log:payment:1", "snippet": "ERROR declined"},
        "container_health": {"pointer": "health:payment:status", "snippet": "status=running"},
    }

    def respond(name, *args, **kwargs):
        calls.append(name)
        item = result_items[name]
        return {
            "ok": True,
            "kind": name.removeprefix("query_").replace("container_", ""),
            "service": "payment",
            "summary": f"{name} returned evidence",
            "items": [item],
        }

    tools = {
        name: (lambda *args, _name=name, **kwargs: respond(_name, *args, **kwargs))
        for name in result_items
    }
    state = IncidentState(
        incident_id="inc-test",
        alert={
            "labels": {"service": "checkout"},
            "annotations": {"description": "checkout / payment path"},
        },
    )

    report = investigate(state, tools=tools)

    assert calls == ["query_metrics", "query_traces", "query_logs", "container_health"]
    assert report["tool_calls"] == 4
    assert [item["pointer"] for item in report["evidence"]] == [
        "promql:payment @ 123",
        "trace:abc:span:def",
        "log:payment:1",
        "health:payment:status",
    ]
    assert "root cause" not in report["symptom_summary"].lower()
    assert all(entry["result"]["items"] for entry in state.scratchpad)


def test_investigate_stops_followups_when_metric_has_no_evidence():
    calls = []

    def metrics(*args, **kwargs):
        calls.append("query_metrics")
        return {"ok": True, "kind": "metric", "service": "payment", "summary": "empty", "items": []}

    state = IncidentState(incident_id="inc-empty", alert={"labels": {"service": "payment"}})
    report = investigate(state, tools={"query_metrics": metrics})

    assert calls == ["query_metrics"]
    assert report["evidence"] == []
    assert report["tool_calls"] == 1
