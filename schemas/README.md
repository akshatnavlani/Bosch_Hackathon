# Incident report schemas

`incident_report.schema.json` is a **Day-1 draft** used by `agent.reporting.schema_validate` and CP2 report checks.

At kickoff, the **organiser official schema replaces this draft**. Drop their file in place of `incident_report.schema.json` (same path); the validator loads that path and does not hard-code field names beyond what the schema file declares.
