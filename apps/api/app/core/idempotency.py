"""
PayGuard AI — Durable Idempotency Store

Prevents duplicate mutations from retried requests, duplicate webhooks,
and concurrent race conditions.

Usage pattern:
    async with idempotency_guard(db, scope="webhook", key=event_id) as guard:
        if guard.already_processed:
            return guard.cached_response
        result = await do_work()
        guard.set_response(200, result)
        return result
"""
from __future__ import annotations

import hashlib
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncGenerator, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.models import IdempotencyRecord
from apps.api.app.utils.ids import new_id


class IdempotencyConflict(Exception):
    """Raised when a concurrent request with the same key is in progress."""
    pass


class IdempotencyGuard:
    """Context manager for idempotency protection."""

    def __init__(self, record: Optional[IdempotencyRecord]) -> None:
        self._record = record
        self.already_processed = record is not None and record.completed_at is not None

    @property
    def cached_response(self) -> Optional[dict]:
        if self._record and self._record.completed_at:
            return self._record.response_body
        return None

    @property
    def cached_status(self) -> int:
        if self._record and self._record.response_status:
            return self._record.response_status
        return 200

    def set_response(self, status: int, body: Any) -> None:
        if self._record:
            self._record.response_status = status
            self._record.response_body = body if isinstance(body, dict) else {"result": str(body)}
            self._record.completed_at = datetime.now(timezone.utc)
            self._record.locked_at = None


@asynccontextmanager
async def idempotency_guard(
    db: AsyncSession,
    scope: str,
    key: str,
    organization_id: Optional[str] = None,
    ttl_hours: int = 24,
) -> AsyncGenerator[IdempotencyGuard, None]:
    """
    Durable idempotency guard backed by PostgreSQL.

    - If key already processed: yields guard with cached response
    - If key in-flight: raises IdempotencyConflict
    - Otherwise: creates lock record, yields guard, caller sets response
    """
    # Hash long keys to fit in column
    hashed_key = hashlib.sha256(f"{scope}:{key}".encode()).hexdigest()

    result = await db.execute(
        select(IdempotencyRecord).where(
            IdempotencyRecord.scope == scope,
            IdempotencyRecord.key == hashed_key,
        )
    )
    record = result.scalar_one_or_none()

    if record:
        if record.completed_at:
            # Already processed — return cached response
            yield IdempotencyGuard(record)
            return
        # In-flight — concurrent request
        raise IdempotencyConflict(
            f"Concurrent request with idempotency key {key!r} is already in progress"
        )

    # Create new lock
    expires_at = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)
    new_record = IdempotencyRecord(
        id=new_id(),
        scope=scope,
        key=hashed_key,
        organization_id=organization_id,
        locked_at=datetime.now(timezone.utc),
        expires_at=expires_at,
    )
    db.add(new_record)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise IdempotencyConflict(
            f"Race condition: idempotency key {key!r} was just claimed by another request"
        )

    guard = IdempotencyGuard(new_record)
    try:
        yield guard
    except Exception:
        # Failed — remove lock so it can be retried
        await db.delete(new_record)
        raise
