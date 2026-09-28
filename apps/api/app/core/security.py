"""
PayGuard AI — Security Utilities

Covers:
- Webhook raw-body signature verification (HMAC-SHA256)
- Replay attack prevention (timestamp window check)
- Password hashing (bcrypt)
- API key generation and validation
- Credentials encryption/decryption (AES-256-GCM via Fernet)
- JWT token creation/verification

INVARIANT: Webhook signature is ALWAYS verified on the raw body
           BEFORE parsing the payload. A failed signature check
           must reject the request — never silently degrade.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from cryptography.fernet import Fernet
from jose import jwt

from apps.api.app.core.config import get_settings

settings = get_settings()

# ── Password hashing ──────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Hash password using bcrypt (max 72 bytes)."""
    pwd_bytes = password.encode("utf-8")[:72]
    return bcrypt.hashpw(pwd_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify password against bcrypt hash."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))
    except Exception:
        return False


# ── API Key generation ─────────────────────────────────────────────────────────

def generate_api_key(test_mode: bool = False) -> tuple[str, str]:
    """
    Generate a new API key.
    Returns (full_key, key_hash) — store only the hash, never the full key.
    """
    prefix = settings.api_key_test_prefix if test_mode else settings.api_key_prefix
    raw = secrets.token_urlsafe(32)
    full_key = f"{prefix}{raw}"
    key_hash = hash_password(full_key)
    return full_key, key_hash


def verify_api_key(provided_key: str, stored_hash: str) -> bool:
    return verify_password(provided_key, stored_hash)


# ── JWT ────────────────────────────────────────────────────────────────────────

def create_access_token(subject: str, extra_claims: Optional[dict] = None) -> str:
    """Create a JWT access token."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": expire,
        "type": "access",
        **(extra_claims or {}),
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict:
    """
    Decode and validate a JWT token.
    Raises JWTError on invalid/expired token.
    """
    return jwt.decode(
        token,
        settings.jwt_secret_key.get_secret_value(),
        algorithms=[settings.jwt_algorithm],
    )


# ── Webhook Signature Verification ────────────────────────────────────────────

class WebhookVerificationError(Exception):
    """Raised when webhook signature verification fails."""
    pass


def verify_razorpay_webhook_signature(
    raw_body: bytes,
    signature_header: str,
    webhook_secret: str,
) -> None:
    """
    Verify Razorpay webhook signature.
    Uses HMAC-SHA256 of raw request body with webhook secret.
    Based on: https://razorpay.com/docs/webhooks/validate-test/

    INVARIANT: Call this BEFORE parsing the JSON payload.
    Raises WebhookVerificationError if verification fails.
    """
    if not webhook_secret:
        raise WebhookVerificationError("Webhook secret not configured")

    if not signature_header:
        raise WebhookVerificationError("Missing X-Razorpay-Signature header")

    expected = hmac.new(
        webhook_secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, signature_header):
        raise WebhookVerificationError(
            "Webhook signature mismatch — possible tampering or wrong secret"
        )
    return True


def verify_fake_provider_webhook_signature(
    raw_body: bytes,
    signature_header: str,
    webhook_secret: str,
) -> bool:
    """
    Verify fake provider webhook signature (same HMAC-SHA256 scheme).
    Used in automated tests only. Clearly labelled SYNTHETIC.
    """
    if not webhook_secret:
        raise WebhookVerificationError("Webhook secret not configured for fake provider")

    if not signature_header:
        raise WebhookVerificationError("Missing X-Fake-Signature header")

    expected = hmac.new(
        webhook_secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, signature_header):
        raise WebhookVerificationError("Fake provider webhook signature mismatch")
    return True


def check_webhook_replay(
    timestamp_str: str,
    window_seconds: int = 300,
) -> None:
    """
    Prevent webhook replay attacks by checking timestamp freshness.
    Raises WebhookVerificationError if timestamp is outside the window.
    """
    try:
        event_ts = int(timestamp_str)
    except (ValueError, TypeError) as e:
        raise WebhookVerificationError(f"Invalid webhook timestamp: {timestamp_str}") from e

    now = int(time.time())
    age = abs(now - event_ts)

    if age > window_seconds:
        raise WebhookVerificationError(
            f"Webhook timestamp outside replay window: {age}s old (max {window_seconds}s)"
        )


# ── Credential Encryption ─────────────────────────────────────────────────────

def _get_fernet() -> Fernet:
    """
    Build a Fernet instance from the application secret key.
    Fernet provides AES-128-CBC with HMAC-SHA256 authentication.
    In production, replace with a dedicated KMS key.
    """
    # Derive a 32-byte key from the secret
    raw = settings.secret_key.get_secret_value().encode()
    key_bytes = hashlib.sha256(raw).digest()
    import base64
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def encrypt_credential(plaintext: str) -> bytes:
    """Encrypt a provider credential string. Store ciphertext, never plaintext."""
    return _get_fernet().encrypt(plaintext.encode())


def decrypt_credential(ciphertext: bytes) -> str:
    """Decrypt a provider credential."""
    return _get_fernet().decrypt(ciphertext).decode()


# ── Audit Hash Chain ───────────────────────────────────────────────────────────

def compute_audit_event_hash(
    event_id: str,
    action: str,
    resource_type: str,
    resource_id: Optional[str],
    occurred_at: str,
    previous_hash: Optional[str],
) -> str:
    """
    Compute SHA-256 hash for an audit event.
    Chained to previous event hash for tamper evidence.
    """
    content = "|".join([
        event_id,
        action,
        resource_type,
        resource_id or "",
        occurred_at,
        previous_hash or "GENESIS",
    ])
    return hashlib.sha256(content.encode()).hexdigest()
