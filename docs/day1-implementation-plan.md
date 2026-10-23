# Day 1 Implementation Plan — Incident Zero

**Scope:** Everything needed through **Checkpoint 2: Brain** (Day 1 wrap ~18:30).  
**Out of scope for Day 1:** Action execute, approval UI polish, verify/rollback (Day 2 / CP3).  
**Repo:** https://github.com/akshatnavlani/Bosch_Hackathon  
**Demo (untouched):** `/root/projects/opentelemetry-demo` on `:8080`

---

## 0. Practice incident set (Day 1 — locked)

Day 1 Eyes + Brain work **only** these three injectable faults. Do not expand the practice set today (other flags are stretch / Day 2 / hidden-test risk).

| ID | Inject flag (human / faultctl) | Failing service (expected) | CP use |
|----|--------------------------------|----------------------------|--------|
| **P1** | `paymentFailure` @ **100%** | `payment` (checkout path) | **CP0 + CP1** hero; also in CP2 matrix |
| **P2** | `cartFailure` @ **50–100%** | `cart` | CP2 matrix |
| **P3** | `productCatalogFailure` | `product-catalog` | CP2 matrix |

**Rules**

- Operator injects via [faultctl-runbook.md](faultctl-runbook.md) (or flag UI until `faultctl` arrives).
- Agent diagnoses from **telemetry only** — never reads flagd / flag UI.
- Same four tools for all three; evidence must name the right `service`.
- Always **reset** the fault after each run before injecting the next.

**Defer (not Day 1 focus):** `emailMemoryLeak`, `adHighCpu`, Kafka/fraud lag, AI-agent flags, multi-flag chaos.

---

## 1. Day 1 outcome (definition of done)

By end of Day 1 the team can demo to a mentor:

1. **CP0:** Demo healthy; inject/reset **P1** (`paymentFailure`); LLM key works; repo usable by all 5.
2. **CP1 Eyes:** Agent summarises **P1** with real metric/trace/log/health citations; architecture one-pager ready.
3. **CP2 Brain:** Agent emits root cause + confidence + evidence for **P1, P2, and P3** (schema-valid JSON); low-confidence path escalates instead of inventing evidence.

Minimum bar from organisers: *an agent that uses tools and correctly diagnoses practice incidents with real evidence.*

---

## 2. Timeline (aligned to hackathon milestones)

| Window | Checkpoint | Goal |
|--------|------------|------|
| 11:30–12:00 | Kickoff | Starter kit, Action API docs, schema, faultctl, LLM key |
| 12:00–13:00 | Setup | Demo + load, faultctl, fork/clone, first commits |
| **13:00** | **CP0 Setup** | Mentor confirms setup — inject/reset **P1** |
| 13:00–15:30 | Eyes build | Four read tools + investigate loop + symptom summary |
| **15:30** | **CP1 Eyes** | Live agent on **P1** only + architecture sketch |
| 15:30–18:30 | Brain build | Diagnosis + confidence + schema; matrix for **P1–P3** |
| **18:30** | **CP2 Brain** | Sequential demos: **P1 → reset → P2 → reset → P3** |
| 18:45 | Wrap | Tag `day1-cp2`; no big refactors overnight |

If coding is only allowed from the official start time, treat pre-day work as **planning + stubs only** and land real tool/agent code after kickoff.

---

## 3. Critical path

```
M1 demo/ports/faultctl
        ↓
M2 tools (metrics → traces → logs → health)
        ↓
M3 investigate loop → diagnosis + confidence + prompts
        ↓
M5 schema validate + architecture + reports folder
        ↘
M4 Action API stub + runbook propose-only (unblocks Day 2 Hands)
```

**Hard blockers**

| Work | Blocked until |
|------|----------------|
| Live Prom/Jaeger tools | Observability endpoints reachable (M1) |
| Investigate loop | At least metrics + one other tool |
| CP1 mentor demo | Investigate loop + **P1** (`paymentFailure`) injectable |
| Diagnosis JSON | Pydantic/schema draft (M5) + tool evidence shape (M2) |
| CP2 mentor demo | Diagnosis node + inject matrix for **P1–P3** |

---

## 4. Role ownership (Day 1)

| Seat | Callsign | Day 1 ownership |
|------|----------|-----------------|
| M1 | Platform | Ports doc, compose health, faultctl/inject runbook for **P1–P3**, matrix script |
| M2 | Eyes | `query_metrics`, `query_traces`, `query_logs`, `container_health`, summary shaping |
| M3 | Brain | LLM ping, LangGraph investigate + diagnose, prompts, confidence/escalate |
| M4 | Hands | Action API client stub, `propose_action` / runbook map (no execute) |
| M5 | Ops UX | Skeleton, `.env.example`, architecture one-pager, schema draft, report writer stub, team form |

---

## 5. Work packages by checkpoint

### CP0 — Setup (issues D1-01 … D1-05)

1. Document demo ports + smoke checks.
2. Inject/reset **P1** (`paymentFailure` @ 100%) via faultctl or [faultctl-runbook.md](faultctl-runbook.md).
3. Bootstrap Python package layout (`pyproject.toml`, empty packages).
4. LLM connectivity smoke test.
5. Team access + team-form stub + everyone can pull `main`.

**Exit:** Mentor opens shop UI, sees checkout/payment failure after **P1** inject, healthy after reset; `ping-llm` works.

### CP1 — Eyes (issues D1-06 … D1-13)

1. Four read-only tools with compact return shapes.
2. Alert/session bootstrap writing scratchpad under `reports/sessions/`.
3. Minimal LangGraph (or equivalent) tool loop → symptom summary.
4. Architecture one-pager.
5. Action API stub interface (no writes).

**Exit:** Inject **P1** → agent prints symptoms citing `payment` / checkout-path telemetry (not flag names).

### CP2 — Brain (issues D1-14 … D1-20)

1. `Diagnosis` model with `evidence[]` that must cite tool outputs.
2. Confidence policy + escalate-when-unsure.
3. Investigate/diagnose prompts (forbid flag cheating).
4. Draft JSON schema validation + markdown report emit.
5. Runbook mapper propose-only (map P1→payment, P2→cart, P3→product-catalog).
6. Tool summary tightening (signal vs noise).
7. Automated inject matrix for **P1, P2, P3** only (`D1-19`).

**Exit:** Sequential mentor runs on **P1 → P2 → P3** (reset between each); schema-valid JSON under `reports/` for all three.

---

## 6. Suggested implementation order (issue sequence)

Execute roughly in this order; parallelise only where noted.

| Order | ID | Title | Parallel OK? |
|------:|----|-------|--------------|
| 1 | D1-01 | Ports + health smoke | with D1-03, D1-05 |
| 2 | D1-03 | Python skeleton | with D1-01 |
| 3 | D1-05 | Team form / access | anytime early |
| 4 | D1-04 | LLM ping | after D1-03 |
| 5 | D1-02 | Inject/reset runbook | after D1-01 |
| 6 | D1-06 | `query_metrics` | after D1-01, D1-03 |
| 7 | D1-07 | `query_traces` | after D1-06 |
| 8 | D1-08 | `query_logs` | parallel with D1-07 |
| 9 | D1-09 | `container_health` | parallel with D1-07 |
| 10 | D1-10 | Alert/session bootstrap | after D1-03 |
| 11 | D1-13 | Action API stub | after D1-03; parallel Eyes |
| 12 | D1-11 | Investigate loop / symptom summary | after D1-06 + one of 07–09 + D1-10 + D1-04 |
| 13 | D1-12 | Architecture one-pager | parallel anytime after skeleton |
| — | **CP1 gate** | Live mentor demo on **P1** only | |
| 14 | D1-16 | Schema draft + validator | after D1-03 |
| 15 | D1-14 | Diagnosis node | after D1-11, D1-16 |
| 16 | D1-15 | Confidence + escalate | after D1-14 |
| 17 | D1-20 | Prompts | parallel with D1-14 |
| 18 | D1-18 | Tighten tool summaries | after D1-11; feeds D1-14 |
| 19 | D1-17 | Runbook propose-only | after D1-13, D1-14 |
| 20 | D1-19 | Inject matrix for **P1–P3** | after D1-02, D1-14 |
| — | **CP2 gate** | Sequential **P1 → P2 → P3** mentor check | |

---

## 7. Technical contracts to implement on Day 1

### IncidentState (minimal)

- `incident_id`, `alert`, `scratchpad[]`, `diagnosis?`, `proposal?`, `kill_switch=False`
- No execute/approval UI required until Day 2

### Tool return shape

Every tool returns:

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

Diagnosis evidence **must** copy `pointer`/`snippet` from tool `items` — never free-invent.

### Confidence policy (Day 1)

| Confidence | Behaviour |
|------------|-----------|
| ≥ 0.75 | Emit diagnosis + optional propose |
| 0.5–0.75 | Diagnosis allowed; prefer escalate if evidence thin |
| < 0.5 | Escalate with findings (correct outcome) |

### Explicit non-goals Day 1

- Calling Action API write endpoints
- Reading flagd / flag UI for diagnosis
- Operator Streamlit polish
- Hidden-test hardening beyond “no flag reads” in prompts
- Practice faults outside **P1–P3**

---

## 7b. Demo protocol (when / how)

| When | What you can show | Incidents | How |
|------|-------------------|-----------|-----|
| **CP0 (~13:00)** | Demo + inject/reset only (no agent required) | **P1** | Human inject → shop breaks → reset |
| **CP1 (~15:30)** | Working Eyes agent (symptoms + citations) | **P1** only | Inject P1 → run agent → show citations → reset |
| **CP2 (~18:30)** | Working Brain (diagnosis JSON + confidence) | **P1, then P2, then P3** | **One at a time:** inject → agent → save report → **reset** → next |
| Overnight / Day 2 | Full Hands loop | Prefer one of P1–P3 first | After approve/act/verify exists |

**Always go by each incident separately** at CP2: never leave two faults on at once. Mentors need a clean signal per service (`payment` vs `cart` vs `product-catalog`).

Internal dry-run before CP2: scripted matrix runs P1→P2→P3 offline or live and writes three JSON files under `reports/`.

---

## 8. Integration with organiser starter kit (day-of)

When kickoff materials arrive, swap in this order (do not block Eyes waiting for perfect Action API):

1. Official JSON schema → replace `schemas/` draft.
2. `faultctl` → replace manual inject notes in D1-02/D1-19.
3. Action API base URL → fill `ActionAPIClient` stub (still no execute until Day 2 unless mentor asks).
4. Template README sections → merge into ours without deleting architecture/PRD.

---

## 9. Risks & mitigations (Day 1)

| Risk | Mitigation |
|------|------------|
| Jaeger/Grafana not up | Ensure `compose.observability.yaml`; M1 smoke script fails loud |
| Context overflow | Cap tool `items` to top-k; summaries only |
| Hallucinated evidence | Validator: evidence pointers must appear in scratchpad |
| Merge conflicts | One package owner; branch per issue; short PRs |
| Demo RAM pressure | Prefer minimal/observability profiles; document on 8GB machines |
| Wrong service blamed | Practice only P1–P3; require `service` in tool evidence to match diagnosis component |
| Overlapping faults | Hard rule: one fault active; reset before next inject |

---

## 10. Day 1 deliverables checklist

- [ ] Architecture one-pager (`docs/architecture.md` or whiteboard photo)
- [ ] Working tools + investigate loop
- [ ] Diagnoses for **P1, P2, P3** with evidence JSON under `reports/`
- [ ] Inject/reset runbook covers P1–P3 ([faultctl-runbook.md](faultctl-runbook.md))
- [ ] Draft evaluation notes started (`team/evaluation-note.md`)
- [ ] Tag `day1-cp2` on `main`
- [ ] No Action API writes without approval code paths merged yet (Hands stub only)
