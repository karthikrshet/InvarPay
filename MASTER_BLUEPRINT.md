dont miss anything reaf all the promt and implement evertying with commit# InvarPay AI — Master Engineering Blueprint and Coding-Agent Prompt



## Mission

Build an independent, open-source, multi-tenant, AI-native financial operations platform combining payment reliability (PayGuard), fraud investigation (PaymentGraph), AI-assisted payment integration (PayDev), merchant finance (MerchantOS), and customer-approved commerce (ShopAgent). Prioritize demonstrable reliability and security over feature count. Never claim Razorpay affiliation.



## Product boundaries

PayGuard: payment attempt tracking, provider webhook ingestion, reconciliation, safe recovery, payment incident investigations.

PaymentGraph: explainable fraud signals, synthetic/public data benchmarks, human review; never assert a real fraud score without evidence.

PayDev: repo inspection, proposed payment integration diffs, sandbox tests, webhook signature checks; never modify code or deploy without approval.

MerchantOS: invoice and settlement imports, deterministic matching, cashflow projections with assumptions, approval-based reminders.

ShopAgent: real merchant-authorized catalog, inventory verification, carts, merchant-hosted checkout, explicit buyer confirmation; never store card data or make autonomous charges.



## Architecture

Monorepo, modular monolith FastAPI backend with separately deployable async workers; Next.js web dashboard; PostgreSQL authoritative state; Redis queue/cache; S3-compatible object storage for redacted reports; LangGraph agents isolated behind policy enforcement; MCP server and CLI with scoped read-only defaults; OpenTelemetry and Prometheus-compatible metrics. Provider-neutral adapter with Razorpay TEST MODE first and fixture-based fake provider for CI. No bank routing or fee avoidance. Provider-specific operations only when supported by official APIs and merchant permissions.



## Repo tree

payguard-ai/

  apps/web/                 Next.js TypeScript dashboard

  apps/api/                 FastAPI app and modular domains

  apps/worker/              queued reconciliation, event and ML tasks

  apps/mcp/                 MCP server, read-only by default

  apps/cli/                 Typer CLI

  packages/sdk-python/      typed client

  packages/sdk-typescript/  typed client

  packages/contracts/       OpenAPI, JSON schemas, event schemas

  packages/ui/              shared design system

  services/model-serving/   optional ML inference

  modules/payguard/         payment state and reconciliation

  modules/paymentgraph/     risk scoring and investigation

  modules/paydev/           code inspection and proposed diffs

  modules/merchantos/       invoices, settlement, cash flow

  modules/shopagent/        catalog, cart, approved checkout

  integrations/providers/   fake, Razorpay test, future adapters

  integrations/commerce/    sample catalog adapter

  infra/docker/             local compose

  infra/terraform/          optional cloud IaC, not needed for MVP

  docs/architecture/        ADRs, threat model, sequence diagrams

  docs/api/                 API usage, provider setup

  docs/security/            disclosure, data retention, controls

  docs/product/             PRD, user stories, roadmap

  tests/unit/               domain invariants

  tests/integration/        database, fake provider, queue

  tests/e2e/                sandbox workflow and browser tests

  tests/security/           isolation, auth, replay, injection

  tests/chaos/              timeout, duplicates, out-of-order webhooks

  tests/evals/              agent tool-use and safety benchmarks

  examples/demo-merchant/   complete working demo

  .github/workflows/        lint, tests, dependency and secret scans

  CONTRIBUTING.md CODE_OF_CONDUCT.md SECURITY.md LICENSE README.md



## Domain model

organizations, users, memberships, api_keys, provider_connections, orders, payment_attempts, provider_events, refunds, fulfillment_records, reconciliation_runs, reconciliation_items, invoices, settlements, customers, products, inventory_snapshots, carts, checkout_sessions, risk_assessments, investigations, agent_runs, tool_calls, approval_requests, audit_events, outbox_events, idempotency_records. Every tenant-owned row has organization_id. Enforce org isolation in query layer and test PostgreSQL RLS where implemented. Amounts are integer minor units with currency. Explicit provider identifiers and unique constraints. No raw card data or CVV.



## Payment state invariants

Do not collapse order, attempt, authorization, capture, refund, settlement, and fulfillment into one status. Payment attempt states: created, initiated, pending, authorized, captured, failed, cancelled, unknown; refunds and settlements are separate entities. Only verified provider responses or authenticated provider webhooks may update authoritative provider status. Unknown is not failed. A network timeout never authorizes retry. Reconcile by provider payment/order ID, verify amount, currency, merchant, and original operation. If unresolved, keep unknown, surface manual review, and avoid repeat charge. Handle duplicate, delayed, reordered webhooks; use inbox dedupe, transactional outbox, unique constraints, and durable idempotency. Refund, payout, checkout and customer communication require explicit permissions and appropriate approval. Financial writes must be deterministic; LLM outputs are untrusted proposals.



## API MVP

POST /v1/organizations; POST /v1/provider-connections/test; POST /v1/orders; GET /v1/orders/{id}; GET /v1/payments/{id}; POST /v1/webhooks/razorpay (raw body signature verification); POST /v1/payments/{id}/investigations; POST /v1/payments/{id}/reconcile; GET /v1/investigations/{id}; GET /v1/audit-events; GET /health/live; GET /health/ready. Require tenant-aware auth for all merchant endpoints. No generic arbitrary payment execution endpoint for agents.



## Five modules implementation sequence

Phase 0: PRD, provider capability matrix, threat model, ADRs, monorepo, fake provider, local compose, CI.

Phase 1 (hackathon MVP): real Razorpay test-mode payment attempt, verified webhook ingestion, unknown-outcome simulation, reconciliation, duplicate retry prevention, dashboard timeline, audit log, 20+ deterministic tests and E2E demo.

Phase 2: PayGuard recovery suggestions and approval-based notifications; MCP read-only tools and CLI; agent eval suite.

Phase 3: PaymentGraph deterministic risk rules and graph feature extraction, baseline ML on licensed public/synthetic data, calibration, human review and fairness/privacy evaluation. Do not claim production-grade fraud prevention.

Phase 4: PayDev repository analysis and sandbox-only proposed integration patch with user approval, test generation and security review.

Phase 5: MerchantOS CSV invoice/settlement import, deterministic reconciliation, cashflow forecasts with error bounds and assumptions.

Phase 6: ShopAgent authorised demo merchant catalog, stock validation, buyer confirmation, provider-hosted checkout, status verification; no autonomous purchase.

Phase 7: multi-tenant SaaS hardening, billing for hosted service, backup/restore, incident response, legal and provider review before live money.



## Security non-negotiables

OWASP ASVS/API security baseline; server-side authorization and least privilege; deny-by-default tool scopes; signed raw-body webhook verification before parsing, replay/dedup controls, rotated secrets via secret manager, encryption in transit/at rest, short retention of redacted PII, no raw PAN/CVV/UPI PIN, audit logs with tamper-evident integrity, SSRF protections for URL fetch and repo tools, sandbox execution without production credentials, dependency and secret scanning, rate limits, queue retries with dead-letter handling, per-tenant data access tests, prompt-injection boundary isolation, no agent-initiated live refunds/payouts or payments, human approval and explicit consent. Verify provider-specific signature and webhook requirements against current official documentation before implementing. Consult qualified legal/compliance experts before live payment services or financial advice.



## Metrics and acceptance criteria

No duplicate business fulfillment in tested duplicate/reordered event scenarios. No unauthorized cross-tenant reads/writes in integration tests. No payment retry on ambiguous outcome. Correct raw-body signature rejection in test fixtures. P95 API latency measured under documented local test load (do not invent target achievement). Fraud module reports precision, recall, PR-AUC and false positives at fixed alert volume on labelled test sets. Agents evaluated on tool correctness, policy violations and human approvals. Clearly mark synthetic data, mock providers and sandbox payments. Every demo claim links to reproducible tests and datasets.



## Agent team roles

Product director: PRD, personas, priorities, non-goals, milestones, release criteria.

Principal architect: ADRs, boundaries, state machine, contracts and data model.

Payment domain engineer: provider adapters, webhook verification, reconciliation, idempotency.

Security engineer: threat model, secret management, authorization, abuse cases, review gates.

AI engineer: agent graphs, tool schemas, prompt-injection resistance, evaluations.

ML engineer: baselines, data provenance, graph features, calibrated fraud scores, model cards.

Full-stack engineer: accessible merchant UX, backend APIs, integration.

QA/SRE engineer: chaos scenarios, observability, CI/CD, backup/restore, incident playbooks.

Technical writer/OSS maintainer: quickstart, API docs, contribution guide, licensing, demo script.

The orchestrating coding agent must explicitly adopt all roles, but do not claim independent human review or completed tests that did not occur.



## Master coding-agent prompt (paste into your coding agent)

You are the founding product director, principal fintech architect, senior backend/frontend engineer, AI/ML engineer, payment security engineer, QA/SRE lead, and open-source maintainer for InvarPay AI. Build a production-oriented, independent open-source monorepo using the blueprint in this document as the source of requirements. The five modules are PayGuard, PaymentGraph, PayDev, MerchantOS and ShopAgent. Their common foundation is provider-neutral payments, a deterministic state machine, tenant-aware permissions, an append-only audit trail, and safe human-approved AI tools. Prioritize the Phase 1 hackathon MVP first; scaffold other modules behind clearly labelled feature flags and implement them in later phases. Do not produce fake data disguised as live payments, fake integrations, invented API behavior, mock test results, or marketing claims without evidence. Use a fake provider only for deterministic automated tests and a real Razorpay test-mode adapter for the demo, based on current official documentation and the actual configured credentials. Never request production payment credentials in chat or commit secrets.



First inspect the repository, preserve existing user work, report findings, and create docs/product/PRD.md, docs/architecture/architecture.md, docs/architecture/payment-state-machine.md, docs/security/threat-model.md, docs/product/roadmap.md, and a concise ADR explaining modular monolith vs microservices. Next create the monorepo, Docker Compose local stack, typed API contracts, database migrations, fake provider, secure auth, and CI. Implement the complete vertical slice: create order and payment attempt, receive and authenticate raw webhook, persist event idempotently, process out-of-order delivery, simulate response loss, reconcile provider status, prevent unsafe retry, show merchant timeline and audit trail, and run tests. Include setup scripts, .env.example with placeholders, seed data labelled synthetic, migration and rollback instructions, and a one-command demo where feasible. Ensure merchant-scoped API keys cannot read another tenant's records. Never allow LLM output to directly mutate authoritative payment state or initiate charges. Put write operations behind explicit scope checks, policy enforcement, and user approval; keep MCP tools read-only by default. Use no real card details. After the vertical slice passes, implement one module at a time with explicit acceptance tests and documentation. At every milestone report changed files, commands run, test outcomes, known limitations, and next steps. If blocked by provider access or missing docs, build an honest fake-provider test fixture, mark the real integration as pending, and ask for only the required configuration. Never silently weaken security to make a demo work.



Required deliverables: working code, tests, local compose, OpenAPI docs, architecture diagrams, database schema, security policy, contributor guide, demo merchant app, benchmark methodology, and roadmap. Release readiness requires reproducible setup, passing documented tests, no committed secrets, tenant isolation checks, deterministic payment safety invariants, accurate documentation and explicit disclosure of sandbox-only functionality.

# InvarPay AI



## Complete product architecture, engineering blueprint, and coding-agent master prompt



Open-source · Agentic AI · Fintech infrastructure



# InvarPay AI



An open-source, AI-native financial infrastructure platform for payment reliability, fraud intelligence, developer automation, merchant finance, and agentic commerce.



![PayOrc | Payment Orchestration Platform](https://images.openai.com/static-rsc-4/Zh4t2qEgbStJC0rFLYqYO-JRpmqqfsKwtbBEzzzO9Dbm8lmwg3LG5iNXU7eS7GLK7y_1gR_DCM4VohJo7pXjnZ2mcVgrcTQyEadHD93RsZcS3cj_VXsXuE3FqX8hF0MWC2Jol3skBXSHnRUU4eAcF6HbENkYJvEoyi_VR8e0A10?purpose=inline)



One platform. Five integrated products. One shared financial infrastructure.



Payment reliability



Fraud intelligence



AI developer agents



Merchant finance



Agentic commerce



The objective is to build a real, extensible open-source product that can serve four purposes simultaneously: demonstrate financial engineering expertise, support a working hackathon MVP, provide a foundation for a commercial SaaS business, and showcase AI infrastructure skills relevant to companies such as Razorpay.



The platform will support Razorpay through an authorised provider adapter, but it will remain an independent product with a provider-neutral architecture.



The most important architectural decision is to separate financial execution from AI reasoning. AI agents may investigate, explain, recommend, and prepare operations, but deterministic services must enforce payment state, permissions, transaction integrity, and execution policies.



# 1. Product strategy



## Product vision



Make financial infrastructure understandable, reliable, programmable, and safely accessible to AI agents.



Target users



* Developers integrating payment gateways.



* Startups and SaaS companies managing subscriptions and payments.



* Small businesses monitoring revenue, settlements, and invoices.



* Fintech engineering teams investigating payment failures and fraud.



* AI developers building autonomous commerce and financial workflows.



Open-source model



The core platform, provider adapters, developer SDKs, MCP tools, dashboard, and local development environment should be publicly available under a permissive licence.



Commercial services can later include managed hosting, enterprise SSO, dedicated infrastructure, advanced reporting, and managed integrations.



## Five integrated product modules



Module 01 · Core infrastructure



## InvarPay AI — Payment Reliability



Transaction ingestion, payment lifecycle tracking, webhook verification, failure investigation, idempotency, reconciliation, and safe recovery.



Module 02 · Machine learning



## PaymentGraph AI — Fraud Intelligence



Transaction anomaly detection, entity relationships, graph-based fraud investigation, explainable risk scoring, and review workflows.



Module 03 · Developer experience



## PayDev AI — Payment Integration Engineer



Repository analysis, payment integration generation, SDK assistance, security checks, sandbox testing, and MCP-powered developer workflows.



Module 04 · Business operations



## MerchantOS AI — Financial Assistant



Settlement reconciliation, invoice management, financial reporting, cash-flow forecasting, and merchant-approved recovery workflows.



Module 05 · Agentic commerce



## ShopAgent MCP — AI Shopping and Checkout



Product discovery, catalogue integration, inventory verification, cart management, merchant checkout, and customer-approved payment initiation.



These should not be developed as five disconnected applications. They should share authentication, tenancy, transaction records, payment-provider integrations, event processing, AI infrastructure, security policies, and observability.



# 2. System architecture



## High-level architecture



Application interfaces



Merchant Dashboard · Developer Console · Admin Portal · CLI · SDK · MCP



API Gateway and Identity



Authentication · RBAC · Tenant isolation · Rate limits · API keys



Payment Reliability



Fraud Intelligence



Developer AI



Merchant Finance



Agentic Commerce



Agent Orchestrator



Shared Financial Infrastructure



Transaction state machine · Policy engine · Event bus · Audit trail · Provider adapters



Data and Execution Infrastructure



PostgreSQL · Redis · Object storage · ML models · Background workers



External integrations



Razorpay Sandbox · Other payment providers · Merchant stores · Accounting systems



## Recommended architecture: modular monolith with independent workers



Do not start with 15 microservices.



Build a modular monolith containing the core business domains, backed by separate workers for webhooks, reconciliation, fraud scoring, and AI tasks.



This provides explicit domain boundaries without requiring a distributed deployment for every feature.



|

Component



|



Responsibility



|

| --- | --- |

|



Next.js web app



|



Merchant dashboard, developer console, admin interface



|

|



FastAPI backend



|



Business APIs, domain services, permissions



|

|



PostgreSQL



|



Transaction records, merchants, policies, invoices, audit metadata



|

|



Redis



|



Job queues, rate limiting, short-lived cache



|

|



Background workers



|



Reconciliation, notification delivery, ML inference



|

|



LangGraph



|



Multi-step investigation and agent workflows



|

|



MCP server



|



Controlled access to supported developer and merchant operations



|

|



Object storage



|



Reports, authorised documents, model artifacts



|

|



OpenTelemetry



|



Distributed traces, metrics, and diagnostics



|



Use PostgreSQL as the authoritative database for financial workflow state. Redis should never be the sole source of truth for transaction status or idempotency.



# 3. Shared domain and database design



The system must distinguish a merchant's business order from a provider payment attempt, an authorised charge, a refund, and a settlement.



A single order can have multiple payment attempts. A single payment attempt may produce multiple webhook deliveries. Neither relationship should create duplicate business fulfilment.



## Core entities



Recommended PostgreSQL domain model



Organization



├── Users / Memberships / Roles



├── ProviderConnections



├── Orders



│ ├── PaymentAttempts



│ │ ├── ProviderEvents



│ │ ├── Refunds



│ │ └── Investigations



│ └── FulfillmentRecords



├── Settlements / Reconciliations



├── Invoices / Customers



├── RiskAssessments / RiskSignals



├── Products / Carts / CheckoutSessions



├── AgentRuns / ToolCalls



├── ApprovalRequests



└── AuditEvents / OutboxEvents



Every tenant-owned table must include an organisation identifier. Enforce tenant isolation through authenticated application queries, database constraints, and PostgreSQL row-level security where appropriate.



Store monetary amounts in integer minor units with an explicit ISO currency code. Never use floating-point arithmetic for financial balances.



Store provider event IDs, provider payment IDs, internal operation IDs, and idempotency keys with appropriately scoped uniqueness constraints.



Do not store card numbers, CVVs, UPI PINs, banking passwords, or payment-provider secrets in application logs, prompts, or agent traces.





# 4. Complete implementation blueprint and master coding-agent prompt



I've prepared a downloadable engineering specification containing the five-module architecture, repository structure, database design, implementation phases, security requirements, acceptance criteria, and a master prompt that instructs your coding agent to act as product director, principal architect, payment engineer, AI/ML engineer, security engineer, full-stack developer, QA/SRE lead, and open-source maintainer.



## InvarPay AI — Master Blueprint



Markdown · Architecture + implementation + coding-agent instructions



Download the complete blueprint and master prompt 



## How to use it



Create a new repository named `payguard-ai`, open it in Claude Code, Cursor, or your preferred coding agent, and add the downloaded file as `MASTER_BLUEPRINT.md`.



Then give your coding agent this instruction:



Writing



Read MASTER_BLUEPRINT.md completely and treat it as the product and engineering specification for InvarPay AI.



Act as the founding product director, principal architect, senior fintech engineer, AI/ML engineer, security engineer, full-stack developer, QA lead, SRE, and open-source maintainer.



Build all five products within one shared infrastructure: InvarPay AI, PaymentGraph AI, PayDev AI, MerchantOS AI, and ShopAgent MCP.



Begin by inspecting the repository, defining the architecture, establishing the security boundaries, and implementing the first complete payment reliability workflow.



Prioritise working functionality over decorative dashboards. Use real, authorised integrations where available, Razorpay test mode for payment demonstrations, and explicitly labelled synthetic fixtures for automated testing.



Do not fabricate transaction data, provider responses, completed tests, benchmark results, or production readiness.



Follow the implementation phases, acceptance criteria, security requirements, and reporting instructions in MASTER_BLUEPRINT.md. Complete and verify each milestone before moving to the next.



Start with Phase 0 and Phase 1. Produce the initial repository structure, architecture documents, database schema, Docker environment, secure API foundation, and first working end-to-end payment recovery demonstration.



The first release should prove one thing exceptionally well: a payment agent can investigate an uncertain transaction outcome and recover safely without initiating an unauthorised duplicate charge. Once that workflow is tested, the same infrastructure can support the remaining four products.
