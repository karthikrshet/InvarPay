"""
PayGuard AI — FastAPI Application Factory

Assembles the complete FastAPI application with:
- CORS, request ID, tenant context middleware
- Health endpoints (liveness + readiness)
- All API routers
- OpenAPI documentation
- OpenTelemetry instrumentation
- Exception handlers
"""
from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from apps.api.app.core.config import get_settings
from apps.api.app.core.database import check_db_connectivity
from apps.api.app.routers import audit, orders, organizations, payments, webhooks

# Phase 5
from apps.api.app.routers import merchantos as merchantos_router

# Phase 4
from apps.api.app.routers import paydev as paydev_router

# Phase 2
from apps.api.app.routers import recovery as recovery_router

# Phase 3
from apps.api.app.routers import risk as risk_router

# Phase 6
from apps.api.app.routers import shopagent as shopagent_router
from apps.api.app.schemas import HealthResponse

logger = logging.getLogger(__name__)
settings = get_settings()


# ── Lifespan ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup / shutdown lifecycle."""
    logger.info(
        "InvarPay AI %s starting (env=%s, provider=%s)",
        settings.app_version, settings.app_env, settings.payment_provider
    )
    if settings.razorpay_configured:
        logger.info("Razorpay TEST-MODE adapter configured")
    else:
        logger.info("Using FAKE provider (no Razorpay credentials — set RAZORPAY_KEY_ID in .env)")

    # Ensure tables exist and seed demo data
    try:
        from apps.api.app.core.database import init_db
        await init_db()
        logger.info("Database tables initialized")
        if settings.seed_demo_data:
            try:
                from examples.demo_merchant.seed import seed_demo_data
                await seed_demo_data()
            except Exception as e:
                logger.warning("Demo seed status: %s", e)
    except Exception as e:
        logger.warning("DB init status: %s", e)

    yield

    logger.info("InvarPay AI shutting down")


# ── App factory ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title="InvarPay AI",
        description=(
            "AI-native financial operations platform. "
            "Independent, open-source. Not affiliated with Razorpay. "
            "Razorpay adapter operates in TEST MODE only."
        ),
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001"] if settings.is_development else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Request ID middleware ─────────────────────────────────────────────────
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next: Any) -> Response:
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        return response

    # ── Latency logging ───────────────────────────────────────────────────────
    @app.middleware("http")
    async def latency_middleware(request: Request, call_next: Any) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.1f}"
        if duration_ms > 1000:
            logger.warning(
                "Slow request: %s %s took %.0fms",
                request.method, request.url.path, duration_ms
            )
        return response

    # ── Exception handlers ────────────────────────────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "request_id": getattr(request.state, "request_id", "")},
        )

    # ── Health endpoints ──────────────────────────────────────────────────────
    @app.get("/health/live", response_model=HealthResponse, tags=["Health"])
    async def liveness() -> HealthResponse:
        """Liveness check — always returns 200 if process is alive."""
        return HealthResponse(
            status="ok",
            version=settings.app_version,
            environment=settings.app_env,
        )

    @app.get("/health/ready", response_model=HealthResponse, tags=["Health"])
    async def readiness() -> HealthResponse:
        """Readiness check — verifies DB and Redis connectivity."""
        db_ok = await check_db_connectivity()
        redis_ok = await _check_redis()

        all_ok = db_ok and redis_ok
        return HealthResponse(
            status="ok" if all_ok else "degraded",
            version=settings.app_version,
            environment=settings.app_env,
            checks={"database": db_ok, "redis": redis_ok},
        )

    # ── API routers ───────────────────────────────────────────────────────────
    api_prefix = "/v1"

    # Phase 1 — Core PayGuard
    app.include_router(organizations.router, prefix=api_prefix, tags=["Organizations & Auth"])
    app.include_router(orders.router, prefix=api_prefix, tags=["Orders"])
    app.include_router(payments.router, prefix=api_prefix, tags=["Payments & Investigations"])
    app.include_router(webhooks.router, prefix=api_prefix, tags=["Webhooks"])
    app.include_router(audit.router, prefix=api_prefix, tags=["Audit"])

    # Phase 2 — Recovery & MCP
    app.include_router(recovery_router.router, prefix=api_prefix, tags=["Recovery (Phase 2)"])

    # Phase 3 — PaymentGraph (behind feature flag)
    if settings.feature_paymentgraph:
        app.include_router(risk_router.router, prefix=api_prefix, tags=["PaymentGraph (Phase 3)"])
    else:
        # Always expose model card even without feature flag
        app.include_router(risk_router.router, prefix=api_prefix, tags=["PaymentGraph"], include_in_schema=True)

    # Phase 4 — PayDev
    if settings.feature_paydev:
        app.include_router(paydev_router.router, prefix=api_prefix, tags=["PayDev (Phase 4)"])

    # Phase 5 — MerchantOS
    if settings.feature_merchantos:
        app.include_router(merchantos_router.router, prefix=api_prefix, tags=["MerchantOS (Phase 5)"])

    # Phase 6 — ShopAgent
    if settings.feature_shopagent:
        app.include_router(shopagent_router.router, prefix=api_prefix, tags=["ShopAgent (Phase 6)"])

    return app


async def _check_redis() -> bool:
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        return True
    except Exception:
        return False


app = create_app()
