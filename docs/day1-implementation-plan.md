# Day 1 Implementation Plan — Incident Zero

**Scope:** Everything needed through **Checkpoint 2: Brain** (Day 1 wrap ~18:30).  
**Out of scope for Day 1:** Action execute, approval UI polish, verify/rollback (Day 2 / CP3).  
**Repo:** https://github.com/akshatnavlani/Bosch_Hackathon  
**Demo (untouched):** `/root/projects/opentelemetry-demo` on `:8080`

---

## 1. Day 1 outcome (definition of done)

By end of Day 1 the team can demo to a mentor:

1. **CP0:** Demo healthy; inject/reset one fault; LLM key works; repo usable by all 5.
2. **CP1 Eyes:** Agent calls metrics/traces/logs/health tools and summarises **one** practice incident with real citations; architecture one-pager ready.
3. **CP2 Brain:** Agent emits root cause + confidence + evidence for **≥3** practice incidents in (draft or official) JSON schema; low-confidence path escalates instead of inventing evidence.

Minimum bar from organisers: *an agent that uses tools and correctly diagnoses practice incidents with real evidence.*

---

## 2. Timeline (aligned to hackathon milestones)

| Window | Checkpoint | Goal |
|--------|------------|------|
| 11:30–12:00 | Kickoff | Starter kit, Action API docs, schema, faultctl, LLM key |
| 12:00–13:00 | Setup | Demo + load, faultctl, fork/clone, first commits |
| **13:00** | **CP0 Setup** | Mentor confirms setup |
| 13:00–15:30 | Eyes build | Four read tools + investigate loop + symptom summary |
| **15:30** | **CP1 Eyes** | Live run on one incident + architecture sketch |
| 15:30–18:30 | Brain build | Diagnosis node, confidence, schema output, 3+ incidents |
| **18:30** | **CP2 Brain** | Mentor picks ≥3 incidents; correct evidence-backed diagnoses |
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
| CP1 mentor demo | Investigate loop + one injectable incident |
| Diagnosis JSON | Pydantic/schema draft (M5) + tool evidence shape (M2) |
| CP2 mentor demo | Diagnosis node + inject matrix for 3 incidents |

---

## 4. Role ownership (Day 1)

| Seat | Callsign | Day 1 ownership |
|------|----------|-----------------|
| M1 | Platform | Ports doc, compose health, faultctl/inject runbook, 3-incident matrix script |
| M2 | Eyes | `query_metrics`, `query_traces`, `query_logs`, `container_health`, summary shaping |
| M3 | Brain | LLM ping, LangGraph investigate + diagnose, prompts, confidence/escalate |
| M4 | Hands | Action API client stub, `propose_action` / runbook map (no execute) |
| M5 | Ops UX | Skeleton, `.env.example`, architecture one-pager, schema draft, report writer stub, team form |

---

## 5. Work packages by checkpoint

### CP0 — Setup (issues D1-01 … D1-05)

1. Document demo ports + smoke checks.
2. Inject/reset one fault (faultctl or documented temporary path).
3. Bootstrap Python package layout (`pyproject.toml`, empty packages).
4. LLM connectivity smoke test.
5. Team access + team-form stub + everyone can pull `main`.

**Exit:** Mentor opens shop UI, sees failure after inject, healthy after reset; `ping-llm` works.

### CP1 — Eyes (issues D1-06 … D1-13)

1. Four read-only tools with compact return shapes.
2. Alert/session bootstrap writing scratchpad under `reports/sessions/`.
3. Minimal LangGraph (or equivalent) tool loop → symptom summary.
4. Architecture one-pager.
5. Action API stub interface (no writes).

**Exit:** Inject one practice incident → agent prints symptoms with metric/trace/log/health citations.

### CP2 — Brain (issues D1-14 … D1-20)

1. `Diagnosis` model with `evidence[]` that must cite tool outputs.
2. Confidence policy + escalate-when-unsure.
3. Investigate/diagnose prompts (forbid flag cheating).
4. Draft JSON schema validation + markdown report emit.
5. Runbook mapper propose-only.
6. Tool summary tightening (signal vs noise).
7. Automated inject matrix for ≥3 practice incidents.

**Exit:** Mentor-chosen 3 incidents diagnosed with non-invented evidence; schema-valid JSON on disk.

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
| — | **CP1 gate** | Live mentor demo | |
| 14 | D1-16 | Schema draft + validator | after D1-03 |
| 15 | D1-14 | Diagnosis node | after D1-11, D1-16 |
| 16 | D1-15 | Confidence + escalate | after D1-14 |
| 17 | D1-20 | Prompts | parallel with D1-14 |
| 18 | D1-18 | Tighten tool summaries | after D1-11; feeds D1-14 |
| 19 | D1-17 | Runbook propose-only | after D1-13, D1-14 |
| 20 | D1-19 | 3+ incident matrix | after D1-02, D1-14 |
| — | **CP2 gate** | Mentor 3-incident check | |

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

---

## 10. Day 1 deliverables checklist

- [ ] Architecture one-pager (`docs/architecture.md` or whiteboard photo)
- [ ] Working tools + investigate loop
- [ ] ≥3 practice diagnoses with evidence JSON under `reports/`
- [ ] Draft evaluation notes started (`team/evaluation-note.md`)
- [ ] Tag `day1-cp2` on `main`
- [ ] No Action API writes without approval code paths merged yet (Hands stub only)
