"""
Phase 2 tests: Recovery engine deterministic recommendations.
All tests use SYNTHETIC data — no real payments.
"""
from __future__ import annotations

from modules.payguard.recovery import RecoveryAction, RecoverySafety, recommend_recovery


class TestRecoveryRecommendations:
    """Test deterministic recovery recommendations."""

    def test_unknown_unreconciled_recommends_reconcile(self) -> None:
        """Unknown + unreconciled → must reconcile before any action."""
        rec = recommend_recovery(
            payment_status="unknown",
            provider_status=None,
            is_reconciled=False,
            provider_payment_id=None,
            initiated_at=None,
            minutes_since_initiation=None,
            failure_code=None,
        )
        assert rec.action == RecoveryAction.RECONCILE
        assert rec.requires_approval is True
        assert rec.estimated_risk == "HIGH"

    def test_unknown_reconciled_requires_manual_review(self) -> None:
        """Unknown + reconciled but still unresolved → manual review."""
        rec = recommend_recovery(
            payment_status="unknown",
            provider_status=None,
            is_reconciled=True,
            provider_payment_id="pay_test_123",
            initiated_at=None,
            minutes_since_initiation=None,
            failure_code=None,
        )
        assert rec.action == RecoveryAction.MANUAL_REVIEW
        assert rec.safety == RecoverySafety.BLOCKED

    def test_failed_recommends_retry(self) -> None:
        """Failed payment → safe to retry with new attempt."""
        rec = recommend_recovery(
            payment_status="failed",
            provider_status="failed",
            is_reconciled=True,
            provider_payment_id=None,
            initiated_at=None,
            minutes_since_initiation=None,
            failure_code="insufficient_funds",
        )
        assert rec.action == RecoveryAction.RETRY_WITH_NEW_ATTEMPT
        assert rec.details["safe_to_retry"] is True
        assert rec.estimated_risk == "LOW"

    def test_captured_no_action_needed(self) -> None:
        """Captured payment → no recovery needed."""
        rec = recommend_recovery(
            payment_status="captured",
            provider_status="captured",
            is_reconciled=True,
            provider_payment_id="pay_123",
            initiated_at=None,
            minutes_since_initiation=None,
            failure_code=None,
        )
        assert rec.action == RecoveryAction.NO_ACTION_NEEDED
        assert rec.requires_approval is False

    def test_pending_not_stale_waits(self) -> None:
        """Fresh pending payment → wait for webhook."""
        rec = recommend_recovery(
            payment_status="pending",
            provider_status="created",
            is_reconciled=False,
            provider_payment_id=None,
            initiated_at=None,
            minutes_since_initiation=5.0,  # 5 minutes — not stale
            failure_code=None,
        )
        assert rec.action == RecoveryAction.WAIT_FOR_WEBHOOK
        assert rec.requires_approval is False

    def test_stale_pending_fetches_from_provider(self) -> None:
        """Stale pending payment → fetch from provider."""
        rec = recommend_recovery(
            payment_status="pending",
            provider_status="created",
            is_reconciled=False,
            provider_payment_id="pay_123",
            initiated_at=None,
            minutes_since_initiation=45.0,  # 45 minutes — stale
            failure_code=None,
        )
        assert rec.action == RecoveryAction.FETCH_FROM_PROVIDER
        assert rec.estimated_risk == "MEDIUM"

    def test_unknown_never_safe_to_retry(self) -> None:
        """Safety invariant: unknown status never results in retry recommendation."""
        rec = recommend_recovery(
            payment_status="unknown",
            provider_status=None,
            is_reconciled=False,
            provider_payment_id=None,
            initiated_at=None,
            minutes_since_initiation=None,
            failure_code=None,
        )
        # Must never recommend retry for unknown
        assert rec.action != RecoveryAction.RETRY_WITH_NEW_ATTEMPT
        # Always requires approval
        assert rec.requires_approval is True
