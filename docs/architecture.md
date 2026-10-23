# System Architecture — Incident Zero

One-page overview of components, tools, decision flow, and safety controls.

## Context

```
┌──────────────────────┐     alerts / metrics      ┌─────────────────────────────┐
│ OpenTelemetry Demo   │ ─────────────────────────▶│  Incident Zero Agent        │
│ (Astronomy Shop)     │                           │  Detect → Investigate →     │
│ :8080 frontend       │◀── Action API (writes) ───│  Diagnose → Propose →       │
│ Prometheus / Jaeger  │◀── tool queries (reads) ──│  Approve → Act → Verify →   │
│ Logs / Docker        │                           │  Report                     │
└──────────────────────┘                           └──────────────┬──────────────┘
                                                                  │
                                                           Human approval
                                                           + kill switch
```

## Components

| Component | Responsibility |
|-----------|----------------|
| **Alert Listener** | Poll Prometheus rules / receive webhook; open an Incident Session |
| **Orchestrator** | LangGraph (or equivalent) state machine for the 7 stages |
| **Tool Layer** | Typed tools: `query_metrics`, `query_traces`, `query_logs`, `container_health`, `list_deploys` (read-only) |
| **LLM Brain** | Tool-calling model; picks next tool; drafts diagnosis + confidence |
| **Runbook Mapper** | Maps diagnosis tags → allowlisted Action API ops |
| **Approval Gate** | Blocks writes until human YES; supports dry-run |
| **Action Client** | Sole writer to Action API; checks kill switch every call |
| **Verifier** | Re-queries health metrics; triggers rollback / escalate |
| **Reporter** | Emits schema JSON + markdown report to `reports/` |
| **Operator UI** | Minimal Streamlit/FastAPI page: live timeline, approve, kill |

## Decision flow

```
ALERT
  → gather high-level symptoms (error rate, latency, failing service name if present)
  → LOOP (max N tool rounds):
        LLM chooses tool + args
        append evidence to scratchpad
        if enough for diagnosis OR stuck → exit loop
  → DIAGNOSIS {component, cause, confidence, evidence[]}
  → if confidence < threshold OR no allowlisted fix → ESCALATE (correct outcome)
  → PROPOSE action from runbook
  → WAIT approval (or dry-run preview)
  → if kill_switch OR reject → STOP
  → ACT via Action API
  → VERIFY metrics recovered
  → if not → ROLLBACK + ESCALATE
  → REPORT
```

## Safety controls

1. **Read/write split** — Investigation tools never mutate; only Action Client writes.
2. **Allowlist** — Actions limited to restart / toggle flag / throttle loadgen / scale (K8s).
3. **Human gate** — Explicit yes required; timeout = escalate.
4. **Dry-run** — Serialises intended Action API payload without sending.
5. **Kill switch** — File/env/UI flag; Action Client refuses all writes when set.
6. **No flagd reads for diagnosis** — Tool layer must not expose flag config APIs.
7. **Audit log** — Every tool call + approval + action appended to session log.

## Deployment topology (laptop)

| Process | Where |
|---------|--------|
| OTel Demo + collector + Prometheus (+ Jaeger/OpenSearch if enabled) | Docker Compose in `../opentelemetry-demo` |
| Action API + faultctl | Provided day-of (adapter stubs until then) |
| Agent orchestrator + UI | Local Python process in this repo |
| LLM | Organiser API key **or** local Ollama as fallback |

## Repo boundary

- `opentelemetry-demo/` — **untouched** (vendor app under test).
- `incident-zero/` — **all** agent code, schemas, reports, docs.
