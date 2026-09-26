"""
PayGuard AI — Audit Trail Helper
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.security import compute_audit_event_hash
from apps.api.app.models import AuditEvent
from apps.api.app.utils.ids import new_id


async def record_audit_event(
    db: AsyncSession,
    action: str,
    resource_type: str,
    actor_type: str = "system",
    organization_id: Optional[str] = None,
    actor_id: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> AuditEvent:
    """Append an audit event with hash chain. Never updates existing events."""
    event_id = new_id()
    occurred_at = datetime.now(timezone.utc).isoformat()

    # Chain within each tenant so tenant-scoped access never needs to inspect another
    # tenant's audit trail. The transaction keeps this read and append atomic.
    previous_query = select(AuditEvent).order_by(AuditEvent.occurred_at.desc()).limit(1)
    if organization_id is None:
        previous_query = previous_query.where(AuditEvent.organization_id.is_(None))
    else:
        previous_query = previous_query.where(AuditEvent.organization_id == organization_id)
    previous_event = (await db.execute(previous_query)).scalar_one_or_none()
    previous_hash = previous_event.event_hash if previous_event else None
    event_hash = compute_audit_event_hash(
        event_id=event_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        occurred_at=occurred_at,
        previous_hash=previous_hash,
    )

    event = AuditEvent(
        id=event_id,
        organization_id=organization_id,
        actor_id=actor_id,
        actor_type=actor_type,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
        previous_hash=previous_hash,
        event_hash=event_hash,
        occurred_at=datetime.now(timezone.utc),
    )
    db.add(event)
    return event
