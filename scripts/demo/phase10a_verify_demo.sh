#!/usr/bin/env bash
# Phase 10A — local demo verification (core profile).
# Writes a brief health summary to docs/evidence/phase10/demo/.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
EVIDENCE_DIR="${ROOT}/docs/evidence/phase10/demo"
API_PORT="${API_PORT:-8000}"
DASHBOARD_PORT="${DASHBOARD_PORT:-3000}"
API_BASE="http://localhost:${API_PORT}"
DASHBOARD_URL="http://localhost:${DASHBOARD_PORT}"
ASSUME_UP="${ASSUME_UP:-false}"
TIMESTAMP="$(date -u +"%Y%m%d-%H%M%S")"
OUTPUT="${EVIDENCE_DIR}/health-check-${TIMESTAMP}.log"
SUMMARY="${EVIDENCE_DIR}/commands-summary.md"

mkdir -p "${EVIDENCE_DIR}"

log() { echo "$@" | tee -a "${OUTPUT}"; }

CRITICAL_FAIL=0
WARN_COUNT=0

check_http() {
  local name="$1"
  local url="$2"
  local critical="${3:-true}"
  local code
  code="$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "${url}" 2>/dev/null || echo "000")"
  if [[ "${code}" =~ ^2 ]]; then
    log "PASS ${name}: ${url} -> HTTP ${code}"
    return 0
  fi
  if [[ "${critical}" == "true" ]]; then
    log "FAIL ${name}: ${url} -> HTTP ${code}"
    CRITICAL_FAIL=$((CRITICAL_FAIL + 1))
  else
    log "WARN ${name}: ${url} -> HTTP ${code} (optional)"
    WARN_COUNT=$((WARN_COUNT + 1))
  fi
  return 1
}

log "=== AXON Phase 10A Demo Verification ==="
log "Timestamp (UTC): ${TIMESTAMP}"
log "Git SHA: $(git -C "${ROOT}" rev-parse HEAD 2>/dev/null || echo unknown)"
log "Branch: $(git -C "${ROOT}" branch --show-current 2>/dev/null || echo unknown)"
log "API_BASE: ${API_BASE}"
log "DASHBOARD_URL: ${DASHBOARD_URL}"
log ""

log "--- Docker Compose config (core) ---"
if docker compose --profile core config >/dev/null 2>&1; then
  log "PASS: docker compose --profile core config"
else
  log "FAIL: docker compose --profile core config"
  CRITICAL_FAIL=$((CRITICAL_FAIL + 1))
fi

if [[ "${ASSUME_UP}" != "true" ]]; then
  log ""
  log "--- Starting core profile (detached) ---"
  docker compose --profile core up -d --build 2>&1 | tee -a "${OUTPUT}" || {
    log "FAIL: docker compose up"
    CRITICAL_FAIL=$((CRITICAL_FAIL + 1))
  }
  log "Waiting 45s for warm-up..."
  sleep 45
fi

log ""
log "--- Container status ---"
docker compose --profile core ps 2>&1 | tee -a "${OUTPUT}" || true

log ""
log "--- Health endpoints ---"
check_http "health" "${API_BASE}/health"
check_http "health_live" "${API_BASE}/health/live"
check_http "health_ready" "${API_BASE}/health/ready"
check_http "status_services" "${API_BASE}/status/services"
check_http "telemetry_status" "${API_BASE}/telemetry/status"
check_http "model_scores_status" "${API_BASE}/model-scores/status"
check_http "mission_status" "${API_BASE}/mission/status" false
check_http "twin_status" "${API_BASE}/api/v1/twin/status" false
check_http "nav_slam_status" "${API_BASE}/api/v1/nav-slam/status" false
check_http "metrics" "${API_BASE}/metrics" false
check_http "openapi" "${API_BASE}/openapi.json" false
check_http "dashboard" "${DASHBOARD_URL}/" 

log ""
log "--- Sample payloads ---"
for ep in health telemetry/status model-scores/status mission/status; do
  log "--- GET /${ep} ---"
  curl -s --connect-timeout 5 "${API_BASE}/${ep}" 2>/dev/null | head -c 2000 | tee -a "${OUTPUT}" || log "WARN: could not fetch /${ep}"
  log ""
done

log ""
log "=== Summary ==="
log "Critical failures: ${CRITICAL_FAIL}"
log "Warnings: ${WARN_COUNT}"

cat > "${SUMMARY}" <<EOF
# Phase 10A Commands Summary

Generated: ${TIMESTAMP} UTC  
Git SHA: \`$(git -C "${ROOT}" rev-parse HEAD 2>/dev/null || echo unknown)\`  
Branch: \`$(git -C "${ROOT}" branch --show-current 2>/dev/null || echo unknown)\`

## Verification run

\`\`\`bash
bash scripts/demo/phase10a_verify_demo.sh
# or skip re-up if stack already running:
ASSUME_UP=true bash scripts/demo/phase10a_verify_demo.sh
\`\`\`

## Latest health log

\`${OUTPUT#${ROOT}/}\`

## Result

- Critical failures: **${CRITICAL_FAIL}**
- Warnings: **${WARN_COUNT}**
EOF

if [[ "${CRITICAL_FAIL}" -gt 0 ]]; then
  log "OVERALL: FAIL"
  exit 1
fi

log "OVERALL: PASS"
exit 0
