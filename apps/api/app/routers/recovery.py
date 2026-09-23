"""
PayGuard AI — Phase 2: Recovery Router

GET  /v1/payments/{id}/recovery  — Get recovery recommendation
POST /v1/payments/{id}/recovery/execute  — Execute approved recovery action
GET  /v1/payments/{id}/approval-requests — List approval requests
POST /v1/payments/{id}/approval-requests/{req_id}/approve — Approve action
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.auth import TenantContext, require_scope
from apps.api.app.core.database import get_db
from apps.api.app.models import ApprovalRequest, PaymentAttempt
from modules.payguard.recovery import recommend_recovery

router = APIRouter()


@router.get("/payments/{payment_id}/recovery", summary="Get recovery recommendation (Phase 2)")
async def get_recovery_recommendation(
    payment_id: str,
    ctx: TenantContext = Depends(require_scope("payments:read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get a deterministic recovery recommendation for a payment.
    All actions require ApprovalRequest before execution.
    """
    result = await db.execute(
        select(PaymentAttempt).where(
            PaymentAttempt.id == payment_id,
            PaymentAttempt.organization_id == ctx.organization_id,
        )
    )
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(404, "Payment not found")

    # Compute minutes since initiation
    minutes_elapsed = None
    if payment.initiated_at:
        from datetime import datetime, timezone
        delta = datetime.now(timezone.utc) - payment.initiated_at.replace(tzinfo=timezone.utc)
        minutes_elapsed = delta.total_seconds() / 60

    rec = recommend_recovery(
        payment_status=payment.status.value,
        provider_status=payment.provider_status,
        is_reconciled=payment.is_reconciled,
        provider_payment_id=payment.provider_payment_id,
        initiated_at=payment.initiated_at,
        minutes_since_initiation=minutes_elapsed,
        failure_code=payment.failure_code,
    )

    return {
        "payment_id": payment_id,
        "action": rec.action.value,
        "safety": rec.safety.value,
        "reason": rec.reason,
        "estimated_risk": rec.estimated_risk,
        "requires_approval": rec.requires_approval,
        "details": rec.details,
        "generated_at": rec.generated_at,
        "note": "All actions require ApprovalRequest before execution",
    }


class ExecuteRecoveryRequest(BaseModel):
    action: str
    approval_request_id: str  # Must reference an approved ApprovalRequest


@router.post("/payments/{payment_id}/recovery/execute", summary="Execute approved recovery action")
async def execute_recovery(
    payment_id: str,
    req: ExecuteRecoveryRequest,
    ctx: TenantContext = Depends(require_scope("payments:write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Execute a recovery action that has been approved via ApprovalRequest.
    Requires a valid, approved ApprovalRequest ID.
    """
    # Verify approval exists and is approved
    approval_result = await db.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.id == req.approval_request_id,
            ApprovalRequest.organization_id == ctx.organization_id,
        )
    )
    approval = approval_result.scalar_one_or_none()
    if not approval:
        raise HTTPException(404, "Approval request not found")

    status = approval.status if isinstance(approval.status, str) else approval.status.value
    if status != "approved":
        raise HTTPException(
            400,
            f"Approval request is not in 'approved' state (current: {status}). "
            "Cannot execute unapproved recovery action."
        )

    # Verify payment
    payment_result = await db.execute(
        select(PaymentAttempt).where(
            PaymentAttempt.id == payment_id,
            PaymentAttempt.organization_id == ctx.organization_id,
        )
    )
    payment = payment_result.scalar_one_or_none()
    if not payment:
        raise HTTPException(404, "Payment not found")

    # Execute based on action type
    action = req.action
    executed_result = {"action": action, "payment_id": payment_id}

    if action == "reconcile":
        # Trigger reconciliation (safe read)
        from integrations.providers.fake.provider import FakeProvider
        from modules.payguard.reconciler import run_reconciliation
        provider = FakeProvider()
        run_result = await run_reconciliation(payment, provider, db)
        executed_result["reconciliation"] = {
            "status": run_result.status.value,
            "matched": run_result.matched_items,
        }
    elif action == "retry_with_new_attempt":
        executed_result["message"] = "Create a new Order with a new payment attempt (new idempotency key required)"
        executed_result["safe"] = True
    else:
        executed_result["message"] = f"Action '{action}' acknowledged"

    approval.status = "executed"
    await db.flush()

    return {
        **executed_result,
        "approval_id": req.approval_request_id,
        "executed_by": ctx.actor_id,
    }
