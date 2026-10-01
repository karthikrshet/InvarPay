# InvarPay AI Product Roadmap

## Phase 0 — Foundation ✅ (Complete)
- Monorepo structure
- Database schema (20+ entities)
- Docker Compose local stack
- Documentation (PRD, architecture, threat model, ADRs)
- CI/CD pipeline

## Phase 1 — Hackathon MVP ✅ (Complete)
- Payment state machine with safety invariants
- Webhook ingestion + HMAC-SHA256 verification
- Inbox deduplication + out-of-order handling
- Payment reconciliation (deterministic)
- Unknown-outcome simulation + retry prevention
- AI investigation agent (deterministic mode)
- 20+ deterministic tests
- Next.js dashboard with payment timeline
- Fake provider (CI) + Razorpay test-mode adapter
- Audit log (hash-chained)
- Demo merchant + seed data

## Phase 2 — Recovery & MCP (In Progress)
- [ ] PayGuard recovery suggestions with approval flow
- [ ] LLM-enhanced investigation agent (LangGraph)
- [ ] MCP server (read-only tools)
- [ ] CLI (`payguard` command)
- [ ] Agent evaluation suite

## Phase 3 — PaymentGraph
- [ ] Deterministic fraud rule engine
- [ ] Graph feature extraction
- [ ] Baseline ML on synthetic/public data
- [ ] Calibrated risk scores with model card
- [ ] Human review workflow
- [ ] Fairness and privacy evaluation
- **Note:** Will NOT claim production-grade fraud prevention

## Phase 4 — PayDev
- [ ] Repository analysis (SSRF-protected)
- [ ] Payment integration diff proposals
- [ ] Sandbox test generation
- [ ] Security review (hardcoded secrets, insecure patterns)
- [ ] User approval before any code changes

## Phase 5 — MerchantOS
- [ ] CSV invoice/settlement import
- [ ] Deterministic reconciliation
- [ ] Cashflow projections with error bounds
- [ ] Approval-based reminders
- [ ] Accounting export

## Phase 6 — ShopAgent
- [ ] Authorized merchant catalog
- [ ] Inventory verification
- [ ] Cart management
- [ ] Buyer confirmation gate
- [ ] Provider-hosted checkout
- [ ] Status verification
- **Note:** No autonomous purchases. Explicit confirmation required.

## Phase 7 — Production Hardening
- [ ] Multi-tenant SaaS billing
- [ ] PostgreSQL RLS (database-level)
- [ ] mTLS between services
- [ ] KMS-backed secret management
- [ ] Backup/restore procedures
- [ ] Incident response playbooks
- [ ] SOC 2 readiness
- [ ] Legal/compliance review
- [ ] Provider review before live money
