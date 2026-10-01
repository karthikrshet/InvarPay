# ADR-001: Modular Monolith vs Microservices

**Status:** Accepted  
**Date:** 2024-09-22  
**Deciders:** Founding team

## Context

InvarPay AI needs to support five integrated products (PayGuard, PaymentGraph, PayDev, MerchantOS, ShopAgent) with shared financial infrastructure. The architecture must support:

1. A hackathon MVP in weeks, not months
2. Clear domain boundaries that allow future independent deployment
3. Strong consistency guarantees for payment state (ACID transactions)
4. Maintainability by a small team

## Decision

**Build a modular monolith for the core application, with separately deployable async workers.**

The application is structured as:
- **FastAPI backend** — all business logic in one deployable unit, organized into modules with explicit boundaries
- **Background workers** — separately deployable for reconciliation, event processing, ML tasks
- **Next.js frontend** — separately deployable dashboard
- **MCP server** — separately deployable agent interface

## Consequences

### Advantages
- **Development velocity**: Single codebase, simpler local dev (one `make dev`), no distributed tracing needed to debug a single request
- **ACID transactions**: Payment state, audit events, and outbox events written atomically in one database transaction — impossible with distributed services
- **Simpler deployment**: One Docker Compose for local dev, one container for production MVP
- **Clear module boundaries**: Each module in `modules/` has explicit public interfaces — migration to microservices is a refactor, not a rewrite
- **Easier security**: Single auth boundary, no inter-service trust complexity in MVP

### Disadvantages
- **Scaling granularity**: Cannot scale individual modules independently (mitigated by worker separation)
- **Language coupling**: All core logic must be Python (mitigated by separate Next.js frontend)
- **Single point of failure**: If the API process crashes, all modules are down (mitigated by load balancer + health checks in production)

## Why not microservices from day one?

The classic argument: "We'll need to scale independently anyway." Reality:

1. **Premature optimization**: InvarPay AI does not yet have the traffic that requires per-module scaling
2. **Distributed systems overhead**: Each microservice boundary adds network latency, retry logic, distributed transactions, service discovery, and inter-service auth — all problems to solve before shipping the first feature
3. **Operational complexity**: 15 microservices require 15x the DevOps infrastructure before product-market fit
4. **Financial data consistency**: Strong consistency for payment state is non-negotiable. Eventual consistency across service boundaries introduces reconciliation edge cases that are extremely hard to reason about

## Future migration path

When a specific module requires independent scaling or different runtime characteristics:

1. Extract the module's database tables to a separate schema or database
2. Define explicit API contracts (already in `packages/contracts/`)
3. Deploy the module as a separate service
4. Use the existing outbox pattern for cross-module events

The explicit module boundaries in `modules/` make this evolution straightforward.
