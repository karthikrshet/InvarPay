# InvarPay AI

**Invariant-First · Independent · Open-Source · Multi-Tenant · AI-Native Financial Operations Platform**

[![CI Test Suite](https://img.shields.io/badge/tests-163%20passed-brightgreen.svg)](#-test-suite-architecture-163-passing-tests)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](pyproject.toml)
[![Next.js 14](https://img.shields.io/badge/next.js-14-black.svg)](apps/web)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-teal.svg)](apps/api)
[![Environment](https://img.shields.io/badge/Razorpay-TEST%20MODE%20ONLY-orange.svg)](#-security--compliance-disclosures)

> ⚠️ **Independent open-source project.** Developed by **Karthik Rajesh Shet**. Not affiliated with, endorsed by, or a product of Razorpay. The Razorpay adapter operates strictly in **TEST MODE** with sandbox credentials (`rzp_test_*`). All demo transactions and datasets are **SYNTHETIC**.

---

## 🌟 What is InvarPay AI?

**InvarPay AI** is an open-source, invariant-first financial operations platform. It unifies payment lifecycle reliability, explainable fraud intelligence, automated integration AST auditing, merchant cashflow dual-entry ledgers, and customer-governed agentic commerce into a single, high-reliability architecture:

| Module | Purpose | Core Capabilities | API Endpoints | Status |
|---|---|---|---|---|
| **InvarGuard** | Payment Lifecycle & Safe Recovery | Lifecycle tracking, raw-body HMAC-SHA256 webhook ingestion, inbox deduplication, deterministic reconciliation, safe retry policy (`unknown ≠ failed`) | `/v1/payments`, `/v1/orders`, `/v1/webhooks` | ✅ Production MVP |
| **PaymentGraph AI** | Explainable Fraud Intelligence | Real-time velocity checks, disposable email detection, Tor exit node recognition, composite risk scoring (0–100), transparent model card | `/v1/risk/evaluate`, `/v1/risk/rules` | ✅ Live AI Engine |
| **PayDev AST** | Payment Code Linter & Auto-Fix | Live Python AST code analyzer, hardcoded credential detection, floating-point currency math prevention, automated unified diff patch generation | `/v1/paydev/scan-code`, `/v1/paydev/rules` | ✅ Live AST Linter |
| **MerchantOS** | Dual-Entry Ledger & Bank Reconciliation | Minor-unit double-entry journal, settlement CSV & UTR matching engine, zero-drift cashflow accounting | `/v1/ledger/accounts`, `/v1/ledger/journal`, `/v1/ledger/reconcile-settlement` | ✅ Live FinEngine |
| **ShopAgent MCP** | Agentic Commerce & Checkout Gate | Model Context Protocol storefront, inventory bounds, strict buyer confirmation gate, Razorpay hosted checkout handoff | `/v1/shop/products`, `/v1/shop/cart`, `/v1/shop/checkout` | ✅ Live MCP Protocol |
| **Audit Log Chain** | Cryptographic Tamper-Evidence | SHA-256 Merkle chain verification, immutable event logs, cryptographic proof of ledger integrity | `/v1/audit`, `/v1/audit/verify` | ✅ Cryptographic Proof |

---

## 🏗️ System Architecture

InvarPay AI is structured as a **modular monolith** with independently deployable async background workers, a Next.js 14 web console, a Model Context Protocol (MCP) server, and a Typer CLI:

```mermaid
flowchart TD
    subgraph Clients["Application Interfaces"]
        WEB["Next.js 14 Dashboard\n(apps/web · Vercel Edge CDN)"]
        CLI["Typer CLI\n(apps/cli · invarpay)"]
        MCP["MCP Server\n(apps/mcp · Protocol Tools)"]
        SDK["Typed SDKs\n(Python & TypeScript)"]
    end

    subgraph API["FastAPI Modular Monolith (apps/api)"]
        AUTH["Auth & Tenant Context\n(JWT & Scoped API Keys)"]
        SEC["Security & Webhooks\n(HMAC-SHA256 Raw-Body)"]
        RATELIMIT["Rate Limiter\n(Sliding-Window Memory/Redis)"]
        
        subgraph Modules["Autonomous Core Engines"]
            PG["InvarGuard\n(State Machine & Outbox)"]
            GRAPH["PaymentGraph AI\n(Risk Rules & Model Card)"]
            DEV["PayDev AST\n(AST Scanner & Patch Engine)"]
            MOS["MerchantOS\n(Dual-Entry Ledger & UTR Engine)"]
            SHOP["ShopAgent MCP\n(Buyer-Confirmed Checkout)"]
            AUDIT["Merkle Audit Engine\n(SHA-256 Cryptographic Chain)"]
        end

        POL["Agent Policy Engine\n(Deny-by-Default · Scoped Tools)"]
    end

    subgraph Storage["Authoritative State & Invariants"]
        DB[("PostgreSQL 16 / SQLite\n(Authoritative State & Ledger)")]
        OUTBOX["Transactional Outbox Worker\n(Event Deduplication & Webhooks)"]
    end

    subgraph Providers["External Payment Gateway Adapters"]
        RZP["Razorpay Sandbox\n(TEST MODE ONLY: rzp_test_*)"]
        FAKE["Fake Provider\n(Deterministic CI Simulator)"]
    end

    WEB --> AUTH
    CLI --> AUTH
    MCP --> POL
    SDK --> AUTH

    AUTH --> RATELIMIT --> Modules
    Modules --> POL
    Modules --> DB
    OUTBOX --> DB

    PG --> RZP
    PG --> FAKE
```

---

## 🔒 Invariant-First Financial Principles

InvarPay enforces strict mathematical state transitions to prevent duplicate charges, phantom authorizations, and desynchronized ledgers:

```
created ──► initiated ──► pending ──► authorized ──► captured (terminal ✓)
                │             │            │
                ▼             ▼            ▼
             failed        failed       failed (terminal ✗)
                │             │
                ▼             ▼
             unknown*      unknown*
                │
                └──────────► cancelled (terminal ⊘)

* unknown = Outcome ambiguous (network timeout, dropped connection).
  CRITICAL INVARIANT: unknown ≠ failed. Automated retry is strictly FORBIDDEN.
```

### Core Invariants Enforced
1. **`unknown ≠ failed`**: Network timeouts or gateway 5xx errors transition into `unknown`. InvarPay strictly blocks automatic re-attempts without prior authoritative bank/provider reconciliation.
2. **Zero Float Currency**: All monetary amounts are processed, computed, and stored exclusively in **minor integer units** (`BIGINT` paise). Floating-point arithmetic is strictly prohibited to prevent IEEE-754 precision loss.
3. **Double-Entry Ledger Balancing**: Every merchant balance mutation requires matching debit and credit journal entries ($\sum \text{debits} \equiv \sum \text{credits}$).
4. **Raw-Body Webhook Verification**: HMAC-SHA256 signatures are computed on the unparsed byte payload before JSON parsing to prevent signature malleability attacks.
5. **Inbox Deduplication & Replay Guard**: Webhooks outside a 5-minute timestamp window are rejected, and provider event IDs are tenant-scoped and deduplicated.
6. **Human-in-the-Loop AI Boundary**: Autonomous agents cannot initiate debits without explicit human buyer cryptographic consent.
7. **Cryptographic SHA-256 Merkle Chain**: Every operational event is hashed with its predecessor ($H_i = \text{SHA256}(H_{i-1} \parallel E_i)$), guaranteeing mathematical tamper-evidence.

---

## 🚀 Deployment Guide (Vercel & Cloud Backend)

InvarPay AI is designed with a modern decoupled deployment topology:
- **Frontend (`apps/web`)**: Hosted globally on **Vercel** Edge CDN.
- **Backend (`apps/api`)**: Hosted on a persistent cloud service (**Render, Railway, Fly.io, or VPS**).

### Option 1: Deploying Frontend to Vercel (Step-by-Step)

1. Import your GitHub repository (`karthikrshet/InvarPay`) on [Vercel](https://vercel.com/new).
2. Configure **Project Settings**:
   - **Root Directory**: `apps/web` *(Important: Must be `apps/web` for monorepo detection)*.
   - **Framework Preset**: `Next.js` *(Auto-detected)*.
   - **Build Command**: Leave default (`next build`).
   - **Output Directory**: Leave default (`.next`) — ensure **Override is OFF**.
3. **Environment Variables**:
   ```env
   NEXT_PUBLIC_API_URL = https://your-backend-api.onrender.com
   ```
   *(If your backend is not yet deployed, leave empty or set to `http://localhost:8000`. The frontend includes a comprehensive built-in Standalone Demo Mode with interactive simulators and zero broken views).*
4. Click **Deploy**!

### Option 2: Deploying Backend (1-Click Render / Railway)

We provide pre-configured deployment manifests:
- [Procfile](Procfile) for Railway, Heroku, or Fly.io:
  ```text
  web: uvicorn apps.api.app.main:app --host 0.0.0.0 --port ${PORT:-8000}
  worker: python -m apps.api.app.core.outbox
  ```
- [render.yaml](render.yaml) for 1-click deployment on Render.

---

## 🔐 Production Environment Configuration (`.env`)

### For Backend Deployment (Render / Railway / VPS)

```env
# ============================================================
# InvarPay AI — Production Backend Configuration
# ============================================================

# --- Core App ---
APP_ENV=production
DEBUG=false
LOG_LEVEL=info
SECRET_KEY=generate_a_64_char_random_hex_string
ALLOWED_HOSTS=*

# --- Database ---
# For PostgreSQL (e.g., Supabase, Neon, Railway Postgres):
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@YOUR_HOST:5432/invarpay
# (Or if using persistent SQLite on a single volume container):
# DATABASE_URL=sqlite:////data/payguard.db

DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# --- Authentication & JWT ---
JWT_SECRET_KEY=generate_another_64_char_random_hex_string
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

API_KEY_PREFIX=pg_live_
API_KEY_TEST_PREFIX=pg_test_

# --- Gateway Mode ---
# Use "fake" for safe autonomous demonstration, or "test" with real Razorpay test credentials
PAYMENT_PROVIDER=fake
RAZORPAY_KEY_ID=rzp_test_YOUR_KEY
RAZORPAY_KEY_SECRET=YOUR_SECRET
RAZORPAY_WEBHOOK_SECRET=YOUR_WEBHOOK_SECRET

# --- AI Investigation Agent (Optional) ---
# If unset, LangGraph falls back to deterministic invariant safety fixtures
GOOGLE_API_KEY=your_gemini_api_key_here
# or OPENAI_API_KEY=your_openai_key_here
LLM_PROVIDER=google
LLM_MODEL=gemini-2.5-flash

# --- Initial Demo Seed ---
SEED_DEMO_DATA=true
DEMO_ORG_NAME=Demo Merchant Inc.
```

---

## ⚡ Local Quickstart

### Prerequisites
- Python 3.10+
- Node.js 20+ & `pnpm` (v9+)
- Git

### 1. Clone & Setup
```bash
git clone https://github.com/karthikrshet/InvarPay.git
cd InvarPay

# Copy environment variables
cp .env.example .env
```

### 2. Install Dependencies
```bash
# Python backend & CLI tools
pip install -e .

# Node.js workspace (Next.js web app & SDKs)
pnpm install
```

### 3. Run the Automated Test Suite (163/163 Tests)
```bash
python -m pytest tests/ -v
```

### 4. Start Development Servers
```bash
# Terminal 1: Start FastAPI backend (port 8000)
uvicorn apps.api.app.main:app --reload --port 8000

# Terminal 2: Start Next.js dashboard (port 3000)
pnpm dev
```

- **Dashboard:** [http://localhost:3000](http://localhost:3000)
- **Interactive API Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check:** [http://localhost:8000/health](http://localhost:8000/health)

---

## 🧪 Test Suite Architecture (163 Passing Tests)

InvarPay includes **163 deterministic tests** covering correctness, financial invariants, and fault injection:

| Test Directory | Focus Area | Passing Tests | Scenarios Covered |
|---|---|:---:|---|
| [`tests/unit/`](tests/unit) | Domain Invariants | **114** | State machine transitions, terminal states, minor-unit reconciliation, recovery rules, fraud signals, secret scanners, cashflow projections, buyer confirmation gates |
| [`tests/chaos/`](tests/chaos) | Network & Faults | **10** | Duplicate webhooks, out-of-order delivery, network timeouts, duplicate charge prevention |
| [`tests/security/`](tests/security) | Tenant Isolation | **8** | Cross-tenant 404 enforcement, API key scope validation, HMAC-SHA256 signature verification |
| [`tests/integration/`](tests/integration) | Lifecycle Verification | **3** | End-to-end payment creation, provider simulation, webhook ingestion, and state matching |
| [`tests/evals/`](tests/evals) | AI Agent Safety | **5** | Deny-by-default tool scoping, cross-tenant tool call rejection, prompt-injection boundary isolation |
| [`tests/e2e/`](tests/e2e) | HTTP API Surface | **7** | Health endpoints, model cards, rules catalogs, buyer confirmation gate specs |
| **Total** | **Full Invariant Suite** | **163 / 163** | **100% Pass Rate** |

---

## 📁 Repository Directory Layout

```text
InvarPay/
├── apps/
│   ├── api/                  FastAPI modular monolith backend
│   │   ├── app/core/         Auth, database, security, idempotency, rate limiting, outbox
│   │   ├── app/models/       SQLAlchemy authoritative entity models
│   │   ├── app/routers/      REST API routers (payments, orders, risk, paydev, merchantos, shop, audit)
│   │   └── app/agents/       LangGraph agents & deny-by-default policy engine
│   ├── web/                  Next.js 14 App Router dashboard (Vercel-ready)
│   │   ├── app/              14 routes: dashboard, payments, orders, risk, paydev, merchantos, shop, audit, settings
│   │   └── components/       Sidebar navigation, metric cards, interactive modals
│   ├── cli/                  Typer CLI with rich terminal tables (invarpay)
│   └── mcp/                  Model Context Protocol (MCP) server
├── modules/
│   ├── payguard/             Core payment state machine, reconciler, safe recovery
│   ├── paymentgraph/         Deterministic fraud rules & risk assessments
│   ├── paydev/               Static AST repo analyzer & secret scanner
│   ├── merchantos/           Dual-entry ledger & bank settlement UTR matching engine
│   └── shopagent/            Catalog, inventory validation & buyer gate
├── packages/
│   ├── contracts/            OpenAPI 3.1 schema & JSON event contracts
│   ├── sdk-python/           Typed Python client library (invarpay-sdk)
│   ├── sdk-typescript/       Typed TypeScript client library (@invarpay/sdk)
│   └── ui/                   Shared UI design tokens & utilities (@invarpay/ui)
├── integrations/
│   └── providers/
│       ├── fake/             Deterministic synthetic CI test adapter
│       └── razorpay_test/    Official Razorpay adapter (TEST MODE only)
├── infra/
│   ├── docker/               Docker dev stack & init scripts
│   └── postgres/             PostgreSQL Row-Level Security (RLS) policies
├── Procfile                  Cloud backend Procfile (Render / Railway / Fly.io)
├── render.yaml               1-click Render blueprint
└── tests/                    163 unit, integration, chaos, security, evals, e2e tests
```

---

## ⚖️ Security & Compliance Disclosures

- **PCI-DSS Compliance Boundary**: InvarPay AI never processes, transmits, or stores unencrypted Primary Account Numbers (PAN), CVVs, or UPI PINs. Checkout is hosted by authorized providers.
- **Razorpay Sandbox Restriction**: The Razorpay integration is strictly restricted to test keys (`rzp_test_*`). Live production credentials are rejected.
- **Synthetic Data**: All demo merchants, transaction figures, customer names, and benchmark datasets are synthetic fixtures.
- **Model Card Disclosure**: PaymentGraph risk scores are heuristic research prototypes. Real-world deployment requires qualified compliance review and merchant calibration.

---

## 📄 License & Credits

- **Author**: [Karthik Rajesh Shet](https://github.com/karthikrshet)
- **License**: Licensed under the [MIT License](LICENSE).
- **Showcase**: Built for the Razorpay AI Builder Showcase.
