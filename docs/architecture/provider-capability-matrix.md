# PayGuard AI — Provider Capability Matrix

## Overview

PayGuard AI is designed as a **provider-neutral, multi-tenant financial operations platform**.
This document defines the capability matrix between our supported integration adapters:
1. **Fake Provider** — Deterministic test adapter used for CI, chaos simulations, and reproducible unit/integration tests.
2. **Razorpay Test Adapter** — Official Razorpay API integration restricted strictly to **TEST MODE** (`rzp_test_*`).

> [!IMPORTANT]
> **No live payment credentials are permitted.**
> All payment interactions must be verifiable in sandbox/test mode. Live execution requires human approval gates, explicit customer consent, and merchant credentials managed via secure secret storage.

---

## Capability Matrix

| Capability | Fake Provider (CI / Deterministic) | Razorpay Adapter (TEST MODE) | Target Production Standard |
|---|---|---|---|
| **Order Creation** | Supported (deterministic IDs `order_fake_*`) | Supported (`order_*` via Razorpay API) | Idempotent, tenant-scoped |
| **Payment Initiation** | Simulated with configurable outcomes | Supported via Razorpay Checkout / Payment Link | Merchant-hosted or provider-hosted |
| **Webhook Ingestion** | HMAC-SHA256 with test secrets | Official HMAC-SHA256 (`X-Razorpay-Signature`) | Raw-body verified prior to parsing |
| **Out-of-Order Webhooks** | Full chaos simulation supported | Handled via inbox deduplication & state guards | Resilient state machine transitions |
| **Duplicate Delivery** | Supported (idempotency key deduplication) | Supported (deduplicated via `provider_event_id`) | Idempotent processing with 409/200 OK |
| **Network Timeout / Ambiguity** | Configurable `timeout` / `unknown` response | Simulated via forced timeouts or network stubs | Transitions to `unknown`, never auto-retries |
| **Refunds** | Simulated (requires human approval) | Supported in test mode (requires human approval) | Explicit policy check + human approval |
| **Settlement Import** | Synthetic settlement CSV ingestion | Supported via Razorpay Settlement API / CSV | Minor unit parsing, automated reconciliation |
| **Dispute / Chargeback** | Synthetic dispute event generation | Supported via test webhook events | Flagged for manual investigation |
| **Card Data Handling** | Zero card data handled or stored | Zero card data handled; provider hosted checkout | PCI-DSS SAQ-A compliant boundary |
| **Agentic Write Guard** | Policy engine strictly enforces read-only | Policy engine strictly enforces read-only | Deny-by-default; human in the loop |

---

## Webhook Verification Protocol

### Razorpay Test Mode
- **Header**: `X-Razorpay-Signature`
- **Algorithm**: `HMAC-SHA256` computed over the **raw byte payload** using the configured webhook secret (`RAZORPAY_WEBHOOK_SECRET`).
- **Timing Safe**: Uses `hmac.compare_digest` to prevent timing attacks.
- **Payload Ingestion**: Stored raw in `provider_events` table for auditability before parsing JSON.

### Fake Provider
- **Header**: `X-Provider-Signature`
- **Algorithm**: Identical HMAC-SHA256 implementation allowing exact parity testing in unit and chaos test suites.

---

## State Invariant Guarantees

1. **Unknown is Not Failed**:
   A network timeout, dropped connection, or 5xx response from the provider sets the attempt state to `unknown`.
   Under no circumstances is an automated payment retry triggered on an `unknown` outcome without verified status reconciliation.

2. **No Double Charges**:
   Before initiating any retry or recovery, PayGuard queries authoritative provider state. If the payment was captured or authorized at the provider, the order is fulfilled and retry is permanently blocked.

3. **Deny-by-Default Tool Scoping**:
   AI agents (via LangGraph or MCP) are provided read-only tools by default. All mutations (refunds, state overrides, retries) require creating a structured `ApprovalRequest` entity requiring merchant human signature.
