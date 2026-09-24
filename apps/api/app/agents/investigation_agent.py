"""
PayGuard AI — Investigation Agent (LangGraph)

AI-assisted payment investigation with strict safety boundaries:
- Read-only tools by default
- Policy enforcement before every tool call
- Human approval required for any write operation
- LLM output is a PROPOSAL only — never directly mutates payment state
- Prompt injection resistance: structured tool schemas, no eval

INVARIANT: No agent tool may modify payment state or initiate charges.
           Write operations require ApprovalRequest creation and human review.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional, TypedDict

from apps.api.app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ── Tool definitions ───────────────────────────────────────────────────────────

class InvestigationState(TypedDict):
    """LangGraph state for investigation agent."""
    payment_attempt_id: str
    organization_id: str
    messages: list[dict]
    tool_calls: list[dict]
    findings: Optional[dict]
    recommendation: Optional[str]
    requires_approval: bool
    completed: bool
    error: Optional[str]


# ── Policy Engine ──────────────────────────────────────────────────────────────

class PolicyViolationError(Exception):
    """Raised when an agent tool call violates policy."""
    pass


ALLOWED_TOOLS: set[str] = {
    "get_payment_attempt",
    "get_provider_events",
    "get_audit_trail",
    "get_reconciliation_history",
    # NOT included: any write/mutation tools
}

WRITE_TOOLS_REQUIRE_APPROVAL: set[str] = {
    "request_refund",
    "mark_for_manual_review",
    "create_approval_request",
}


def check_tool_policy(
    tool_name: str,
    organization_id: str,
    requested_org_id: str,
) -> None:
    """
    Enforce tool-level policy before execution.
    Raises PolicyViolationError on any violation.

    Checks:
    1. Tool is in allowed set (deny-by-default)
    2. Organization scope matches (no cross-tenant)
    3. Write tools are blocked by default (require approval)
    """
    # Check 1: Tool allowed?
    if tool_name not in ALLOWED_TOOLS and tool_name not in WRITE_TOOLS_REQUIRE_APPROVAL:
        raise PolicyViolationError(
            f"Tool '{tool_name}' is not in the allowed tool set. "
            "Deny-by-default policy enforced."
        )

    # Check 2: Cross-tenant access?
    if requested_org_id != organization_id:
        raise PolicyViolationError(
            f"Cross-tenant tool call blocked: agent context is org {organization_id}, "
            f"but tool requested org {requested_org_id}."
        )

    # Check 3: Write tool without approval?
    if tool_name in WRITE_TOOLS_REQUIRE_APPROVAL:
        raise PolicyViolationError(
            f"Write tool '{tool_name}' requires explicit human approval. "
            "Create an ApprovalRequest and wait for review."
        )


# ── Tool implementations (read-only) ──────────────────────────────────────────

async def tool_get_payment_attempt(
    payment_attempt_id: str,
    organization_id: str,
    db: Any,
) -> dict:
    """Read-only: fetch payment attempt data."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from apps.api.app.models import PaymentAttempt

    result = await db.execute(
        select(PaymentAttempt)
        .options(selectinload(PaymentAttempt.provider_events))
        .where(
            PaymentAttempt.id == payment_attempt_id,
            PaymentAttempt.organization_id == organization_id,
        )
    )
    attempt = result.scalar_one_or_none()
    if not attempt:
        return {"error": "Payment attempt not found or access denied"}

    return {
        "id": attempt.id,
        "status": attempt.status.value,
        "provider_status": attempt.provider_status,
        "provider_payment_id": attempt.provider_payment_id,
        "amount": attempt.amount,
        "currency": attempt.currency,
        "is_reconciled": attempt.is_reconciled,
        "initiated_at": attempt.initiated_at.isoformat() if attempt.initiated_at else None,
        "captured_at": attempt.captured_at.isoformat() if attempt.captured_at else None,
        "failed_at": attempt.failed_at.isoformat() if attempt.failed_at else None,
        "failure_reason": attempt.failure_reason,
        "provider_events_count": len(attempt.provider_events),
    }


async def tool_get_provider_events(
    payment_attempt_id: str,
    organization_id: str,
    db: Any,
) -> dict:
    """Read-only: fetch all verified provider events for a payment."""
    from sqlalchemy import select

    from apps.api.app.models import ProviderEvent

    result = await db.execute(
        select(ProviderEvent).where(
            ProviderEvent.payment_attempt_id == payment_attempt_id,
            ProviderEvent.organization_id == organization_id,
        ).order_by(ProviderEvent.received_at)
    )
    events = result.scalars().all()

    return {
        "events": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "provider": e.provider,
                "provider_event_id": e.provider_event_id,
                "signature_verified": e.signature_verified,
                "processed": e.processed,
                "received_at": e.received_at.isoformat(),
                # NOTE: raw_payload not included to reduce LLM context size
                # and avoid sending sensitive data to external LLM
            }
            for e in events
        ],
        "total": len(events),
        "all_signatures_verified": all(e.signature_verified for e in events),
    }


async def tool_get_audit_trail(
    resource_id: str,
    organization_id: str,
    db: Any,
) -> dict:
    """Read-only: fetch audit events for a resource."""
    from sqlalchemy import select

    from apps.api.app.models import AuditEvent

    result = await db.execute(
        select(AuditEvent).where(
            AuditEvent.resource_id == resource_id,
            AuditEvent.organization_id == organization_id,
        ).order_by(AuditEvent.occurred_at)
    )
    events = result.scalars().all()

    return {
        "audit_events": [
            {
                "id": e.id,
                "action": e.action,
                "actor_type": e.actor_type,
                "occurred_at": e.occurred_at.isoformat(),
                "event_hash": e.event_hash,
            }
            for e in events
        ],
        "total": len(events),
    }


# ── Deterministic investigation (no LLM required) ─────────────────────────────

async def run_deterministic_investigation(
    payment_attempt_id: str,
    organization_id: str,
    db: Any,
) -> dict:
    """
    Run a deterministic (no-LLM) investigation of a payment outcome.
    Used when LLM is not configured or as a fallback.

    This is the primary investigation path for MVP.
    LLM-enhanced investigation is a Phase 2 feature.
    """
    findings: dict[str, Any] = {}
    issues: list[str] = []
    recommendations: list[str] = []

    # 1. Get payment data
    payment_data = await tool_get_payment_attempt(payment_attempt_id, organization_id, db)
    findings["payment"] = payment_data

    if "error" in payment_data:
        return {"error": payment_data["error"]}

    status = payment_data["status"]
    findings["status_analysis"] = {}

    # 2. Analyze state
    if status == "unknown":
        issues.append("Payment outcome is UNKNOWN — possible network timeout or provider error")
        issues.append("SAFETY: Do not retry until reconciliation confirms the outcome")
        recommendations.append("Run reconciliation to determine actual provider status")
        recommendations.append("Check provider dashboard for payment " + str(payment_data.get("provider_payment_id") or "ID unknown"))
        findings["status_analysis"]["risk"] = "HIGH"
        findings["status_analysis"]["safe_to_retry"] = False
        findings["status_analysis"]["reason"] = "Unknown outcomes may already be captured — retrying risks duplicate charge"

    elif status == "captured":
        findings["status_analysis"]["risk"] = "NONE"
        findings["status_analysis"]["safe_to_retry"] = False
        findings["status_analysis"]["reason"] = "Payment successfully captured — no action needed"
        recommendations.append("Payment captured. Trigger business fulfillment if not already done.")

    elif status == "failed":
        findings["status_analysis"]["risk"] = "LOW"
        findings["status_analysis"]["safe_to_retry"] = True
        findings["status_analysis"]["reason"] = "Definitive failure — retry is safe with a new payment attempt"
        recommendations.append(f"Failure reason: {payment_data.get('failure_reason') or 'not specified'}")
        recommendations.append("Safe to create a new payment attempt for this order")

    elif status == "pending":
        issues.append("Payment is still pending — may be processing")
        recommendations.append("Wait for webhook delivery before taking action")
        findings["status_analysis"]["safe_to_retry"] = False

    # 3. Get provider events
    events_data = await tool_get_provider_events(payment_attempt_id, organization_id, db)
    findings["provider_events"] = events_data

    if not events_data.get("all_signatures_verified") and events_data.get("total", 0) > 0:
        issues.append("WARNING: Some provider events could not be signature-verified")

    if events_data.get("total", 0) == 0 and status not in ("created", "initiated"):
        issues.append("No provider webhooks received — possible delivery failure")
        recommendations.append("Check provider webhook configuration and delivery logs")

    # 4. Get audit trail
    audit_data = await tool_get_audit_trail(payment_attempt_id, organization_id, db)
    findings["audit_trail"] = audit_data

    return {
        "findings": findings,
        "issues_detected": issues,
        "recommendations": recommendations,
        "investigation_type": "deterministic",
        "llm_used": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "disclaimer": (
            "This investigation uses deterministic rules only. "
            "No LLM output is involved. "
            "Recommendations are proposals only — human review required for any action."
        ),
    }


async def run_investigation(
    payment_attempt_id: str,
    organization_id: str,
    db: Any,
) -> dict:
    """
    Main investigation entry point.
    Uses LLM if configured, otherwise runs deterministic investigation.
    """
    if not settings.llm_configured:
        logger.info(
            "LLM not configured — running deterministic investigation for %s",
            payment_attempt_id
        )
        return await run_deterministic_investigation(payment_attempt_id, organization_id, db)

    # Phase 2: LLM-enhanced investigation
    # For MVP, fall back to deterministic
    logger.info("LLM configured but Phase 2 agent not yet implemented — using deterministic path")
    return await run_deterministic_investigation(payment_attempt_id, organization_id, db)
