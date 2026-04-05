#!/usr/bin/env bash
# Meta-OS v3.2 — end-to-end health check
set -euo pipefail

API="http://localhost:8000"
OBSERVER="http://localhost:8081"
OLLAMA="http://localhost:11434"
N8N="http://localhost:5678"

PASS=0; FAIL=0

check() {
    local name="$1" url="$2" expect="$3"
    local body
    body=$(curl -sf --max-time 5 "$url" 2>/dev/null) || { echo "FAIL  $name ($url unreachable)"; ((FAIL++)); return; }
    if echo "$body" | grep -q "$expect"; then
        echo "OK    $name"
        ((PASS++))
    else
        echo "FAIL  $name (unexpected: $body)"
        ((FAIL++))
    fi
}

echo "=== Meta-OS Health Check ==="
check "API /health"           "$API/health"      '"ok"'
check "Observer /health"      "$OBSERVER/health" '"ok"'
check "Ollama /api/tags"      "$OLLAMA/api/tags"  'models'
check "n8n healthcheck"       "$N8N/healthcheck"  '"status"'

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
