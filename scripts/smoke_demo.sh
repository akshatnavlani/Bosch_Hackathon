#!/usr/bin/env bash
# Smoke-check OpenTelemetry Demo endpoints from the agent host.
# See docs/ports.md for compose flags and port table.
set -euo pipefail

FRONTEND_URL="${FRONTEND_URL:-http://localhost:8080/}"
PROMETHEUS_URL="${PROMETHEUS_URL:-http://localhost:9090/-/healthy}"
JAEGER_URL="${JAEGER_URL:-http://localhost:8080/jaeger/ui/}"
GRAFANA_URL="${GRAFANA_URL:-http://localhost:8080/grafana/}"
CURL_OPTS=(--silent --show-error --fail --max-time 5 --connect-timeout 3 -o /dev/null -w "%{http_code}")

OBS_HINT="Start demo with: docker compose -f compose.yaml -f compose.observability.yaml up -d (from ../opentelemetry-demo)"

failed=0

check() {
  local name="$1"
  local url="$2"
  local hint="${3:-}"
  local code
  if code="$(curl "${CURL_OPTS[@]}" "$url" 2>/dev/null)"; then
    echo "PASS  ${name}  (${url})  HTTP ${code}"
  else
    echo "FAIL  ${name}  (${url})"
    if [[ -n "$hint" ]]; then
      echo "      ${hint}"
    fi
    failed=1
  fi
}

echo "Incident Zero — demo smoke checks"
echo "---------------------------------"

check "frontend" "$FRONTEND_URL" "Is frontend-proxy up on :8080? (base compose.yaml)"
check "prometheus" "$PROMETHEUS_URL" "${OBS_HINT}"
check "jaeger (via proxy)" "$JAEGER_URL" "${OBS_HINT}"
check "grafana (via proxy)" "$GRAFANA_URL" "${OBS_HINT}"

# Collector host ports are often ephemeral; do not fail the smoke on them.
echo "SKIP  otel-collector host ports (4317/4318 often ephemeral; see docs/ports.md)"

if [[ "$failed" -ne 0 ]]; then
  echo "---------------------------------"
  echo "Smoke FAILED — see docs/ports.md"
  exit 1
fi

echo "---------------------------------"
echo "Smoke PASSED"
exit 0
