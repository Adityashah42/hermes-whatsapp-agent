#!/bin/bash
# ==============================================================================
# Antigravity Headless Authentication Script
# ==============================================================================
# This script executes the official Google Antigravity CLI (agy) authentication
# flow in a headless / remote terminal environment.
#
# Process:
# 1. Runs `agy` in headless interactive auth mode.
# 2. agy prints a unique Google OAuth authorization URL.
# 3. You copy and open the URL in your local browser, sign in with your
#    Google / Antigravity Pro account, and authorize the session.
# 4. Paste the authorization code back into the terminal prompt.
# 5. agy verifies the token and saves the session to ~/.gemini/antigravity-cli/.
# 6. Because ~/.gemini is symlinked to /opt/data/.gemini on the Railway volume,
#    the authentication persists across all container redeployments and restarts!
# ==============================================================================

set -e

echo "=== Google Antigravity Pro Authentication Setup ==="
echo ""
echo "Security notice:"
echo "- Your Google password is NEVER requested or stored."
echo "- Tokens are stored securely in ~/.gemini on the persistent Railway volume."
echo "- Do NOT share your authorization URL or token code with anyone."
echo ""

# Verify agy is installed
if ! command -v agy >/dev/null 2>&1; then
    echo "Error: 'agy' CLI command not found. Installing..."
    curl -fsSL https://antigravity.google/cli/install.sh | bash
    export PATH="$HOME/.local/bin:$PATH"
fi

echo "Antigravity CLI Version: $(agy --version)"
echo ""
echo "Starting authentication flow now..."
echo "When the Google authorization URL appears below:"
echo "1. Click or copy the URL into your browser."
echo "2. Log in with your Antigravity Pro Google account."
echo "3. Copy the resulting authorization code."
echo "4. Paste it into this terminal prompt."
echo ""

# Launch agy in interactive login mode
agy --prompt-interactive "Check authentication status"

echo ""
echo "=== Authentication verification ==="
echo "Running smoke test turn with Antigravity CLI..."
agy -p "Respond with 'Antigravity Pro authentication is active!'" --model "Gemini 3.1 Pro (High)"

echo ""
echo "✓ Antigravity session successfully authenticated and persisted on volume!"
