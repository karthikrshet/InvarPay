"""
PayGuard AI — Audit Events Router

GET /v1/audit-events — Paginated, tamper-evident audit log (tenant-scoped)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.auth import TenantContext, require_scope
from apps.api.app.core.database import get_db
from apps.api.app.models import AuditEvent
from apps.api.app.schemas import AuditEventResponse, PaginatedResponse

router = APIRouter()


@router.get(
    "/audit",
    response_model=PaginatedResponse,
    summary="Get audit log alias",
)
@router.get(
    "/audit-events",
    response_model=PaginatedResponse,
    summary="Get audit log",
    description=(
        "Paginated, append-only audit log. Events are hash-chained for tamper evidence. "
        "Scoped to the authenticated organization — cross-tenant access is impossible."
    ),
)
async def list_audit_events(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    resource_type: str | None = Query(default=None),
    action: str | None = Query(default=None),
    ctx: TenantContext = Depends(require_scope("audit:read")),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse:
    query = select(AuditEvent).where(
        AuditEvent.organization_id == ctx.organization_id  # TENANT ISOLATION
    )

    if resource_type:
        query = query.where(AuditEvent.resource_type == resource_type)
    if action:
        query = query.where(AuditEvent.action == action)

    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar() or 0

    query = (
        query
        .order_by(AuditEvent.occurred_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    events = result.scalars().all()

    return PaginatedResponse(
        items=[AuditEventResponse.model_validate(e) for e in events],
        total=total,
        page=page,
        page_size=page_size,
        has_next=(page * page_size) < total,
    )
