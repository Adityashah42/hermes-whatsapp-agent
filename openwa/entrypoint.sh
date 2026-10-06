#!/bin/bash
set -e

echo "=== Starting OpenWA WhatsApp Service ==="

DATA_DIR="${OPENWA_DATA_PATH:-/app/data}"
mkdir -p "$DATA_DIR"
chmod -R 777 "$DATA_DIR" 2>/dev/null || true

if [ ! -f "$DATA_DIR/default.data.json" ]; then
    echo "No saved session data found. Cleaning stale temporary profile..."
    rm -rf "$DATA_DIR/_IGNORE_default"
fi

export PUPPETEER_ARGS="--no-sandbox,--disable-setuid-sandbox,--disable-dev-shm-usage,--disable-gpu"
export CHROME_BIN=/usr/bin/chromium
export PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium
export WA_EXECUTABLE_PATH=/usr/bin/chromium

exec node /app/server.js
