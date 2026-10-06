#!/bin/bash
set -e

echo "=== Starting OpenWA WhatsApp Service ==="

DATA_DIR="${OPENWA_DATA_PATH:-/app/data}"
mkdir -p "$DATA_DIR"

PORT="${OPENWA_PORT:-2785}"
KEY="${OPENWA_API_KEY:-default_secret_key}"
WEBHOOK="${OPENWA_WEBHOOK_URL:-http://hermes:8080/webhook/whatsapp}"

echo "Configuration:"
echo "- Port: $PORT"
echo "- Session Data Path: $DATA_DIR"
echo "- Webhook URL: $WEBHOOK"

# Check if wa-automate or npx is available
if command -v wa-automate >/dev/null 2>&1; then
    exec wa-automate \
        --port "$PORT" \
        --key "$KEY" \
        --webhook "$WEBHOOK" \
        --session-data-path "$DATA_DIR" \
        --multi-device \
        --headless \
        --config /app/config/wa.config.json
else
    exec npx --yes @open-wa/wa-automate \
        --port "$PORT" \
        --key "$KEY" \
        --webhook "$WEBHOOK" \
        --session-data-path "$DATA_DIR" \
        --multi-device \
        --headless \
        --config /app/config/wa.config.json
fi
