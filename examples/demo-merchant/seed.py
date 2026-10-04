"""
InvarPay AI — Demo Seed Script

Generates SYNTHETIC demo data for development and demonstration purposes.
ALL data here is fictional. No real payments, real merchants, or real customers.
Labelled clearly throughout.

Run: python examples/demo-merchant/seed.py
Or:  make seed
"""
from __future__ import annotations

import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed")

SYNTHETIC_MARKER = "[SYNTHETIC-DEMO-DATA]"


async def seed_demo_data() -> None:
    """Seed synthetic demo data into the database."""
    from apps.api.app.core.database import get_db_context
    from apps.api.app.core.security import hash_password, encrypt_credential
    from apps.api.app.models import (
        Organization, User, Membership, ApiKey, ProviderConnection,
        Customer, Order, PaymentAttempt, PaymentAttemptStatus,
        AuditEvent, Product, InventorySnapshot,
    )
    from apps.api.app.utils.ids import new_id
    from apps.api.app.core.security import generate_api_key, compute_audit_event_hash
    from datetime import datetime, timezone, timedelta

    logger.info("🌱 Seeding SYNTHETIC demo data — NOT real payments")
    logger.info("   Marker: %s", SYNTHETIC_MARKER)

    from apps.api.app.core.database import init_db
    await init_db()

    async with get_db_context() as db:
        # Check if org exists
        from sqlalchemy import select
        existing = await db.execute(select(Organization).where(Organization.slug == "demo-merchant"))
        org = existing.scalar_one_or_none()

        if not org:
            # ── Create demo organization ──────────────────────────────────────────
            org = Organization(
                id=new_id(),
                name=f"Demo Merchant Inc. {SYNTHETIC_MARKER}",
                slug="demo-merchant",
                email="demo@payguard-ai.example",
                is_active=True,
                settings={"demo": True, "marker": SYNTHETIC_MARKER},
            )
            db.add(org)
            await db.flush()
            logger.info("  → Created organization: %s (%s)", org.name, org.id)

            # ── Create demo user ──────────────────────────────────────────────────
            user = User(
                id=new_id(),
                organization_id=org.id,
                email="admin@payguard-ai.example",
                hashed_password=hash_password("demo-password-123"),
                full_name=f"Demo Admin {SYNTHETIC_MARKER}",
                is_active=True,
            )
            db.add(user)

            membership = Membership(
                id=new_id(),
                organization_id=org.id,
                user_id=user.id,
                role="owner",
                is_active=True,
            )
            db.add(membership)
            await db.flush()
            logger.info("  → Created user: %s", user.email)

            # ── Create test API key ───────────────────────────────────────────────
            full_key, key_hash = generate_api_key(test_mode=True)
            from apps.api.app.core.config import get_settings
            s = get_settings()
            api_key = ApiKey(
                id=new_id(),
                organization_id=org.id,
                name=f"Demo Test Key {SYNTHETIC_MARKER}",
                key_prefix=s.api_key_test_prefix,
                key_hash=key_hash,
                scopes="payments:read,orders:read,orders:write,payments:reconcile,investigations:write,investigations:read,audit:read,api_keys:write",
                is_test_mode=True,
                is_active=True,
            )
            db.add(api_key)
            await db.flush()

            # ── Create fake provider connection ───────────────────────────────────
            provider_conn = ProviderConnection(
                id=new_id(),
                organization_id=org.id,
                provider="fake",
                display_name=f"Fake Provider {SYNTHETIC_MARKER}",
                is_test_mode=True,
                is_active=True,
                encrypted_credentials=encrypt_credential("fake-key-id:fake-secret"),
                encrypted_webhook_secret=encrypt_credential("fake-webhook-secret-for-tests"),
                last_test_status="ok",
            )
            db.add(provider_conn)
            await db.flush()
            logger.info("  → Created fake provider connection")

            # ── Create synthetic customers ────────────────────────────────────────
            customers = []
            for i in range(3):
                c = Customer(
                    id=new_id(),
                    organization_id=org.id,
                    email=f"customer{i+1}@example.com",
                    name=f"Customer {i+1} {SYNTHETIC_MARKER}",
                )
                db.add(c)
                customers.append(c)
            await db.flush()
            logger.info("  → Created %d synthetic customers", len(customers))

            # ── Create synthetic orders and payments ──────────────────────────────
            scenarios = [
                ("success", 50000, "INR", "Order for Product A"),
                ("failure", 25000, "INR", "Order for Product B"),
                ("unknown", 75000, "INR", "Order for Product C — TIMEOUT"),
                ("success", 100000, "INR", "Order for Product D"),
                ("success", 10099, "INR", "Order for Product E"),
            ]

            from integrations.providers.fake.provider import FakeProvider
            fake_provider = FakeProvider("fake-webhook-secret-for-tests")

            for i, (outcome, amount, currency, desc) in enumerate(scenarios):
                order = Order(
                    id=new_id(),
                    organization_id=org.id,
                    amount=amount,
                    currency=currency,
                    description=f"{desc} {SYNTHETIC_MARKER}",
                    status="pending",
                    customer_id=customers[i % len(customers)].id,
                )
                db.add(order)
                await db.flush()

                # Simulate payment via fake provider
                fake_order = fake_provider.create_order(amount, currency, receipt=order.id)
                order.provider_order_id = fake_order["id"]

                fake_payment = fake_provider.initiate_payment(fake_order["id"], outcome=outcome)
                fake_provider.process_payment(fake_payment["id"])

                # Map outcome to internal status
                status_map = {
                    "success": PaymentAttemptStatus.CAPTURED,
                    "failure": PaymentAttemptStatus.FAILED,
                    "unknown": PaymentAttemptStatus.UNKNOWN,
                }

                now = datetime.now(timezone.utc)
                attempt = PaymentAttempt(
                    id=new_id(),
                    organization_id=org.id,
                    order_id=order.id,
                    amount=amount,
                    currency=currency,
                    status=status_map[outcome],
                    provider_status=fake_payment["status"],
                    provider_payment_id=fake_payment["id"],
                    provider_order_id=fake_order["id"],
                    idempotency_key=f"demo-{order.id}-attempt-1",
                    initiated_at=now - timedelta(minutes=5),
                    captured_at=now if outcome == "success" else None,
                    failed_at=now if outcome == "failure" else None,
                    is_reconciled=outcome != "unknown",
                    reconciled_at=now if outcome != "unknown" else None,
                )
                db.add(attempt)
                logger.info("  → Created %s payment: %s %d %s (ID: %s)",
                           outcome.upper(), currency, amount, desc, attempt.id)

            await db.flush()

            # ── Audit event for setup ─────────────────────────────────────────────
            event_id = new_id()
            audit = AuditEvent(
                id=event_id,
                organization_id=org.id,
                actor_id="system",
                actor_type="system",
                action="demo.seeded",
                resource_type="organization",
                resource_id=org.id,
                details={"marker": SYNTHETIC_MARKER, "scenarios": len(scenarios)},
                event_hash=compute_audit_event_hash(
                    event_id, "demo.seeded", "organization", org.id,
                    datetime.now(timezone.utc).isoformat(), None
                ),
                occurred_at=datetime.now(timezone.utc),
            )
            db.add(audit)
            await db.flush()

        # ── Ensure Product Catalog & Inventory Snapshots ───────────────────────
        prod_check = await db.execute(select(Product).where(Product.organization_id == org.id))
        existing_prods = prod_check.scalars().all()
        if not existing_prods:
            demo_products = [
                {
                    "name": "InvarPay Sentinel Hardware Node",
                    "description": "High-throughput edge hardware security module for autonomous webhook verification & tamper-proofing.",
                    "sku": "INVAR-HW-01",
                    "price": 2499900,  # ₹24,999.00
                    "currency": "INR",
                    "extra_metadata": {"category": "Hardware", "stock": 45, "rating": 4.9, "badge": "Hardware HSM"},
                    "quantity": 45,
                },
                {
                    "name": "Enterprise PayDev AST Linter Suite",
                    "description": "Static code analysis engine detecting webhook bugs, hardcoded secrets, and float rounding vulnerabilities.",
                    "sku": "INVAR-DEV-S1",
                    "price": 999900,   # ₹9,999.00
                    "currency": "INR",
                    "extra_metadata": {"category": "Software", "stock": 120, "rating": 5.0, "badge": "Developer Tool"},
                    "quantity": 120,
                },
                {
                    "name": "Autonomous Ledger Reconciler Box",
                    "description": "Automated double-entry general ledger with real-time bank settlement UTR matching and dispute hold protection.",
                    "sku": "INVAR-LEDGER-01",
                    "price": 4999900,  # ₹49,999.00
                    "currency": "INR",
                    "extra_metadata": {"category": "Enterprise", "stock": 25, "rating": 4.8, "badge": "Financial Engine"},
                    "quantity": 25,
                },
                {
                    "name": "PaymentGraph AI Sentinel License",
                    "description": "Multi-signal heuristic risk graph scoring velocity, proxy IPs, BIN mismatches, and synthetic chargeback vectors.",
                    "sku": "INVAR-GRAPH-AI",
                    "price": 1499900,  # ₹14,999.00
                    "currency": "INR",
                    "extra_metadata": {"category": "AI / ML", "stock": 80, "rating": 4.9, "badge": "Autonomous AI"},
                    "quantity": 80,
                },
                {
                    "name": "Cryptographic Merkle HSM Key Token",
                    "description": "FIPS 140-3 Level 4 tamper-evident cryptographic USB token for SHA-256 audit log notarization.",
                    "sku": "INVAR-HSM-K1",
                    "price": 750000,   # ₹7,500.00
                    "currency": "INR",
                    "extra_metadata": {"category": "Hardware", "stock": 60, "rating": 4.7, "badge": "Security Token"},
                    "quantity": 60,
                },
                {
                    "name": "ShopAgent Safe Checkout Adapter",
                    "description": "Autonomous commerce agent client with mandatory buyer confirmation gates and zero-card-retention guarantee.",
                    "sku": "INVAR-SHOP-AGENT",
                    "price": 1250000,  # ₹12,500.00
                    "currency": "INR",
                    "extra_metadata": {"category": "Software", "stock": 95, "rating": 4.9, "badge": "Agentic Commerce"},
                    "quantity": 95,
                },
            ]

            for p_info in demo_products:
                prod = Product(
                    id=new_id(),
                    organization_id=org.id,
                    name=p_info["name"],
                    description=p_info["description"],
                    sku=p_info["sku"],
                    price=p_info["price"],
                    currency=p_info["currency"],
                    is_active=True,
                    extra_metadata=p_info["extra_metadata"],
                )
                db.add(prod)
                inv = InventorySnapshot(
                    id=new_id(),
                    organization_id=org.id,
                    product_id=prod.id,
                    quantity_available=p_info["quantity"],
                    snapshot_at=datetime.now(timezone.utc),
                )
                db.add(inv)
            await db.flush()
            logger.info("  ✓ Seeded %d products and inventory snapshots", len(demo_products))

        # ── Ensure Sample Investigations for Unknown Payments ─────────────────
        from apps.api.app.models import Investigation, InvestigationStatus
        inv_check = await db.execute(select(Investigation).where(Investigation.organization_id == org.id))
        existing_invs = inv_check.scalars().all()
        if not existing_invs:
            # Find an unknown or pending payment attempt
            unknown_pay_res = await db.execute(
                select(PaymentAttempt).where(
                    PaymentAttempt.organization_id == org.id,
                    PaymentAttempt.status == PaymentAttemptStatus.UNKNOWN,
                ).limit(1)
            )
            unknown_pay = unknown_pay_res.scalar_one_or_none()
            pay_id = unknown_pay.id if unknown_pay else "pay_demo_ambiguous_01"

            sample_investigations = [
                Investigation(
                    id=new_id(),
                    organization_id=org.id,
                    payment_attempt_id=pay_id,
                    status=InvestigationStatus.PENDING,
                    triggered_by="InvarPay Policy Engine",
                    trigger_reason="Provider returned 504 Gateway Timeout during capture call. Policy engine blocked blind retry.",
                    findings={
                        "risk_score": 78,
                        "ip_reputation": "TOR_EXIT_NODE_SUSPECTED",
                        "attempt_id": pay_id,
                        "recommendation": "Require manual compliance verification before capture confirmation.",
                    },
                    recommendation="Hold capture until bank UTR confirmation is verified via MerchantOS.",
                ),
                Investigation(
                    id=new_id(),
                    organization_id=org.id,
                    payment_attempt_id=pay_id,
                    status=InvestigationStatus.COMPLETED,
                    triggered_by="PaymentGraph Heuristic PG001",
                    trigger_reason="High-velocity card retry detected (3 attempts in 45s). Verified merchant customer profile.",
                    findings={
                        "risk_score": 14,
                        "card_hash_match": True,
                        "chargeback_probability": "0.001%",
                    },
                    recommendation="Auto-cleared step-up verification. Payment authorized for settlement.",
                    completed_at=datetime.now(timezone.utc),
                ),
            ]
            for sinv in sample_investigations:
                db.add(sinv)
            await db.flush()
            logger.info("  ✓ Seeded %d sample investigations", len(sample_investigations))

        # ── Ensure Chained Audit Trail Events ─────────────────────────────────
        from sqlalchemy import func
        audit_check = await db.execute(select(func.count(AuditEvent.id)).where(AuditEvent.organization_id == org.id))
        audit_count = audit_check.scalar() or 0
        if audit_count < 4:
            actions = [
                ("payment.capture.verified", "payment_attempt", "webhook:razorpay-test", "HMAC-SHA256 signature verified with zero double-charge risk."),
                ("webhook.signature.validated", "provider_event", "security:hmac-sha256", "Inbound payload verified against active secret key."),
                ("retry.prevented.ambiguous_state", "payment_attempt", "state_machine:guard", "Automated retry blocked by deny-by-default safety policy."),
                ("langgraph.dispute_triage.logged", "investigation", "langgraph:agent", "Autonomous dispute investigation completed and logged to ledger."),
            ]
            last_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            for i, (action, r_type, actor, note) in enumerate(actions):
                ev_id = new_id()
                occurred = datetime.now(timezone.utc) - timedelta(minutes=(40 - i * 8))
                h = compute_audit_event_hash(
                    ev_id, action, r_type, f"res_{i+1}", occurred.isoformat(), last_hash
                )
                last_hash = h
                db.add(AuditEvent(
                    id=ev_id,
                    organization_id=org.id,
                    actor_id=actor,
                    actor_type="system",
                    action=action,
                    resource_type=r_type,
                    resource_id=f"res_{i+1}",
                    details={"note": note, "marker": SYNTHETIC_MARKER},
                    event_hash=h,
                    occurred_at=occurred,
                ))
            await db.flush()
            logger.info("  ✓ Seeded %d chained audit events", len(actions))

        logger.info("")
        logger.info("✅ Demo seeding complete!")
        logger.info("")
        logger.info("  Organization:  %s", org.slug)
        logger.info("  Login:         admin@payguard-ai.example / demo-password-123")
        logger.info("  API Key:       %s  (save this — shown once!)", full_key if 'full_key' in locals() else 'pg_test_live_key_configured')
        logger.info("")
        logger.info("  Dashboard:     http://localhost:3000")
        logger.info("  API Docs:      http://localhost:8000/docs")
        logger.info("")
        logger.info("  ⚠  ALL DATA IS SYNTHETIC. No real payments were made.")
        logger.info("     Marker: %s", SYNTHETIC_MARKER)


if __name__ == "__main__":
    asyncio.run(seed_demo_data())
