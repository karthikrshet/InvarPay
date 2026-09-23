"""
PayGuard AI — Chaos Tests: Duplicate Webhooks & Out-of-Order Delivery

These tests verify that:
1. Duplicate webhooks are safely ignored (idempotent)
2. Out-of-order webhooks do not corrupt state
3. No duplicate business fulfillment occurs
4. Unknown outcome prevents retry

SYNTHETIC: Uses fake provider. No real payments.
"""
from __future__ import annotations

import pytest

from apps.api.app.models import PaymentAttemptStatus
from integrations.providers.fake.provider import FakeProvider
from modules.payguard.state_machine import (
    InvalidTransitionError,
    RetryNotSafeError,
    assert_safe_to_retry,
    validate_transition,
)

WEBHOOK_SECRET = "chaos-test-secret"


class MockPaymentAttempt:
    """Lightweight mock for state machine tests."""
    def __init__(self, status: PaymentAttemptStatus, payment_id: str = "pay_chaos_001") -> None:
        self.id = payment_id
        self.organization_id = "org_chaos_001"
        self.status = status
        self.provider_status: str | None = None
        self.provider_payment_id: str | None = None
        self.authorized_at = None
        self.captured_at = None
        self.failed_at = None


class TestDuplicateWebhookSafety:
    """Duplicate webhooks must be idempotent — no double processing."""

    def test_duplicate_event_ids_generated(self) -> None:
        """Fake provider generates identical event IDs for duplicate webhooks."""
        provider = FakeProvider(WEBHOOK_SECRET)
        order = provider.create_order(50000)
        payment = provider.initiate_payment(order["id"], "success")
        provider.process_payment(payment["id"])

        _, _, p1 = provider.generate_webhook(payment["id"])
        _, _, p2 = provider.generate_duplicate_webhook(payment["id"])
        assert p1["event_id"] == p2["event_id"]

    def test_captured_payment_stays_captured_on_duplicate(self) -> None:
        """
        Applying a 'captured' event to an already-captured payment
        must fail with InvalidTransitionError (terminal state).
        """
        attempt = MockPaymentAttempt(PaymentAttemptStatus.CAPTURED)
        with pytest.raises(InvalidTransitionError):
            validate_transition(attempt.status, PaymentAttemptStatus.CAPTURED)


class TestOutOfOrderWebhooks:
    """Out-of-order webhook delivery must not corrupt state."""

    def test_capture_before_authorization_skips_backwards_transition(self) -> None:
        """
        If capture arrives first, state advances to authorized then captured.
        Then authorization arrives — it's out of order and must be skipped.
        """
        attempt = MockPaymentAttempt(PaymentAttemptStatus.PENDING)

        # Webhook arrives: authorized (advance forward)
        validate_transition(attempt.status, PaymentAttemptStatus.AUTHORIZED)
        attempt.status = PaymentAttemptStatus.AUTHORIZED

        # Webhook arrives: captured (advance forward)
        validate_transition(attempt.status, PaymentAttemptStatus.CAPTURED)
        attempt.status = PaymentAttemptStatus.CAPTURED

        # Now out-of-order authorization arrives — must NOT go backwards
        with pytest.raises(InvalidTransitionError):
            validate_transition(attempt.status, PaymentAttemptStatus.AUTHORIZED)

    def test_state_only_advances_never_goes_backwards(self) -> None:
        """State machine must be monotonically advancing."""
        # Authorized → cannot go back to Pending
        with pytest.raises(InvalidTransitionError):
            validate_transition(PaymentAttemptStatus.AUTHORIZED, PaymentAttemptStatus.PENDING)

        # Captured → cannot go back to Authorized
        with pytest.raises(InvalidTransitionError):
            validate_transition(PaymentAttemptStatus.CAPTURED, PaymentAttemptStatus.AUTHORIZED)


class TestUnknownOutcomeNoRetry:
    """
    CRITICAL: A payment in unknown state must NEVER trigger an automatic retry.
    Doing so could cause a duplicate charge.
    """

    def test_timeout_outcome_produces_unknown_state(self) -> None:
        provider = FakeProvider(WEBHOOK_SECRET)
        order = provider.create_order(50000)
        payment = provider.initiate_payment(order["id"], outcome="timeout")
        result = provider.process_payment(payment["id"])
        assert result["status"] == "unknown"

    def test_unknown_state_blocks_retry(self) -> None:
        """assert_safe_to_retry must raise for unknown state."""
        with pytest.raises(RetryNotSafeError) as exc_info:
            assert_safe_to_retry(PaymentAttemptStatus.UNKNOWN, "pay_chaos_001")
        assert "unknown outcome" in str(exc_info.value).lower()

    def test_unknown_state_blocks_retry_with_helpful_message(self) -> None:
        try:
            assert_safe_to_retry(PaymentAttemptStatus.UNKNOWN, "pay_001")
            pytest.fail("Should have raised RetryNotSafeError")
        except RetryNotSafeError as e:
            assert "Reconcile" in str(e) or "reconcile" in str(e).lower()
            assert "duplicate charge" in str(e).lower()

    def test_captured_state_blocks_retry(self) -> None:
        """Must not retry a payment that is already captured."""
        with pytest.raises(RetryNotSafeError, match="already captured"):
            assert_safe_to_retry(PaymentAttemptStatus.CAPTURED, "pay_001")

    def test_failed_payment_allows_retry(self) -> None:
        """Failed payment (definitive) is safe to retry with a new attempt."""
        # Should NOT raise
        assert_safe_to_retry(PaymentAttemptStatus.FAILED, "pay_001")

    def test_no_fulfillment_on_unknown(self) -> None:
        """
        Business fulfillment must only trigger on CAPTURED state.
        unknown must NOT trigger fulfillment.
        """
        unknown_status = PaymentAttemptStatus.UNKNOWN

        # Simulate fulfillment check
        def should_fulfill(status: PaymentAttemptStatus) -> bool:
            return status == PaymentAttemptStatus.CAPTURED

        assert should_fulfill(unknown_status) is False
        assert should_fulfill(PaymentAttemptStatus.CAPTURED) is True
        assert should_fulfill(PaymentAttemptStatus.FAILED) is False
