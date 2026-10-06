#!/bin/bash
# ==============================================================================
# Comprehensive System Diagnostics Script
# ==============================================================================
# Checks:
# 1. Railway Environment & CLI status
# 2. Hermes Service and API status
# 3. OpenWA Service status
# 4. WhatsApp Web connection state
# 5. Antigravity CLI (agy) installation and authentication state
# 6. Webhook and Message Router end-to-end flow test
# ==============================================================================

set -u

ROUTER_URL="${ROUTER_URL:-http://localhost:8080}"
HERMES_API_URL="${HERMES_API_URL:-http://localhost:8642}"
OPENWA_URL="${OPENWA_URL:-http://localhost:2785}"
OPENWA_KEY="${OPENWA_API_KEY:-}"
HERMES_KEY="${HERMES_API_KEY:-}"

echo "=========================================================="
echo "   HERMES + ANTIGRAVITY + OPENWA SYSTEM DIAGNOSTICS       "
echo "=========================================================="
echo "Timestamp: $(date -u)"
echo ""

# 1. Check Railway CLI Status
echo "[1/6] Checking Railway CLI Status..."
if command -v railway >/dev/null 2>&1; then
    RW_USER=$(railway whoami 2>&1 | tr '\n' ' ' || echo "Not logged in")
    echo "  Railway CLI: INSTALLED (${RW_USER})"
    RW_STATUS=$(railway status 2>&1 | head -n 3 | tr '\n' ' ' || echo "No project linked")
    echo "  Railway Link: ${RW_STATUS}"
else
    echo "  Railway CLI: Not found on local PATH (skipping CLI link check)."
fi

# 2. Check Integration Router & System Health Endpoint
echo ""
echo "[2/6] Checking Integration Router & Health Endpoint..."
HEALTH_RESP=$(curl -s -w "\n%{http_code}" "${ROUTER_URL}/health" 2>/dev/null || echo "000")
HTTP_CODE=$(echo "$HEALTH_RESP" | tail -n1)
BODY=$(echo "$HEALTH_RESP" | head -n -1)

if [ "$HTTP_CODE" = "200" ]; then
    echo "  ✓ Router Health: OK (HTTP 200)"
    echo "  Details:"
    echo "$BODY" | sed 's/^/    /'
else
    echo "  ✗ Router Health: UNHEALTHY (HTTP ${HTTP_CODE})"
fi

# 3. Check Hermes Internal API Server
echo ""
echo "[3/6] Checking Hermes Internal API Server (${HERMES_API_URL})..."
HERMES_CHECK=$(curl -s -w "\n%{http_code}" "${HERMES_API_URL}/health" 2>/dev/null || echo "000")
HERMES_CODE=$(echo "$HERMES_CHECK" | tail -n1)

if [ "$HERMES_CODE" = "200" ]; then
    echo "  ✓ Hermes Core Engine: RUNNING (HTTP 200)"
else
    echo "  ✗ Hermes Core Engine: DOWN or unreachable at ${HERMES_API_URL} (HTTP ${HERMES_CODE})"
fi

# 4. Check Antigravity CLI (agy)
echo ""
echo "[4/6] Checking Antigravity CLI (agy)..."
if command -v agy >/dev/null 2>&1; then
    AGY_VER=$(agy --version 2>/dev/null || echo "error")
    echo "  ✓ agy binary: INSTALLED (${AGY_VER})"
    
    # Check if ~/.gemini/antigravity-cli or token store exists
    if [ -d "$HOME/.gemini/antigravity-cli" ]; then
        echo "  ✓ Antigravity config directory exists (~/.gemini/antigravity-cli)"
        if [ -f "$HOME/.gemini/antigravity-cli/settings.json" ]; then
            echo "  ✓ Antigravity settings.json detected."
        fi
    else
        echo "  ℹ Antigravity config directory not yet created."
    fi
else
    echo "  ℹ agy binary not found in PATH on current host (check inside container)."
fi

# 5. Check OpenWA Service & WhatsApp Connection
echo ""
echo "[5/6] Checking OpenWA Service (${OPENWA_URL})..."
OPENWA_CHECK=$(curl -s -w "\n%{http_code}" "${OPENWA_URL}/" 2>/dev/null || echo "000")
OPENWA_CODE=$(echo "$OPENWA_CHECK" | tail -n1)

if [ "$OPENWA_CODE" != "000" ] && [ "$OPENWA_CODE" != "502" ]; then
    echo "  ✓ OpenWA Gateway: RESPONDING (HTTP ${OPENWA_CODE})"
    # Check session status via OpenWA API
    SESSION_CHECK=$(curl -s -H "X-API-Key: ${OPENWA_KEY}" "${OPENWA_URL}/api/sessions/default/status" 2>/dev/null || echo "{}")
    echo "  Session Info: ${SESSION_CHECK}"
else
    echo "  ✗ OpenWA Gateway: UNREACHABLE at ${OPENWA_URL}"
fi

# 6. Test Synthetic Webhook Flow
echo ""
echo "[6/6] Testing Integration Webhook Ingress (Dry Run)..."
TEST_PAYLOAD='{
  "id": "diag_test_'$(date +%s)'",
  "from": "15551234567@c.us",
  "body": "ping",
  "type": "chat",
  "fromMe": false
}'

WEBHOOK_RESP=$(curl -s -w "\n%{http_code}" -X POST "${ROUTER_URL}/webhook/whatsapp" \
    -H "Content-Type: application/json" \
    -d "$TEST_PAYLOAD" 2>/dev/null || echo "000")
WH_CODE=$(echo "$WEBHOOK_RESP" | tail -n1)
WH_BODY=$(echo "$WEBHOOK_RESP" | head -n -1)

if [ "$WH_CODE" = "200" ]; then
    echo "  ✓ Webhook Ingress: OPERATIONAL (HTTP 200, Response: ${WH_BODY})"
else
    echo "  ✗ Webhook Ingress: FAILED (HTTP ${WH_CODE})"
fi

echo ""
echo "=========================================================="
echo "Diagnostics complete."
echo "=========================================================="
