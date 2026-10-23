# Fault inject & reset runbook (CP0 / CP1 demos)

How to inject ONE practice fault into the OpenTelemetry Demo and reset it to healthy.
Used by operators (humans) before a mentor demo. The agent never does this.

> **WARNING — telemetry only.**
> The agent must diagnose from **telemetry only** (metrics, traces, logs, container health).
> Never read feature-flag settings, flagd, or the flag UI to diagnose. Flag access below is
> for a **human operator** injecting the fault, nothing else. Do not give the agent any flag
> data, and do not tell it the answer.

Do **not** modify anything inside `opentelemetry-demo/`. Ports and compose flags are in
[ports.md](ports.md).

## 0. Before you start

1. Start the demo with observability (see [ports.md](ports.md)):

   ```bash
   cd ../opentelemetry-demo
   docker compose -f compose.yaml -f compose.observability.yaml up -d
   ```

2. Check it is healthy:

   ```bash
   ./scripts/smoke_demo.sh
   ```

   Expect `Smoke PASSED`. If it fails, fix that first (see ports.md).

3. Note the time. You will compare "before" and "after" in Prometheus and Jaeger.

## 1. Inject ONE fault

### Preferred: organiser `faultctl`

When the organiser starter kit arrives at kickoff, use `faultctl`.

```text
TO CONFIRM (kickoff): exact faultctl command to list and inject a practice incident, e.g.
  faultctl <inject-command> <incident-name>
```

Paste the real command here once you have it.

### Temporary fallback: manual flag UI (only until faultctl is available)

Use this only if `faultctl` is not available yet.

```text
TO CONFIRM (teammate with a running demo): flag UI address, and the name of ONE practice
fault to turn on (pick one that makes a service fail visibly).
```

Turn on exactly one fault. Write down which one, so you can reset it. Remember the WARNING
above: this is for injecting only, never for diagnosis.

## 2. Expected symptoms

Give it 1–2 minutes (with the load generator running), then you should see:

| Where | What to look for |
|-------|------------------|
| Shop UI (`http://localhost:8080/`) | Errors or failures on some pages or actions (e.g. checkout or product pages) |
| Prometheus (`http://localhost:9090/`) | Error rate for the affected service goes up. Example query (TO CONFIRM metric names in your Prometheus): `sum by (service_name) (rate(traces_span_metrics_calls_total{status_code="STATUS_CODE_ERROR"}[1m]))` |
| Jaeger (`http://localhost:8080/jaeger/ui/`) | Traces for the affected service show error spans |
| Docker (`docker ps`) | Containers may still show "Up". A fault does not always crash a container. |

If you see nothing after a few minutes, check that the load generator is running and the
fault is really on.

## 3. Reset to healthy

1. Undo the same fault you injected:
   - With `faultctl`: use its reset command (TO CONFIRM at kickoff).
   - With the manual fallback: turn the same fault back off.
2. Wait 1–2 minutes, then check:

   ```bash
   ./scripts/smoke_demo.sh
   ```

   Expect `Smoke PASSED`, the shop UI works, and the error rate returns to its normal level.
3. If it is still unhealthy, restart only the affected service:

   ```bash
   cd ../opentelemetry-demo
   docker compose -f compose.yaml -f compose.observability.yaml restart <service>
   ```

## 4. Checklist for a mentor demo

- [ ] Smoke passes before injecting
- [ ] Exactly one fault injected (written down)
- [ ] Symptoms visible in UI and in Prometheus / Jaeger
- [ ] Agent run uses telemetry tools only
- [ ] Fault reset; smoke passes again