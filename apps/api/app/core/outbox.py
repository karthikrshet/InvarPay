"""
InvarPay AI — Transactional Outbox

Events are written to the outbox in the SAME database transaction as the
business mutation. A background worker polls the outbox and delivers events
to Redis queues, webhooks, or other targets.

This ensures "at-least-once" delivery without dual-write consistency problems.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.models import OutboxEvent, OutboxStatus
from apps.api.app.utils.ids import new_id


async def emit_event(
    db: AsyncSession,
    aggregate_type: str,
    aggregate_id: str,
    event_type: str,
    payload: dict[str, Any],
    organization_id: str | None = None,
) -> OutboxEvent:
    """
    Append an event to the transactional outbox.
    Must be called within an active database transaction.
    The event is delivered by the worker process asynchronously.
    """
    event = OutboxEvent(
        id=new_id(),
        organization_id=organization_id,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        event_type=event_type,
        payload=payload,
        status=OutboxStatus.PENDING,
        next_attempt_at=datetime.now(timezone.utc),
    )
    db.add(event)
    # NOTE: Do NOT flush here — let the caller commit atomically
    return event


async def emit_payment_event(
    db: AsyncSession,
    payment_attempt_id: str,
    event_type: str,
    organization_id: str,
    extra: dict | None = None,
) -> OutboxEvent:
    """Convenience wrapper for payment domain events."""
    payload: dict = {"payment_attempt_id": payment_attempt_id}
    if extra:
        payload.update(extra)
    return await emit_event(
        db=db,
        aggregate_type="payment_attempt",
        aggregate_id=payment_attempt_id,
        event_type=event_type,
        payload=payload,
        organization_id=organization_id,
    )
