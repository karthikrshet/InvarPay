"""
PayGuard AI — Phase 5: MerchantOS Router

GET  /v1/invoices                 — List invoices
POST /v1/invoices                 — Create invoice
GET  /v1/invoices/{id}            — Get invoice
POST /v1/settlements/import       — Import settlement CSV
GET  /v1/cashflow/projection      — Get cashflow projection
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.auth import TenantContext, require_scope
from apps.api.app.core.database import get_db
from apps.api.app.models import Invoice
from apps.api.app.utils.ids import new_id
from modules.merchantos.finance import (
    compute_cashflow_projection,
    parse_settlement_csv,
)

router = APIRouter()


class CreateInvoiceRequest(BaseModel):
    customer_id: Optional[str] = None
    amount: int = Field(..., gt=0, description="Amount in minor units (paise)")
    currency: str = Field("INR", max_length=3)
    description: Optional[str] = None
    due_date: Optional[date] = None
    line_items: Optional[list[dict]] = None


@router.post("/invoices", summary="Create invoice")
async def create_invoice(
    req: CreateInvoiceRequest,
    ctx: TenantContext = Depends(require_scope("orders:write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new invoice for the organization."""
    invoice = Invoice(
        id=new_id(),
        organization_id=ctx.organization_id,
        customer_id=req.customer_id,
        amount=req.amount,
        currency=req.currency,
        description=req.description,
        due_date=req.due_date,
        status="draft",
        line_items=req.line_items or [],
    )
    db.add(invoice)
    await db.flush()
    return {
        "id": invoice.id,
        "amount": invoice.amount,
        "currency": invoice.currency,
        "status": invoice.status.value,
        "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
    }


@router.get("/invoices", summary="List invoices")
async def list_invoices(
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, le=100),
    ctx: TenantContext = Depends(require_scope("orders:read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List invoices for the organization."""
    query = select(Invoice).where(
        Invoice.organization_id == ctx.organization_id
    )
    if status:
        query = query.where(Invoice.status == status)
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    invoices = result.scalars().all()

    return {
        "items": [
            {
                "id": inv.id,
                "amount": inv.amount,
                "currency": inv.currency,
                "status": inv.status.value if hasattr(inv.status, "value") else inv.status,
                "due_date": inv.due_date.isoformat() if inv.due_date else None,
            }
            for inv in invoices
        ],
        "page": page,
        "page_size": page_size,
    }


@router.post("/settlements/import", summary="Import settlement CSV")
async def import_settlement(
    file: UploadFile = File(...),
    ctx: TenantContext = Depends(require_scope("payments:write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Import a settlement CSV from a payment provider.
    Matches settlement rows against existing payments.
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(400, "Only CSV files are accepted")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(413, "File too large (max 10MB)")

    result = parse_settlement_csv(content.decode("utf-8-sig", errors="replace"))

    return {
        "rows_processed": result.rows_processed,
        "matched": result.matched,
        "unmatched": result.unmatched,
        "errors": result.errors[:20],
        "unmatched_preview": result.unmatched_rows[:10],
        "note": "Review unmatched rows manually before marking settlement complete",
    }


@router.get("/cashflow/projection", summary="Get cashflow projection")
async def get_cashflow_projection(
    days: int = Query(30, ge=7, le=90),
    currency: str = Query("INR"),
    ctx: TenantContext = Depends(require_scope("orders:read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get a cashflow projection for the next N days.
    Based on trailing captured payment data.
    Includes confidence bounds and explicit disclaimer.
    """
    from datetime import datetime, timedelta, timezone

    from apps.api.app.models import PaymentAttempt, PaymentAttemptStatus

    # Fetch recent captures for projection baseline
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    result = await db.execute(
        select(PaymentAttempt).where(
            PaymentAttempt.organization_id == ctx.organization_id,
            PaymentAttempt.status == PaymentAttemptStatus.CAPTURED,
            PaymentAttempt.captured_at >= thirty_days_ago,
        )
    )
    captures = result.scalars().all()
    historical = [
        {"date": p.captured_at.date() if p.captured_at else None, "amount": p.amount}
        for p in captures if p.captured_at
    ]

    projection = compute_cashflow_projection(
        historical_captures=historical,
        currency=currency,
        projection_days=days,
        organization_id=ctx.organization_id,
    )

    return {
        "projection_start": projection.projection_start.isoformat(),
        "projection_end": projection.projection_end.isoformat(),
        "currency": projection.currency,
        "methodology": projection.methodology,
        "data_points": len(historical),
        "points": [
            {
                "date": p.date.isoformat(),
                "expected": p.expected,
                "lower_bound": p.lower_bound,
                "upper_bound": p.upper_bound,
                "confidence": p.confidence,
            }
            for p in projection.points
        ],
        "disclaimer": projection.disclaimer,
        "generated_at": projection.generated_at,
    }
