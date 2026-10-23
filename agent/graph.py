"""Bounded read-only investigate loop for the Day-1 Eyes demo.

Each tool result is added to the session scratchpad before the next tool is
selected. Follow-up calls therefore depend on the evidence already collected.
This stage reports symptoms only; diagnosis belongs to D1-14.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from agent.prompts import DIAGNOSE_PROMPT, INVESTIGATE_PROMPT
from agent.state import IncidentState
from agent.tools.health import container_health
from agent.tools.logs import query_logs
from agent.tools.metrics import query_metrics
from agent.tools.traces import query_traces

Tool = Callable[..., dict[str, Any]]

ERROR_RATE_QUERY = (
    "sum by (service_name) (rate(traces_span_metrics_calls_total"
    '{status_code="STATUS_CODE_ERROR"}[1m]))'
)
MAX_TOOL_ROUNDS = 4

# Expose the checked-in system prompts to graph nodes. Diagnosis is introduced
# by D1-14; keeping its prompt loaded here gives that node one canonical source.
STAGE_PROMPTS = {
    "investigate": INVESTIGATE_PROMPT,
    "diagnose": DIAGNOSE_PROMPT,
}


def _service_for_alert(alert: dict[str, Any]) -> str:
    """Pick the practice service from alert text and labels, without flag reads."""
    labels = alert.get("labels") or {}
    text = " ".join(
        str(value)
        for value in (
            labels.get("service", ""),
            labels.get("alertname", ""),
            (alert.get("annotations") or {}).get("summary", ""),
            (alert.get("annotations") or {}).get("description", ""),
        )
    ).lower()
    if "product" in text and ("catalog" in text or "product-catalog" in text):
        return "product-catalog"
    if "cart" in text:
        return "cart"
    if "payment" in text or "checkout" in text:
        return "payment"
    return str(labels.get("service") or "unknown")


def _metric_query(service: str) -> str:
    return ERROR_RATE_QUERY.replace(
        'status_code="STATUS_CODE_ERROR"',
        f'status_code="STATUS_CODE_ERROR",service_name="{service}"',
    )


def _has_items(result: dict[str, Any]) -> bool:
    return bool(result.get("ok") and result.get("items"))


def investigate(
    state: IncidentState,
    *,
    tools: dict[str, Tool] | None = None,
    max_rounds: int = MAX_TOOL_ROUNDS,
) -> dict[str, Any]:
    """Gather telemetry iteratively and return a symptom summary with citations.

    ``tools`` is injectable so the loop can be exercised without live demo
    services. Returned evidence pointers/snippets are copied verbatim.
    """
    available = tools or {
        "query_metrics": query_metrics,
        "query_traces": query_traces,
        "query_logs": query_logs,
        "container_health": container_health,
    }
    service = _service_for_alert(state.alert)
    calls: list[dict[str, Any]] = []

    # The next tool depends on the prior result: telemetry evidence on the
    # primary signal triggers trace inspection; trace evidence/failure is then
    # cross-checked with logs and container health in bounded rounds.
    sequence = ["query_metrics", "query_traces", "query_logs", "container_health"]
    previous: dict[str, Any] = {}
    for tool_name in sequence[: max(0, min(max_rounds, len(sequence)))]:
        if tool_name == "query_metrics":
            result = available[tool_name](_metric_query(service), "5m", service=service)
        elif tool_name == "query_traces":
            if not _has_items(previous) and previous.get("ok") is True:
                continue
            result = available[tool_name](service, error=True, limit=5)
        elif tool_name == "query_logs":
            if previous.get("ok") is True and not _has_items(previous):
                continue
            result = available[tool_name](service, level="ERROR", limit=5)
        else:
            if previous.get("ok") is True and not _has_items(previous):
                continue
            result = available[tool_name](service)
        entry = {"tool": tool_name, "result": result}
        state.scratchpad.append(entry)
        calls.append(entry)
        previous = result

    summaries = [
        f"{call['result'].get('kind', 'telemetry')}: {call['result'].get('summary', 'no summary')}"
        for call in calls
    ]
    evidence = [
        {
            "kind": call["result"].get("kind"),
            "service": call["result"].get("service"),
            "pointer": item.get("pointer", ""),
            "snippet": item.get("snippet", ""),
        }
        for call in calls
        for item in call["result"].get("items", [])
        if item.get("pointer") and item.get("snippet")
    ]

    symptom = f"Telemetry collected for the {service} service. " + (
        "; ".join(summaries) if summaries else "No telemetry tools returned results."
    )
    if not evidence:
        symptom += " No evidence items were returned."
    report = {
        "incident_id": state.incident_id,
        "symptom_summary": symptom,
        "evidence": evidence,
        "tool_calls": len(calls),
    }
    return report
