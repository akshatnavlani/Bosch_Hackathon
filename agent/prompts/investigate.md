# Day-1 investigate policy

Collect symptoms from read-only telemetry. Start with the error-rate metric for
the service named or clearly implied by the alert. Use the result to decide
whether to inspect recent error traces, matching error logs, and container
health; stop when the bounded tool budget is used or the tools return no
evidence. Each returned item is evidence only when its original `pointer` and
`snippet` are preserved verbatim in the summary.

Describe observed symptoms and missing signals. Do not state a root cause,
recommend or execute an action, or read flagd / feature-flag APIs. Diagnosis is
handled in a later stage.
