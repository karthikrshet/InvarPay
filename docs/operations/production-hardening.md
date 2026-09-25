# PayGuard AI — Phase 7: Production Deployment

## Overview

This document covers production hardening requirements for Phase 7.

> **Status:** Phase 7 is a checklist — not all items are automated.
> Human judgment and qualified legal/compliance review are required before processing real payments.

## Checklist

### Infrastructure
- [ ] PostgreSQL RLS enabled (`infra/postgres/rls_policies.sql`)
- [ ] Application connects as `payguard_app` role (not superuser)
- [ ] All secrets managed via KMS (not `.env` files)
- [ ] TLS 1.3 on all endpoints
- [ ] Redis TLS enabled
- [ ] S3 bucket encrypted at rest

### Rate Limiting
- [ ] `rate_limit.py` wired into ASGI middleware
- [ ] Redis available in production
- [ ] Limits tuned per endpoint

### Secret Management
- [ ] `ENCRYPTION_KEY` rotated from development default
- [ ] `SECRET_KEY` and `JWT_SECRET_KEY` set to 32+ char random values
- [ ] Razorpay production webhook secret stored in KMS
- [ ] Fernet key rotation procedure documented

### Monitoring
- [ ] OpenTelemetry traces exported to your backend
- [ ] Prometheus metrics scraped
- [ ] Alerts configured: p99 latency > 2s, error rate > 1%, unknown payment rate > 5%

### Audit & Compliance
- [ ] Audit hash chain verified on startup
- [ ] Log retention policy documented
- [ ] PII redaction in logs confirmed

### Provider Review
- [ ] Razorpay production credentials stored securely (NOT in code)
- [ ] Webhook endpoint registered in Razorpay dashboard
- [ ] Provider's TOS reviewed by legal team

### Legal & Compliance
- [ ] Legal review of financial data handling
- [ ] Applicable payment regulations reviewed (PCI DSS if card data flows through)
- [ ] Data retention and deletion policy implemented
- [ ] User consent flows documented

### Load Testing
- [ ] Load test with k6 or locust (target: 500 req/s)
- [ ] Webhook ingestion tested under burst (1000 webhooks/min)
- [ ] Reconciliation tested under concurrent load

### Incident Response
- [ ] Runbook: unknown payment spike
- [ ] Runbook: webhook signature failure spike
- [ ] Runbook: database failover
- [ ] On-call rotation established

## Environment Variables (Production)

```bash
APP_ENV=production
SECRET_KEY=<32+ char random>
JWT_SECRET_KEY=<32+ char random>
DATABASE_URL=postgresql+asyncpg://payguard_app:<password>@<host>:5432/payguard
REDIS_URL=rediss://<host>:6380/0  # Note: TLS scheme
ENCRYPTION_KEY=<Fernet key>
RAZORPAY_KEY_ID=rzp_live_<...>   # Live key — use ONLY in production
RAZORPAY_KEY_SECRET=<live_secret>
RAZORPAY_WEBHOOK_SECRET=<live_webhook_secret>
```

> **Warning:** Never commit live credentials. Use a secrets manager.

## Migration to Production

1. Run `alembic upgrade head` against production DB
2. Run `psql -d payguard -f infra/postgres/rls_policies.sql`
3. Create `payguard_app` role with limited privileges
4. Verify RLS with `SELECT * FROM pg_tables WHERE rowsecurity = true`
5. Start API with `gunicorn -w 4 -k uvicorn.workers.UvicornWorker apps.api.app.main:app`
