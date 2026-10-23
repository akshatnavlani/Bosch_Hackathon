# PRD — Incident Zero: AI On-Call Engineer

**Product:** AI On-Call Engineer agent for the OpenTelemetry Demo (Astronomy Shop)  
**Event:** Bosch / PES University AI hackathon  
**Team size:** 5  
**Success metric:** Full Detect → Report loop on practice + unseen incidents, scored via organiser JSON schema

---

## 1. Problem

When a cloud-native app fails, the first hour of on-call work is mostly searching: logs, metrics, traces, recent deploys. Humans are slow at correlation under pressure. We will build an agent that does that first hour — investigate, diagnose with evidence, propose a safe fix, wait for approval, act, verify, report.

## 2. Goals

| Priority | Goal |
|----------|------|
| P0 | Detect an alert and start investigation automatically |
| P0 | Tool-calling agent over traces, metrics, logs, container health |
| P0 | Root cause + confidence + real evidence (no invented evidence) |
| P0 | Propose only allowlisted Action API remedies |
| P0 | Human approval gate, dry-run mode, kill switch |
| P0 | Execute, verify recovery, rollback/escalate on failure |
| P0 | Emit incident report matching organiser JSON schema |
| P1 | Correct diagnosis on ≥3 practice incidents (CP2) |
| P1 | Full loop alert→recovery on ≥1 incident (CP3) |
| P2 | Stretch: incident memory, reviewer agent, chat approval UI, calibrated confidence |

## 3. Non-goals / constraints

- Do **not** edit OpenTelemetry Demo source or config.
- Do **not** read feature-flag settings / flagd / flag UI to diagnose.
- Do **not** change the system except via Action API after explicit human yes.
- Do **not** hard-code answers to practice incidents.
- Everything runs on the team laptop; no shared infra.
- Diagnosis must come from telemetry only.

## 4. Users

| Persona | Need |
|---------|------|
| On-call human (demo judge / mentor) | See diagnosis + plan, approve/reject, kill switch |
| Scoring harness | Valid JSON schema output per incident |
| Mentors at checkpoints | Live demo of eyes / brain / hands |

## 5. Functional requirements

1. **Alert ingest** — Subscribe to or poll error-rate / latency threshold signals from demo metrics (Prometheus or organiser alert hook).
2. **Investigation loop** — LLM chooses next tool based on prior results (ReAct / tool-calling), not one giant dump.
3. **Tools (read-only)** — Query traces (Jaeger/OTLP store), metrics (Prometheus), logs (OpenSearch/collector), container health (Docker API or organiser helper).
4. **Diagnosis** — Failing component, cause hypothesis, confidence ∈ [0,1], evidence pointers (trace IDs, log lines, metric queries/values).
5. **Low confidence** — Escalate with findings; do not force a fix.
6. **Proposal** — Map diagnosis → allowlisted Action API action + short reason.
7. **Approval UX** — CLI and/or simple web/chat UI; block until yes/no; dry-run shows intended call without executing.
8. **Act + verify** — Call Action API; re-check health metrics; on fail → rollback action if available + escalate.
9. **Report** — Timeline, root cause, evidence, action, prevention note; schema-compliant JSON + human-readable copy.
10. **Kill switch** — Global halt that prevents any further Action API writes.

## 6. Non-functional requirements

- Latency: investigation usable within a few minutes per practice incident.
- Safety: no write path bypasses approval; all actions logged.
- Honesty: evaluation note lists wins/losses.
- Reproducibility: README with setup, env vars, how to run dry-run / kill switch.
- Parallelism: 5 people can work on separate packages without merge hell.

## 7. Deliverables (code freeze)

1. Source code + README  
2. Architecture overview (1 page)  
3. Incident reports (schema + readable)  
4. Evaluation note  
5. Team form (members, ownership, models, AI assistants declared)

## 8. Scoring alignment

| Area | Points | Product implication |
|------|-------:|---------------------|
| CP1 Eyes | 10 | Tools + symptom summary must work live |
| CP2 Brain | 20 | Evidence-backed diagnosis on ≥3 incidents |
| CP3 Hands | 20 | Full approve→act→verify loop + action log |
| CP4 Hidden | 30 | Generalise; no flag cheating; escalate when unsure |
| Judges | 20 | Safety, tool use, explainability, honesty, demo |

## 9. Assumptions (confirm at kickoff)

- Organisers provide: Action API, faultctl, template repo, JSON schema, LLM key, practice incidents.
- Until then we stub Action API + alert webhook interfaces behind adapters.
- OTel Demo already running locally (`:8080`); observability stack may need `compose.observability.yaml` if Jaeger/Grafana not up.
