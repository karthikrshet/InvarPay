"""
Phase 3 tests: PaymentGraph fraud rule engine.
All tests use SYNTHETIC data. No real fraud assessments.
"""
from __future__ import annotations

from modules.paymentgraph.rules import (
    RiskLevel,
    SignalConfidence,
    compute_risk_assessment,
    signal_amount_anomaly,
    signal_unknown_outcome_history,
    signal_unverified_webhooks,
    signal_velocity_check,
)


class TestFraudSignals:
    """Test individual fraud signal computations."""

    def test_high_velocity_triggers(self) -> None:
        signal = signal_velocity_check(payment_count_last_hour=15, threshold=10)
        assert signal.triggered is True
        assert signal.name == "high_velocity"

    def test_normal_velocity_no_trigger(self) -> None:
        signal = signal_velocity_check(payment_count_last_hour=5, threshold=10)
        assert signal.triggered is False

    def test_amount_anomaly_extreme_amount(self) -> None:
        signal = signal_amount_anomaly(amount=500_000_00)  # ₹50000 — extreme
        assert signal.triggered is True

    def test_normal_amount_no_trigger(self) -> None:
        signal = signal_amount_anomaly(amount=50000)  # ₹500 — normal
        assert signal.triggered is False

    def test_repeated_unknowns_trigger(self) -> None:
        signal = signal_unknown_outcome_history(previous_unknown_count=3, threshold=2)
        assert signal.triggered is True

    def test_unverified_webhooks_always_trigger(self) -> None:
        signal = signal_unverified_webhooks(unverified_count=1, total_count=5)
        assert signal.triggered is True
        assert signal.confidence == SignalConfidence.HIGH

    def test_no_unverified_no_trigger(self) -> None:
        signal = signal_unverified_webhooks(unverified_count=0, total_count=5)
        assert signal.triggered is False


class TestRiskAssessment:
    """Test composite risk assessment."""

    def test_clean_payment_low_risk(self) -> None:
        """Clean payment with no signals → low risk."""
        result = compute_risk_assessment(
            payment_attempt_id="pay_test_123",
            organization_id="org_test_456",
            amount=50000,  # ₹500 — normal
            payment_count_last_hour=2,
            previous_unknown_count=0,
            unverified_webhooks=0,
            total_webhooks=3,
        )
        assert result.risk_level in (RiskLevel.LOW,)
        assert result.composite_score < 0.5
        assert result.requires_human_review is True  # Always required

    def test_suspicious_payment_higher_risk(self) -> None:
        """Multiple signals triggered → medium/high risk."""
        result = compute_risk_assessment(
            payment_attempt_id="pay_suspicious_123",
            organization_id="org_test_456",
            amount=500_000_00,  # Extreme amount
            payment_count_last_hour=50,  # High velocity
            previous_unknown_count=5,   # Repeated unknowns
            unverified_webhooks=2,       # Signature failures
            total_webhooks=3,
        )
        assert result.composite_score > 0.3
        assert result.requires_human_review is True

    def test_assessment_always_requires_human_review(self) -> None:
        """Safety invariant: every assessment requires human review."""
        for amount in [100, 50000, 1_000_000]:
            result = compute_risk_assessment(
                payment_attempt_id="test",
                organization_id="org_test",
                amount=amount,
            )
            assert result.requires_human_review is True, (
                "Risk assessment must ALWAYS require human review — "
                "never auto-deny based on score alone"
            )

    def test_all_signals_have_explanations(self) -> None:
        """Every signal must have a non-empty explanation."""
        result = compute_risk_assessment(
            payment_attempt_id="test",
            organization_id="org_test",
            amount=50000,
        )
        for signal in result.signals:
            assert signal.explanation, f"Signal '{signal.name}' has no explanation"
            assert signal.name, "Signal has no name"
