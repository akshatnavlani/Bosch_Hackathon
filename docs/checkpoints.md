# Checkpoint Plan & Role Split (5 members)

## Role map

| Seat | Callsign | Owns | Primary packages |
|------|----------|------|------------------|
| M1 | **Platform** | Demo health, compose, faultctl, env, CI smoke | `scripts/`, `.env`, demo runbook |
| M2 | **Eyes** | Metrics / traces / logs / health tools | `agent/tools/` |
| M3 | **Brain** | LangGraph, prompts, diagnosis, confidence | `agent/graph.py`, `prompts/` |
| M4 | **Hands** | Action API, approval, dry-run, kill switch, verify | `agent/adapters/`, `agent/safety/` |
| M5 | **Ops UX** | Operator UI, reporting schema, README, team form, eval note | `ui/`, `reporting/`, `team/`, docs |

Everyone must land ≥1 meaningful commit on the day (rules).

---

## Day 1 practice incidents (locked)

| ID | Flag | Expected failing service | Mentor slot |
|----|------|--------------------------|-------------|
| **P1** | `paymentFailure` @ 100% | `payment` | CP0 + CP1 + CP2 |
| **P2** | `cartFailure` @ 50–100% | `cart` | CP2 |
| **P3** | `productCatalogFailure` | `product-catalog` | CP2 |

See [day1-implementation-plan.md](day1-implementation-plan.md) §0 and [faultctl-runbook.md](faultctl-runbook.md). One fault at a time; reset between runs.

## Day 1

### Checkpoint 0 — Setup (by 13:00) — **10 min mentor gate**

**Outcome:** Demo + load running; inject/reset **P1** works; LLM key works; repo forked; all members committed once.

| Owner | Tasks |
|-------|-------|
| M1 | Demo up, ports documented, inject/reset **P1** via faultctl (or runbook fallback) |
| M5 | Fork template (day-of), invite team, protect main lightly |
| All | Clone, venv, first empty commit / team form stub |

**Exit criteria:** Mentor can open `:8080`, see checkout/payment failure after **P1**, healthy after reset.

---

### Checkpoint 1 — Eyes (by 15:30) — **10 pts**

**Outcome:** Tools for logs, metrics, traces, container health; agent summarises symptoms of **P1** (`paymentFailure`); 1-page architecture sketch.

| Owner | Tasks |
|-------|-------|
| M2 | Implement 4 read tools + unit tests with live or fixture data |
| M3 | Wire tool loop that calls tools and prints symptom summary (even if diagnosis naive) |
| M5 | Architecture sketch (photo or `docs/architecture.md`) |
| M1 | Keep demo stable; PromQL examples for payment/checkout error rate |
| M4 | Stub Action API client (no execute yet) |

**Exit criteria:** Live run: inject **P1** → agent prints `payment`-path symptoms with real metric/trace/log citations.

**First agent demo:** after Eyes loop works (~15:30). Show **P1 only**.

---

### Checkpoint 2 — Brain (by 18:30) — **20 pts**

**Outcome:** Root cause + evidence + confidence; schema-valid JSON for **P1, P2, and P3**.

| Owner | Tasks |
|-------|-------|
| M3 | Diagnosis node, confidence policy, escalate path |
| M2 | Tighten tool summaries so brain gets signal not noise |
| M5 | Schema validation + sample reports folder |
| M4 | Runbook mapper propose-only (payment / cart / product-catalog) |
| M1 | Scripted inject matrix: **P1 → reset → P2 → reset → P3** |

**Exit criteria:** Sequential demos **P1 → P2 → P3** (reset between); non-invented evidence each time.

**Day 1 wrap:** Tag `day1-checkpoint2`; no big refactors overnight.

---

## Day 2

### Checkpoint 3 — Hands (by 12:00) — **20 pts**

**Outcome:** Allowlisted action proposed; approval gate; execute; recovery verified; dry-run + kill switch; incident report; action log.

| Owner | Tasks |
|-------|-------|
| M4 | Approval UX hook, kill switch, dry-run, execute, rollback, verify |
| M3 | Connect propose→approve→act edges in graph |
| M5 | Operator UI approve/reject/kill + report renderer |
| M2 | Health/metrics checks for verifier |
| M1 | End-to-end script: inject → run agent → reset |

**Exit criteria:** One full alert→verified recovery demo with action log.

---

### Harden & submit (12:00–14:00)

No new features. Fix bugs, clean run from scratch, README, evaluation note, team form, schema compliance.

**Code freeze:** 14:00 Day 2 (confirm with organisers if slides conflict).

### Checkpoint 4 — Hidden test (14:00–15:30) — **30 pts**

Organisers run unseen incidents. Prefer escalate-when-unsure over wrong confident fixes.

---

## Parallel workstreams (who unblocks whom)

```
M1 (demo) ──▶ M2 (tools) ──▶ M3 (brain)
                  │              │
                  └────▶ M4 (hands) ◀── M5 (UI/schema)
```

Critical path: **M2 tools → M3 brain → M4 hands**.  
M5 can build UI against fake events from hour 1.

## Stretch (only after CP3 green)

1. Incident memory store  
2. Reviewer agent (devil’s advocate)  
3. Chat-style approval polish  
4. Calibrated confidence chart on practice set  
5. Prevention suggestions in report  
