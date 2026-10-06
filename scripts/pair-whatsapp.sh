#!/bin/bash
# ==============================================================================
# WhatsApp QR Code Pairing Helper Script
# ==============================================================================
# Connects to OpenWA service to check pairing status or fetch QR code.
# ==============================================================================

set -e

OPENWA_URL="${OPENWA_URL:-http://localhost:2785}"
OPENWA_KEY="${OPENWA_API_KEY:-}"

echo "=== WhatsApp Pairing Assistant ==="
echo "Checking OpenWA status at ${OPENWA_URL}..."

# Check if session is already connected
STATUS_RESP=$(curl -s -H "X-API-Key: ${OPENWA_KEY}" "${OPENWA_URL}/api/sessions/default/status" 2>/dev/null || echo "{}")

if echo "$STATUS_RESP" | grep -q '"status":"isLogged"'; then
    echo "✓ WhatsApp is ALREADY CONNECTED and authenticated!"
    echo "Session is active and persisting on the attached volume."
    exit 0
fi

echo "Session is not yet connected. Retrieving QR Code..."
echo ""
echo "To pair WhatsApp:"
echo "1. Open WhatsApp on your phone."
echo "2. Go to Settings > Linked Devices > Link a Device."
echo "3. Scan the QR code displayed in the OpenWA logs or visit the web dashboard."
echo ""
echo "Fetching latest QR from OpenWA API..."

QR_RESP=$(curl -s -H "X-API-Key: ${OPENWA_KEY}" "${OPENWA_URL}/api/sessions/default/qr" 2>/dev/null || echo "")

if [ -n "$QR_RESP" ]; then
    echo "$QR_RESP"
else
    echo "Please check Railway container logs for the ASCII QR code:"
    echo "railway logs --service openwa"
fi
