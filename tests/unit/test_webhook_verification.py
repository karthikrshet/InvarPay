"""
InvarPay AI — Webhook Security Unit Tests

Tests:
- Valid signature accepted
- Bad signature rejected
- Wrong secret rejected
- Replay attack (old timestamp) rejected
- Missing signature rejected
- Empty body rejected

SYNTHETIC: Uses test secrets only. No real Razorpay credentials.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time

import pytest

from apps.api.app.core.security import (
    WebhookVerificationError,
    check_webhook_replay,
    verify_fake_provider_webhook_signature,
    verify_razorpay_webhook_signature,
)
from modules.payguard.webhook_processor import (
    WebhookProcessingError,
    _extract_razorpay_payment_event,
    _redact_provider_payload,
)

WEBHOOK_SECRET = "test-webhook-secret-synthetic"


def _make_signature(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _make_payload(status: str = "captured") -> bytes:
    payload = {
        "id": "fake_evt_001",
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "fake_pay_001",
                    "order_id": "fake_order_001",
                    "status": status,
                    "amount": 50000,
                    "currency": "INR",
                }
            }
        },
        "timestamp": int(time.time()),
    }
    return json.dumps(payload, separators=(",", ":")).encode()


class TestRazorpayWebhookVerification:

    def test_valid_signature_accepted(self) -> None:
        body = _make_payload()
        sig = _make_signature(body, WEBHOOK_SECRET)
        # Must not raise
        verify_razorpay_webhook_signature(body, sig, WEBHOOK_SECRET)

    def test_wrong_signature_rejected(self) -> None:
        body = _make_payload()
        bad_sig = "a" * 64  # Wrong hex string
        with pytest.raises(WebhookVerificationError, match="signature mismatch"):
            verify_razorpay_webhook_signature(body, bad_sig, WEBHOOK_SECRET)

    def test_wrong_secret_rejected(self) -> None:
        body = _make_payload()
        sig = _make_signature(body, "different-secret")
        with pytest.raises(WebhookVerificationError, match="signature mismatch"):
            verify_razorpay_webhook_signature(body, sig, WEBHOOK_SECRET)

    def test_tampered_body_rejected(self) -> None:
        """Modifying the body after computing signature must fail."""
        body = _make_payload()
        sig = _make_signature(body, WEBHOOK_SECRET)
        tampered = body[:-10] + b'"tampered"}'  # Modify payload after signing
        with pytest.raises(WebhookVerificationError):
            verify_razorpay_webhook_signature(tampered, sig, WEBHOOK_SECRET)

    def test_empty_signature_rejected(self) -> None:
        body = _make_payload()
        with pytest.raises(WebhookVerificationError, match="Missing"):
            verify_razorpay_webhook_signature(body, "", WEBHOOK_SECRET)

    def test_missing_secret_rejected(self) -> None:
        body = _make_payload()
        sig = _make_signature(body, WEBHOOK_SECRET)
        with pytest.raises(WebhookVerificationError, match="not configured"):
            verify_razorpay_webhook_signature(body, sig, "")


class TestWebhookReplayPrevention:

    def test_fresh_timestamp_accepted(self) -> None:
        # Current timestamp — should pass
        ts = str(int(time.time()))
        check_webhook_replay(ts, window_seconds=300)

    def test_old_timestamp_rejected(self) -> None:
        """Timestamp older than window must be rejected."""
        old_ts = str(int(time.time()) - 400)  # 400 seconds ago
        with pytest.raises(WebhookVerificationError, match="outside replay window"):
            check_webhook_replay(old_ts, window_seconds=300)

    def test_future_timestamp_rejected(self) -> None:
        """Far-future timestamp (possible replay from future) must be rejected."""
        future_ts = str(int(time.time()) + 400)
        with pytest.raises(WebhookVerificationError, match="outside replay window"):
            check_webhook_replay(future_ts, window_seconds=300)

    def test_invalid_timestamp_rejected(self) -> None:
        with pytest.raises(WebhookVerificationError, match="Invalid"):
            check_webhook_replay("not-a-number", window_seconds=300)

    def test_boundary_timestamp_accepted(self) -> None:
        """Exactly at boundary edge — just within window."""
        ts = str(int(time.time()) - 299)
        check_webhook_replay(ts, window_seconds=300)


class TestFakeProviderWebhookVerification:

    def test_valid_fake_signature_accepted(self) -> None:
        body = b'{"event_id":"test","status":"captured"}'
        secret = "fake-test-secret"
        sig = _make_signature(body, secret)
        verify_fake_provider_webhook_signature(body, sig, secret)

    def test_invalid_fake_signature_rejected(self) -> None:
        body = b'{"event_id":"test","status":"captured"}'
        with pytest.raises(WebhookVerificationError):
            verify_fake_provider_webhook_signature(body, "badsig", "fake-test-secret")


class TestRazorpayPayloadExtraction:
    """Validate the documented nested Razorpay payment webhook structure."""

    def test_uses_authenticated_raw_body_digest_when_event_has_no_id(self) -> None:
        raw_body = _make_payload()
        payload = json.loads(raw_body)

        event_id, event_type, payment_id, order_id, payment_status = (
            _extract_razorpay_payment_event(payload, raw_body)
        )

        assert event_id == hashlib.sha256(raw_body).hexdigest()
        assert event_type == "payment.captured"
        assert payment_id == "fake_pay_001"
        assert order_id == "fake_order_001"
        assert payment_status == "captured"

    def test_rejects_payload_without_a_payment_entity(self) -> None:
        raw_body = b'{"entity":"event","event":"payment.captured","payload":{}}'
        with pytest.raises(WebhookProcessingError, match="payment ID"):
            _extract_razorpay_payment_event(json.loads(raw_body), raw_body)

    def test_redacts_customer_and_payment_details_before_persistence(self) -> None:
        payload = json.loads(_make_payload())
        entity = payload["payload"]["payment"]["entity"]
        entity.update({"email": "buyer@example.test", "contact": "+919999999999", "vpa": "buyer@upi"})

        redacted = _redact_provider_payload(payload)
        persisted_entity = redacted["payload"]["payment"]["entity"]

        assert "email" not in persisted_entity
        assert "contact" not in persisted_entity
        assert "vpa" not in persisted_entity
        assert "email" in entity  # The caller's parsed object is not mutated.
