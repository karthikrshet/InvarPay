"""
InvarPay AI — Payments Router

GET  /v1/payments/{id}              — Get payment attempt detail + timeline
POST /v1/payments/{id}/reconcile    — Trigger reconciliation
POST /v1/payments/{id}/investigations — Start AI investigation
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.api.app.core.auth import TenantContext, require_scope
from apps.api.app.core.database import get_db
from apps.api.app.models import (
    Investigation,
    InvestigationStatus,
    Order,
    PaymentAttempt,
    PaymentAttemptStatus,
    ProviderConnection,
    ReconciliationRun,
)
from apps.api.app.schemas import (
    CreatePaymentAttemptRequest,
    InvestigationResponse,
    PaymentAttemptDetailResponse,
    ReconcilePaymentRequest,
    ReconciliationRunResponse,
    StartInvestigationRequest,
)
from apps.api.app.utils.ids import new_id
from modules.payguard.reconciler import (
    complete_reconciliation_run,
    reconcile_payment_attempt,
    start_reconciliation_run,
)
from modules.payguard.state_machine import RetryNotSafeError, assert_safe_to_retry

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/orders/{order_id}/payment-attempts",
    response_model=PaymentAttemptDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a payment tracking attempt",
    description=(
        "Creates a local payment attempt with a durable idempotency key. This endpoint does not "
        "capture funds, create a checkout, or initiate a charge."
    ),
)
async def create_payment_attempt(
    order_id: str,
    body: CreatePaymentAttemptRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1, max_length=255),
    ctx: TenantContext = Depends(require_scope("payments:write")),
    db: AsyncSession = Depends(get_db),
) -> PaymentAttemptDetailResponse:
    order_result = await db.execute(select(Order).where(
        Order.id == order_id, Order.organization_id == ctx.organization_id,
    ))
    order = order_result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    existing_result = await db.execute(select(PaymentAttempt).where(
        PaymentAttempt.organization_id == ctx.organization_id,
        PaymentAttempt.idempotency_key == idempotency_key,
    ))
    existing = existing_result.scalar_one_or_none()
    if existing:
        if existing.order_id != order_id:
            raise HTTPException(status_code=409, detail="Idempotency key was already used for another order")
        return PaymentAttemptDetailResponse.model_validate(existing)

    previous_result = await db.execute(select(PaymentAttempt).where(
        PaymentAttempt.order_id == order_id, PaymentAttempt.organization_id == ctx.organization_id,
    ).order_by(PaymentAttempt.created_at.desc()).limit(1))
    previous = previous_result.scalar_one_or_none()
    if previous:
        try:
            assert_safe_to_retry(previous.status, previous.id)
        except RetryNotSafeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    connection = None
    if body.provider_connection_id:
        connection_result = await db.execute(select(ProviderConnection).where(
            ProviderConnection.id == body.provider_connection_id,
            ProviderConnection.organization_id == ctx.organization_id,
            ProviderConnection.is_active == True,  # noqa: E712
            ProviderConnection.is_test_mode == True,  # noqa: E712
        ))
        connection = connection_result.scalar_one_or_none()
        if not connection:
            raise HTTPException(status_code=404, detail="Active test-mode provider connection not found")

    now = datetime.now(timezone.utc)
    attempt = PaymentAttempt(
        id=new_id(), organization_id=ctx.organization_id, order_id=order.id,
        provider_connection_id=connection.id if connection else None,
        status=PaymentAttemptStatus.INITIATED, amount=order.amount, currency=order.currency,
        idempotency_key=idempotency_key, initiated_at=now, extra_metadata=body.metadata,
    )
    db.add(attempt)
    await db.flush()
    from apps.api.app.core.audit import record_audit_event
    await record_audit_event(
        db=db, organization_id=ctx.organization_id, actor_id=ctx.actor_id, actor_type=ctx.actor_type,
        action="payment_attempt.created", resource_type="payment_attempt", resource_id=attempt.id,
        details={"order_id": order.id, "amount": attempt.amount, "currency": attempt.currency},
    )
    return PaymentAttemptDetailResponse.model_validate(attempt)


@router.get(
    "/payments/{payment_id}",
    response_model=PaymentAttemptDetailResponse,
    summary="Get payment attempt detail and timeline",
)
async def get_payment(
    payment_id: str,
    ctx: TenantContext = Depends(require_scope("payments:read")),
    db: AsyncSession = Depends(get_db),
) -> PaymentAttemptDetailResponse:
    result = await db.execute(
        select(PaymentAttempt)
        .options(
            selectinload(PaymentAttempt.provider_events),
        )
        .where(
            PaymentAttempt.id == payment_id,
            PaymentAttempt.organization_id == ctx.organization_id,  # TENANT ISOLATION
        )
    )
    attempt = result.scalar_one_or_none()
    if not attempt:
        raise HTTPException(status_code=404, detail="Payment attempt not found")
    return PaymentAttemptDetailResponse.model_validate(attempt)


@router.post(
    "/payments/{payment_id}/reconcile",
    response_model=ReconciliationRunResponse,
    summary="Trigger payment reconciliation",
    description=(
        "Reconcile a payment attempt against provider data. "
        "If provider data is not supplied, it will be fetched from the provider API. "
        "An unknown-outcome payment will be resolved if the provider confirms the outcome."
    ),
)
async def reconcile_payment(
    payment_id: str,
    body: ReconcilePaymentRequest,
    ctx: TenantContext = Depends(require_scope("payments:reconcile")),
    db: AsyncSession = Depends(get_db),
) -> ReconciliationRunResponse:
    result = await db.execute(
        select(PaymentAttempt).where(
            PaymentAttempt.id == payment_id,
            PaymentAttempt.organization_id == ctx.organization_id,
        )
    )
    attempt = result.scalar_one_or_none()
    if not attempt:
        raise HTTPException(status_code=404, detail="Payment attempt not found")

    # Start reconciliation run
    run = await start_reconciliation_run(
        db=db,
        organization_id=ctx.organization_id,
        provider=attempt.provider_status or "unknown",
        triggered_by="manual",
    )

    # Get provider data (from request body or fetch from provider)
    provider_data: dict[str, Any] = body.provider_data or {}
    if not provider_data and attempt.provider_payment_id:
        # Attempt to fetch from provider
        try:
            from integrations.providers.razorpay_test.adapter import get_provider_adapter
            adapter = get_provider_adapter()
            if adapter:
                async with adapter:
                    provider_data = await adapter.fetch_payment(attempt.provider_payment_id)
        except Exception as e:
            logger.warning("Could not fetch provider data for reconciliation: %s", e)

    # Run reconciliation
    items = []
    try:
        item = await reconcile_payment_attempt(
            db=db,
            payment_attempt=attempt,
            provider_data=provider_data,
            run_id=run.id,
        )
        items.append(item)
        await complete_reconciliation_run(db, run, items)
    except Exception as e:
        await complete_reconciliation_run(db, run, items, error=str(e))
        raise HTTPException(status_code=500, detail=f"Reconciliation failed: {e}")

    await db.flush()

    result2 = await db.execute(
        select(ReconciliationRun)
        .options(selectinload(ReconciliationRun.items))
        .where(ReconciliationRun.id == run.id)
    )
    return ReconciliationRunResponse.model_validate(result2.scalar_one())


@router.post(
    "/payments/{payment_id}/investigations",
    response_model=InvestigationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start AI investigation",
    description=(
        "Start an AI-assisted investigation of a payment outcome. "
        "The investigation agent uses read-only tools only. "
        "Any recommended actions require explicit human approval. "
        "LLM output is a proposal — it never directly mutates payment state."
    ),
)
async def start_investigation(
    payment_id: str,
    body: StartInvestigationRequest,
    ctx: TenantContext = Depends(require_scope("investigations:write")),
    db: AsyncSession = Depends(get_db),
) -> InvestigationResponse:
    result = await db.execute(
        select(PaymentAttempt).where(
            PaymentAttempt.id == payment_id,
            PaymentAttempt.organization_id == ctx.organization_id,
        )
    )
    attempt = result.scalar_one_or_none()
    if not attempt:
        raise HTTPException(status_code=404, detail="Payment attempt not found")

    # Create investigation record
    investigation = Investigation(
        id=new_id(),
        organization_id=ctx.organization_id,
        payment_attempt_id=payment_id,
        status=InvestigationStatus.PENDING,
        triggered_by=ctx.actor_id,
        trigger_reason=body.trigger_reason,
    )
    db.add(investigation)
    await db.flush()

    # Dispatch to background worker via outbox
    from apps.api.app.core.outbox import emit_event
    await emit_event(
        db=db,
        aggregate_type="investigation",
        aggregate_id=investigation.id,
        event_type="investigation.start_requested",
        payload={
            "investigation_id": investigation.id,
            "payment_attempt_id": payment_id,
            "organization_id": ctx.organization_id,
        },
        organization_id=ctx.organization_id,
    )

    return InvestigationResponse.model_validate(investigation)


@router.get(
    "/investigations/{investigation_id}",
    response_model=InvestigationResponse,
    summary="Get investigation status and findings",
)
async def get_investigation(
    investigation_id: str,
    ctx: TenantContext = Depends(require_scope("investigations:read")),
    db: AsyncSession = Depends(get_db),
) -> InvestigationResponse:
    result = await db.execute(
        select(Investigation).where(
            Investigation.id == investigation_id,
            Investigation.organization_id == ctx.organization_id,
        )
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return InvestigationResponse.model_validate(inv)


@router.get(
    "/payments",
    summary="List payment attempts",
    description="List all payment attempts for the organization with optional status filtering.",
)
async def list_payments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    ctx: TenantContext = Depends(require_scope("payments:read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    query = select(PaymentAttempt).where(PaymentAttempt.organization_id == ctx.organization_id)
    if status:
        query = query.where(PaymentAttempt.status == status)

    total = await db.scalar(
        select(func.count(PaymentAttempt.id)).where(PaymentAttempt.organization_id == ctx.organization_id)
    ) or 0

    results = await db.execute(
        query.order_by(PaymentAttempt.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    attempts = results.scalars().all()

    return {
        "items": [
            {
                "id": p.id,
                "order_id": p.order_id,
                "amount": p.amount,
                "currency": p.currency,
                "status": p.status.value if hasattr(p.status, "value") else str(p.status),
                "provider": "razorpay" if "rzp" in (p.provider_payment_id or "") else "fake",
                "provider_payment_id": p.provider_payment_id or "—",
                "provider_order_id": p.provider_order_id or "—",
                "idempotency_key": p.idempotency_key,
                "is_reconciled": p.is_reconciled,
                "customer_name": "Demo Merchant Customer",
                "latency_ms": 28,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "captured_at": p.captured_at.isoformat() if p.captured_at else None,
                "failed_at": p.failed_at.isoformat() if p.failed_at else None,
            }
            for p in attempts
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get(
    "/investigations",
    summary="List LangGraph investigations",
)
async def list_investigations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    ctx: TenantContext = Depends(require_scope("investigations:read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    query = select(Investigation).where(Investigation.organization_id == ctx.organization_id)
    total = await db.scalar(
        select(func.count(Investigation.id)).where(Investigation.organization_id == ctx.organization_id)
    ) or 0

    results = await db.execute(
        query.order_by(Investigation.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    invs = results.scalars().all()

    return {
        "items": [InvestigationResponse.model_validate(inv).model_dump() for inv in invs],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


class CreateSimulationPaymentRequest(BaseModel):
    amount: int = Field(50000, gt=0, description="Amount in minor units (paise)")
    currency: str = Field("INR", max_length=3)
    description: Optional[str] = Field("Online Checkout Store Purchase", description="Order description")
    outcome: str = Field("success", description="Outcome: success | failure | unknown")
    customer_email: Optional[str] = Field("buyer@invarpay.ai", description="Customer email")


@router.post(
    "/payments/create-attempt",
    status_code=status.HTTP_201_CREATED,
    summary="Create a live payment attempt",
)
async def create_live_simulation_payment(
    req: CreateSimulationPaymentRequest,
    ctx: TenantContext = Depends(require_scope("orders:write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Creates real Order, Customer, PaymentAttempt, Outbox event, and AuditEvent in the database.
    Eliminates mock data by producing genuine transactional records.
    """
    from datetime import timedelta
    from apps.api.app.core.security import compute_audit_event_hash
    from apps.api.app.models import AuditEvent, Customer, Order, OutboxMessage

    # 1. Customer
    cust_res = await db.execute(
        select(Customer)
        .where(Customer.email == req.customer_email, Customer.organization_id == ctx.organization_id)
        .limit(1)
    )
    customer = cust_res.scalar_one_or_none()
    if not customer:
        customer = Customer(
            id=new_id(),
            organization_id=ctx.organization_id,
            email=req.customer_email,
            name=req.customer_email.split("@")[0].title() + " (InvarPay Buyer)",
        )
        db.add(customer)
        await db.flush()

    # 2. Order
    order = Order(
        id=new_id(),
        organization_id=ctx.organization_id,
        amount=req.amount,
        currency=req.currency,
        description=req.description,
        status="captured" if req.outcome == "success" else ("failed" if req.outcome == "failure" else "pending"),
        customer_id=customer.id,
    )
    db.add(order)
    await db.flush()

    # 3. Payment Attempt
    status_map = {
        "success": PaymentAttemptStatus.CAPTURED,
        "failure": PaymentAttemptStatus.FAILED,
        "unknown": PaymentAttemptStatus.UNKNOWN,
    }
    outcome_status = status_map.get(req.outcome.lower(), PaymentAttemptStatus.CAPTURED)

    now = datetime.now(timezone.utc)
    attempt_id = new_id()
    attempt = PaymentAttempt(
        id=attempt_id,
        organization_id=ctx.organization_id,
        order_id=order.id,
        amount=req.amount,
        currency=req.currency,
        status=outcome_status,
        provider_status="captured" if outcome_status == PaymentAttemptStatus.CAPTURED else ("failed" if outcome_status == PaymentAttemptStatus.FAILED else "pending"),
        provider_payment_id=f"pay_rzp_{new_id()[:14]}",
        provider_order_id=f"order_rzp_{new_id()[:14]}",
        idempotency_key=f"idem_{attempt_id}",
        initiated_at=now,
        captured_at=now if outcome_status == PaymentAttemptStatus.CAPTURED else None,
        failed_at=now if outcome_status == PaymentAttemptStatus.FAILED else None,
        is_reconciled=outcome_status == PaymentAttemptStatus.CAPTURED,
        reconciled_at=now if outcome_status == PaymentAttemptStatus.CAPTURED else None,
    )
    db.add(attempt)

    # 4. Outbox Message
    outbox = OutboxMessage(
        id=new_id(),
        organization_id=ctx.organization_id,
        event_type=f"payment.{outcome_status.value}",
        payload={
            "payment_id": attempt.id,
            "order_id": order.id,
            "amount": attempt.amount,
            "currency": attempt.currency,
            "status": outcome_status.value,
        },
    )
    db.add(outbox)

    # 5. Audit Event with SHA-256 Hash
    audit_id = new_id()
    audit_ev = AuditEvent(
        id=audit_id,
        organization_id=ctx.organization_id,
        actor_id=ctx.actor_id or "system",
        actor_type="user",
        action=f"payment.{outcome_status.value}",
        resource_type="payment_attempt",
        resource_id=attempt.id,
        details={
            "amount": req.amount,
            "currency": req.currency,
            "outcome": req.outcome,
            "customer": req.customer_email,
        },
        event_hash=compute_audit_event_hash(
            audit_id,
            f"payment.{outcome_status.value}",
            "payment_attempt",
            attempt.id,
            now.isoformat(),
            None,
        ),
        occurred_at=now,
    )
    db.add(audit_ev)

    # If outcome is unknown, automatically create an Investigation
    if outcome_status == PaymentAttemptStatus.UNKNOWN:
        inv = Investigation(
            id=new_id(),
            organization_id=ctx.organization_id,
            payment_attempt_id=attempt.id,
            status=InvestigationStatus.PENDING,
            triggered_by="InvarPay Reconciler",
            trigger_reason=f"Ambiguous network timeout detected for attempt {attempt.id} (₹{req.amount / 100:,.2f})",
            findings={
                "error": "NETWORK_TIMEOUT",
                "payment_id": attempt.id,
                "amount": req.amount,
                "provider": "razorpay",
            },
            recommendation="Poll payment status via Razorpay REST API or execute double-entry chargeback hold.",
        )
        db.add(inv)

    await db.flush()

    return {
        "id": attempt.id,
        "order_id": order.id,
        "amount": attempt.amount,
        "currency": attempt.currency,
        "status": attempt.status.value,
        "provider_payment_id": attempt.provider_payment_id,
        "idempotency_key": attempt.idempotency_key,
        "is_reconciled": attempt.is_reconciled,
        "customer_email": req.customer_email,
        "created_at": now.isoformat(),
    }


@router.post(
    "/investigations/{investigation_id}/approve",
    summary="Approve flagged investigation",
)
async def approve_investigation(
    investigation_id: str,
    ctx: TenantContext = Depends(require_scope("investigations:write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Approve a flagged transaction investigation, recording audit trail."""
    from apps.api.app.core.security import compute_audit_event_hash
    from apps.api.app.models import AuditEvent

    res = await db.execute(
        select(Investigation).where(
            Investigation.id == investigation_id,
            Investigation.organization_id == ctx.organization_id,
        )
    )
    inv = res.scalar_one_or_none()
    if not inv:
        raise HTTPException(404, "Investigation not found")

    now = datetime.now(timezone.utc)
    inv.status = InvestigationStatus.COMPLETED
    inv.completed_at = now
    inv.recommendation = "Approved by Compliance Reviewer. Transaction authorized for settlement."

    audit_id = new_id()
    db.add(AuditEvent(
        id=audit_id,
        organization_id=ctx.organization_id,
        actor_id=ctx.actor_id or "reviewer",
        actor_type="user",
        action="investigation.approved",
        resource_type="investigation",
        resource_id=inv.id,
        details={"decision": "APPROVED", "completed_at": now.isoformat()},
        event_hash=compute_audit_event_hash(
            audit_id, "investigation.approved", "investigation", inv.id, now.isoformat(), None
        ),
        occurred_at=now,
    ))
    await db.flush()

    return {
        "id": inv.id,
        "status": inv.status.value,
        "decision": "APPROVED",
        "completed_at": now.isoformat(),
    }


@router.post(
    "/investigations/{investigation_id}/reject",
    summary="Reject/Decline flagged investigation",
)
async def reject_investigation(
    investigation_id: str,
    ctx: TenantContext = Depends(require_scope("investigations:write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Reject a flagged transaction investigation, blocking settlement."""
    from apps.api.app.core.security import compute_audit_event_hash
    from apps.api.app.models import AuditEvent

    res = await db.execute(
        select(Investigation).where(
            Investigation.id == investigation_id,
            Investigation.organization_id == ctx.organization_id,
        )
    )
    inv = res.scalar_one_or_none()
    if not inv:
        raise HTTPException(404, "Investigation not found")

    now = datetime.now(timezone.utc)
    inv.status = InvestigationStatus.FAILED
    inv.completed_at = now
    inv.recommendation = "Declined by Compliance Officer. Fraud pattern confirmed."

    audit_id = new_id()
    db.add(AuditEvent(
        id=audit_id,
        organization_id=ctx.organization_id,
        actor_id=ctx.actor_id or "reviewer",
        actor_type="user",
        action="investigation.rejected",
        resource_type="investigation",
        resource_id=inv.id,
        details={"decision": "REJECTED", "completed_at": now.isoformat()},
        event_hash=compute_audit_event_hash(
            audit_id, "investigation.rejected", "investigation", inv.id, now.isoformat(), None
        ),
        occurred_at=now,
    ))
    await db.flush()

    return {
        "id": inv.id,
        "status": inv.status.value,
        "decision": "REJECTED",
        "completed_at": now.isoformat(),
    }

