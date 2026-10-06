"""Security and sanitization helpers for the Hermes-OpenWA Integration."""

import hmac
import re
from typing import Set, Optional


def normalize_phone_number(raw: str) -> str:
    """Extract digits only from a WhatsApp ID or phone number.
    
    Examples:
        '15551234567@c.us' -> '15551234567'
        '+1 (555) 123-4567' -> '15551234567'
        '919876543210@s.whatsapp.net' -> '919876543210'
    """
    if not raw:
        return ""
    # Strip WhatsApp JID suffix if present
    base = raw.split("@")[0]
    # Remove all non-digit characters
    digits = re.sub(r"\D", "", base)
    return digits


def parse_allowed_numbers(config_str: str) -> Set[str]:
    """Parse a comma-separated list of allowed phone numbers into a normalized set."""
    if not config_str:
        return set()
    return {
        normalize_phone_number(num)
        for num in config_str.split(",")
        if normalize_phone_number(num)
    }


def is_sender_authorized(sender_id: str, allowed_numbers: Set[str]) -> bool:
    """Check if the normalized sender ID is present in the allowlist."""
    if not allowed_numbers:
        # If no allowlist is configured, fail closed for security!
        return False
    normalized = normalize_phone_number(sender_id)
    return normalized in allowed_numbers


def verify_webhook_secret(provided_token: Optional[str], expected_secret: Optional[str]) -> bool:
    """Verify webhook token using timing-safe comparison to prevent timing attacks."""
    if not expected_secret:
        # No secret configured, allow through
        return True
    if not provided_token:
        return False
    return hmac.compare_digest(provided_token.strip(), expected_secret.strip())


def mask_phone_number(phone: str) -> str:
    """Mask phone number for safe, non-sensitive logging.
    
    Example: '15551234567' -> '1555****567'
    """
    digits = normalize_phone_number(phone)
    if len(digits) <= 5:
        return "****"
    return f"{digits[:4]}****{digits[-3:]}"


def sanitize_log_text(text: str) -> str:
    """Remove potential secrets (Bearer tokens, API keys) from log text."""
    if not text:
        return ""
    # Mask Bearer tokens
    sanitized = re.sub(r"(Bearer\s+)[A-Za-z0-9_\-\.]{8,}", r"\1[REDACTED]", text, flags=re.IGNORECASE)
    # Mask standard api keys
    sanitized = re.sub(r"(key[=:\s]+)[A-Za-z0-9_\-\.]{8,}", r"\1[REDACTED]", sanitized, flags=re.IGNORECASE)
    return sanitized
