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
        AuditEvent,
    )
    from apps.api.app.utils.ids import new_id
    from apps.api.app.core.security import generate_api_key, compute_audit_event_hash
    from datetime import datetime, timezone, timedelta

    logger.info("🌱 Seeding SYNTHETIC demo data — NOT real payments")
    logger.info("   Marker: %s", SYNTHETIC_MARKER)

    from apps.api.app.core.database import init_db
    await init_db()

    async with get_db_context() as db:
        # Check if already seeded
        from sqlalchemy import select
        existing = await db.execute(select(Organization).where(Organization.slug == "demo-merchant"))
        if existing.scalar_one_or_none():
            logger.info("✓ Demo data already seeded — skipping")
            return

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

        logger.info("")
        logger.info("✅ Demo seeding complete!")
        logger.info("")
        logger.info("  Organization:  %s", org.slug)
        logger.info("  Login:         admin@payguard-ai.example / demo-password-123")
        logger.info("  API Key:       %s  (save this — shown once!)", full_key)
        logger.info("")
        logger.info("  Dashboard:     http://localhost:3000")
        logger.info("  API Docs:      http://localhost:8000/docs")
        logger.info("")
        logger.info("  ⚠  ALL DATA IS SYNTHETIC. No real payments were made.")
        logger.info("     Marker: %s", SYNTHETIC_MARKER)


if __name__ == "__main__":
    asyncio.run(seed_demo_data())
