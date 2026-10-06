#!/bin/bash
# ==============================================================================
# Health Check Script
# ==============================================================================
set -e

ROUTER_URL="${ROUTER_URL:-http://localhost:8080}"
OPENWA_URL="${OPENWA_URL:-http://localhost:2785}"

echo "=== Querying System Health ==="
echo "1. Checking Hermes & Router Health at ${ROUTER_URL}/health..."

if curl -s -f "${ROUTER_URL}/health" > /tmp/health.json 2>/dev/null; then
    echo "✓ Hermes & Integration Router is HEALTHY!"
    if command -v jq >/dev/null 2>&1; then
        jq . /tmp/health.json
    else
        cat /tmp/health.json
    fi
else
    echo "✗ Failed to query ${ROUTER_URL}/health. Service may still be starting or unreachable."
fi

echo ""
echo "2. Checking OpenWA Service at ${OPENWA_URL}..."
if curl -s -f -I "${OPENWA_URL}/" 2>/dev/null | grep -q "HTTP"; then
    echo "✓ OpenWA HTTP listener is ACTIVE!"
else
    echo "✗ Failed to reach OpenWA at ${OPENWA_URL}."
fi

echo "==============================="
