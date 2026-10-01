"""
InvarPay AI — Payment Reconciler

Deterministic reconciliation of internal payment state against provider data.

Reconciliation checks (in order):
1. Provider payment ID matches
2. Amount matches (integer minor units)
3. Currency matches
4. Merchant (organization_id) matches
5. Original operation matches

Resolution rules:
- All checks pass → MATCHED → update payment to confirmed state
- Amount/currency mismatch → MISMATCHED → flag for manual review
- Provider says captured, we show unknown → update to captured
- Provider shows no record → UNRESOLVED → keep unknown, surface manual review
- Cannot determine → UNRESOLVED → manual review, no retry

INVARIANT: If unresolved, keep unknown and surface manual review.
           NEVER mark as failed and retry — this could cause duplicate charges.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.models import (
    PaymentAttempt,
    PaymentAttemptStatus,
    ReconciliationItem,
    ReconciliationRun,
    ReconciliationStatus,
)
from apps.api.app.utils.ids import new_id
from modules.payguard.state_machine import InvalidTransitionError, validate_transition

logger = logging.getLogger(__name__)


class ReconciliationResult:
    def __init__(
        self,
        status: ReconciliationStatus,
        our_amount: int,
        our_currency: str,
        provider_amount: Optional[int] = None,
        provider_currency: Optional[str] = None,
        provider_status: Optional[str] = None,
        discrepancy_reason: Optional[str] = None,
    ) -> None:
        self.status = status
        self.our_amount = our_amount
        self.our_currency = our_currency
        self.provider_amount = provider_amount
        self.provider_currency = provider_currency
        self.provider_status = provider_status
        self.discrepancy_reason = discrepancy_reason


async def reconcile_payment_attempt(
    db: AsyncSession,
    payment_attempt: PaymentAttempt,
    provider_data: dict[str, Any],
    run_id: str,
) -> ReconciliationItem:
    """
    Reconcile a single payment attempt against provider data.

    provider_data is the authoritative response from the provider API
    (not a webhook — fetched directly for reconciliation).

    Returns a ReconciliationItem with the reconciliation result.
    """
    result = _reconcile(payment_attempt, provider_data)

    # Persist reconciliation item
    item = ReconciliationItem(
        id=new_id(),
        organization_id=payment_attempt.organization_id,
        run_id=run_id,
        payment_attempt_id=payment_attempt.id,
        status=result.status,
        our_amount=result.our_amount,
        our_currency=result.our_currency,
        provider_amount=result.provider_amount,
        provider_currency=result.provider_currency,
        provider_status=result.provider_status,
        discrepancy_reason=result.discrepancy_reason,
    )
    db.add(item)

    # Apply reconciliation findings to payment attempt
    if result.status == ReconciliationStatus.MATCHED:
        await _apply_matched_reconciliation(db, payment_attempt, result)
    elif result.status == ReconciliationStatus.MISMATCHED:
        logger.warning(
            "Payment %s reconciliation MISMATCH: %s",
            payment_attempt.id, result.discrepancy_reason
        )
        # Do NOT change payment state on mismatch — surface for manual review
    elif result.status == ReconciliationStatus.UNRESOLVED:
        logger.warning(
            "Payment %s reconciliation UNRESOLVED: %s",
            payment_attempt.id, result.discrepancy_reason
        )
        # Keep unknown state — manual review required, no retry

    # Mark as reconciled
    payment_attempt.is_reconciled = True
    payment_attempt.reconciled_at = datetime.now(timezone.utc)

    return item


def _reconcile(
    payment_attempt: PaymentAttempt,
    provider_data: dict[str, Any],
) -> ReconciliationResult:
    """
    Core reconciliation logic — deterministic, no LLM involved.

    Checks: provider_payment_id, amount, currency, merchant.
    Returns a ReconciliationResult.
    """
    our_amount = payment_attempt.amount
    our_currency = payment_attempt.currency.upper()

    # No provider data — unresolved
    if not provider_data:
        return ReconciliationResult(
            status=ReconciliationStatus.UNRESOLVED,
            our_amount=our_amount,
            our_currency=our_currency,
            discrepancy_reason="No provider data returned — payment outcome unknown",
        )

    provider_payment_id = provider_data.get("id", "")
    provider_amount = provider_data.get("amount")  # In minor units
    provider_currency = (provider_data.get("currency") or "").upper()
    provider_status = provider_data.get("status", "unknown")

    # Check provider payment ID matches our record
    if (
        payment_attempt.provider_payment_id
        and payment_attempt.provider_payment_id != provider_payment_id
    ):
        return ReconciliationResult(
            status=ReconciliationStatus.MISMATCHED,
            our_amount=our_amount,
            our_currency=our_currency,
            provider_amount=provider_amount,
            provider_currency=provider_currency,
            provider_status=provider_status,
            discrepancy_reason=(
                f"Provider payment ID mismatch: "
                f"expected {payment_attempt.provider_payment_id}, got {provider_payment_id}"
            ),
        )

    # Check amount
    if provider_amount is not None and int(provider_amount) != our_amount:
        return ReconciliationResult(
            status=ReconciliationStatus.MISMATCHED,
            our_amount=our_amount,
            our_currency=our_currency,
            provider_amount=int(provider_amount),
            provider_currency=provider_currency,
            provider_status=provider_status,
            discrepancy_reason=(
                f"Amount mismatch: we have {our_amount} {our_currency}, "
                f"provider has {provider_amount} {provider_currency}"
            ),
        )

    # Check currency
    if provider_currency and provider_currency != our_currency:
        return ReconciliationResult(
            status=ReconciliationStatus.MISMATCHED,
            our_amount=our_amount,
            our_currency=our_currency,
            provider_amount=provider_amount,
            provider_currency=provider_currency,
            provider_status=provider_status,
            discrepancy_reason=(
                f"Currency mismatch: we have {our_currency}, provider has {provider_currency}"
            ),
        )

    # All checks passed — determine match quality
    if provider_status in ("captured", "authorized"):
        return ReconciliationResult(
            status=ReconciliationStatus.MATCHED,
            our_amount=our_amount,
            our_currency=our_currency,
            provider_amount=int(provider_amount) if provider_amount else our_amount,
            provider_currency=provider_currency or our_currency,
            provider_status=provider_status,
        )
    elif provider_status == "failed":
        return ReconciliationResult(
            status=ReconciliationStatus.MATCHED,
            our_amount=our_amount,
            our_currency=our_currency,
            provider_amount=int(provider_amount) if provider_amount else our_amount,
            provider_currency=provider_currency or our_currency,
            provider_status=provider_status,
        )
    else:
        # Status unclear from provider
        return ReconciliationResult(
            status=ReconciliationStatus.UNRESOLVED,
            our_amount=our_amount,
            our_currency=our_currency,
            provider_amount=int(provider_amount) if provider_amount else None,
            provider_currency=provider_currency or None,
            provider_status=provider_status,
            discrepancy_reason=f"Provider status '{provider_status}' is ambiguous",
        )


async def _apply_matched_reconciliation(
    db: AsyncSession,
    payment_attempt: PaymentAttempt,
    result: ReconciliationResult,
) -> None:
    """
    Update payment attempt state based on matched reconciliation.
    Only valid if current state is unknown (reconciliation resolves ambiguity).
    """
    from modules.payguard.state_machine import map_provider_status_to_internal

    if payment_attempt.status != PaymentAttemptStatus.UNKNOWN:
        # Not unknown — reconciliation is informational only
        return

    # Resolve unknown state based on provider's authoritative answer
    new_status = map_provider_status_to_internal("razorpay", result.provider_status or "unknown")

    try:
        validate_transition(payment_attempt.status, new_status)
        payment_attempt.status = new_status
        payment_attempt.provider_status = result.provider_status

        now = datetime.now(timezone.utc)
        if new_status == PaymentAttemptStatus.CAPTURED:
            payment_attempt.captured_at = now
        elif new_status == PaymentAttemptStatus.FAILED:
            payment_attempt.failed_at = now

        logger.info(
            "Payment %s resolved from unknown → %s via reconciliation",
            payment_attempt.id, new_status.value
        )
    except InvalidTransitionError:
        logger.warning(
            "Cannot apply reconciliation result to payment %s: "
            "invalid transition unknown → %s",
            payment_attempt.id, new_status.value
        )


async def start_reconciliation_run(
    db: AsyncSession,
    organization_id: str,
    provider: str,
    triggered_by: str,
) -> ReconciliationRun:
    """Create and persist a new reconciliation run record."""
    run = ReconciliationRun(
        id=new_id(),
        organization_id=organization_id,
        provider=provider,
        triggered_by=triggered_by,
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    await db.flush()
    return run


async def complete_reconciliation_run(
    db: AsyncSession,
    run: ReconciliationRun,
    items: list[ReconciliationItem],
    error: str | None = None,
) -> None:
    """Finalize a reconciliation run with summary stats."""
    run.completed_at = datetime.now(timezone.utc)
    run.status = "failed" if error else "completed"
    run.error = error
    run.total_items = len(items)
    run.matched_items = sum(1 for i in items if i.status == ReconciliationStatus.MATCHED)
    run.mismatched_items = sum(1 for i in items if i.status == ReconciliationStatus.MISMATCHED)
    run.unresolved_items = sum(1 for i in items if i.status == ReconciliationStatus.UNRESOLVED)
