# InvarPay AI — Threat Model

**Status:** Draft MVP  
**Date:** 2024-09-22  
**Scope:** Phase 1 MVP + API boundary

> This threat model covers the Phase 1 MVP. It must be reviewed and updated before any production deployment with real money.

## STRIDE Analysis

### S — Spoofing

| Threat | Control | Status |
|--------|---------|--------|
| Fake webhook from attacker | HMAC-SHA256 signature verification on raw body before parsing | ✅ Implemented |
| Stolen API key | bcrypt hash stored, full key shown once on creation only | ✅ Implemented |
| JWT token forgery | HMAC-SHA256 with 32+ char secret, short expiry | ✅ Implemented |
| Cross-tenant API key spoofing | Key prefix encodes test/live mode, org_id stored in DB | ✅ Implemented |

### T — Tampering

| Threat | Control | Status |
|--------|---------|--------|
| Webhook body modification after signing | Signature verified before JSON parsing; modified body → hash mismatch | ✅ Implemented |
| Audit event manipulation | Append-only audit table, SHA-256 hash chain | ✅ Implemented |
| Payment amount modification | Amount verified in reconciliation; integer minor units, no float | ✅ Implemented |
| Database row manipulation | PostgreSQL constraints; RLS enforced at app layer | ✅ Partial (app layer) |

### R — Repudiation

| Threat | Control | Status |
|--------|---------|--------|
| Deny performing an action | Audit trail records all API key and user actions | ✅ Implemented |
| Deny receiving a webhook | ProviderEvent table records all verified webhooks with timestamps | ✅ Implemented |

### I — Information Disclosure

| Threat | Control | Status |
|--------|---------|--------|
| Cross-tenant payment data access | All queries filter by `organization_id`; 404 not 403 on miss | ✅ Implemented |
| Payment credentials in logs | No raw secrets, CVV, or card data in any model or log | ✅ Implemented |
| Encrypted provider credentials in DB | AES-256 encryption via Fernet before storage | ✅ Implemented |
| LLM exfiltrating payment data | Agent tools return minimal data; raw_payload not sent to LLM | ✅ Implemented |
| Error messages leaking internals | Generic 500 responses; detailed errors only in logs | ✅ Implemented |

### D — Denial of Service

| Threat | Control | Status |
|--------|---------|--------|
| Webhook flood | Rate limiting on webhook endpoints | 🔧 Phase 2 |
| Large payload attack | 1 MB webhook payload limit | ✅ Implemented |
| Slow DB query (tenant isolation bypass) | Indexed `organization_id` on all tenant tables | ✅ Implemented |
| Redis cache poisoning | Redis used for queuing only, not authoritative state | ✅ Design |

### E — Elevation of Privilege

| Threat | Control | Status |
|--------|---------|--------|
| API key scope escalation | Scopes checked on every endpoint; JWT users have full org scope | ✅ Implemented |
| Agent autonomously initiating charges | No agent tool can create payment attempts; policy blocks writes | ✅ Implemented |
| LLM prompt injection | Structured tool schemas; no eval; tool inputs validated | ✅ Implemented |
| Refund without approval | Refund requires ApprovalRequest; agent cannot bypass | ✅ Design |

## Known Limitations (Phase 1)

1. **PostgreSQL RLS** is enforced at application layer only; database-level RLS policies are scaffolded but not fully activated in Phase 1
2. **Rate limiting** is defined but not enforced in Phase 1 (requires Redis middleware)
3. **mTLS between services** not implemented (single-process monolith in Phase 1)
4. **Secret rotation** uses Fernet but not integrated with a KMS in Phase 1
5. **Audit hash chain** is computed but previous_hash is not fetched from DB (simplified in Phase 1)

## Not In Scope

- Real payment processing (TEST MODE only)
- PCI DSS compliance (no card data stored at any point)
- SOC 2 compliance (Phase 7)
- Banking regulations (no banking products)

## Security Contact

Report vulnerabilities to: security@payguard-ai.example  
See [SECURITY.md](../SECURITY.md) for full disclosure policy.
