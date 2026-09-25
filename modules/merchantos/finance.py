"""
PayGuard AI — Phase 5: MerchantOS Finance Engine

Handles:
- Invoice management (CRUD)
- Settlement reconciliation (CSV import)
- Cashflow projections with confidence bounds
- Approval-based payment reminders

All projections include explicit uncertainty bounds.
No projection is presented as a guarantee.
"""
from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

logger = logging.getLogger(__name__)


@dataclass
class CashflowPoint:
    """Single point in a cashflow projection."""
    date: date
    expected: int         # Minor units (paise)
    lower_bound: int      # Conservative estimate
    upper_bound: int      # Optimistic estimate
    confidence: float     # 0.0–1.0


@dataclass
class CashflowProjection:
    """
    Cashflow projection with explicit uncertainty bounds.
    All values in minor units (paise for INR).
    """
    organization_id: str
    projection_start: date
    projection_end: date
    currency: str
    points: list[CashflowPoint]
    methodology: str = "trailing_average_30d"
    disclaimer: str = (
        "Cashflow projections are estimates based on historical averages. "
        "Actual amounts may vary significantly. "
        "Not financial advice."
    )
    generated_at: str = ""

    def __post_init__(self) -> None:
        self.generated_at = datetime.now(timezone.utc).isoformat()


@dataclass
class SettlementImportResult:
    """Result of importing a settlement CSV."""
    rows_processed: int
    matched: int
    unmatched: int
    errors: list[str] = field(default_factory=list)
    unmatched_rows: list[dict] = field(default_factory=list)


def parse_settlement_csv(csv_content: str) -> SettlementImportResult:
    """
    Parse a settlement CSV file from a payment provider.

    Expected columns (case-insensitive):
      payment_id, amount, currency, settled_at, status, reference_id

    Returns a structured import result — no DB writes (caller handles persistence).
    """
    result = SettlementImportResult(rows_processed=0, matched=0, unmatched=0)

    try:
        reader = csv.DictReader(io.StringIO(csv_content))
        if not reader.fieldnames:
            result.errors.append("CSV has no headers")
            return result

        # Normalize headers
        headers = {h.lower().strip() for h in reader.fieldnames}
        required = {"payment_id", "amount", "currency"}
        missing = required - headers
        if missing:
            result.errors.append(f"Missing required columns: {missing}")
            return result

        for row in reader:
            result.rows_processed += 1
            normalized = {k.lower().strip(): v.strip() for k, v in row.items()}

            payment_id = normalized.get("payment_id", "")
            if not payment_id:
                result.unmatched += 1
                result.unmatched_rows.append({"reason": "missing_payment_id", **normalized})
                continue

            try:
                amount_str = normalized.get("amount", "0").replace(",", "")
                _ = int(float(amount_str) * 100)  # Validate amount converts to paise
            except (ValueError, TypeError):
                result.errors.append(f"Invalid amount in row {result.rows_processed}")
                result.unmatched += 1
                continue

            # Row is processable
            result.matched += 1

    except Exception as e:
        result.errors.append(f"Parse error: {e}")

    return result


def compute_cashflow_projection(
    historical_captures: list[dict],  # [{"date": date, "amount": int}, ...]
    currency: str,
    projection_days: int = 30,
    organization_id: str = "",
) -> CashflowProjection:
    """
    Compute a simple cashflow projection based on trailing 30-day average.
    Uses standard deviation for confidence bounds.
    """
    from statistics import StatisticsError, mean, stdev

    today = date.today()

    if not historical_captures:
        # No history — return zero projection with maximum uncertainty
        points = []
        for i in range(projection_days):
            d = today + timedelta(days=i + 1)
            points.append(CashflowPoint(
                date=d, expected=0, lower_bound=0, upper_bound=0, confidence=0.0
            ))
        return CashflowProjection(
            organization_id=organization_id,
            projection_start=points[0].date if points else today,
            projection_end=points[-1].date if points else today,
            currency=currency,
            points=points,
        )

    amounts = [c["amount"] for c in historical_captures]
    avg = int(mean(amounts))

    try:
        std = int(stdev(amounts))
    except StatisticsError:
        std = 0

    # Confidence decreases with more uncertainty (higher std/avg ratio)
    cv = std / avg if avg > 0 else 1.0
    base_confidence = max(0.1, min(0.9, 1.0 - cv))

    points = []
    for i in range(projection_days):
        d = today + timedelta(days=i + 1)
        # Confidence degrades over time
        time_decay = max(0.1, base_confidence * (1 - i / (projection_days * 2)))
        points.append(CashflowPoint(
            date=d,
            expected=avg,
            lower_bound=max(0, avg - std),
            upper_bound=avg + std,
            confidence=round(time_decay, 3),
        ))

    return CashflowProjection(
        organization_id=organization_id,
        projection_start=points[0].date,
        projection_end=points[-1].date,
        currency=currency,
        points=points,
    )
