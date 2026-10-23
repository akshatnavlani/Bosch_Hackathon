# Fault inject & reset runbook (CP0 / CP1 / CP2 demos)

How to inject **one** practice fault into the OpenTelemetry Demo and reset it to healthy.
Used by operators (humans) before a mentor demo. The agent never does this.

> **WARNING — telemetry only.**
> The agent must diagnose from **telemetry only** (metrics, traces, logs, container health).
> Never read feature-flag settings, flagd, or the flag UI to diagnose. Flag access below is
> for a **human operator** injecting the fault, nothing else. Do not give the agent any flag
> data, and do not tell it the answer.

Do **not** modify anything inside `opentelemetry-demo/`. Ports and compose flags are in
[ports.md](ports.md). Day 1 incident IDs are defined in [day1-implementation-plan.md](day1-implementation-plan.md) §0.

## Locked Day 1 practice set

| ID | Flag | Variant | Expected failing service | Use when |
|----|------|---------|--------------------------|----------|
| **P1** | `paymentFailure` | `100%` | `payment` | CP0, CP1, CP2 |
| **P2** | `cartFailure` | `50%` or `100%` | `cart` | CP2 |
| **P3** | `productCatalogFailure` | on (flag default “fail” variant) | `product-catalog` | CP2 |

**Hard rule:** only one of P1/P2/P3 active at a time. Always reset before injecting the next.

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
TO CONFIRM (kickoff): exact faultctl command for P1/P2/P3, e.g.
  faultctl inject paymentFailure
  faultctl reset paymentFailure
```

Paste the real commands here once you have them. Map organiser names to **P1/P2/P3** if they differ.

### Temporary fallback: manual flag UI (only until faultctl is available)

1. Open http://localhost:8080/feature/
2. Set exactly one flag from the table above (e.g. CP1 → `paymentFailure` = `100%`).
3. Save. Write down which ID (P1/P2/P3) you turned on.

Remember the WARNING above: this is for injecting only, never for diagnosis.

## 2. Expected symptoms

Give it 1–2 minutes (with the load generator running), then you should see:

| ID | Shop UI | Prometheus / Jaeger focus |
|----|---------|---------------------------|
| P1 | Checkout / pay fails | Service `payment` (and often `checkout`) error spans / error rate up |
| P2 | Add-to-cart / cart flows fail | Service `cart` error spans / error rate up |
| P3 | Product browse / catalog path fails | Service `product-catalog` error spans / error rate up |

Useful PromQL starting point (confirm label names in your Prometheus):

```promql
sum by (service_name) (rate(traces_span_metrics_calls_total{status_code="STATUS_CODE_ERROR"}[1m]))
```

Jaeger UI: http://localhost:8080/jaeger/ui/ — search the expected service; look for red / error spans.

Docker (`docker ps`): containers may still show "Up". A fault does not always crash a container.

If you see nothing after a few minutes, check that the load generator is running and the fault is really on.

## 3. Reset to healthy

1. Undo the same fault you injected:
   - With `faultctl`: reset that incident.
   - With the manual fallback: set the flag variant back to `off` (or resting default).
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

   For P1/P2/P3 that is typically `payment`, `cart`, or `product-catalog`.

## 4. Mentor demo checklists

### CP0 / CP1 (P1 only)

- [ ] Smoke passes before injecting
- [ ] **P1** injected (`paymentFailure` @ 100%)
- [ ] Symptoms visible in UI and in Prometheus / Jaeger on `payment`
- [ ] Agent run (CP1) uses telemetry tools only
- [ ] **P1** reset; smoke passes again

### CP2 (all three, sequential)

- [ ] **P1** → agent diagnosis JSON → reset
- [ ] **P2** → agent diagnosis JSON → reset
- [ ] **P3** → agent diagnosis JSON → reset
- [ ] Three reports under `reports/` with non-invented evidence
- [ ] Never two faults on at once
