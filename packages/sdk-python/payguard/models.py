"""
InvarPay AI Python SDK — Data Models
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class PaymentAttempt:
    id: str
    organization_id: str
    order_id: str
    amount: int
    currency: str
    status: str
    provider: str
    provider_payment_id: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class RecoveryRecommendation:
    action: str
    safety: str
    reason: str
    requires_approval: bool
    estimated_risk: str


@dataclass
class RiskAssessment:
    payment_attempt_id: str
    risk_level: str
    composite_score: float
    explanation: str
    requires_human_review: bool
