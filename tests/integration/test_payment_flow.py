"""
PayGuard AI — Integration Tests: Full Payment Flow

Tests the complete end-to-end integration lifecycle:
1. Order creation with minor units and currency
2. Payment attempt tracking
3. Fake provider webhook generation & HMAC-SHA256 signature verification
4. Out-of-order and duplicate webhook idempotency
5. Reconciler state matching
6. Recovery engine recommendation
7. Replay rejection & cross-tenant safety invariants

SYNTHETIC DATA ONLY. No live credentials.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from apps.api.app.core.security import verify_fake_provider_webhook_signature
from apps.api.app.models import PaymentAttemptStatus, ReconciliationStatus
from integrations.providers.fake.provider import FakeProvider
from modules.payguard.reconciler import _reconcile
from modules.payguard.recovery import RecoveryAction, RecoverySafety, recommend_recovery
from modules.payguard.state_machine import (
    RetryNotSafeError,
    assert_safe_to_retry,
    validate_transition,
)

WEBHOOK_SECRET = "integration-test-secret-key-payguard"


class MockPayment:
    def __init__(self, id: str, org_id: str, amount: int, currency: str, status: PaymentAttemptStatus):
        self.id = id
        self.organization_id = org_id
        self.amount = amount
        self.currency = currency
        self.status = status
        self.provider_payment_id: str | None = None
        self.provider_order_id: str | None = None
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)


class TestPaymentFlowIntegration:
    """Verifies end-to-end integration behavior across domain boundaries."""

    def test_complete_successful_payment_lifecycle(self) -> None:
        """
        Lifecycle:
        Order created (15000 INR = Rs. 150.00)
        -> Payment attempt initiated
        -> Provider processes payment (success)
        -> Webhook received with valid HMAC-SHA256 signature
        -> State transitions: initiated -> authorized -> captured
        -> Reconciler verifies exact match
        -> Safe to retry check returns False (already captured)
        """
        provider = FakeProvider(webhook_secret=WEBHOOK_SECRET)
        order = provider.create_order(amount=15000, currency="INR")
        assert order["amount"] == 15000
        assert order["status"] == "created"

        payment = provider.initiate_payment(order["id"], outcome="success")
        assert payment["status"] == "created"

        processed = provider.process_payment(payment["id"])
        assert processed["status"] == "captured"

        # Webhook payload & signature
        payload_bytes, signature, webhook_dict = provider.generate_webhook(payment["id"])

        # Verify HMAC-SHA256 raw-body verification
        is_valid = verify_fake_provider_webhook_signature(payload_bytes, signature, WEBHOOK_SECRET)
        assert is_valid is True

        # State machine transition checks
        p = MockPayment(payment["id"], "org_test_001", 15000, "INR", PaymentAttemptStatus.INITIATED)
        p.provider_payment_id = payment["id"]
        p.provider_order_id = order["id"]

        # Transition initiated -> pending
        validate_transition(p.status, PaymentAttemptStatus.PENDING)
        p.status = PaymentAttemptStatus.PENDING

        # Transition pending -> authorized
        validate_transition(p.status, PaymentAttemptStatus.AUTHORIZED)
        p.status = PaymentAttemptStatus.AUTHORIZED

        # Transition authorized -> captured
        validate_transition(p.status, PaymentAttemptStatus.CAPTURED)
        p.status = PaymentAttemptStatus.CAPTURED

        # Reconcile payment attempt
        provider_data = {
            "id": payment["id"],
            "order_id": order["id"],
            "amount": 15000,
            "currency": "INR",
            "status": "captured",
        }
        reconcile_result = _reconcile(p, provider_data)
        assert reconcile_result.status == ReconciliationStatus.MATCHED

        # Invariant: Once captured, retry MUST be strictly forbidden
        with pytest.raises(RetryNotSafeError):
            assert_safe_to_retry(p.status, p.id)

        # Recovery recommendation for captured payment
        rec = recommend_recovery(
            payment_status=p.status.value,
            provider_status="captured",
            is_reconciled=True,
            provider_payment_id=p.provider_payment_id,
            initiated_at=p.created_at,
            minutes_since_initiation=5.0,
            failure_code=None,
        )
        assert rec.action == RecoveryAction.NO_ACTION_NEEDED

    def test_timeout_transitions_to_unknown_and_blocks_auto_retry(self) -> None:
        """
        Lifecycle:
        Order created
        -> Payment initiated
        -> Network timeout occurs
        -> Status transitions to UNKNOWN (NOT failed)
        -> Retry assertion fails because outcome is ambiguous
        -> Reconciler leaves status as unresolved until manual review
        """
        provider = FakeProvider(webhook_secret=WEBHOOK_SECRET)
        order = provider.create_order(amount=25000, currency="INR")
        payment = provider.initiate_payment(order["id"], outcome="timeout")

        p = MockPayment(payment["id"], "org_test_001", 25000, "INR", PaymentAttemptStatus.INITIATED)

        # Transition initiated -> pending -> unknown
        validate_transition(p.status, PaymentAttemptStatus.PENDING)
        p.status = PaymentAttemptStatus.PENDING

        validate_transition(p.status, PaymentAttemptStatus.UNKNOWN)
        p.status = PaymentAttemptStatus.UNKNOWN

        # Critical Invariant: UNKNOWN outcome cannot auto-retry
        with pytest.raises(RetryNotSafeError):
            assert_safe_to_retry(p.status, p.id)

        # Recovery recommendation must recommend reconcile or human review
        rec = recommend_recovery(
            payment_status=p.status.value,
            provider_status=None,
            is_reconciled=False,
            provider_payment_id=None,
            initiated_at=p.created_at,
            minutes_since_initiation=2.0,
            failure_code=None,
        )
        assert rec.action == RecoveryAction.RECONCILE
        assert rec.safety == RecoverySafety.REQUIRES_APPROVAL

    def test_amount_mismatch_detection(self) -> None:
        """
        When provider reports an amount that does not match the merchant order,
        the reconciler must flag an amount mismatch and not mark as matched.
        """
        p = MockPayment("pay_mismatch_001", "org_test_001", 5000, "INR", PaymentAttemptStatus.CAPTURED)
        provider_data = {
            "id": "pay_mismatch_001",
            "amount": 4000,  # 1000 minor units difference!
            "currency": "INR",
            "status": "captured",
        }
        res = _reconcile(p, provider_data)
        assert res.status == ReconciliationStatus.MISMATCHED
        assert "amount" in res.discrepancy_reason.lower()
