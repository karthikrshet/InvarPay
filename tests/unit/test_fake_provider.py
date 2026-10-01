"""
InvarPay AI — Fake Provider Unit Tests

Tests the fake provider (SYNTHETIC — not real payments):
- Order creation
- Payment initiation with different outcomes
- Webhook generation and signature validity
- Duplicate webhook generation
- Out-of-order webhook generation
"""
from __future__ import annotations

import pytest

from apps.api.app.core.security import verify_fake_provider_webhook_signature
from integrations.providers.fake.provider import FakeProvider

WEBHOOK_SECRET = "test-fake-secret"


@pytest.fixture
def provider() -> FakeProvider:
    return FakeProvider(webhook_secret=WEBHOOK_SECRET)


class TestFakeProviderOrders:
    def test_create_order_returns_id(self, provider: FakeProvider) -> None:
        order = provider.create_order(amount=50000, currency="INR")
        assert order["id"].startswith("fake_order_")
        assert order["amount"] == 50000
        assert order["currency"] == "INR"
        assert order["_marker"] == provider.MARKER

    def test_create_order_minor_units(self, provider: FakeProvider) -> None:
        order = provider.create_order(amount=10099)  # 100.99 INR
        assert order["amount"] == 10099

    def test_unknown_order_raises_on_payment(self, provider: FakeProvider) -> None:
        with pytest.raises(ValueError, match="not found"):
            provider.initiate_payment("nonexistent_order_id")


class TestFakeProviderPayments:
    def test_success_outcome(self, provider: FakeProvider) -> None:
        order = provider.create_order(amount=50000)
        payment = provider.initiate_payment(order["id"], outcome="success")
        payment = provider.process_payment(payment["id"])
        assert payment["status"] == "captured"

    def test_failure_outcome(self, provider: FakeProvider) -> None:
        order = provider.create_order(amount=50000)
        payment = provider.initiate_payment(order["id"], outcome="failure")
        payment = provider.process_payment(payment["id"])
        assert payment["status"] == "failed"
        assert "error_code" in payment

    def test_timeout_outcome_stays_unknown(self, provider: FakeProvider) -> None:
        """
        CRITICAL: Network timeout must NOT resolve to failed.
        Status stays 'unknown'.
        """
        order = provider.create_order(amount=50000)
        payment = provider.initiate_payment(order["id"], outcome="timeout")
        payment = provider.process_payment(payment["id"])
        assert payment["status"] == "unknown"

    def test_unknown_outcome(self, provider: FakeProvider) -> None:
        order = provider.create_order(amount=50000)
        payment = provider.initiate_payment(order["id"], outcome="unknown")
        payment = provider.process_payment(payment["id"])
        assert payment["status"] == "unknown"


class TestFakeProviderWebhooks:
    def test_generated_webhook_has_valid_signature(self, provider: FakeProvider) -> None:
        order = provider.create_order(amount=50000)
        payment = provider.initiate_payment(order["id"], outcome="success")
        provider.process_payment(payment["id"])

        raw_body, sig, payload = provider.generate_webhook(payment["id"])
        # Should not raise
        verify_fake_provider_webhook_signature(raw_body, sig, WEBHOOK_SECRET)

    def test_webhook_contains_payment_id(self, provider: FakeProvider) -> None:
        order = provider.create_order(amount=50000)
        payment = provider.initiate_payment(order["id"], outcome="success")
        provider.process_payment(payment["id"])

        _, _, payload = provider.generate_webhook(payment["id"])
        assert payload["payment_id"] == payment["id"]
        assert payload["_marker"] == provider.MARKER

    def test_duplicate_webhook_is_identical_event_id(self, provider: FakeProvider) -> None:
        """Duplicate webhooks must have the same event_id for deduplication."""
        order = provider.create_order(amount=50000)
        payment = provider.initiate_payment(order["id"], outcome="success")
        provider.process_payment(payment["id"])

        _, _, payload1 = provider.generate_webhook(payment["id"])
        _, _, payload2 = provider.generate_duplicate_webhook(payment["id"])
        assert payload1["event_id"] == payload2["event_id"]

    def test_out_of_order_webhooks(self, provider: FakeProvider) -> None:
        """Out-of-order delivery: capture comes before authorization."""
        order = provider.create_order(amount=50000)
        payment = provider.initiate_payment(order["id"], outcome="success")
        provider.process_payment(payment["id"])

        webhooks = provider.generate_out_of_order_webhooks(payment["id"])
        assert len(webhooks) == 2
        _, _, first = webhooks[0]
        _, _, second = webhooks[1]
        assert first["event_type"] == "payment.captured"
        assert second["event_type"] == "payment.authorized"
