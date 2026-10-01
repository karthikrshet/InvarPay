"""Initial schema — all tables for InvarPay AI MVP

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2024-09-22

Creates all 20+ domain tables:
- Organizations, Users, Memberships, ApiKeys
- ProviderConnections
- Orders, PaymentAttempts, ProviderEvents, Refunds, FulfillmentRecords
- IdempotencyRecords, OutboxEvents
- ReconciliationRuns, ReconciliationItems
- RiskAssessments, Investigations, AgentRuns, ToolCalls, ApprovalRequests
- AuditEvents
- Customers, Invoices, Settlements
- Products, InventorySnapshots, Carts, CheckoutSessions
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Tenancy ───────────────────────────────────────────────────────────────
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, default=True),
        sa.Column("settings", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("organization_id", sa.String(26), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, default=True),
        sa.Column("is_superuser", sa.Boolean, nullable=False, default=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_organization_id", "users", ["organization_id"])

    op.create_table(
        "memberships",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("organization_id", sa.String(26), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(26), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, default="member"),
        sa.Column("is_active", sa.Boolean, nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_membership_org_user"),
    )

    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("organization_id", sa.String(26), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("key_prefix", sa.String(20), nullable=False),
        sa.Column("key_hash", sa.String(255), nullable=False),
        sa.Column("scopes", sa.Text, nullable=False, default="payments:read"),
        sa.Column("is_test_mode", sa.Boolean, nullable=False, default=False),
        sa.Column("is_active", sa.Boolean, nullable=False, default=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_api_keys_organization_id", "api_keys", ["organization_id"])

    # ── Provider connections ──────────────────────────────────────────────────
    op.create_table(
        "provider_connections",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("organization_id", sa.String(26), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("is_test_mode", sa.Boolean, nullable=False, default=True),
        sa.Column("is_active", sa.Boolean, nullable=False, default=True),
        sa.Column("encrypted_credentials", sa.LargeBinary, nullable=True),
        sa.Column("encrypted_webhook_secret", sa.LargeBinary, nullable=True),
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_test_status", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "provider", name="uq_provider_connection_org_provider"),
    )
    op.create_index("ix_provider_connections_org_id", "provider_connections", ["organization_id"])

    # ── Commerce ──────────────────────────────────────────────────────────────
    op.create_table(
        "customers",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("organization_id", sa.String(26), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_customer_id", sa.String(255), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_customers_organization_id", "customers", ["organization_id"])

    # ── Orders ────────────────────────────────────────────────────────────────
    op.create_table(
        "orders",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("organization_id", sa.String(26), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_order_id", sa.String(255), nullable=True),
        sa.Column("provider_order_id", sa.String(255), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("amount", sa.BigInteger, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, default="INR"),
        sa.Column("status", sa.String(50), nullable=False, default="pending"),
        sa.Column("customer_id", sa.String(26), sa.ForeignKey("customers.id"), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("is_fulfilled", sa.Boolean, nullable=False, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("amount > 0", name="ck_order_amount_positive"),
    )
    op.create_index("ix_orders_organization_id", "orders", ["organization_id"])
    op.create_index("ix_orders_external_id", "orders", ["external_order_id"])

    # ── Approval requests (needed before payment_attempts FK) ─────────────────
    op.create_table(
        "approval_requests",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("organization_id", sa.String(26), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requested_by", sa.String(26), nullable=False),
        sa.Column("operation_type", sa.String(100), nullable=False),
        sa.Column("operation_payload", postgresql.JSONB, nullable=False),
        sa.Column("status", sa.String(50), nullable=False, default="pending"),
        sa.Column("reviewed_by", sa.String(26), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_notes", sa.Text, nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_approval_requests_org_id", "approval_requests", ["organization_id"])

    # ── Payment attempts ──────────────────────────────────────────────────────
    op.create_table(
        "payment_attempts",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("organization_id", sa.String(26), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_id", sa.String(26), sa.ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("provider_connection_id", sa.String(26), sa.ForeignKey("provider_connections.id"), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, default="created"),
        sa.Column("provider_status", sa.String(50), nullable=True),
        sa.Column("provider_payment_id", sa.String(255), nullable=True),
        sa.Column("provider_order_id", sa.String(255), nullable=True),
        sa.Column("amount", sa.BigInteger, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, default="INR"),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("failure_reason", sa.Text, nullable=True),
        sa.Column("failure_code", sa.String(100), nullable=True),
        sa.Column("initiated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("authorized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("is_reconciled", sa.Boolean, nullable=False, default=False),
        sa.Column("reconciled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "idempotency_key", name="uq_payment_attempt_idempotency"),
        sa.UniqueConstraint("organization_id", "provider_payment_id", name="uq_payment_attempt_provider_id"),
        sa.CheckConstraint("amount > 0", name="ck_payment_attempt_amount_positive"),
    )
    op.create_index("ix_payment_attempts_organization_id", "payment_attempts", ["organization_id"])
    op.create_index("ix_payment_attempts_order_id", "payment_attempts", ["order_id"])
    op.create_index("ix_payment_attempts_provider_payment_id", "payment_attempts", ["provider_payment_id"])
    op.create_index("ix_payment_attempts_status", "payment_attempts", ["organization_id", "status"])

    # ── Provider events ───────────────────────────────────────────────────────
    op.create_table(
        "provider_events",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("organization_id", sa.String(26), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("payment_attempt_id", sa.String(26), sa.ForeignKey("payment_attempts.id"), nullable=True),
        sa.Column("provider_connection_id", sa.String(26), sa.ForeignKey("provider_connections.id"), nullable=True),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("provider_event_id", sa.String(255), nullable=False),
        sa.Column("provider_payment_id", sa.String(255), nullable=True),
        sa.Column("provider_order_id", sa.String(255), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB, nullable=False),
        sa.Column("signature_verified", sa.Boolean, nullable=False, default=False),
        sa.Column("processed", sa.Boolean, nullable=False, default=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_error", sa.Text, nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("provider", "provider_event_id", name="uq_provider_event_dedup"),
    )
    op.create_index("ix_provider_events_organization_id", "provider_events", ["organization_id"])
    op.create_index("ix_provider_events_payment_attempt_id", "provider_events", ["payment_attempt_id"])
    op.create_index("ix_provider_events_provider_payment_id", "provider_events", ["provider_payment_id"])
    op.create_index("ix_provider_events_unprocessed", "provider_events", ["processed", "received_at"])

    # ── Refunds ───────────────────────────────────────────────────────────────
    op.create_table(
        "refunds",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("organization_id", sa.String(26), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("payment_attempt_id", sa.String(26), sa.ForeignKey("payment_attempts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("provider_refund_id", sa.String(255), nullable=True),
        sa.Column("amount", sa.BigInteger, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("status", sa.String(50), nullable=False, default="pending"),
        sa.Column("initiated_by", sa.String(26), nullable=True),
        sa.Column("approval_request_id", sa.String(26), sa.ForeignKey("approval_requests.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("amount > 0", name="ck_refund_amount_positive"),
    )
    op.create_index("ix_refunds_organization_id", "refunds", ["organization_id"])
    op.create_index("ix_refunds_payment_attempt_id", "refunds", ["payment_attempt_id"])

    # ── Fulfillment records ───────────────────────────────────────────────────
    op.create_table(
        "fulfillment_records",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("organization_id", sa.String(26), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_id", sa.String(26), sa.ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("payment_attempt_id", sa.String(26), sa.ForeignKey("payment_attempts.id"), nullable=False),
        sa.Column("fulfillment_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, default="pending"),
        sa.Column("fulfilled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "order_id", "fulfillment_type", name="uq_fulfillment_order_type"),
    )

    # ── Reconciliation ────────────────────────────────────────────────────────
    op.create_table(
        "reconciliation_runs",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("organization_id", sa.String(26), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("triggered_by", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, default="running"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_items", sa.Integer, default=0),
        sa.Column("matched_items", sa.Integer, default=0),
        sa.Column("mismatched_items", sa.Integer, default=0),
        sa.Column("unresolved_items", sa.Integer, default=0),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_reconciliation_runs_org_id", "reconciliation_runs", ["organization_id"])

    op.create_table(
        "reconciliation_items",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("organization_id", sa.String(26), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_id", sa.String(26), sa.ForeignKey("reconciliation_runs.id"), nullable=False),
        sa.Column("payment_attempt_id", sa.String(26), sa.ForeignKey("payment_attempts.id"), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("our_amount", sa.BigInteger, nullable=False),
        sa.Column("our_currency", sa.String(3), nullable=False),
        sa.Column("provider_amount", sa.BigInteger, nullable=True),
        sa.Column("provider_currency", sa.String(3), nullable=True),
        sa.Column("provider_status", sa.String(50), nullable=True),
        sa.Column("discrepancy_reason", sa.Text, nullable=True),
        sa.Column("resolved", sa.Boolean, nullable=False, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_reconciliation_items_run_id", "reconciliation_items", ["run_id"])
    op.create_index("ix_reconciliation_items_payment_id", "reconciliation_items", ["payment_attempt_id"])

    # ── Idempotency & Outbox ──────────────────────────────────────────────────
    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("scope", sa.String(100), nullable=False),
        sa.Column("key", sa.String(255), nullable=False),
        sa.Column("organization_id", sa.String(26), nullable=True),
        sa.Column("response_status", sa.Integer, nullable=True),
        sa.Column("response_body", postgresql.JSONB, nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("scope", "key", name="uq_idempotency_scope_key"),
    )

    op.create_table(
        "outbox_events",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("organization_id", sa.String(26), nullable=True),
        sa.Column("aggregate_type", sa.String(100), nullable=False),
        sa.Column("aggregate_id", sa.String(26), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("status", sa.String(50), nullable=False, default="pending"),
        sa.Column("attempts", sa.Integer, nullable=False, default=0),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_outbox_pending", "outbox_events", ["status", "next_attempt_at"])
    op.create_index("ix_outbox_org_id", "outbox_events", ["organization_id"])

    # ── Agent infrastructure ──────────────────────────────────────────────────
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("organization_id", sa.String(26), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_type", sa.String(100), nullable=False),
        sa.Column("triggered_by", sa.String(26), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, default="running"),
        sa.Column("input", postgresql.JSONB, nullable=True),
        sa.Column("output", postgresql.JSONB, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("token_usage", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_agent_runs_org_id", "agent_runs", ["organization_id"])

    op.create_table(
        "tool_calls",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("agent_run_id", sa.String(26), sa.ForeignKey("agent_runs.id"), nullable=False),
        sa.Column("tool_name", sa.String(100), nullable=False),
        sa.Column("input", postgresql.JSONB, nullable=True),
        sa.Column("output", postgresql.JSONB, nullable=True),
        sa.Column("status", sa.String(50), nullable=False, default="success"),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("policy_checked", sa.Boolean, nullable=False, default=False),
        sa.Column("policy_approved", sa.Boolean, nullable=False, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_tool_calls_agent_run_id", "tool_calls", ["agent_run_id"])

    op.create_table(
        "investigations",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("organization_id", sa.String(26), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("payment_attempt_id", sa.String(26), sa.ForeignKey("payment_attempts.id"), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, default="pending"),
        sa.Column("triggered_by", sa.String(26), nullable=False),
        sa.Column("trigger_reason", sa.Text, nullable=True),
        sa.Column("findings", postgresql.JSONB, nullable=True),
        sa.Column("recommendation", sa.Text, nullable=True),
        sa.Column("agent_run_id", sa.String(26), sa.ForeignKey("agent_runs.id"), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_investigations_org_id", "investigations", ["organization_id"])
    op.create_index("ix_investigations_payment_id", "investigations", ["payment_attempt_id"])

    # ── Risk assessments (PaymentGraph scaffold) ──────────────────────────────
    op.create_table(
        "risk_assessments",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("organization_id", sa.String(26), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("payment_attempt_id", sa.String(26), sa.ForeignKey("payment_attempts.id"), nullable=False),
        sa.Column("risk_level", sa.String(20), nullable=False),
        sa.Column("score", sa.Float, nullable=True),
        sa.Column("signals", postgresql.JSONB, nullable=True),
        sa.Column("explanation", sa.Text, nullable=True),
        sa.Column("model_version", sa.String(50), nullable=True),
        sa.Column("human_reviewed", sa.Boolean, nullable=False, default=False),
        sa.Column("reviewer_id", sa.String(26), nullable=True),
        sa.Column("review_decision", sa.String(50), nullable=True),
        sa.Column("review_notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_risk_assessments_payment_id", "risk_assessments", ["payment_attempt_id"])

    # ── Audit events (append-only, hash-chained) ──────────────────────────────
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("organization_id", sa.String(26), nullable=True),
        sa.Column("actor_id", sa.String(26), nullable=True),
        sa.Column("actor_type", sa.String(50), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(26), nullable=True),
        sa.Column("details", postgresql.JSONB, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("previous_hash", sa.String(64), nullable=True),
        sa.Column("event_hash", sa.String(64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_events_organization_id", "audit_events", ["organization_id"])
    op.create_index("ix_audit_events_occurred_at", "audit_events", ["occurred_at"])
    op.create_index("ix_audit_events_org_occurred", "audit_events", ["organization_id", "occurred_at"])

    # ── MerchantOS (Phase 5 scaffold) ─────────────────────────────────────────
    op.create_table(
        "invoices",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("organization_id", sa.String(26), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invoice_number", sa.String(255), nullable=False),
        sa.Column("customer_id", sa.String(26), sa.ForeignKey("customers.id"), nullable=True),
        sa.Column("amount", sa.BigInteger, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, default="draft"),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("line_items", postgresql.JSONB, nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "invoice_number", name="uq_invoice_org_number"),
    )

    op.create_table(
        "settlements",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("organization_id", sa.String(26), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("provider_settlement_id", sa.String(255), nullable=True),
        sa.Column("amount", sa.BigInteger, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, default="pending"),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── ShopAgent (Phase 6 scaffold) ──────────────────────────────────────────
    op.create_table(
        "products",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("organization_id", sa.String(26), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("sku", sa.String(100), nullable=True),
        sa.Column("price", sa.BigInteger, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, default=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "inventory_snapshots",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("organization_id", sa.String(26), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.String(26), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("quantity_available", sa.Integer, nullable=False),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "carts",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("organization_id", sa.String(26), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_id", sa.String(26), sa.ForeignKey("customers.id"), nullable=True),
        sa.Column("session_id", sa.String(255), nullable=True),
        sa.Column("items", postgresql.JSONB, nullable=True),
        sa.Column("status", sa.String(50), nullable=False, default="active"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "checkout_sessions",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("organization_id", sa.String(26), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cart_id", sa.String(26), sa.ForeignKey("carts.id"), nullable=False),
        sa.Column("order_id", sa.String(26), sa.ForeignKey("orders.id"), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, default="open"),
        sa.Column("buyer_confirmed", sa.Boolean, nullable=False, default=False),
        sa.Column("buyer_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("amount", sa.BigInteger, nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_checkout_url", sa.Text, nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("checkout_sessions")
    op.drop_table("carts")
    op.drop_table("inventory_snapshots")
    op.drop_table("products")
    op.drop_table("settlements")
    op.drop_table("invoices")
    op.drop_table("audit_events")
    op.drop_table("risk_assessments")
    op.drop_table("investigations")
    op.drop_table("tool_calls")
    op.drop_table("agent_runs")
    op.drop_table("outbox_events")
    op.drop_table("idempotency_records")
    op.drop_table("reconciliation_items")
    op.drop_table("reconciliation_runs")
    op.drop_table("fulfillment_records")
    op.drop_table("refunds")
    op.drop_table("provider_events")
    op.drop_table("payment_attempts")
    op.drop_table("approval_requests")
    op.drop_table("orders")
    op.drop_table("customers")
    op.drop_table("provider_connections")
    op.drop_table("api_keys")
    op.drop_table("memberships")
    op.drop_table("users")
    op.drop_table("organizations")
