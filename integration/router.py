"""Production Message Router and Webhook Intake Service for Hermes Agent + OpenWA."""

import os
import sys
import json
import asyncio
import logging
import subprocess
from typing import Dict, Any, Optional
from aiohttp import web, ClientSession, ClientTimeout

from security import (
    normalize_phone_number,
    parse_allowed_numbers,
    is_sender_authorized,
    verify_webhook_secret,
    mask_phone_number,
    sanitize_log_text,
)
from deduplication import IdempotencyStore

# Logging setup with sanitized formatting
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [router] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("router")

# Configuration from Environment Variables
PORT = int(os.getenv("PORT", "8080"))
HERMES_BASE_URL = os.getenv("HERMES_BASE_URL", "http://127.0.0.1:8642").rstrip("/")
HERMES_API_KEY = os.getenv("HERMES_API_KEY", "")
OPENWA_BASE_URL = os.getenv("OPENWA_BASE_URL", "http://openwa:2785").rstrip("/")
OPENWA_API_KEY = os.getenv("OPENWA_API_KEY", "")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
ALLOWED_WHATSAPP_NUMBERS_RAW = os.getenv("ALLOWED_WHATSAPP_NUMBERS", "")
UNAUTHORIZED_RESPONSE = os.getenv(
    "UNAUTHORIZED_RESPONSE", "Access denied. This is a private personal AI agent."
)
DATA_PATH = os.getenv("HERMES_DATA_PATH", "/opt/data")
DEDUP_DB_PATH = os.path.join(DATA_PATH, "router", "dedup.db")

# Parse Allowed Numbers
ALLOWED_NUMBERS = parse_allowed_numbers(ALLOWED_WHATSAPP_NUMBERS_RAW)
logger.info(
    "Authorized WhatsApp numbers loaded: %d number(s) configured.", len(ALLOWED_NUMBERS)
)

# Global Idempotency Store
idempotency_store = IdempotencyStore(db_path=DEDUP_DB_PATH)


async def check_agy_cli() -> Dict[str, Any]:
    """Check if the Antigravity CLI (agy) binary is present and report its version."""
    agy_path = "/usr/local/bin/agy"
    if not os.path.exists(agy_path):
        # Fallback check on PATH
        try:
            res = await asyncio.create_subprocess_exec(
                "which", "agy", stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, _ = await res.communicate()
            if res.returncode == 0:
                agy_path = stdout.decode().strip()
            else:
                return {"installed": False, "version": None, "path": None}
        except Exception:
            return {"installed": False, "version": None, "path": None}

    try:
        proc = await asyncio.create_subprocess_exec(
            agy_path, "--version", stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        version = stdout.decode().strip() if proc.returncode == 0 else "unknown"
        return {"installed": True, "version": version, "path": agy_path}
    except Exception as e:
        return {"installed": True, "version": f"error: {str(e)}", "path": agy_path}


async def send_to_openwa(chat_id: str, text: str, max_retries: int = 3) -> bool:
    """Send an outgoing text message to WhatsApp via OpenWA REST API with retry backoff."""
    if not text or not chat_id:
        return False

    headers = {
        "Content-Type": "application/json",
    }
    if OPENWA_API_KEY:
        headers["X-API-Key"] = OPENWA_API_KEY
        headers["Authorization"] = f"Bearer {OPENWA_API_KEY}"

    payload = {
        "chatId": chat_id,
        "text": text,
    }

    # OpenWA endpoints: modern EasyAPI uses /api/sessions/default/messages/send-text or /api/sendText
    endpoints = [
        f"{OPENWA_BASE_URL}/api/sessions/default/messages/send-text",
        f"{OPENWA_BASE_URL}/api/sendText",
        f"{OPENWA_BASE_URL}/sendText",
    ]

    timeout = ClientTimeout(total=20)
    async with ClientSession(timeout=timeout) as session:
        for attempt in range(1, max_retries + 1):
            for endpoint in endpoints:
                try:
                    logger.info(
                        "Sending response to OpenWA (attempt %d/%d) for chat %s",
                        attempt,
                        max_retries,
                        mask_phone_number(chat_id),
                    )
                    async with session.post(endpoint, json=payload, headers=headers) as resp:
                        if resp.status in (200, 201):
                            logger.info("Successfully sent message to OpenWA.")
                            return True
                        elif resp.status == 404:
                            # Try fallback endpoint
                            continue
                        else:
                            resp_text = await resp.text()
                            logger.warning(
                                "OpenWA returned HTTP %d on %s: %s",
                                resp.status,
                                endpoint,
                                sanitize_log_text(resp_text)[:200],
                            )
                except Exception as e:
                    logger.warning("Error connecting to OpenWA (%s): %s", endpoint, e)

            if attempt < max_retries:
                backoff = attempt * 2
                logger.info("Retrying OpenWA send in %d seconds...", backoff)
                await asyncio.sleep(backoff)

    logger.error("Failed to send message to OpenWA after %d attempts.", max_retries)
    return False


async def query_hermes_agent(user_message: str, session_key: str) -> Optional[str]:
    """Query Hermes Agent via its OpenAI-compatible completions API with session tracking."""
    url = f"{HERMES_BASE_URL}/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "X-Hermes-Session-Key": session_key,
    }
    if HERMES_API_KEY:
        headers["Authorization"] = f"Bearer {HERMES_API_KEY}"

    payload = {
        "model": "hermes-agent",
        "messages": [
            {"role": "user", "content": user_message}
        ],
        "stream": False,
    }

    timeout = ClientTimeout(total=180)  # Agent runs may take time when executing tools
    try:
        async with ClientSession(timeout=timeout) as session:
            logger.info("Dispatching turn to Hermes Agent (session: %s)...", session_key)
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.error("Hermes returned status %d: %s", resp.status, body[:300])
                    return None
                data = await resp.json()
                choices = data.get("choices", [])
                if choices and len(choices) > 0:
                    message = choices[0].get("message", {})
                    content = message.get("content", "")
                    return content
                return None
    except asyncio.TimeoutError:
        logger.error("Hermes Agent request timed out after 180s.")
        return "I apologize, but processing your request took longer than expected. Please try again."
    except Exception as e:
        logger.error("Exception querying Hermes Agent: %s", e)
        return None


async def handle_health(request: web.Request) -> web.Response:
    """Detailed health check endpoint verifying router, Hermes, agy, and OpenWA status."""
    agy_info = await check_agy_cli()

    # Check Hermes API connectivity
    hermes_healthy = False
    try:
        async with ClientSession(timeout=ClientTimeout(total=3)) as session:
            async with session.get(f"{HERMES_BASE_URL}/health") as resp:
                hermes_healthy = (resp.status == 200)
    except Exception:
        hermes_healthy = False

    # Check OpenWA connectivity
    openwa_healthy = False
    try:
        async with ClientSession(timeout=ClientTimeout(total=3)) as session:
            async with session.get(f"{OPENWA_BASE_URL}/") as resp:
                openwa_healthy = resp.status in (200, 401, 403, 404)
    except Exception:
        openwa_healthy = False

    status = {
        "status": "ok" if (hermes_healthy or openwa_healthy) else "starting",
        "router": "running",
        "hermes": {
            "healthy": hermes_healthy,
            "url": HERMES_BASE_URL,
        },
        "openwa": {
            "healthy": openwa_healthy,
            "url": OPENWA_BASE_URL,
        },
        "antigravity_cli": agy_info,
        "authorized_senders_count": len(ALLOWED_NUMBERS),
        "data_directory": DATA_PATH,
    }
    return web.json_response(status, status=200 if status["status"] == "ok" else 503)


async def handle_whatsapp_webhook(request: web.Request) -> web.Response:
    """Intake endpoint for incoming OpenWA WhatsApp webhooks."""
    # 1. Verify Webhook Secret if configured
    if WEBHOOK_SECRET:
        token = request.headers.get("X-Webhook-Secret") or request.query.get("secret")
        if not verify_webhook_secret(token, WEBHOOK_SECRET):
            logger.warning("Rejected webhook: invalid or missing webhook secret.")
            return web.json_response({"error": "unauthorized"}, status=401)

    # 2. Parse incoming JSON
    try:
        payload = await request.json()
    except Exception as e:
        logger.warning("Failed to parse webhook JSON body: %s", e)
        return web.json_response({"error": "invalid json"}, status=400)

    # Handle wrapper structures (e.g. {"event": "onMessage", "data": {...}})
    msg_data = payload.get("data") if ("event" in payload and "data" in payload) else payload

    # 3. Extract Message Attributes
    message_id = msg_data.get("id") or msg_data.get("messageId")
    body = msg_data.get("body") or msg_data.get("text") or msg_data.get("content")
    from_jid = msg_data.get("from") or msg_data.get("chatId") or ""
    sender_obj = msg_data.get("sender") or {}
    sender_jid = sender_obj.get("id") or from_jid
    is_group = bool(msg_data.get("isGroupMsg") or "@g.us" in from_jid)
    is_from_me = bool(msg_data.get("fromMe") or msg_data.get("self") == "out")
    msg_type = msg_data.get("type", "chat")

    # 4. Filters: Drop non-chat, broadcasts, and self-messages
    if is_from_me:
        return web.json_response({"status": "ignored_self_message"}, status=200)

    if "@broadcast" in from_jid or from_jid == "status@broadcast":
        return web.json_response({"status": "ignored_status_broadcast"}, status=200)

    if not body or not isinstance(body, str):
        return web.json_response({"status": "ignored_non_text"}, status=200)

    body = body.strip()
    if not body:
        return web.json_response({"status": "ignored_empty_text"}, status=200)

    # 5. Idempotency Check (Prevent duplicate execution)
    if message_id:
        is_dup = await idempotency_store.is_duplicate_or_record(message_id, sender_jid)
        if is_dup:
            logger.info("Ignoring duplicate message delivery: %s", message_id)
            return web.json_response({"status": "duplicate_ignored"}, status=200)

    sender_phone = normalize_phone_number(sender_jid)
    masked_phone = mask_phone_number(sender_phone)
    logger.info("Incoming WhatsApp message from %s (msg_id: %s)", masked_phone, message_id)

    # 6. Access Control: Check Sender Allowlist
    if not is_sender_authorized(sender_phone, ALLOWED_NUMBERS):
        logger.warning(
            "Access denied: Sender %s is NOT in the allowed numbers list.", masked_phone
        )
        if UNAUTHORIZED_RESPONSE and UNAUTHORIZED_RESPONSE.lower() != "ignore":
            asyncio.create_task(send_to_openwa(from_jid, UNAUTHORIZED_RESPONSE))
        return web.json_response({"status": "unauthorized_sender"}, status=200)

    # 7. Asynchronously process message through Hermes and send response back
    session_key = f"whatsapp:{sender_phone}"
    asyncio.create_task(process_message_flow(from_jid, body, session_key, message_id))

    # Respond immediately with 200 OK to OpenWA webhook to prevent webhook timeout
    return web.json_response({"status": "accepted", "id": message_id}, status=200)


async def process_message_flow(chat_id: str, prompt: str, session_key: str, message_id: str) -> None:
    """Full asynchronous turnaround: Hermes reasoning -> OpenWA delivery."""
    try:
        reply = await query_hermes_agent(prompt, session_key)
        if not reply:
            reply = (
                "Hermes is currently processing your request or encountered an error. "
                "Please check the service status if the issue persists."
            )

        success = await send_to_openwa(chat_id, reply)
        if not success:
            logger.error("Failed to deliver reply for message %s to chat %s", message_id, mask_phone_number(chat_id))
    except Exception as e:
        logger.error("Exception in process_message_flow: %s", e, exc_info=True)


async def periodic_cleanup_task() -> None:
    """Background loop to periodically prune old message IDs from the idempotency store."""
    while True:
        try:
            await asyncio.sleep(3600)  # Every hour
            await idempotency_store.cleanup_expired()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning("Error in periodic idempotency cleanup: %s", e)


async def init_app() -> web.Application:
    """Build and configure the aiohttp application."""
    await idempotency_store.initialize()

    app = web.Application()
    app.router.add_get("/health", handle_health)
    app.router.add_post("/webhook/whatsapp", handle_whatsapp_webhook)
    app.router.add_get("/", lambda req: web.Response(text="Hermes-OpenWA Message Router is active."))

    # Background task for cleanup
    cleanup_task = asyncio.create_task(periodic_cleanup_task())

    async def on_cleanup(app_instance):
        cleanup_task.cancel()
        with asyncio.CancelledError():
            await cleanup_task

    app.on_cleanup.append(on_cleanup)
    return app


def main():
    logger.info("Starting Hermes-OpenWA Integration Router on port %d...", PORT)
    app = asyncio.run(init_app())
    web.run_app(app, host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    main()
