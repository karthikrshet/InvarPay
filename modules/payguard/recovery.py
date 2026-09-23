"""
PayGuard AI — Phase 2: Safe Recovery Engine

Provides safe, idempotent recovery recommendations for payment incidents.
ALL recovery actions require explicit human approval before execution.

Recovery strategies:
- UNKNOWN outcome: trigger reconciliation, then decide
- Failed payment: safe retry with new idempotency key
- Stale pending: query provider, update state
- Webhook missed: fetch from provider API
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class RecoveryAction(str, Enum):
    RECONCILE = "reconcile"
    RETRY_WITH_NEW_ATTEMPT = "retry_with_new_attempt"
    FETCH_FROM_PROVIDER = "fetch_from_provider"
    MANUAL_REVIEW = "manual_review"
    NO_ACTION_NEEDED = "no_action_needed"
    WAIT_FOR_WEBHOOK = "wait_for_webhook"


class RecoverySafety(str, Enum):
    SAFE = "safe"            # Can proceed automatically (after approval)
    REQUIRES_APPROVAL = "requires_approval"  # Needs human sign-off
    BLOCKED = "blocked"      # Cannot proceed — manual intervention only


@dataclass
class RecoveryRecommendation:
    """
    Deterministic recovery recommendation for a payment incident.
    LLM output never directly produces this — only deterministic rules do.
    Any action requires ApprovalRequest before execution.
    """
    action: RecoveryAction
    safety: RecoverySafety
    reason: str
    details: dict[str, Any]
    requires_approval: bool = True
    estimated_risk: str = "LOW"  # LOW / MEDIUM / HIGH / CRITICAL
    generated_at: str = ""

    def __post_init__(self) -> None:
        self.generated_at = datetime.now(timezone.utc).isoformat()


def recommend_recovery(
    payment_status: str,
    provider_status: Optional[str],
    is_reconciled: bool,
    provider_payment_id: Optional[str],
    initiated_at: Optional[datetime],
    minutes_since_initiation: Optional[float],
    failure_code: Optional[str],
) -> RecoveryRecommendation:
    """
    Deterministic recovery recommendation based on payment state.
    No LLM involved — pure rule-based logic.

    Returns a recommendation that MUST be approved before execution.
    """

    # ── UNKNOWN outcome ────────────────────────────────────────────────────────
    if payment_status == "unknown":
        if not is_reconciled:
            return RecoveryRecommendation(
                action=RecoveryAction.RECONCILE,
                safety=RecoverySafety.REQUIRES_APPROVAL,
                reason=(
                    "Payment outcome is unknown (possible network timeout). "
                    "Reconciliation must happen before any other action. "
                    "DO NOT retry — payment may already be captured."
                ),
                details={
                    "invariant": "unknown != failed",
                    "safe_to_retry": False,
                    "next_step": "Run reconciliation against provider API",
                },
                estimated_risk="HIGH",
            )
        else:
            return RecoveryRecommendation(
                action=RecoveryAction.MANUAL_REVIEW,
                safety=RecoverySafety.BLOCKED,
                reason="Reconciliation completed but outcome still unknown. Manual investigation required.",
                details={"provider_payment_id": provider_payment_id},
                estimated_risk="HIGH",
            )

    # ── FAILED — safe to retry ─────────────────────────────────────────────────
    if payment_status == "failed":
        return RecoveryRecommendation(
            action=RecoveryAction.RETRY_WITH_NEW_ATTEMPT,
            safety=RecoverySafety.REQUIRES_APPROVAL,
            reason=(
                f"Payment definitively failed (code: {failure_code or 'unknown'}). "
                "A new payment attempt is safe — the failure is confirmed."
            ),
            details={
                "safe_to_retry": True,
                "new_idempotency_key_required": True,
                "failure_code": failure_code,
            },
            estimated_risk="LOW",
        )

    # ── CAPTURED — no recovery needed ─────────────────────────────────────────
    if payment_status == "captured":
        return RecoveryRecommendation(
            action=RecoveryAction.NO_ACTION_NEEDED,
            safety=RecoverySafety.SAFE,
            reason="Payment successfully captured. No recovery action needed.",
            details={"fulfillment_check": "Verify business fulfillment was triggered"},
            requires_approval=False,
            estimated_risk="LOW",
        )

    # ── PENDING — stale detection ──────────────────────────────────────────────
    if payment_status == "pending":
        stale_threshold_minutes = 30
        if minutes_since_initiation and minutes_since_initiation > stale_threshold_minutes:
            return RecoveryRecommendation(
                action=RecoveryAction.FETCH_FROM_PROVIDER,
                safety=RecoverySafety.REQUIRES_APPROVAL,
                reason=(
                    f"Payment has been pending for {minutes_since_initiation:.0f} minutes "
                    f"(threshold: {stale_threshold_minutes}m). Fetching from provider."
                ),
                details={"provider_payment_id": provider_payment_id},
                estimated_risk="MEDIUM",
            )
        return RecoveryRecommendation(
            action=RecoveryAction.WAIT_FOR_WEBHOOK,
            safety=RecoverySafety.SAFE,
            reason="Payment is pending. Waiting for webhook delivery.",
            details={"minutes_elapsed": minutes_since_initiation},
            requires_approval=False,
            estimated_risk="LOW",
        )

    # ── DEFAULT ────────────────────────────────────────────────────────────────
    return RecoveryRecommendation(
        action=RecoveryAction.MANUAL_REVIEW,
        safety=RecoverySafety.REQUIRES_APPROVAL,
        reason=f"Unrecognised payment status '{payment_status}'. Manual review required.",
        details={"status": payment_status},
        estimated_risk="MEDIUM",
    )
