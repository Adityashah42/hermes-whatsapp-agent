# Railway Deployment Architecture & Operational Guide

## 1. Multi-Service Architecture Overview

The system is deployed on Railway as a unified project containing two private, interconnected services:

```
Railway Project: "hermes-whatsapp-agent"
│
├── Service: "hermes"
│     ├── Container: ghcr.io/nousresearch/hermes-agent base + custom router
│     ├── Antigravity CLI: /usr/local/bin/agy (official Google binary)
│     ├── Skills: antigravity-cli skill (/opt/data/skills/antigravity-cli)
│     ├── Ports: 8080 (Integration Webhook Router & Health Check), 8642 (Hermes API Server)
│     └── Persistent Volume: hermes-data -> /opt/data
│           ├── /opt/data/.hermes     (Hermes memory, sessions, configs)
│           ├── /opt/data/.gemini     (Antigravity CLI credentials & state)
│           ├── /opt/data/router      (Deduplication SQLite database)
│           └── /opt/data/skills      (Enabled custom skills)
│
└── Service: "openwa"
      ├── Container: openwa/wa-automate (headless Chromium WhatsApp Web bridge)
      ├── Ports: 2785 (REST API, Webhook sender, QR scan dashboard)
      └── Persistent Volume: openwa-data -> /app/data
            └── /app/data             (WhatsApp Web session tokens & keys)
```

## 2. Private Networking

Railway Private Networking (`*.railway.internal`) provides encrypted WireGuard mesh communication between services:

- **OpenWA → Hermes Webhook**:
  `OPENWA_WEBHOOK_URL=http://hermes.railway.internal:8080/webhook/whatsapp`
  OpenWA forwards every incoming message privately to the Hermes router.

- **Hermes → OpenWA REST API**:
  `OPENWA_BASE_URL=http://openwa.railway.internal:2785`
  Hermes delivers AI replies directly to OpenWA's internal API.

- **Zero Unnecessary Public Exposure**:
  Neither OpenWA's REST API nor Hermes's core execution engine is exposed to the public internet.

## 3. Persistent Volumes

| Service | Volume Name | Mount Path | Purpose |
| :--- | :--- | :--- | :--- |
| `hermes` | `hermes-data` | `/opt/data` | Persists Hermes agent memory, sessions, transcripts, Antigravity OAuth tokens (`.gemini`), and idempotency database. |
| `openwa` | `openwa-data` | `/app/data` | Persists WhatsApp Web multi-device session credentials, avoiding QR re-pairing across deployments. |

## 4. Environment Variables Reference

### Service `hermes`:
- `PORT`: `8080`
- `HERMES_API_PORT`: `8642`
- `HERMES_API_KEY`: Strong 32+ character random secret
- `OPENWA_API_KEY`: Matching secret configured on OpenWA
- `OPENWA_BASE_URL`: `http://openwa.railway.internal:2785`
- `HERMES_BASE_URL`: `http://127.0.0.1:8642`
- `ALLOWED_WHATSAPP_NUMBERS`: Your international phone number (e.g., `15551234567`)
- `UNAUTHORIZED_RESPONSE`: `Access denied. This is a private personal AI agent.`
- `HERMES_DATA_PATH`: `/opt/data`
- `GEMINI_API_KEY`: (Optional) Google AI Studio API key companion

### Service `openwa`:
- `PORT`: `2785`
- `OPENWA_PORT`: `2785`
- `OPENWA_API_KEY`: Strong 32+ character random secret
- `OPENWA_WEBHOOK_URL`: `http://hermes.railway.internal:8080/webhook/whatsapp`
- `OPENWA_DATA_PATH`: `/app/data`

## 5. Health Checks & Restart Behavior

- **Hermes Health Check**:
  Path: `/health` (HTTP Port 8080)
  Verifies that the router is operational, the internal Hermes API is responding, and Antigravity CLI is installed.
- **OpenWA Health Check**:
  Path: `/` (HTTP Port 2785)
- **Restart Policy**: `ON_FAILURE` (max 10 retries) ensures transient crashes recover automatically.
