"""
Phase 5 tests: MerchantOS finance engine.
Tests cashflow projections, settlement CSV parsing.
"""
from __future__ import annotations

from datetime import date, timedelta

from modules.merchantos.finance import (
    compute_cashflow_projection,
    parse_settlement_csv,
)


class TestSettlementCSVParsing:
    """Test CSV settlement import parsing."""

    def test_valid_csv_parsed_correctly(self) -> None:
        csv = (
            "payment_id,amount,currency,settled_at,status\n"
            "pay_001,500.00,INR,2024-01-01,settled\n"
            "pay_002,1000.00,INR,2024-01-01,settled\n"
        )
        result = parse_settlement_csv(csv)
        assert result.rows_processed == 2
        assert result.matched == 2
        assert result.unmatched == 0
        assert not result.errors

    def test_missing_payment_id_counted_as_unmatched(self) -> None:
        csv = (
            "payment_id,amount,currency\n"
            ",500.00,INR\n"  # Missing payment_id
            "pay_002,1000.00,INR\n"
        )
        result = parse_settlement_csv(csv)
        assert result.unmatched == 1
        assert result.matched == 1

    def test_missing_required_column_returns_error(self) -> None:
        csv = "payment_id,settled_at\npay_001,2024-01-01\n"  # Missing amount, currency
        result = parse_settlement_csv(csv)
        assert len(result.errors) > 0

    def test_empty_csv_returns_zero_rows(self) -> None:
        result = parse_settlement_csv("")
        assert result.rows_processed == 0


class TestCashflowProjection:
    """Test cashflow projection engine."""

    def test_empty_history_returns_zero_projection(self) -> None:
        projection = compute_cashflow_projection(
            historical_captures=[],
            currency="INR",
            projection_days=7,
        )
        for point in projection.points:
            assert point.expected == 0
            assert point.confidence == 0.0

    def test_projection_has_correct_number_of_days(self) -> None:
        history = [{"date": date.today() - timedelta(days=i), "amount": 50000} for i in range(10)]
        projection = compute_cashflow_projection(
            historical_captures=history,
            currency="INR",
            projection_days=14,
        )
        assert len(projection.points) == 14

    def test_projection_bounds_are_valid(self) -> None:
        """Lower bound <= expected <= upper bound for all points."""
        history = [{"date": date.today() - timedelta(days=i), "amount": 50000 + i * 1000}
                   for i in range(15)]
        projection = compute_cashflow_projection(
            historical_captures=history,
            currency="INR",
            projection_days=10,
        )
        for point in projection.points:
            assert point.lower_bound <= point.expected <= point.upper_bound, \
                f"Bounds invalid: {point.lower_bound} <= {point.expected} <= {point.upper_bound}"

    def test_projection_has_disclaimer(self) -> None:
        """Projection must always include disclaimer about uncertainty."""
        projection = compute_cashflow_projection([], "INR", 7)
        assert "estimate" in projection.disclaimer.lower() or "advice" in projection.disclaimer.lower()

    def test_confidence_between_0_and_1(self) -> None:
        history = [{"date": date.today() - timedelta(days=i), "amount": 50000}
                   for i in range(20)]
        projection = compute_cashflow_projection(history, "INR", 10)
        for point in projection.points:
            assert 0.0 <= point.confidence <= 1.0, f"Confidence out of range: {point.confidence}"


class TestDualEntryLedger:
    """Test double-entry bookkeeping invariants and settlement posting."""

    def test_settlement_journal_entry_is_balanced(self) -> None:
        from modules.merchantos.finance import build_settlement_journal_entry
        entry = build_settlement_journal_entry(
            entry_id="je_test_01",
            settlement_utr="UTR998877665544",
            gross_amount=100000,
            fee_amount=2000,
            net_bank_amount=98000,
            settlement_date="2026-10-02",
        )
        assert entry.balanced is True
        assert entry.total_debits == 100000
        assert entry.total_credits == 100000
        assert len(entry.lines) == 3

    def test_unbalanced_journal_entry_raises_error(self) -> None:
        import pytest

        from modules.merchantos.finance import JournalEntry, JournalLine
        with pytest.raises(ValueError, match="Dual-entry invariant failed"):
            JournalEntry(
                id="je_err",
                entry_date="2026-10-02",
                description="Unbalanced",
                reference_id="ref_01",
                lines=[
                    JournalLine(account_code="1010", account_name="Cash", debit=100, credit=0),
                    JournalLine(account_code="4010", account_name="Revenue", debit=0, credit=90),
                ]
            )

