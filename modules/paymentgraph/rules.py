"""
InvarPay AI — Phase 3: PaymentGraph Fraud Rule Engine

Deterministic, explainable fraud signal computation.
NO black-box ML scores are presented as authoritative fraud labels.

Every signal has:
- Name and description
- Computed value
- Threshold and why
- Human-readable explanation
- Confidence level

IMPORTANT CONSTRAINTS:
- Never assert a real fraud score without calibrated evaluation
- Every rule is documented and auditable
- Scores require human review before action
- Model card must be present before any ML claims
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class SignalConfidence(str, Enum):
    HIGH = "high"      # Rule is well-tested, low false-positive rate
    MEDIUM = "medium"  # Rule is reasonable but not exhaustively tested
    LOW = "low"        # Heuristic — treat as a weak signal only


@dataclass
class FraudSignal:
    """A single explainable fraud signal."""
    name: str
    value: Any
    triggered: bool
    explanation: str
    confidence: SignalConfidence
    weight: float = 1.0  # Relative weight in composite score
    references: list[str] = field(default_factory=list)


@dataclass
class RiskAssessmentResult:
    """
    Complete risk assessment result.

    DISCLAIMER: This is a research prototype, NOT a production fraud system.
    All signals are rule-based heuristics computed on SYNTHETIC or public data.
    Do not use to deny real transactions without human review.
    """
    payment_attempt_id: str
    organization_id: str
    risk_level: RiskLevel
    composite_score: float   # 0.0 (lowest risk) – 1.0 (highest risk)
    signals: list[FraudSignal]
    explanation: str
    requires_human_review: bool
    model_version: str = "rule_engine_v1"
    assessed_at: str = ""
    disclaimer: str = (
        "Research prototype. Not a production fraud system. "
        "All signals are heuristics. Human review required before any action."
    )

    def __post_init__(self) -> None:
        self.assessed_at = datetime.now(timezone.utc).isoformat()
        self.requires_human_review = True  # Always require review


# ── Rule implementations ───────────────────────────────────────────────────────

def signal_velocity_check(
    payment_count_last_hour: int,
    threshold: int = 10,
) -> FraudSignal:
    """High payment velocity — many attempts in a short window."""
    triggered = payment_count_last_hour > threshold
    return FraudSignal(
        name="high_velocity",
        value=payment_count_last_hour,
        triggered=triggered,
        explanation=(
            f"{payment_count_last_hour} payments in the last hour "
            f"({'exceeds' if triggered else 'within'} threshold of {threshold})"
        ),
        confidence=SignalConfidence.MEDIUM,
        weight=2.0,
        references=["velocity_threshold_v1"],
    )


def signal_amount_anomaly(
    amount: int,
    typical_min: int = 100,
    typical_max: int = 10_000_00,  # 1 lakh paise = ₹1000
    extreme_max: int = 100_000_00,  # ₹10000
) -> FraudSignal:
    """Amount outside typical range."""
    triggered = amount > extreme_max or amount < typical_min
    return FraudSignal(
        name="amount_anomaly",
        value=amount,
        triggered=triggered,
        explanation=(
            f"Amount {amount} paise "
            f"({'outside' if triggered else 'within'} typical range "
            f"{typical_min}–{extreme_max})"
        ),
        confidence=SignalConfidence.LOW,
        weight=1.0,
    )


def signal_unknown_outcome_history(
    previous_unknown_count: int,
    threshold: int = 2,
) -> FraudSignal:
    """Multiple unknown outcomes may indicate manipulation."""
    triggered = previous_unknown_count >= threshold
    return FraudSignal(
        name="repeated_unknown_outcomes",
        value=previous_unknown_count,
        triggered=triggered,
        explanation=(
            f"{previous_unknown_count} previous unknown-outcome payments "
            f"({'suspicious pattern' if triggered else 'normal'})"
        ),
        confidence=SignalConfidence.MEDIUM,
        weight=1.5,
    )


def signal_unverified_webhooks(
    unverified_count: int,
    total_count: int,
) -> FraudSignal:
    """Webhook signature failures may indicate tampering."""
    ratio = unverified_count / max(total_count, 1)
    triggered = unverified_count > 0
    return FraudSignal(
        name="unverified_webhooks",
        value={"unverified": unverified_count, "total": total_count, "ratio": ratio},
        triggered=triggered,
        explanation=(
            f"{unverified_count}/{total_count} webhooks failed signature verification"
        ),
        confidence=SignalConfidence.HIGH,
        weight=3.0,  # High weight — signature failure is always suspicious
    )


def signal_new_customer(
    customer_age_hours: Optional[float],
    threshold_hours: float = 24.0,
) -> FraudSignal:
    """Recently created customer account."""
    if customer_age_hours is None:
        triggered = False
        explanation = "Customer age unknown"
    else:
        triggered = customer_age_hours < threshold_hours
        explanation = (
            f"Customer created {customer_age_hours:.1f}h ago "
            f"({'new account' if triggered else 'established account'})"
        )
    return FraudSignal(
        name="new_customer",
        value=customer_age_hours,
        triggered=triggered,
        explanation=explanation,
        confidence=SignalConfidence.LOW,
        weight=0.5,
    )


# ── Composite scorer ───────────────────────────────────────────────────────────

def compute_risk_assessment(
    payment_attempt_id: str,
    organization_id: str,
    amount: int,
    payment_count_last_hour: int = 0,
    previous_unknown_count: int = 0,
    unverified_webhooks: int = 0,
    total_webhooks: int = 0,
    customer_age_hours: Optional[float] = None,
) -> RiskAssessmentResult:
    """
    Compute a composite risk assessment from deterministic signals.
    Score is a simple weighted sum of triggered signals, normalized to 0-1.
    """
    signals = [
        signal_velocity_check(payment_count_last_hour),
        signal_amount_anomaly(amount),
        signal_unknown_outcome_history(previous_unknown_count),
        signal_unverified_webhooks(unverified_webhooks, total_webhooks),
        signal_new_customer(customer_age_hours),
    ]

    total_weight = sum(s.weight for s in signals)
    triggered_weight = sum(s.weight for s in signals if s.triggered)
    composite_score = triggered_weight / total_weight if total_weight > 0 else 0.0

    if composite_score >= 0.7:
        risk_level = RiskLevel.HIGH
    elif composite_score >= 0.4:
        risk_level = RiskLevel.MEDIUM
    elif composite_score >= 0.15:
        risk_level = RiskLevel.LOW
    else:
        risk_level = RiskLevel.LOW

    triggered = [s for s in signals if s.triggered]
    explanation = (
        f"Risk level {risk_level.value} (score {composite_score:.2f}). "
        f"{len(triggered)} of {len(signals)} signals triggered: "
        + (", ".join(s.name for s in triggered) if triggered else "none")
    )

    return RiskAssessmentResult(
        payment_attempt_id=payment_attempt_id,
        organization_id=organization_id,
        risk_level=risk_level,
        composite_score=round(composite_score, 4),
        signals=signals,
        explanation=explanation,
        requires_human_review=True,
    )
