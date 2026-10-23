# Architecture one-pager — CP1 mentor

Day-1-accurate sketch of what Incident Zero is building. Planning detail lives in [architecture.md](architecture.md) and [design.md](design.md).

## Context

```
┌──────────────────────┐   alerts / metrics        ┌─────────────────────────────┐
│ OpenTelemetry Demo   │ ─────────────────────────▶│  Incident Zero Agent        │
│ (Astronomy Shop)     │                           │  Detect → Investigate →     │
│ :8080 frontend       │◀── tool queries (reads) ──│  Diagnose → Propose        │
│ Prometheus / Jaeger  │                           │  (Approve → Act → Verify   │
│ Logs / Docker        │◀── Action API (Day 2) ────│   → Report = Day 2)        │
└──────────────────────┘   propose / stub Day 1    └──────────────┬──────────────┘
                                                                  │
                                                     Human gate + kill switch
                                                     (wired Day 2; stub now)
```

## Stack (what we are building)

| Layer | Choice |
|-------|--------|
| Language | Python 3.11+ |
| Orchestrator | LangGraph state machine |
| Telemetry | Prometheus `:9090`, Jaeger, OpenSearch, Docker Engine API |
| Schemas | Pydantic v2 (+ organiser JSON schema when available) |
| LLM | Organiser API key; OpenAI-compatible client; Ollama fallback |
| Action path | `ActionAPIClient` **stub** — propose-only on Day 1; no writes |
| Operator UI | Streamlit / FastAPI — Day 2 polish |

## Components

| Component | Responsibility | Day 1 |
|-----------|----------------|-------|
| **Alert / session** | Open incident from mock alert / Prom signal; scratchpad under `reports/sessions/` | Live |
| **Orchestrator** | LangGraph investigate loop → symptom summary → diagnosis | Live (Eyes → Brain) |
| **Tool layer** | `query_metrics`, `query_traces`, `query_logs`, `container_health` | Live |
| **LLM brain** | Chooses tools; drafts diagnosis + confidence | Live by CP2 |
| **Runbook mapper** | Maps diagnosis → allowlisted Action API ops | Propose-only |
| **Action client** | Sole future writer; checks kill switch | Stub (no execute) |
| **Approval / dry-run / kill** | Human YES, dry-run payload, refuse writes | Stub / Day 2 |
| **Verifier / rollback** | Re-query health; escalate if unrecovered | Day 2 |
| **Reporter** | Schema JSON + markdown under `reports/` | Stub → CP2 |
| **Operator UI** | Timeline, approve, kill | Day 2 |

## Tools

Read-only investigation tools (never mutate the demo):

| Tool | Source |
|------|--------|
| `query_metrics` | Prometheus |
| `query_traces` | Jaeger |
| `query_logs` | OpenSearch / collector |
| `container_health` | Docker API |

Compact return shape (every tool):

```json
{
  "ok": true,
  "kind": "metric|trace|log|health",
  "service": "payment",
  "summary": "...",
  "items": [{"pointer": "...", "snippet": "..."}],
  "raw_refs": []
}
```

`propose_action` drafts an allowlisted fix from the runbook. **No** `execute_action` on Day 1. **No** flagd / flag UI reads for diagnosis.

## Decision flow (Day 1)

```
ALERT / open-session
  → gather symptoms (error rate, latency, service if present)
  → LOOP (max N tool rounds):
        LLM chooses tool + args
        append evidence to scratchpad
        if enough for summary/diagnosis OR stuck → exit
  → SYMPTOM SUMMARY (CP1) / DIAGNOSIS {component, cause, confidence, evidence[]} (CP2)
  → if confidence < threshold OR no allowlisted fix → ESCALATE
  → PROPOSE action from runbook (dry-run payload OK)
  → STOP for human ── Act / Verify / Report execute path = Day 2
```

## Safety controls

1. **Read/write split** — Investigation tools never mutate; only Action Client may write (not called on Day 1).
2. **Allowlist** — restart / toggle flag / throttle loadgen / scale only.
3. **Human gate** — Explicit yes required before any write; timeout = escalate.
4. **Dry-run** — Serialise intended Action API payload without sending.
5. **Kill switch** — Env / file / UI; Action Client refuses all writes when set.
6. **No flagd for diagnosis** — Telemetry only; never read feature-flag config APIs.
7. **Audit log** — Tool calls, approvals, and actions append to the session log.

## Day 1 practice incidents

| ID | Fault | Expected service | Mentor slot |
|----|-------|------------------|-------------|
| **P1** | `paymentFailure` | `payment` (checkout) | **CP1** (+ CP0/CP2) |
| **P2** | `cartFailure` | `cart` | CP2 |
| **P3** | `productCatalogFailure` | `product-catalog` | CP2 |

Inject/reset: [faultctl-runbook.md](faultctl-runbook.md). One fault at a time; reset between runs.

## Repo boundary

- `opentelemetry-demo/` — **untouched** (vendor app under test).
- `incident-zero/` — **all** agent code, schemas, reports, docs.
