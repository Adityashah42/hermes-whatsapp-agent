# Railway Infrastructure Guide

This folder contains Railway deployment manifests and operational runbooks for the Hermes + Antigravity + OpenWA agent stack.

## Deploying to Railway

1. **Create the Project**:
   ```bash
   railway init
   ```
2. **Provision Services**:
   - `hermes` from `./hermes/Dockerfile`
   - `openwa` from `./openwa/Dockerfile`
3. **Attach Volumes**:
   - Create volume `hermes-data` attached to `hermes` at `/opt/data`.
   - Create volume `openwa-data` attached to `openwa` at `/app/data`.
4. **Set Variables**:
   Apply variables as defined in `railway/deployment-notes.md`.
5. **Pair WhatsApp & Authenticate Antigravity**:
   Follow procedures in `scripts/authenticate-antigravity.sh` and `scripts/pair-whatsapp.sh`.
