#!/bin/bash
set -e

echo "=== Starting Hermes Agent + Antigravity Integration ==="

DATA_DIR="${HERMES_DATA_PATH:-/opt/data}"
mkdir -p "$DATA_DIR/.hermes"
mkdir -p "$DATA_DIR/.gemini"
mkdir -p "$DATA_DIR/router"
mkdir -p "$DATA_DIR/skills"

# Symlink persistent storage for Antigravity CLI (~/.gemini)
if [ ! -L "/root/.gemini" ]; then
    rm -rf /root/.gemini
    ln -s "$DATA_DIR/.gemini" /root/.gemini
fi

if id -u hermes >/dev/null 2>&1; then
    mkdir -p /home/hermes
    if [ ! -L "/home/hermes/.gemini" ]; then
        rm -rf /home/hermes/.gemini
        ln -s "$DATA_DIR/.gemini" /home/hermes/.gemini
    fi
    chown -R hermes:hermes "$DATA_DIR" || true
fi

# Link Antigravity CLI skill into Hermes skills directory
if [ -d "/opt/hermes/skills/antigravity-cli" ]; then
    mkdir -p "$DATA_DIR/skills/antigravity-cli"
    cp -r /opt/hermes/skills/antigravity-cli/* "$DATA_DIR/skills/antigravity-cli/" || true
fi

# Ensure Hermes configuration has API Server enabled
HERMES_ENV_FILE="$DATA_DIR/.hermes/.env"
touch "$HERMES_ENV_FILE"

# Export / write required internal config
if [ -n "$HERMES_API_KEY" ]; then
    grep -q "API_SERVER_KEY=" "$HERMES_ENV_FILE" 2>/dev/null && \
        sed -i "s/^API_SERVER_KEY=.*/API_SERVER_KEY=$HERMES_API_KEY/" "$HERMES_ENV_FILE" || \
        echo "API_SERVER_KEY=$HERMES_API_KEY" >> "$HERMES_ENV_FILE"
fi

echo "API_SERVER_ENABLED=true" >> "$HERMES_ENV_FILE" 2>/dev/null || true
echo "API_SERVER_HOST=0.0.0.0" >> "$HERMES_ENV_FILE" 2>/dev/null || true
echo "API_SERVER_PORT=8642" >> "$HERMES_ENV_FILE" 2>/dev/null || true

# Test Antigravity CLI availability
echo "Checking Antigravity CLI (agy)..."
if command -v agy >/dev/null 2>&1; then
    echo "Antigravity CLI installed: $(agy --version 2>/dev/null || echo 'available')"
else
    echo "Warning: agy binary not detected in PATH. Please verify installation."
fi

# Trap signals for graceful shutdown
cleanup() {
    echo "Caught termination signal. Shutting down services..."
    if [ -n "$HERMES_PID" ]; then
        kill -TERM "$HERMES_PID" 2>/dev/null || true
    fi
    if [ -n "$ROUTER_PID" ]; then
        kill -TERM "$ROUTER_PID" 2>/dev/null || true
    fi
    wait
    echo "All services terminated cleanly."
    exit 0
}

trap cleanup SIGTERM SIGINT

# Start Hermes Gateway / API Server in background
echo "Starting Hermes Gateway (API Server on port 8642)..."
if command -v hermes >/dev/null 2>&1; then
    hermes gateway run &
    HERMES_PID=$!
elif [ -f "/opt/hermes/run_agent.py" ]; then
    python /opt/hermes/run_agent.py --gateway &
    HERMES_PID=$!
else
    echo "Starting hermes module..."
    python -m gateway.run &
    HERMES_PID=$!
fi

# Wait briefly for Hermes to bind
sleep 3

# Start Integration Router
echo "Starting Integration Router on port ${PORT:-8080}..."
python /opt/hermes/integration/router.py &
ROUTER_PID=$!

echo "Hermes and Router services are running. Monitoring processes..."

# Wait for background processes
wait -n "$HERMES_PID" "$ROUTER_PID"
cleanup
