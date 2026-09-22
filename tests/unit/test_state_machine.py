"""
PayGuard AI — Payment State Machine Unit Tests

Tests all valid and invalid transitions.
SYNTHETIC: No real payment providers involved.
"""
from __future__ import annotations

import pytest

from apps.api.app.models import PaymentAttemptStatus
from modules.payguard.state_machine import (
    InvalidTransitionError,
    RetryNotSafeError,
    assert_safe_to_retry,
    is_safe_to_retry,
    is_terminal,
    map_provider_status_to_internal,
    validate_transition,
)

S = PaymentAttemptStatus


class TestValidTransitions:
    """All valid state machine transitions must succeed."""

    def test_created_to_initiated(self) -> None:
        validate_transition(S.CREATED, S.INITIATED)

    def test_created_to_cancelled(self) -> None:
        validate_transition(S.CREATED, S.CANCELLED)

    def test_initiated_to_pending(self) -> None:
        validate_transition(S.INITIATED, S.PENDING)

    def test_initiated_to_failed(self) -> None:
        validate_transition(S.INITIATED, S.FAILED)

    def test_initiated_to_unknown_on_timeout(self) -> None:
        """Network timeout → unknown, never retry."""
        validate_transition(S.INITIATED, S.UNKNOWN)

    def test_pending_to_authorized(self) -> None:
        validate_transition(S.PENDING, S.AUTHORIZED)

    def test_pending_to_failed(self) -> None:
        validate_transition(S.PENDING, S.FAILED)

    def test_authorized_to_captured(self) -> None:
        validate_transition(S.AUTHORIZED, S.CAPTURED)

    def test_authorized_to_failed(self) -> None:
        validate_transition(S.AUTHORIZED, S.FAILED)

    def test_unknown_to_captured_via_reconciliation(self) -> None:
        """unknown can be resolved by reconciliation to captured."""
        validate_transition(S.UNKNOWN, S.CAPTURED)

    def test_unknown_to_failed_via_reconciliation(self) -> None:
        validate_transition(S.UNKNOWN, S.FAILED)

    def test_unknown_to_cancelled_via_reconciliation(self) -> None:
        validate_transition(S.UNKNOWN, S.CANCELLED)


class TestInvalidTransitions:
    """Invalid transitions must raise InvalidTransitionError."""

    def test_captured_is_terminal(self) -> None:
        with pytest.raises(InvalidTransitionError):
            validate_transition(S.CAPTURED, S.FAILED)

    def test_failed_is_terminal(self) -> None:
        with pytest.raises(InvalidTransitionError):
            validate_transition(S.FAILED, S.CAPTURED)

    def test_cancelled_is_terminal(self) -> None:
        with pytest.raises(InvalidTransitionError):
            validate_transition(S.CANCELLED, S.AUTHORIZED)

    def test_cannot_skip_from_created_to_captured(self) -> None:
        with pytest.raises(InvalidTransitionError):
            validate_transition(S.CREATED, S.CAPTURED)

    def test_cannot_go_backwards_from_captured_to_authorized(self) -> None:
        with pytest.raises(InvalidTransitionError):
            validate_transition(S.CAPTURED, S.AUTHORIZED)

    def test_cannot_go_backwards_from_authorized_to_pending(self) -> None:
        with pytest.raises(InvalidTransitionError):
            validate_transition(S.AUTHORIZED, S.PENDING)

    def test_unknown_cannot_go_to_authorized(self) -> None:
        """reconciliation resolves to terminal states only, not intermediate."""
        with pytest.raises(InvalidTransitionError):
            validate_transition(S.UNKNOWN, S.AUTHORIZED)

    def test_unknown_cannot_go_to_pending(self) -> None:
        with pytest.raises(InvalidTransitionError):
            validate_transition(S.UNKNOWN, S.PENDING)


class TestTerminalStates:
    def test_captured_is_terminal(self) -> None:
        assert is_terminal(S.CAPTURED) is True

    def test_failed_is_terminal(self) -> None:
        assert is_terminal(S.FAILED) is True

    def test_cancelled_is_terminal(self) -> None:
        assert is_terminal(S.CANCELLED) is True

    def test_unknown_is_not_terminal(self) -> None:
        """CRITICAL: unknown is NOT failed. It is NOT terminal."""
        assert is_terminal(S.UNKNOWN) is False

    def test_pending_is_not_terminal(self) -> None:
        assert is_terminal(S.PENDING) is False

    def test_authorized_is_not_terminal(self) -> None:
        assert is_terminal(S.AUTHORIZED) is False


class TestRetrySafety:
    """
    CRITICAL: These tests verify the retry safety invariant.
    An ambiguous payment must never be retried without reconciliation.
    """

    def test_failed_is_safe_to_retry(self) -> None:
        assert is_safe_to_retry(S.FAILED) is True

    def test_cancelled_is_safe_to_retry(self) -> None:
        assert is_safe_to_retry(S.CANCELLED) is True

    def test_unknown_is_NOT_safe_to_retry(self) -> None:
        """CRITICAL: unknown may already be captured — never retry."""
        assert is_safe_to_retry(S.UNKNOWN) is False

    def test_captured_is_NOT_safe_to_retry(self) -> None:
        assert is_safe_to_retry(S.CAPTURED) is False

    def test_pending_is_NOT_safe_to_retry(self) -> None:
        assert is_safe_to_retry(S.PENDING) is False

    def test_assert_safe_raises_on_unknown(self) -> None:
        with pytest.raises(RetryNotSafeError, match="unknown outcome"):
            assert_safe_to_retry(S.UNKNOWN, "pay_test_123")

    def test_assert_safe_raises_on_captured(self) -> None:
        with pytest.raises(RetryNotSafeError, match="already captured"):
            assert_safe_to_retry(S.CAPTURED, "pay_test_123")

    def test_assert_safe_does_not_raise_on_failed(self) -> None:
        # Should not raise
        assert_safe_to_retry(S.FAILED, "pay_test_123")


class TestProviderStatusMapping:
    """Provider status strings must map to correct internal states."""

    def test_razorpay_captured(self) -> None:
        assert map_provider_status_to_internal("razorpay", "captured") == S.CAPTURED

    def test_razorpay_authorized(self) -> None:
        assert map_provider_status_to_internal("razorpay", "authorized") == S.AUTHORIZED

    def test_razorpay_failed(self) -> None:
        assert map_provider_status_to_internal("razorpay", "failed") == S.FAILED

    def test_razorpay_created_maps_to_pending(self) -> None:
        assert map_provider_status_to_internal("razorpay", "created") == S.PENDING

    def test_razorpay_unknown_status_maps_to_unknown(self) -> None:
        """Unknown/unrecognized provider status → UNKNOWN (safe default)."""
        assert map_provider_status_to_internal("razorpay", "xyzzy") == S.UNKNOWN

    def test_fake_captured(self) -> None:
        assert map_provider_status_to_internal("fake", "captured") == S.CAPTURED

    def test_fake_timeout_maps_to_unknown(self) -> None:
        """CRITICAL: Network timeout → UNKNOWN, not failed."""
        assert map_provider_status_to_internal("fake", "timeout") == S.UNKNOWN

    def test_unknown_provider_maps_to_unknown(self) -> None:
        """Completely unknown provider → safe UNKNOWN."""
        assert map_provider_status_to_internal("mystery_bank", "ok") == S.UNKNOWN
