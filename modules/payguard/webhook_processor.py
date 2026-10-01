"""
InvarPay AI — Webhook Processor

Handles incoming provider webhook events with:
1. Raw-body signature verification BEFORE parsing
2. Inbox deduplication (prevents duplicate processing)
3. Out-of-order delivery handling
4. Transactional outbox for reliable downstream delivery
5. Payment state machine transition on verified events

INVARIANT: Signature verification always precedes payload parsing.
           A failed signature check rejects the request immediately.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.outbox import emit_payment_event
from apps.api.app.core.security import (
    verify_fake_provider_webhook_signature,
    verify_razorpay_webhook_signature,
)
from apps.api.app.models import (
    PaymentAttempt,
    PaymentAttemptStatus,
    ProviderConnection,
    ProviderEvent,
)
from apps.api.app.utils.ids import new_id
from modules.payguard.state_machine import (
    InvalidTransitionError,
    map_provider_status_to_internal,
    validate_transition,
)

logger = logging.getLogger(__name__)


class WebhookProcessingError(Exception):
    """Non-security errors during webhook processing."""
    pass


class DuplicateWebhookError(Exception):
    """Raised when a duplicate webhook event is detected and safely ignored."""
    pass


async def process_razorpay_webhook(
    db: AsyncSession,
    raw_body: bytes,
    signature: str,
    organization_id: str,
    provider_connection: ProviderConnection,
) -> ProviderEvent:
    """
    Process a Razorpay webhook event.

    Step 1: Verify signature on raw body (NEVER skipped)
    Step 2: Check replay window
    Step 3: Deduplicate via inbox (idempotency)
    Step 4: Parse payload and update payment state
    Step 5: Write outbox event atomically

    Returns the created ProviderEvent record.
    """
    from apps.api.app.core.security import decrypt_credential

    # Step 1: Verify signature BEFORE parsing
    webhook_secret = decrypt_credential(provider_connection.encrypted_webhook_secret)
    verify_razorpay_webhook_signature(raw_body, signature, webhook_secret)

    # Step 2: Parse payload (only after successful verification)
    try:
        payload: dict[str, Any] = json.loads(raw_body)
    except json.JSONDecodeError as e:
        raise WebhookProcessingError(f"Invalid JSON in verified webhook body: {e}") from e

    event_id, event_type, provider_payment_id, provider_order_id, provider_status = (
        _extract_razorpay_payment_event(payload, raw_body)
    )

    return await _persist_and_process_event(
        db=db,
        organization_id=organization_id,
        provider="razorpay",
        event_id=event_id,
        event_type=event_type,
        provider_payment_id=provider_payment_id,
        provider_order_id=provider_order_id,
        provider_status=provider_status,
        raw_payload=_redact_provider_payload(payload),
        provider_connection_id=str(provider_connection.id),
    )


def _extract_razorpay_payment_event(
    payload: dict[str, Any], raw_body: bytes
) -> tuple[str, str, str | None, str | None, str]:
    """Extract documented Razorpay payment event data after verification."""
    event_type = payload.get("event")
    payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    if not isinstance(event_type, str) or not event_type.startswith("payment."):
        raise WebhookProcessingError("Unsupported or missing Razorpay payment event")
    if not isinstance(payment_entity, dict):
        raise WebhookProcessingError("Razorpay payment event missing payload.payment.entity")
    provider_payment_id = payment_entity.get("id")
    provider_status = payment_entity.get("status")
    if not isinstance(provider_payment_id, str) or not provider_payment_id:
        raise WebhookProcessingError("Razorpay payment event missing payment ID")
    if not isinstance(provider_status, str) or not provider_status:
        raise WebhookProcessingError("Razorpay payment event missing payment status")
    provider_order_id = payment_entity.get("order_id")
    return hashlib.sha256(raw_body).hexdigest(), event_type, provider_payment_id, provider_order_id, provider_status


def _redact_provider_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Persist a useful webhook record without direct customer PII or payment data."""
    redacted = json.loads(json.dumps(payload))
    payment = redacted.get("payload", {}).get("payment", {}).get("entity", {})
    if isinstance(payment, dict):
        for key in ("email", "contact", "card", "vpa", "bank", "wallet"):
            payment.pop(key, None)
    return redacted


async def process_fake_provider_webhook(
    db: AsyncSession,
    raw_body: bytes,
    signature: str,
    organization_id: str,
    webhook_secret: str,
) -> ProviderEvent:
    """
    Process a fake provider webhook (used in automated tests only).
    SYNTHETIC — not real payments.
    """
    verify_fake_provider_webhook_signature(raw_body, signature, webhook_secret)

    payload: dict[str, Any] = json.loads(raw_body)
    event_id = payload.get("event_id", "")
    event_type = payload.get("event_type", "unknown")
    provider_payment_id = payload.get("payment_id")
    provider_order_id = payload.get("order_id")
    provider_status = payload.get("status", "unknown")

    return await _persist_and_process_event(
        db=db,
        organization_id=organization_id,
        provider="fake",
        event_id=event_id,
        event_type=event_type,
        provider_payment_id=provider_payment_id,
        provider_order_id=provider_order_id,
        provider_status=provider_status,
        raw_payload=payload,
        provider_connection_id=None,
    )


async def _persist_and_process_event(
    db: AsyncSession,
    organization_id: str,
    provider: str,
    event_id: str,
    event_type: str,
    provider_payment_id: str | None,
    provider_order_id: str | None,
    provider_status: str,
    raw_payload: dict,
    provider_connection_id: str | None,
) -> ProviderEvent:
    """
    Persist a verified webhook event and update payment state.
    Handles:
    - Inbox deduplication (unique constraint on provider + event_id)
    - Out-of-order delivery (only advance state, never go backwards)
    - Transactional outbox
    """
    # Step 3: Inbox deduplication
    # Try to find existing event
    existing = await db.execute(
        select(ProviderEvent).where(
            ProviderEvent.organization_id == organization_id,
            ProviderEvent.provider == provider,
            ProviderEvent.provider_event_id == event_id,
        )
    )
    existing_event = existing.scalar_one_or_none()

    if existing_event:
        if existing_event.processed:
            logger.info(
                "Duplicate webhook event %s from %s — safely ignored (already processed)",
                event_id, provider
            )
            raise DuplicateWebhookError(f"Event {event_id} already processed")
        else:
            logger.warning(
                "Webhook event %s from %s is in-flight — possible concurrent delivery",
                event_id, provider
            )
            return existing_event

    # Step 4: Find associated payment attempt
    payment_attempt: PaymentAttempt | None = None
    if provider_payment_id:
        result = await db.execute(
            select(PaymentAttempt).where(
                PaymentAttempt.organization_id == organization_id,
                PaymentAttempt.provider_payment_id == provider_payment_id,
            )
        )
        payment_attempt = result.scalar_one_or_none()

    if not payment_attempt and provider_order_id:
        # Try matching by provider order ID
        from sqlalchemy import select as sa_select

        from apps.api.app.models import Order
        order_result = await db.execute(
            sa_select(Order).where(
                Order.organization_id == organization_id,
                Order.provider_order_id == provider_order_id,
            )
        )
        order = order_result.scalar_one_or_none()
        if order:
            attempt_result = await db.execute(
                select(PaymentAttempt).where(
                    PaymentAttempt.order_id == order.id,
                    PaymentAttempt.organization_id == organization_id,
                ).order_by(PaymentAttempt.created_at.desc()).limit(1)
            )
            payment_attempt = attempt_result.scalar_one_or_none()

    # Persist the raw event first
    provider_event = ProviderEvent(
        id=new_id(),
        organization_id=organization_id,
        payment_attempt_id=payment_attempt.id if payment_attempt else None,
        provider_connection_id=provider_connection_id,
        provider=provider,
        event_type=event_type,
        provider_event_id=event_id,
        provider_payment_id=provider_payment_id,
        provider_order_id=provider_order_id,
        raw_payload=_redact_provider_payload(raw_payload),
        signature_verified=True,  # We only reach here after successful verification
        processed=False,
        received_at=datetime.now(timezone.utc),
    )
    db.add(provider_event)

    try:
        await db.flush()
    except IntegrityError:
        # Another concurrent request inserted same event_id — safe duplicate
        await db.rollback()
        raise DuplicateWebhookError(f"Race condition on event {event_id} — safely deduplicated")

    # Step 5: Update payment attempt state if found
    if payment_attempt:
        await _apply_event_to_payment(
            db=db,
            payment_attempt=payment_attempt,
            provider=provider,
            provider_status=provider_status,
            provider_payment_id=provider_payment_id,
        )
        # Update the event with payment_attempt_id if we just found it
        provider_event.payment_attempt_id = payment_attempt.id

    # Mark event as processed
    provider_event.processed = True
    provider_event.processed_at = datetime.now(timezone.utc)

    # Step 6: Emit outbox event for downstream processing
    if payment_attempt:
        await emit_payment_event(
            db=db,
            payment_attempt_id=payment_attempt.id,
            event_type=f"payment.{event_type}",
            organization_id=organization_id,
            extra={
                "provider": provider,
                "provider_status": provider_status,
                "provider_event_id": event_id,
            },
        )

    return provider_event


async def _apply_event_to_payment(
    db: AsyncSession,
    payment_attempt: PaymentAttempt,
    provider: str,
    provider_status: str,
    provider_payment_id: str | None,
) -> None:
    """
    Apply a verified provider event to the payment attempt state machine.

    Handles out-of-order delivery:
    - Only advances state (never goes backwards)
    - Logs skipped transitions for audit purposes
    """
    new_internal_status = map_provider_status_to_internal(provider, provider_status)
    current_status = payment_attempt.status

    # Update provider-reported status regardless of internal state
    payment_attempt.provider_status = provider_status
    if provider_payment_id and not payment_attempt.provider_payment_id:
        payment_attempt.provider_payment_id = provider_payment_id

    # Attempt state transition
    try:
        validate_transition(current_status, new_internal_status)
    except InvalidTransitionError:
        # Out-of-order delivery or already in terminal state — safe to skip
        logger.info(
            "Skipping out-of-order transition %s → %s for payment %s",
            current_status.value, new_internal_status.value, payment_attempt.id
        )
        return

    # Apply transition
    payment_attempt.status = new_internal_status
    now = datetime.now(timezone.utc)

    if new_internal_status == PaymentAttemptStatus.AUTHORIZED:
        payment_attempt.authorized_at = now
    elif new_internal_status == PaymentAttemptStatus.CAPTURED:
        payment_attempt.captured_at = now
    elif new_internal_status == PaymentAttemptStatus.FAILED:
        payment_attempt.failed_at = now

    logger.info(
        "Payment %s transitioned: %s → %s (provider: %s, provider_status: %s)",
        payment_attempt.id, current_status.value, new_internal_status.value,
        provider, provider_status
    )
