"""
InvarPay AI — Fake Payment Provider

A fully deterministic fake payment provider for automated testing.
ALL payments here are SYNTHETIC — clearly labelled, never real.

Features:
- Configurable outcomes: success, failure, timeout, unknown, duplicate
- Generates valid webhook payloads with correct HMAC-SHA256 signatures
- Simulates out-of-order webhook delivery
- Simulates duplicate webhook delivery
- Never makes real network calls

Usage in tests:
    provider = FakeProvider(webhook_secret="test-secret")
    order = provider.create_order(amount=50000, currency="INR")
    payment = provider.capture_payment(order["id"], outcome="success")
    webhook = provider.generate_webhook(payment["id"], event="captured")
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from typing import Any, Literal, Optional

PaymentOutcome = Literal["success", "failure", "timeout", "unknown", "duplicate"]


class FakeProvider:
    """
    SYNTHETIC fake payment provider for deterministic CI testing.
    Not a real payment processor. No real money involved.
    """

    PROVIDER_NAME = "fake"
    MARKER = "[SYNTHETIC-TEST-ONLY]"  # Always include in descriptions

    def __init__(self, webhook_secret: str = "fake-webhook-secret-for-tests") -> None:
        self.webhook_secret = webhook_secret
        self._orders: dict[str, dict] = {}
        self._payments: dict[str, dict] = {}
        self._delivered_events: set[str] = set()
        self._cached_webhooks: dict[str, tuple[bytes, str, dict]] = {}  # payment_id -> (raw, sig, payload)

    def create_order(
        self,
        amount: int,
        currency: str = "INR",
        receipt: str | None = None,
    ) -> dict[str, Any]:
        """Create a fake order. Returns provider order object."""
        order_id = f"fake_order_{uuid.uuid4().hex[:16]}"
        order = {
            "id": order_id,
            "entity": "order",
            "amount": amount,
            "amount_paid": 0,
            "amount_due": amount,
            "currency": currency,
            "receipt": receipt or f"rcpt_{uuid.uuid4().hex[:8]}",
            "status": "created",
            "created_at": int(time.time()),
            "_marker": self.MARKER,
        }
        self._orders[order_id] = order
        return order

    def initiate_payment(
        self,
        order_id: str,
        outcome: PaymentOutcome = "success",
    ) -> dict[str, Any]:
        """
        Initiate a fake payment with a pre-configured outcome.
        The outcome determines what state the payment ends in and
        what webhooks will be generated.
        """
        order = self._orders.get(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found in fake provider")

        payment_id = f"fake_pay_{uuid.uuid4().hex[:16]}"
        payment = {
            "id": payment_id,
            "entity": "payment",
            "order_id": order_id,
            "amount": order["amount"],
            "currency": order["currency"],
            "status": self._initial_status_for(outcome),
            "outcome": outcome,
            "created_at": int(time.time()),
            "_marker": self.MARKER,
        }
        self._payments[payment_id] = payment
        return payment

    def _initial_status_for(self, outcome: PaymentOutcome) -> str:
        return {
            "success": "created",
            "failure": "created",
            "timeout": "created",
            "unknown": "created",
            "duplicate": "created",
        }[outcome]

    def process_payment(self, payment_id: str) -> dict[str, Any]:
        """
        Simulate payment processing and set final status based on outcome.
        Returns updated payment object.
        """
        payment = self._payments.get(payment_id)
        if not payment:
            raise ValueError(f"Payment {payment_id} not found in fake provider")

        outcome = payment["outcome"]
        if outcome == "success":
            payment["status"] = "captured"
            payment["captured_at"] = int(time.time())
        elif outcome == "failure":
            payment["status"] = "failed"
            payment["error_code"] = "PAYMENT_FAILED"
            payment["error_description"] = f"{self.MARKER} Simulated payment failure"
        elif outcome == "timeout":
            # Simulate network timeout — payment stays in ambiguous state
            payment["status"] = "unknown"
        elif outcome == "unknown":
            payment["status"] = "unknown"
        # "duplicate" case — payment stays as-is

        return payment

    def generate_webhook(
        self,
        payment_id: str,
        event_type: str | None = None,
        delay_seconds: int = 0,
    ) -> tuple[bytes, str, dict]:
        """
        Generate a signed webhook payload for a payment event.

        Returns:
            (raw_body_bytes, signature_header, parsed_payload)

        The signature is HMAC-SHA256 of raw_body with webhook_secret,
        matching the verification logic in security.py.
        """
        payment = self._payments.get(payment_id)
        if not payment:
            raise ValueError(f"Payment {payment_id} not found")

        status = payment["status"]
        if event_type is None:
            event_type = self._event_type_for_status(status)

        event_id = f"fake_evt_{uuid.uuid4().hex[:16]}"
        now = int(time.time()) + delay_seconds

        payload = {
            "event_id": event_id,
            "event_type": event_type,
            "payment_id": payment_id,
            "order_id": payment["order_id"],
            "status": status,
            "amount": payment["amount"],
            "currency": payment["currency"],
            "timestamp": now,
            "_marker": self.MARKER,
        }

        raw_body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        signature = hmac.new(
            self.webhook_secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()

        # Cache on first generation so duplicates share the same event_id
        result = (raw_body, signature, payload)
        if payment_id not in self._cached_webhooks and delay_seconds == 0:
            self._cached_webhooks[payment_id] = result
        return result

    def generate_duplicate_webhook(self, payment_id: str) -> tuple[bytes, str, dict]:
        """Generate the SAME webhook again — identical event_id for deduplication testing."""
        if payment_id in self._cached_webhooks:
            return self._cached_webhooks[payment_id]
        # Generate and cache if not yet cached
        result = self.generate_webhook(payment_id)
        self._cached_webhooks[payment_id] = result
        return result

    def generate_out_of_order_webhooks(
        self, payment_id: str
    ) -> list[tuple[bytes, str, dict]]:
        """
        Generate webhooks in REVERSE order to test out-of-order handling.
        Returns [capture_webhook, authorization_webhook] — reversed.
        """
        capture = self.generate_webhook(payment_id, "payment.captured")
        auth = self.generate_webhook(payment_id, "payment.authorized")
        return [capture, auth]

    def get_payment(self, payment_id: str) -> Optional[dict]:
        """Fetch payment details (simulates provider API fetch for reconciliation)."""
        return self._payments.get(payment_id)

    def _event_type_for_status(self, status: str) -> str:
        return {
            "captured": "payment.captured",
            "authorized": "payment.authorized",
            "failed": "payment.failed",
            "unknown": "payment.unknown",
        }.get(status, "payment.updated")
