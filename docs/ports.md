# OpenTelemetry Demo — ports & health

How the agent host reaches the Astronomy Shop demo under `../opentelemetry-demo`.  
**Do not modify** files under `opentelemetry-demo/`; this doc is read-only guidance for Incident Zero.

## Start with observability (required for Day 1 Eyes)

Prometheus, Jaeger, Grafana, and OpenSearch are **not** in the base compose file. They come from `compose.observability.yaml`.

```bash
cd ../opentelemetry-demo
docker compose -f compose.yaml -f compose.observability.yaml up -d
```

| Compose files | What you get |
|---------------|--------------|
| `-f compose.yaml` only | Shop UI + services + OTel collector (no Prom/Jaeger/Grafana) |
| `-f compose.yaml -f compose.observability.yaml` | Above **plus** Prometheus, Jaeger, Grafana, OpenSearch |

Defaults below match `../opentelemetry-demo/.env` (do not edit that tree from this repo).

## Key ports (agent host)

| Service | Default port | Agent-host URL | Notes |
|---------|-------------:|----------------|-------|
| Frontend (shop) | **8080** | `http://localhost:8080/` | Via `frontend-proxy` (Envoy). Stable host bind `8080:8080`. |
| Prometheus | **9090** | `http://localhost:9090/` | Needs observability compose. Health: `/-/healthy`. Stable bind `9090:9090`. |
| Jaeger UI | **16686** | `http://localhost:8080/jaeger/ui/` | Needs observability compose. Demo sets Jaeger `base_path: /jaeger/ui`. Prefer Envoy path; direct publish of `16686` may be an ephemeral host port. |
| Grafana | **3000** | `http://localhost:8080/grafana/` | Needs observability compose. Prefer Envoy path; direct `3000` may be ephemeral. |
| OTel collector (gRPC) | **4317** | container / ephemeral host | In **base** `compose.yaml`. Host port often ephemeral (`docker compose port otel-collector 4317`). |
| OTel collector (HTTP) | **4318** | container / ephemeral host | Same as gRPC. Browser OTLP often via proxy: `http://localhost:8080/otlp-http/...`. |

Optional for later Eyes work (logs): OpenSearch defaults to container port **9200** (observability compose; host publish may be ephemeral).

## Smoke check

From this repo:

```bash
./scripts/smoke_demo.sh
```

The script curls the frontend and Prometheus (required), plus Jaeger/Grafana via the Envoy proxy. Non-zero exit on any failure. If Prom/Jaeger/Grafana fail, re-run compose with both `-f` flags above.

## Day 1 constraints

- Do **not** diagnose via feature-flag / flagd APIs.
- Do **not** execute Action API writes (stubs / propose-only only on Day 1).
- Investigation tools should use Prometheus / Jaeger / logs / container health — not flag config.
- Practice injects for Day 1 are only **P1–P3** — see [faultctl-runbook.md](faultctl-runbook.md) and [day1-implementation-plan.md](day1-implementation-plan.md) §0.
