# Design Doc — Incident Zero Agent

## 1. Recommended tech stack (5-person team)

| Layer | Choice | Why |
|-------|--------|-----|
| Language | **Python 3.11+** | Organiser prep pack assumes Python; richest LLM/agent ecosystem; fastest for 2-day hack |
| Agent framework | **LangGraph** (+ LangChain tools) | Explicit state machine maps 1:1 to Detect→Report; easy parallel ownership of nodes |
| LLM | Organiser key first; **OpenAI-compatible** client; optional **Ollama** fallback | Swap models without rewriting tools |
| Telemetry clients | `prometheus-api-client`, Jaeger HTTP / OTLP query, OpenSearch/`httpx`, Docker SDK | Thin wrappers; mockable in tests |
| API / approval UI | **FastAPI** + minimal HTMX or **Streamlit** | FastAPI if someone wants websocket timeline; Streamlit if UI owner wants speed |
| Schemas | **Pydantic v2** + JSON Schema from organisers | Validate every tool I/O and final report |
| Packaging | `uv` or `poetry` + `pyproject.toml` | Reproducible installs day-of |
| Tests | `pytest` + recorded fixtures (offline bundles) | CP2/CP4 resilience when demo flaky |
| Observability of agent | Structured JSON logs + session folder per incident | Judges care about explainability |

### Stack we explicitly avoid for day 1

- Multi-language microservices for the agent itself (split brain across TS+Go+Python burns hours).
- Fine-tuning / RAG over flag files (disallowed + risk of DQ).
- Heavy frontend (Next.js) unless stretch chat-approval after CP3.

### Alternate if team is TS-heavy

Node + **Vercel AI SDK** / LangGraph.js — only if ≥3 members are stronger in TS than Python. Default remains Python.

## 2. Target repository structure

```
incident-zero/
├── README.md                 # setup, run, approval, kill switch, limitations
├── pyproject.toml
├── .env.example
├── docs/
│   ├── PRD.md
│   ├── architecture.md
│   ├── design.md
│   └── checkpoints.md
├── schemas/                  # organiser JSON schema + our Pydantic mirrors
│   └── incident_report.schema.json
├── agent/
│   ├── __init__.py
│   ├── main.py               # CLI entry: run / dry-run / kill
│   ├── graph.py              # LangGraph state machine
│   ├── state.py              # IncidentState TypedDict / dataclass
│   ├── config.py
│   ├── prompts/
│   │   ├── investigate.md
│   │   ├── diagnose.md
│   │   └── report.md
│   ├── tools/
│   │   ├── metrics.py
│   │   ├── traces.py
│   │   ├── logs.py
│   │   ├── health.py
│   │   └── runbook.py        # propose allowlisted actions (no execute)
│   ├── adapters/
│   │   ├── action_api.py     # write path
│   │   ├── alert_source.py
│   │   └── stubs.py          # pre-kickoff mocks
│   ├── safety/
│   │   ├── approval.py
│   │   ├── kill_switch.py
│   │   └── dry_run.py
│   └── reporting/
│       ├── schema_validate.py
│       └── render.py
├── ui/
│   └── app.py                # Streamlit or FastAPI operator console
├── tests/
│   ├── fixtures/             # offline incident bundles
│   ├── test_tools.py
│   ├── test_safety.py
│   └── test_schema.py
├── reports/                  # generated incident reports
└── team/
    ├── team-form.md
    └── evaluation-note.md
```

Sibling (do not modify):

```
opentelemetry-demo/           # already cloned; running on :8080
```

## 3. Core data model

```python
class Evidence(BaseModel):
    kind: Literal["trace", "metric", "log", "health"]
    pointer: str          # trace_id, promql+timestamp, log line ref
    snippet: str          # short real excerpt — never invented
    service: str | None

class Diagnosis(BaseModel):
    component: str
    cause: str
    confidence: float     # 0..1
    evidence: list[Evidence]
    uncertain: bool

class ProposedAction(BaseModel):
    action_type: Literal["restart", "toggle_flag", "throttle_loadgen", "scale"]
    target: str
    params: dict
    reason: str
    dry_run_payload: dict

class IncidentState(BaseModel):
    incident_id: str
    alert: dict
    scratchpad: list[dict]      # tool call/result history
    diagnosis: Diagnosis | None
    proposal: ProposedAction | None
    approval: Literal["pending", "approved", "rejected", "escalated"]
    action_log: list[dict]
    recovered: bool | None
    report_path: str | None
    kill_switch: bool
```

## 4. Tool contracts (Eyes)

| Tool | Input | Output | Source |
|------|-------|--------|--------|
| `query_metrics` | PromQL, window | series + summary stats | Prometheus `:9090` |
| `query_traces` | service, error=true, limit | span summaries + trace IDs | Jaeger / Tempo |
| `query_logs` | service, level, query, limit | log lines with timestamps | OpenSearch / collector |
| `container_health` | service name | status, restarts, OOM | Docker API |
| `propose_action` | diagnosis | allowlisted action draft | Runbook table |
| `execute_action` | approved action | Action API response | **gated** |

Investigation tools return compact summaries (top-k), not raw dumps, to stay inside context limits.

## 5. Confidence policy

| Confidence | Behaviour |
|------------|-----------|
| ≥ 0.75 and allowlisted fix exists | Propose → ask approval |
| 0.5–0.75 | Propose only with strong evidence; prefer escalate if evidence thin |
| < 0.5 | Escalate with findings (scores better than wrong fix) |

Never invent evidence. If tool returns empty, say so.

## 6. Safety design

- `KILL_SWITCH=1` env or `data/KILL` file or UI toggle → `execute_action` raises `KillSwitchError`.
- Approval store: in-memory + file append for audit.
- Dry-run: same code path as execute with `transport=NullTransport`.
- Separate API tokens: read tooling needs no Action API write token.

## 7. Testing strategy

1. Unit: schema validation, kill switch, approval blocking.
2. Contract: tools against live Prometheus when demo up.
3. Fixture: offline bundles for brain path without Docker.
4. Golden: 3 practice incidents must produce non-empty evidence arrays.

## 8. Day-of integration points (stubs until kickoff)

| Interface | Stub behaviour | Real behaviour |
|-----------|----------------|----------------|
| `ActionAPIClient` | Log payload, return `{ok: true, stub: true}` | HTTP to organiser Action API |
| `AlertSource` | CLI `inject --incident payment_fail` | Webhook / Prom alert |
| `faultctl` | Documented manual steps | Organiser CLI |
| Report schema | Our draft Pydantic | Replace with official schema file |

## 9. Risks

| Risk | Mitigation |
|------|------------|
| Observability ports not exposed | Ensure `compose.observability.yaml` is in the up command |
| Context overflow from logs | Summarise + top-k; never paste full dump |
| Hallucinated evidence | Evidence must cite tool output IDs; validator rejects free-text-only |
| Merge conflicts | Own packages per role; integrate via graph nodes only |
| Pre-day coding ban | Keep this repo as planning + stubs; real agent code from kickoff per rules |
