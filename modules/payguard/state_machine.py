"""
InvarPay AI — Payment Attempt State Machine

Implements the formal payment state machine with strict transition guards.

States: created → initiated → pending → authorized → captured
                                                   → failed
                                                   → cancelled
                                      → unknown    (outcome unclear)

SAFETY INVARIANTS (non-negotiable):
1. unknown is NOT failed — do not treat as definitive failure
2. A network timeout NEVER authorizes retry — set state to unknown
3. Only verified provider responses may update authoritative status
4. captured is terminal and idempotent
5. failed and cancelled are terminal — no further state changes
6. An attempt in unknown state requires reconciliation before any retry

See: docs/architecture/payment-state-machine.md
"""
from __future__ import annotations

from typing import FrozenSet

from apps.api.app.models import PaymentAttemptStatus


class InvalidTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""

    def __init__(self, from_state: PaymentAttemptStatus, to_state: PaymentAttemptStatus) -> None:
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(
            f"Invalid payment state transition: {from_state.value} → {to_state.value}"
        )


class RetryNotSafeError(Exception):
    """
    Raised when a payment retry is requested on an ambiguous outcome.
    Prevents duplicate charges on unknown-outcome payments.
    """
    pass


# Valid state transitions. Every (from, to) pair must be explicitly listed.
# There is NO implicit fallback or wildcard.
_VALID_TRANSITIONS: dict[PaymentAttemptStatus, FrozenSet[PaymentAttemptStatus]] = {
    PaymentAttemptStatus.CREATED: frozenset({
        PaymentAttemptStatus.INITIATED,
        PaymentAttemptStatus.CANCELLED,
    }),
    PaymentAttemptStatus.INITIATED: frozenset({
        PaymentAttemptStatus.PENDING,
        PaymentAttemptStatus.FAILED,
        PaymentAttemptStatus.UNKNOWN,   # Network timeout — never retry without reconcile
        PaymentAttemptStatus.CANCELLED,
    }),
    PaymentAttemptStatus.PENDING: frozenset({
        PaymentAttemptStatus.AUTHORIZED,
        PaymentAttemptStatus.FAILED,
        PaymentAttemptStatus.CANCELLED,
        PaymentAttemptStatus.UNKNOWN,
    }),
    PaymentAttemptStatus.AUTHORIZED: frozenset({
        PaymentAttemptStatus.CAPTURED,
        PaymentAttemptStatus.FAILED,    # Capture failed after authorization
        PaymentAttemptStatus.CANCELLED,
    }),
    # Terminal states — no outgoing transitions
    PaymentAttemptStatus.CAPTURED: frozenset(),
    PaymentAttemptStatus.FAILED: frozenset(),
    PaymentAttemptStatus.CANCELLED: frozenset(),
    # unknown can be resolved by reconciliation only
    PaymentAttemptStatus.UNKNOWN: frozenset({
        PaymentAttemptStatus.CAPTURED,    # Reconciliation confirmed capture
        PaymentAttemptStatus.FAILED,      # Reconciliation confirmed failure
        PaymentAttemptStatus.CANCELLED,   # Reconciliation confirmed cancellation
    }),
}

# States from which a new payment attempt is SAFE to create for the same order
_SAFE_TO_RETRY_FROM: FrozenSet[PaymentAttemptStatus] = frozenset({
    PaymentAttemptStatus.FAILED,
    PaymentAttemptStatus.CANCELLED,
})

# Terminal states (no further transitions)
_TERMINAL_STATES: FrozenSet[PaymentAttemptStatus] = frozenset({
    PaymentAttemptStatus.CAPTURED,
    PaymentAttemptStatus.FAILED,
    PaymentAttemptStatus.CANCELLED,
})


def validate_transition(
    current: PaymentAttemptStatus,
    target: PaymentAttemptStatus,
) -> None:
    """
    Assert that a state transition is valid.
    Raises InvalidTransitionError if not.

    INVARIANT: Only transitions in _VALID_TRANSITIONS are allowed.
    This is the single source of truth for all state machine logic.
    """
    allowed = _VALID_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise InvalidTransitionError(current, target)


def is_terminal(state: PaymentAttemptStatus) -> bool:
    """Returns True if the state has no valid outgoing transitions."""
    return state in _TERMINAL_STATES


def is_safe_to_retry(state: PaymentAttemptStatus) -> bool:
    """
    Returns True if creating a new payment attempt for the same order is safe.

    INVARIANT: unknown is NOT safe to retry — it may already be captured.
    A merchant MUST reconcile first.
    """
    return state in _SAFE_TO_RETRY_FROM


def assert_safe_to_retry(state: PaymentAttemptStatus, payment_attempt_id: str) -> None:
    """
    Raise RetryNotSafeError if the payment state makes retry unsafe.
    Call before creating a new payment attempt for an order that has a prior attempt.
    """
    if not is_safe_to_retry(state):
        if state == PaymentAttemptStatus.UNKNOWN:
            raise RetryNotSafeError(
                f"Payment attempt {payment_attempt_id} has unknown outcome. "
                "Reconcile the payment before creating a new attempt. "
                "Retrying now could result in a duplicate charge."
            )
        elif state == PaymentAttemptStatus.CAPTURED:
            raise RetryNotSafeError(
                f"Payment attempt {payment_attempt_id} is already captured. "
                "Do not create another payment attempt for this order."
            )
        elif state == PaymentAttemptStatus.AUTHORIZED:
            raise RetryNotSafeError(
                f"Payment attempt {payment_attempt_id} is authorized but not yet captured. "
                "Wait for capture completion or cancel before retrying."
            )
        else:
            raise RetryNotSafeError(
                f"Payment attempt {payment_attempt_id} in state {state.value} "
                "cannot be retried safely."
            )


def map_provider_status_to_internal(
    provider: str,
    provider_status: str,
) -> PaymentAttemptStatus:
    """
    Map provider-specific payment status strings to internal state machine states.
    ONLY call this after webhook signature has been verified.

    unknown is returned for ANY ambiguous or unrecognized status.
    Never raise — return unknown instead.
    """
    provider_lower = provider.lower()

    if provider_lower == "razorpay":
        return _map_razorpay_status(provider_status)
    elif provider_lower == "fake":
        return _map_fake_provider_status(provider_status)
    else:
        # Unknown provider — safest is unknown
        return PaymentAttemptStatus.UNKNOWN


def _map_razorpay_status(status: str) -> PaymentAttemptStatus:
    """
    Maps Razorpay payment status strings to internal states.
    Reference: https://razorpay.com/docs/payments/payment-statuses/
    """
    _map = {
        "created": PaymentAttemptStatus.PENDING,
        "authorized": PaymentAttemptStatus.AUTHORIZED,
        "captured": PaymentAttemptStatus.CAPTURED,
        "refunded": PaymentAttemptStatus.CAPTURED,     # Captured, then refunded
        "failed": PaymentAttemptStatus.FAILED,
    }
    return _map.get(status.lower(), PaymentAttemptStatus.UNKNOWN)


def _map_fake_provider_status(status: str) -> PaymentAttemptStatus:
    """Maps fake provider status strings to internal states. Used in tests only."""
    _map = {
        "created": PaymentAttemptStatus.PENDING,
        "authorized": PaymentAttemptStatus.AUTHORIZED,
        "captured": PaymentAttemptStatus.CAPTURED,
        "failed": PaymentAttemptStatus.FAILED,
        "cancelled": PaymentAttemptStatus.CANCELLED,
        "timeout": PaymentAttemptStatus.UNKNOWN,
        "unknown": PaymentAttemptStatus.UNKNOWN,
    }
    return _map.get(status.lower(), PaymentAttemptStatus.UNKNOWN)
