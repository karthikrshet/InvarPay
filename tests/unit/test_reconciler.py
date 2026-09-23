"""
PayGuard AI — Reconciliation Unit Tests

Tests deterministic reconciliation logic:
- Amount match / mismatch
- Currency match / mismatch
- Provider ID match / mismatch
- Unknown/ambiguous provider status
- Unresolved outcome handling

SYNTHETIC: No real payments.
"""
from __future__ import annotations

from apps.api.app.models import PaymentAttemptStatus, ReconciliationStatus
from modules.payguard.reconciler import _reconcile


def make_attempt(
    amount: int = 50000,
    currency: str = "INR",
    provider_payment_id: str | None = "fake_pay_001",
    status: PaymentAttemptStatus = PaymentAttemptStatus.UNKNOWN,
) -> object:
    class MockAttempt:
        pass
    a = MockAttempt()
    a.amount = amount
    a.currency = currency
    a.provider_payment_id = provider_payment_id
    a.status = status
    a.organization_id = "org_test_001"
    a.id = "pay_test_001"
    return a


class TestReconciliationMatching:

    def test_full_match_captured(self) -> None:
        attempt = make_attempt(amount=50000, currency="INR")
        provider_data = {
            "id": "fake_pay_001",
            "amount": 50000,
            "currency": "INR",
            "status": "captured",
        }
        result = _reconcile(attempt, provider_data)
        assert result.status == ReconciliationStatus.MATCHED
        assert result.provider_status == "captured"

    def test_full_match_failed(self) -> None:
        attempt = make_attempt(amount=50000, currency="INR")
        provider_data = {
            "id": "fake_pay_001",
            "amount": 50000,
            "currency": "INR",
            "status": "failed",
        }
        result = _reconcile(attempt, provider_data)
        assert result.status == ReconciliationStatus.MATCHED

    def test_no_provider_data_is_unresolved(self) -> None:
        """No provider data → unresolved. Never mark as failed."""
        attempt = make_attempt()
        result = _reconcile(attempt, {})
        assert result.status == ReconciliationStatus.UNRESOLVED
        assert "unknown" in result.discrepancy_reason.lower()

    def test_amount_mismatch_is_mismatched(self) -> None:
        attempt = make_attempt(amount=50000)
        provider_data = {
            "id": "fake_pay_001",
            "amount": 45000,  # WRONG amount
            "currency": "INR",
            "status": "captured",
        }
        result = _reconcile(attempt, provider_data)
        assert result.status == ReconciliationStatus.MISMATCHED
        assert "Amount mismatch" in result.discrepancy_reason

    def test_currency_mismatch_is_mismatched(self) -> None:
        attempt = make_attempt(currency="INR")
        provider_data = {
            "id": "fake_pay_001",
            "amount": 50000,
            "currency": "USD",  # WRONG currency
            "status": "captured",
        }
        result = _reconcile(attempt, provider_data)
        assert result.status == ReconciliationStatus.MISMATCHED
        assert "Currency mismatch" in result.discrepancy_reason

    def test_provider_id_mismatch_is_mismatched(self) -> None:
        attempt = make_attempt(provider_payment_id="fake_pay_001")
        provider_data = {
            "id": "fake_pay_DIFFERENT",  # WRONG payment ID
            "amount": 50000,
            "currency": "INR",
            "status": "captured",
        }
        result = _reconcile(attempt, provider_data)
        assert result.status == ReconciliationStatus.MISMATCHED
        assert "mismatch" in result.discrepancy_reason.lower()

    def test_ambiguous_provider_status_is_unresolved(self) -> None:
        attempt = make_attempt()
        provider_data = {
            "id": "fake_pay_001",
            "amount": 50000,
            "currency": "INR",
            "status": "processing",  # Ambiguous — not captured or failed
        }
        result = _reconcile(attempt, provider_data)
        assert result.status == ReconciliationStatus.UNRESOLVED

    def test_no_provider_payment_id_no_mismatch(self) -> None:
        """If we don't have a provider ID yet, don't check it."""
        attempt = make_attempt(provider_payment_id=None)
        provider_data = {
            "id": "fake_pay_new",
            "amount": 50000,
            "currency": "INR",
            "status": "captured",
        }
        result = _reconcile(attempt, provider_data)
        assert result.status == ReconciliationStatus.MATCHED

    def test_amounts_stored_as_integer_minor_units(self) -> None:
        """Verify that reconciliation uses integer comparison (no float)."""
        attempt = make_attempt(amount=10099)  # 100.99 in paise
        provider_data = {
            "id": "fake_pay_001",
            "amount": 10099,  # Must match exactly as integer
            "currency": "INR",
            "status": "captured",
        }
        result = _reconcile(attempt, provider_data)
        assert result.status == ReconciliationStatus.MATCHED
