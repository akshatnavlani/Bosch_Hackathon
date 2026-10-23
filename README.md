# Incident Zero — AI On-Call Engineer

Team planning + agent repo for the Bosch / PES **Incident Zero** hackathon.

**GitHub:** https://github.com/akshatnavlani/Bosch_Hackathon  
**Demo under test (do not modify):** `../opentelemetry-demo` (frontend `:8080`)

## What we are building

An agent that does the first hour of on-call work on the OpenTelemetry Astronomy Shop:

**Detect → Investigate → Diagnose → Propose → Get Approval → Act → Report**

It must reason from **telemetry** (metrics, traces, logs, container health), propose fixes only via the organiser **Action API**, and never act without **human approval** (plus dry-run + kill switch).

## Docs (local)

| Doc | Path |
|-----|------|
| PRD | [docs/PRD.md](docs/PRD.md) |
| Architecture | [docs/architecture.md](docs/architecture.md) |
| Architecture one-pager (CP1) | [docs/architecture-one-pager.md](docs/architecture-one-pager.md) |
| Design + stack + repo layout | [docs/design.md](docs/design.md) |
| Checkpoints + 5-person roles | [docs/checkpoints.md](docs/checkpoints.md) |
| Day 1 implementation plan | [docs/day1-implementation-plan.md](docs/day1-implementation-plan.md) |
| Demo ports + compose flags | [docs/ports.md](docs/ports.md) |
| Demo health smoke | [scripts/smoke_demo.sh](scripts/smoke_demo.sh) (`./scripts/smoke_demo.sh`) |
| Fault inject/reset (P1–P3) | [docs/faultctl-runbook.md](docs/faultctl-runbook.md) |

## Issues

Day 1 work is tracked on:  
https://github.com/akshatnavlani/Bosch_Hackathon/issues

## Contributing / CI

`main` is **protected**: no direct pushes. Open a PR; the **`ci`** check (lint + tests + secret/actions guards) must pass and at least one review is required. See [docs/branch-protection.md](docs/branch-protection.md).

```bash
pip install -e ".[dev]"
ruff check . && ruff format --check . && pytest -q
```

## Status

- OpenTelemetry Demo cloned and reachable on port **8080** (use observability compose; see ports doc).
- **Day 1 practice set:** P1 `paymentFailure`, P2 `cartFailure`, P3 `productCatalogFailure` (see Day 1 plan §0).
- Agent demos: **CP1** = P1 only; **CP2** = P1→P2→P3 sequential (reset between).
- Action API / faultctl / official JSON schema: integrate day-of when starter kit arrives; adapters are stubbed until then.
