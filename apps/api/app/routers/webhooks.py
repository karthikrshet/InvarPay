"""
PayGuard AI — Webhook Ingestion Router

POST /v1/webhooks/razorpay  — Razorpay webhook ingestion

SECURITY INVARIANTS:
1. Raw body is read BEFORE FastAPI parses JSON
2. Signature is verified BEFORE any payload parsing
3. Replay window is checked on timestamp
4. Failed verification → 400 (never 200)
5. Duplicate events → 200 with "already_processed" status
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.config import get_settings
from apps.api.app.core.database import get_db
from apps.api.app.core.security import WebhookVerificationError
from apps.api.app.models import ProviderConnection
from modules.payguard.webhook_processor import (
    DuplicateWebhookError,
    WebhookProcessingError,
    process_razorpay_webhook,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/webhooks/razorpay",
    status_code=status.HTTP_200_OK,
    summary="Razorpay webhook receiver",
    description=(
        "Receives raw Razorpay webhook events. "
        "Signature is verified on the raw body using HMAC-SHA256 before any parsing. "
        "Duplicate events are safely ignored."
    ),
)
async def razorpay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_razorpay_signature: str = Header(..., alias="X-Razorpay-Signature"),
) -> dict:
    """
    Razorpay webhook ingestion endpoint.

    Legacy route. It accepts a request only if one active Razorpay connection
    exists; a multi-tenant deployment must use the connection-specific route.
    """
    # Read raw body BEFORE any parsing — required for signature verification
    raw_body = await request.body()

    if not raw_body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty webhook body",
        )

    if len(raw_body) > get_settings().webhook_max_payload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Webhook payload too large",
        )

    result = await db.execute(
        select(ProviderConnection).where(
            ProviderConnection.provider == "razorpay",
            ProviderConnection.is_active == True,  # noqa: E712
        )
    )
    connections = result.scalars().all()
    if len(connections) != 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Use /v1/webhooks/razorpay/connections/{connection_id} when zero or multiple connections exist.",
        )
    return await _process_razorpay_webhook(
        db, raw_body, x_razorpay_signature, connections[0]
    )


@router.post(
    "/webhooks/razorpay/connections/{connection_id}",
    status_code=status.HTTP_200_OK,
    summary="Razorpay test-mode webhook receiver for one connection",
)
async def razorpay_connection_webhook(
    connection_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_razorpay_signature: str = Header(..., alias="X-Razorpay-Signature"),
) -> dict:
    """Route an authenticated webhook to the connection whose secret verifies it."""
    raw_body = await request.body()
    if not raw_body:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty webhook body")
    if len(raw_body) > get_settings().webhook_max_payload_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Webhook payload too large")
    result = await db.execute(select(ProviderConnection).where(
        ProviderConnection.id == connection_id,
        ProviderConnection.provider == "razorpay",
        ProviderConnection.is_active == True,  # noqa: E712
        ProviderConnection.is_test_mode == True,  # noqa: E712
    ))
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test-mode Razorpay connection not found")
    return await _process_razorpay_webhook(db, raw_body, x_razorpay_signature, connection)


async def _process_razorpay_webhook(
    db: AsyncSession,
    raw_body: bytes,
    signature: str,
    provider_connection: ProviderConnection,
) -> dict:
    """Verify and process a previously routed Razorpay webhook."""

    try:
        event = await process_razorpay_webhook(
            db=db,
            raw_body=raw_body,
            signature=signature,
            organization_id=provider_connection.organization_id,
            provider_connection=provider_connection,
        )
        return {
            "status": "processed",
            "event_id": event.id,
            "provider_event_id": event.provider_event_id,
        }

    except WebhookVerificationError as e:
        logger.warning("Webhook signature verification failed: %s", e)
        # Return 400 — never 200 for failed verification
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Webhook signature verification failed: {e}",
        )

    except DuplicateWebhookError as e:
        logger.info("Duplicate webhook safely ignored: %s", e)
        return {"status": "already_processed", "message": str(e)}

    except WebhookProcessingError as e:
        logger.error("Webhook processing error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )


@router.post(
    "/webhooks/fake",
    status_code=status.HTTP_200_OK,
    summary="[TEST ONLY] Fake provider webhook receiver",
    description=(
        "Receives fake provider webhook events for automated testing. "
        "SYNTHETIC data only — not real payments. "
        "Disabled in production."
    ),
)
async def fake_provider_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_fake_signature: str = Header(..., alias="X-Fake-Signature"),
    x_organization_id: str = Header(..., alias="X-Organization-Id"),
) -> dict:
    """Fake provider webhook endpoint for automated tests."""
    from apps.api.app.core.config import get_settings
    s = get_settings()

    if not s.is_development:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found",
        )

    raw_body = await request.body()

    try:
        from modules.payguard.webhook_processor import process_fake_provider_webhook
        event = await process_fake_provider_webhook(
            db=db,
            raw_body=raw_body,
            signature=x_fake_signature,
            organization_id=x_organization_id,
            webhook_secret="fake-webhook-secret-for-tests",
        )
        return {
            "status": "processed",
            "event_id": event.id,
            "provider_event_id": event.provider_event_id,
            "_marker": "SYNTHETIC-TEST-ONLY",
        }

    except WebhookVerificationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DuplicateWebhookError:
        return {"status": "already_processed", "_marker": "SYNTHETIC-TEST-ONLY"}
