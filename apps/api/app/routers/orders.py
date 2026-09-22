"""
PayGuard AI — Orders Router

POST /v1/orders    — Create order
GET  /v1/orders    — List orders (tenant-scoped)
GET  /v1/orders/{id} — Get order with payment attempts
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.api.app.core.auth import TenantContext, require_scope
from apps.api.app.core.database import get_db
from apps.api.app.models import Order
from apps.api.app.schemas import CreateOrderRequest, OrderResponse, PaginatedResponse
from apps.api.app.utils.ids import new_id

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/orders",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create order",
    description="Create a merchant order. Amount must be in integer minor units (e.g., paise).",
)
async def create_order(
    body: CreateOrderRequest,
    ctx: TenantContext = Depends(require_scope("orders:write")),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    order = Order(
        id=new_id(),
        organization_id=ctx.organization_id,
        amount=body.amount,
        currency=body.currency,
        description=body.description,
        external_order_id=body.external_order_id,
        customer_id=body.customer_id,
        metadata=body.metadata,
        status="pending",
        is_fulfilled=False,
    )
    db.add(order)
    await db.flush()

    # Emit audit event
    from apps.api.app.core.audit import record_audit_event
    await record_audit_event(
        db=db,
        organization_id=ctx.organization_id,
        actor_id=ctx.actor_id,
        actor_type=ctx.actor_type,
        action="order.created",
        resource_type="order",
        resource_id=order.id,
        details={"amount": order.amount, "currency": order.currency},
    )

    result = await db.execute(
        select(Order)
        .options(selectinload(Order.payment_attempts))
        .where(Order.id == order.id)
    )
    return OrderResponse.model_validate(result.scalar_one())


@router.get(
    "/orders",
    response_model=PaginatedResponse,
    summary="List orders",
)
async def list_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(default=None),
    ctx: TenantContext = Depends(require_scope("orders:read")),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse:
    query = select(Order).where(Order.organization_id == ctx.organization_id)
    if status:
        query = query.where(Order.status == status)

    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar() or 0

    query = (
        query
        .options(selectinload(Order.payment_attempts))
        .order_by(Order.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    orders = result.scalars().all()

    return PaginatedResponse(
        items=[OrderResponse.model_validate(o) for o in orders],
        total=total,
        page=page,
        page_size=page_size,
        has_next=(page * page_size) < total,
    )


@router.get(
    "/orders/{order_id}",
    response_model=OrderResponse,
    summary="Get order",
)
async def get_order(
    order_id: str,
    ctx: TenantContext = Depends(require_scope("orders:read")),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.payment_attempts))
        .where(
            Order.id == order_id,
            Order.organization_id == ctx.organization_id,  # TENANT ISOLATION
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return OrderResponse.model_validate(order)
