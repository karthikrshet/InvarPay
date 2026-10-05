"""
InvarPay AI — InvarInvestigator Deterministic Policy Layer
Connects to the repository's existing Agent Policy Engine.
Enforces non-negotiable financial invariants regardless of AI recommendation:
1. UNKNOWN IS NOT FAILED: AUTOMATIC_RETRY is STRICTLY DENIED for UNKNOWN payments.
2. CAPTURED IS TERMINAL: RETRY is STRICTLY DENIED for CAPTURED payments.
3. FAILED payments allow retry if authorized by policy.
4. Cross-tenant investigations are strictly blocked.
5. AI can never directly authorize money movement or mutate financial records.
"""
from __future__ import annotations

import logging

from apps.api.app.agents.policy_engine import PolicyEngine
from modules.investigator.schemas import (
    InvestigationEvidence,
    InvestigationResult,
    PolicyDecision,
    PolicyEvaluationResult,
    RecommendedAction,
)

logger = logging.getLogger(__name__)


class InvestigatorPolicyEngine:
    """
    Authoritative deterministic gatekeeper for AI investigation recommendations.
    Wraps the core PolicyEngine.
    """

    def __init__(self, organization_id: str) -> None:
        self.organization_id = organization_id
        self.core_policy = PolicyEngine(organization_id=organization_id)

    def evaluate(
        self,
        evidence: InvestigationEvidence,
        ai_result: InvestigationResult,
    ) -> PolicyEvaluationResult:
        """
        Deterministically evaluates AI findings against hard financial invariants.
        Returns the authoritative policy verdict.
        """
        # 1. Tenant boundary enforcement
        if evidence.organization_id != self.organization_id:
            logger.error(
                "Tenant violation in policy engine: context=%s, evidence=%s",
                self.organization_id, evidence.organization_id
            )
            return PolicyEvaluationResult(
                recommendation=ai_result.recommendation,
                policy_approved=False,
                final_action="BLOCKED",
                decisions=[
                    PolicyDecision(
                        action=ai_result.recommendation,
                        allowed=False,
                        blocked_reason=f"Cross-tenant access strictly blocked: {self.organization_id} != {evidence.organization_id}",
                        policy_rule="RULE_TENANT_ISOLATION",
                    )
                ],
                blocked_actions=[ai_result.recommendation, "AUTOMATIC_RETRY", "RECONCILE"],
                allowed_actions=[],
                explanation="Tenant boundary mismatch: Access denied under tenant isolation invariant.",
            )

        decisions: list[PolicyDecision] = []
        blocked_actions: set[str] = set()
        allowed_actions: set[str] = set()

        raw_rec = (ai_result.recommendation or "").upper().strip()
        current_status = (evidence.current_status or "").lower().strip()

        # ── INVARIANT 1: UNKNOWN IS NOT FAILED ────────────────────────────────
        if current_status == "unknown":
            # AUTOMATIC_RETRY is non-negotiably blocked for UNKNOWN status
            retry_decision = PolicyDecision(
                action=RecommendedAction.AUTOMATIC_RETRY.value,
                allowed=False,
                blocked_reason="Payment outcome is UNKNOWN (UNKNOWN ≠ FAILED). Automatic retry is forbidden until authoritative reconciliation.",
                policy_rule="INVARIANT_UNKNOWN_NOT_FAILED",
            )
            decisions.append(retry_decision)
            blocked_actions.add(RecommendedAction.AUTOMATIC_RETRY.value)

            # RECONCILE and MANUAL_REVIEW are safe and permitted
            reconcile_decision = PolicyDecision(
                action=RecommendedAction.RECONCILE.value,
                allowed=True,
                blocked_reason=None,
                policy_rule="INVARIANT_RECONCILE_MANDATORY_FOR_UNKNOWN",
            )
            decisions.append(reconcile_decision)
            allowed_actions.add(RecommendedAction.RECONCILE.value)
            allowed_actions.add(RecommendedAction.MANUAL_REVIEW.value)

        # ── INVARIANT 2: CAPTURED IS TERMINAL ─────────────────────────────────
        elif current_status == "captured":
            # Retrying a captured payment causes double charging
            retry_decision = PolicyDecision(
                action=RecommendedAction.AUTOMATIC_RETRY.value,
                allowed=False,
                blocked_reason="Payment is already CAPTURED in terminal state. Retries are strictly blocked.",
                policy_rule="INVARIANT_CAPTURED_TERMINAL",
            )
            decisions.append(retry_decision)
            blocked_actions.add(RecommendedAction.AUTOMATIC_RETRY.value)

            no_action_decision = PolicyDecision(
                action=RecommendedAction.NO_ACTION_REQUIRED.value,
                allowed=True,
                blocked_reason=None,
                policy_rule="INVARIANT_TERMINAL_SETTLED",
            )
            decisions.append(no_action_decision)
            allowed_actions.add(RecommendedAction.NO_ACTION_REQUIRED.value)

        # ── INVARIANT 3: DETERMINISTIC FAILURE RETRY ──────────────────────────
        elif current_status in ("failed", "cancelled"):
            retry_decision = PolicyDecision(
                action=RecommendedAction.AUTOMATIC_RETRY.value,
                allowed=True,
                blocked_reason=None,
                policy_rule="INVARIANT_DETERMINISTIC_FAILURE_RETRY_PERMITTED",
            )
            decisions.append(retry_decision)
            allowed_actions.add(RecommendedAction.AUTOMATIC_RETRY.value)
            allowed_actions.add(RecommendedAction.MANUAL_REVIEW.value)

        # ── OTHER STATES (CREATED, PENDING) ──────────────────────────────────
        else:
            allowed_actions.add(RecommendedAction.RECONCILE.value)
            allowed_actions.add(RecommendedAction.MANUAL_REVIEW.value)
            blocked_actions.add(RecommendedAction.AUTOMATIC_RETRY.value)
            decisions.append(
                PolicyDecision(
                    action=RecommendedAction.AUTOMATIC_RETRY.value,
                    allowed=False,
                    blocked_reason=f"Payment is in in-flight status '{current_status}'. Awaiting webhook delivery.",
                    policy_rule="INVARIANT_IN_FLIGHT_GUARD",
                )
            )

        # ── RECONCILIATION OF AI RECOMMENDATION WITH POLICY ────────────────────
        policy_approved = False
        final_action = raw_rec

        if raw_rec == RecommendedAction.AUTOMATIC_RETRY.value:
            if current_status == "unknown":
                # Policy rejects AI recommendation to retry UNKNOWN!
                policy_approved = False
                final_action = RecommendedAction.RECONCILE.value
                explanation = (
                    "BLOCKED: AI proposed AUTOMATIC_RETRY on UNKNOWN payment. "
                    "Policy Engine strictly intercepted and blocked retry (UNKNOWN ≠ FAILED). "
                    "Authoritative action forced to RECONCILE."
                )
            elif current_status == "captured":
                policy_approved = False
                final_action = RecommendedAction.NO_ACTION_REQUIRED.value
                explanation = (
                    "BLOCKED: AI proposed AUTOMATIC_RETRY on CAPTURED payment. "
                    "Policy Engine blocked retry to prevent duplicate billing."
                )
            elif current_status in ("failed", "cancelled"):
                policy_approved = True
                final_action = RecommendedAction.AUTOMATIC_RETRY.value
                explanation = "APPROVED: Payment is definitively FAILED. Automatic retry with a new attempt is safe."
            else:
                policy_approved = False
                final_action = RecommendedAction.RECONCILE.value
                explanation = f"BLOCKED: Automatic retry not permitted for payment status '{current_status}'."

        elif raw_rec == RecommendedAction.RECONCILE.value:
            policy_approved = True
            final_action = RecommendedAction.RECONCILE.value
            explanation = "APPROVED: Reconciliation recommended and permitted by policy."

        elif raw_rec in (RecommendedAction.FLAG_FRAUD.value, RecommendedAction.HOLD_SETTLEMENT.value):
            policy_approved = True
            final_action = raw_rec
            explanation = f"APPROVED: Risk advisory action '{raw_rec}' accepted by policy."

        elif raw_rec == RecommendedAction.NO_ACTION_REQUIRED.value:
            policy_approved = True
            final_action = RecommendedAction.NO_ACTION_REQUIRED.value
            explanation = "APPROVED: Payment lifecycle verified settled."

        elif raw_rec == RecommendedAction.UNCERTAIN.value:
            policy_approved = True
            final_action = RecommendedAction.MANUAL_REVIEW.value
            explanation = "ACCEPTED: Evidence was uncertain. Escalating to human manual review queue."

        else:
            # Unknown or unexpected action — deny by default
            policy_approved = False
            final_action = RecommendedAction.MANUAL_REVIEW.value
            explanation = f"BLOCKED: Proposed action '{raw_rec}' is unrecognized. Defaulting to MANUAL_REVIEW (deny-by-default)."
            blocked_actions.add(raw_rec)

        return PolicyEvaluationResult(
            recommendation=ai_result.recommendation,
            policy_approved=policy_approved,
            final_action=final_action,
            decisions=decisions,
            blocked_actions=sorted(blocked_actions),
            allowed_actions=sorted(allowed_actions),
            explanation=explanation,
        )
