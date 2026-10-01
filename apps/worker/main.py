"""
InvarPay AI — Background Worker

Polls the transactional outbox and delivers events to:
- Redis queues for async processing
- AI agent runners for investigations
- Webhook delivery (future)

SYNTHETIC: No real payments are processed here in Phase 1.
All data uses fake provider unless Razorpay test mode is configured.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import structlog

from apps.api.app.core.database import get_db_context
from apps.api.app.models import OutboxEvent, OutboxStatus

logger = structlog.get_logger(__name__)


async def process_outbox() -> None:
    """Process pending outbox events."""
    from sqlalchemy import select

    async with get_db_context() as db:
        result = await db.execute(
            select(OutboxEvent).where(
                OutboxEvent.status == OutboxStatus.PENDING,
                OutboxEvent.next_attempt_at <= datetime.now(timezone.utc),
            ).limit(50).with_for_update(skip_locked=True)
        )
        events = result.scalars().all()

        for event in events:
            try:
                await deliver_event(event, db)
                event.status = OutboxStatus.DELIVERED
                event.delivered_at = datetime.now(timezone.utc)
            except Exception as e:
                event.attempts += 1
                event.last_attempt_at = datetime.now(timezone.utc)
                event.error = str(e)

                if event.attempts >= 5:
                    event.status = OutboxStatus.DEAD_LETTER
                    logger.error("Event %s sent to dead-letter after %d attempts", event.id, event.attempts)
                else:
                    # Exponential backoff
                    backoff = min(2 ** event.attempts * 60, 3600)
                    event.next_attempt_at = datetime.now(timezone.utc) + timedelta(seconds=backoff)
                    event.status = OutboxStatus.PENDING


async def deliver_event(event: "OutboxEvent", db: object) -> None:
    """Route and deliver an outbox event."""
    event_type = event.event_type

    if event_type == "investigation.start_requested":
        await handle_investigation_start(event, db)
    else:
        # Default: log event (Phase 2 will add webhook delivery)
        logger.info("Outbox event: %s for %s/%s", event_type, event.aggregate_type, event.aggregate_id)


async def handle_investigation_start(event: "OutboxEvent", db: object) -> None:
    """Handle investigation start request from outbox."""
    from sqlalchemy import select

    from apps.api.app.agents.investigation_agent import run_investigation
    from apps.api.app.models import AgentRun, Investigation, InvestigationStatus
    from apps.api.app.utils.ids import new_id

    investigation_id = event.payload.get("investigation_id")
    payment_attempt_id = event.payload.get("payment_attempt_id")
    organization_id = event.payload.get("organization_id")

    if not all([investigation_id, payment_attempt_id, organization_id]):
        raise ValueError("Missing required fields in investigation event payload")

    # Update status to in-progress
    result = await db.execute(
        select(Investigation).where(Investigation.id == investigation_id)
    )
    investigation = result.scalar_one_or_none()
    if not investigation:
        return

    investigation.status = InvestigationStatus.IN_PROGRESS

    # Create agent run record
    agent_run = AgentRun(
        id=new_id(),
        organization_id=organization_id,
        agent_type="investigation",
        triggered_by=investigation.triggered_by,
        status="running",
        input={"payment_attempt_id": payment_attempt_id},
    )
    db.add(agent_run)
    await db.flush()

    investigation.agent_run_id = agent_run.id

    try:
        # Run investigation
        result_data = await run_investigation(payment_attempt_id, organization_id, db)

        investigation.status = InvestigationStatus.COMPLETED
        investigation.findings = result_data.get("findings")
        investigation.recommendation = "\n".join(result_data.get("recommendations", []))
        investigation.completed_at = datetime.now(timezone.utc)

        agent_run.status = "completed"
        agent_run.output = result_data
        agent_run.completed_at = datetime.now(timezone.utc)

    except Exception as e:
        investigation.status = InvestigationStatus.FAILED
        investigation.error = str(e)
        agent_run.status = "failed"
        agent_run.error = str(e)
        raise


async def main() -> None:
    """Worker main loop."""
    logging.basicConfig(level=logging.INFO)
    logger.info("InvarPay AI Worker starting")

    while True:
        try:
            await process_outbox()
        except Exception as e:
            logger.error("Worker error: %s", e)
        await asyncio.sleep(5)  # Poll every 5 seconds


if __name__ == "__main__":
    asyncio.run(main())
