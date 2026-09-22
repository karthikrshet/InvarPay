# Payment State Machine

## Overview

The PayGuard payment state machine defines the authoritative lifecycle of a `PaymentAttempt`. It is the single source of truth for all state transitions and enforces safety invariants that prevent duplicate charges and financial data corruption.

## States

| State | Description | Terminal? |
|-------|-------------|-----------|
| `created` | Attempt record created internally | No |
| `initiated` | Payment request sent to provider | No |
| `pending` | Provider processing (awaiting webhook) | No |
| `authorized` | Provider authorized the charge | No |
| `captured` | Payment successfully captured | **Yes** |
| `failed` | Provider definitively declined | **Yes** |
| `cancelled` | Attempt cancelled before capture | **Yes** |
| `unknown` | Outcome unclear (timeout/error) | **No — requires reconciliation** |

## State Diagram

```
                        ┌──────────────────────────────────┐
                        │           created                │
                        └──────────────┬───────────────────┘
                                       │
                              initiiate_payment()
                                       │
                        ┌──────────────▼───────────────────┐
                        │           initiated              │
                        └──────┬────────────┬──────────────┘
                               │            │
                        pending│     failed │ network timeout
                               │            │        │
               ┌───────────────▼──┐         │   ┌────▼───────────────┐
               │    pending        │    failed   │    unknown         │◄─┐
               └──┬────────────┬──┘         │   │  (NOT failed!)     │  │
                  │            │            │   └────────────────────┘  │
         authorized│      failed│            │         │                │
                  │            │            │   reconciliation          │
     ┌────────────▼──┐         │            │   resolves outcome        │
     │  authorized   │         │            │         │                 │
     └──┬──────────┬─┘         │            │   ┌─────┴─────┐          │
        │          │            │            │   │           │          │
    captured│  failed│           │            │ captured   failed       │
        │          │            │            │                          │
    ┌───▼───┐  ┌───▼───┐   ┌───▼───┐                                   │
    │captured│  │failed │   │failed │                                   │
    │(✓ OK) │  │(✓ OK) │   │(✓ OK) │                                   │
    └───────┘  └───────┘   └───────┘                                   │
                                                                        │
                             cancelled available from any non-terminal──┘
```

## Safety Invariants

### 1. `unknown` ≠ `failed`

**The most critical invariant.** When a network timeout occurs or a provider response is lost, the internal status is set to `unknown` — not `failed`. This reflects the reality that the payment outcome is ambiguous.

A payment in `unknown` state **may already have been captured** by the provider. Treating it as `failed` and initiating a retry could result in a **duplicate charge**.

### 2. Never retry on `unknown`

```python
# CORRECT — raises RetryNotSafeError
assert_safe_to_retry(PaymentAttemptStatus.UNKNOWN, payment_id)

# Safe states for retry
safe_states = {PaymentAttemptStatus.FAILED, PaymentAttemptStatus.CANCELLED}
```

### 3. Reconcile before any action on `unknown`

The only safe path for an `unknown` payment is reconciliation against the provider's authoritative API:

```
unknown → (reconciliation confirms captured) → captured
unknown → (reconciliation confirms failed)   → failed
unknown → (no provider record found)         → UNRESOLVED → manual review
```

### 4. Only verified provider responses update authoritative status

Provider status is only applied after webhook signature verification (HMAC-SHA256). Unverified status updates are rejected.

### 5. Out-of-order webhook handling

Webhooks may arrive out of order (capture before authorization). The state machine:
- Accepts valid **forward** transitions
- Silently discards **backward** transitions (already in more advanced state)
- Logs skipped transitions for audit purposes

### 6. Duplicate webhook deduplication

Each `provider_event_id` is stored with a `UNIQUE` constraint. Duplicate deliveries are idempotently discarded.

## Code References

- State machine: [`modules/payguard/state_machine.py`](../../modules/payguard/state_machine.py)
- Webhook processor: [`modules/payguard/webhook_processor.py`](../../modules/payguard/webhook_processor.py)
- Reconciler: [`modules/payguard/reconciler.py`](../../modules/payguard/reconciler.py)
- Tests: [`tests/unit/test_state_machine.py`](../../tests/unit/test_state_machine.py)
- Chaos tests: [`tests/chaos/test_duplicate_and_reorder.py`](../../tests/chaos/test_duplicate_and_reorder.py)
