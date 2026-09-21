"""
PayGuard AI — SQLAlchemy ORM Models
Complete domain model for all five product modules.

Key invariants enforced here:
- Every tenant-owned row has organization_id (FK + index)
- Monetary amounts are BIGINT minor units + VARCHAR(3) currency code
- No raw card data, CVV, UPI PIN, or banking passwords
- Unique constraints on provider event IDs, idempotency keys
"""
from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


# ──────────────────────────────────────────────
# ENUMS
# ──────────────────────────────────────────────

class PaymentAttemptStatus(str, enum.Enum):
    """
    Payment attempt state machine states.
    See docs/architecture/payment-state-machine.md for transition graph.
    INVARIANT: unknown is NOT failed. A network timeout never authorizes retry.
    """
    CREATED = "created"
    INITIATED = "initiated"
    PENDING = "pending"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    FAILED = "failed"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"  # Outcome unclear — do NOT retry without reconciliation


class RefundStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ReconciliationStatus(str, enum.Enum):
    MATCHED = "matched"
    MISMATCHED = "mismatched"
    UNRESOLVED = "unresolved"
    MANUAL_REVIEW = "manual_review"


class InvestigationStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    AWAITING_APPROVAL = "awaiting_approval"


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class UserRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class OutboxStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DELIVERED = "delivered"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class CheckoutStatus(str, enum.Enum):
    OPEN = "open"
    PENDING_CONFIRMATION = "pending_confirmation"
    CONFIRMED = "confirmed"
    EXPIRED = "expired"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# ──────────────────────────────────────────────
# MIXINS
# ──────────────────────────────────────────────

class TimestampMixin:
    """Adds created_at and updated_at to any model."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False
    )


class TenantMixin:
    """Every tenant-owned table must include organization_id."""
    organization_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )


# ──────────────────────────────────────────────
# TENANCY & AUTH
# ──────────────────────────────────────────────

class Organization(TimestampMixin, Base):
    """Top-level tenant. All data scoped under org."""
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)  # ULID
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    settings: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Relationships
    users: Mapped[list["User"]] = relationship("User", back_populates="organization")
    memberships: Mapped[list["Membership"]] = relationship("Membership", back_populates="organization")
    api_keys: Mapped[list["ApiKey"]] = relationship("ApiKey", back_populates="organization")
    provider_connections: Mapped[list["ProviderConnection"]] = relationship(
        "ProviderConnection", back_populates="organization"
    )
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="organization")


class User(TimestampMixin, Base):
    """Application user. May belong to multiple orgs via Membership."""
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="users")
    memberships: Mapped[list["Membership"]] = relationship("Membership", back_populates="user")


class Membership(TimestampMixin, Base):
    """User's role within an organization."""
    __tablename__ = "memberships"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), nullable=False, default=UserRole.MEMBER
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="memberships")
    user: Mapped["User"] = relationship("User", back_populates="memberships")

    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_membership_org_user"),
    )


class ApiKey(TimestampMixin, Base):
    """Scoped API key for programmatic access. Prefix indicates environment."""
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(20), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False)  # bcrypt hash
    # Scopes: comma-separated list e.g. "payments:read,orders:read"
    scopes: Mapped[str] = mapped_column(Text, nullable=False, default="payments:read")
    is_test_mode: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="api_keys")


# ──────────────────────────────────────────────
# PROVIDER CONNECTIONS
# ──────────────────────────────────────────────

class ProviderConnection(TimestampMixin, Base):
    """
    Payment provider credentials for an organization.
    Credentials are stored encrypted — never in plaintext.
    """
    __tablename__ = "provider_connections"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # "razorpay", "fake"
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_test_mode: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Encrypted credentials blob (AES-256-GCM). Never stored plaintext.
    encrypted_credentials: Mapped[Optional[bytes]] = mapped_column(nullable=True)
    # Webhook signing secret (encrypted)
    encrypted_webhook_secret: Mapped[Optional[bytes]] = mapped_column(nullable=True)
    last_tested_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_test_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="provider_connections"
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "provider", name="uq_provider_connection_org_provider"),
    )


# ──────────────────────────────────────────────
# PAYMENT DOMAIN
# ──────────────────────────────────────────────

class Order(TimestampMixin, TenantMixin, Base):
    """
    Merchant's business intent to collect payment.
    Separate from payment attempts — one order can have multiple attempts.
    """
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    # organization_id from TenantMixin
    external_order_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    provider_order_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Amounts in minor units (paise for INR)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    customer_id: Mapped[Optional[str]] = mapped_column(
        String(26), ForeignKey("customers.id"), nullable=True
    )
    extra_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    is_fulfilled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="orders")
    payment_attempts: Mapped[list["PaymentAttempt"]] = relationship(
        "PaymentAttempt", back_populates="order"
    )
    fulfillment_records: Mapped[list["FulfillmentRecord"]] = relationship(
        "FulfillmentRecord", back_populates="order"
    )
    customer: Mapped[Optional["Customer"]] = relationship("Customer", back_populates="orders")

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_order_amount_positive"),
    )


class PaymentAttempt(TimestampMixin, TenantMixin, Base):
    """
    A single attempt to process payment for an order.
    State machine: created → initiated → pending → authorized → captured | failed | cancelled | unknown

    INVARIANTS:
    - unknown is NOT failed — do not retry without reconciliation
    - Network timeout → unknown, never triggers retry
    - Only verified provider responses may update provider_status
    """
    __tablename__ = "payment_attempts"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    # organization_id from TenantMixin
    order_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    provider_connection_id: Mapped[Optional[str]] = mapped_column(
        String(26), ForeignKey("provider_connections.id"), nullable=True
    )

    # Internal state (authoritative)
    status: Mapped[PaymentAttemptStatus] = mapped_column(
        Enum(PaymentAttemptStatus, name="payment_attempt_status"),
        nullable=False,
        default=PaymentAttemptStatus.CREATED
    )
    # Provider-reported status (unverified until webhook signature confirmed)
    provider_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    provider_payment_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    provider_order_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")

    # Idempotency key for this attempt
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)

    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    failure_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    initiated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    authorized_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    captured_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    extra_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Safety: track if this attempt was reconciled
    is_reconciled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reconciled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    order: Mapped["Order"] = relationship("Order", back_populates="payment_attempts")
    provider_events: Mapped[list["ProviderEvent"]] = relationship(
        "ProviderEvent", back_populates="payment_attempt"
    )
    refunds: Mapped[list["Refund"]] = relationship("Refund", back_populates="payment_attempt")
    investigations: Mapped[list["Investigation"]] = relationship(
        "Investigation", back_populates="payment_attempt"
    )
    reconciliation_items: Mapped[list["ReconciliationItem"]] = relationship(
        "ReconciliationItem", back_populates="payment_attempt"
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "idempotency_key", name="uq_payment_attempt_idempotency"),
        UniqueConstraint("organization_id", "provider_payment_id", name="uq_payment_attempt_provider_id"),
        CheckConstraint("amount > 0", name="ck_payment_attempt_amount_positive"),
        Index("ix_payment_attempts_status", "organization_id", "status"),
    )


class ProviderEvent(TimestampMixin, TenantMixin, Base):
    """
    Raw event received from a payment provider (webhook).
    Stored before any processing. Signature must be verified before trusting payload.
    Inbox deduplication prevents duplicate processing.
    """
    __tablename__ = "provider_events"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    # organization_id from TenantMixin
    payment_attempt_id: Mapped[Optional[str]] = mapped_column(
        String(26), ForeignKey("payment_attempts.id"), nullable=True, index=True
    )
    provider_connection_id: Mapped[Optional[str]] = mapped_column(
        String(26), ForeignKey("provider_connections.id"), nullable=True
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    # Provider's unique event ID for deduplication
    provider_event_id: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_payment_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    provider_order_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Raw payload stored as-is (after signature verification)
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Signature verification result
    signature_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Processing state
    processed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    payment_attempt: Mapped[Optional["PaymentAttempt"]] = relationship(
        "PaymentAttempt", back_populates="provider_events"
    )

    __table_args__ = (
        # Inbox deduplication: same provider event processed only once per tenant.
        UniqueConstraint("organization_id", "provider", "provider_event_id", name="uq_provider_event_dedup"),
        Index("ix_provider_events_unprocessed", "processed", "received_at"),
    )


class Refund(TimestampMixin, TenantMixin, Base):
    """Refund on a captured payment. Requires explicit permission and approval."""
    __tablename__ = "refunds"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    # organization_id from TenantMixin
    payment_attempt_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("payment_attempts.id", ondelete="RESTRICT"),
        nullable=False, index=True
    )
    provider_refund_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[RefundStatus] = mapped_column(
        Enum(RefundStatus, name="refund_status"), nullable=False, default=RefundStatus.PENDING
    )
    initiated_by: Mapped[Optional[str]] = mapped_column(String(26), nullable=True)  # user_id
    approval_request_id: Mapped[Optional[str]] = mapped_column(
        String(26), ForeignKey("approval_requests.id"), nullable=True
    )

    payment_attempt: Mapped["PaymentAttempt"] = relationship("PaymentAttempt", back_populates="refunds")

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_refund_amount_positive"),
    )


class FulfillmentRecord(TimestampMixin, TenantMixin, Base):
    """
    Business fulfillment triggered after successful payment.
    Separate from payment state — prevents double fulfillment.
    """
    __tablename__ = "fulfillment_records"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    # organization_id from TenantMixin
    order_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    payment_attempt_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("payment_attempts.id"), nullable=False
    )
    fulfillment_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    fulfilled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    extra_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    order: Mapped["Order"] = relationship("Order", back_populates="fulfillment_records")

    __table_args__ = (
        # Prevent double fulfillment for the same order
        UniqueConstraint("organization_id", "order_id", "fulfillment_type",
                         name="uq_fulfillment_order_type"),
    )


# ──────────────────────────────────────────────
# RECONCILIATION
# ──────────────────────────────────────────────

class ReconciliationRun(TimestampMixin, TenantMixin, Base):
    """A reconciliation job run for an organization."""
    __tablename__ = "reconciliation_runs"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    # organization_id from TenantMixin
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    triggered_by: Mapped[str] = mapped_column(String(50), nullable=False)  # "manual", "scheduled", "auto"
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    matched_items: Mapped[int] = mapped_column(Integer, default=0)
    mismatched_items: Mapped[int] = mapped_column(Integer, default=0)
    unresolved_items: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    items: Mapped[list["ReconciliationItem"]] = relationship(
        "ReconciliationItem", back_populates="run"
    )


class ReconciliationItem(TimestampMixin, TenantMixin, Base):
    """Result of reconciling a single payment attempt against provider data."""
    __tablename__ = "reconciliation_items"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    # organization_id from TenantMixin
    run_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("reconciliation_runs.id"), nullable=False, index=True
    )
    payment_attempt_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("payment_attempts.id"), nullable=False, index=True
    )
    status: Mapped[ReconciliationStatus] = mapped_column(
        Enum(ReconciliationStatus, name="reconciliation_status"), nullable=False
    )
    our_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    our_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    provider_amount: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    provider_currency: Mapped[Optional[str]] = mapped_column(String(3), nullable=True)
    provider_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    discrepancy_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    run: Mapped["ReconciliationRun"] = relationship("ReconciliationRun", back_populates="items")
    payment_attempt: Mapped["PaymentAttempt"] = relationship(
        "PaymentAttempt", back_populates="reconciliation_items"
    )


# ──────────────────────────────────────────────
# IDEMPOTENCY & OUTBOX
# ──────────────────────────────────────────────

class IdempotencyRecord(TimestampMixin, Base):
    """
    Durable idempotency store. Ensures duplicate requests return cached responses.
    NOT tenant-specific — keyed by (scope, key) globally.
    """
    __tablename__ = "idempotency_records"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    scope: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "webhook", "payment"
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    organization_id: Mapped[Optional[str]] = mapped_column(String(26), nullable=True)
    response_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response_body: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("scope", "key", name="uq_idempotency_scope_key"),
    )


class OutboxEvent(TimestampMixin, Base):
    """
    Transactional outbox. Events written atomically with DB mutations.
    Worker delivers them to queues/webhooks.
    """
    __tablename__ = "outbox_events"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    organization_id: Mapped[Optional[str]] = mapped_column(String(26), nullable=True, index=True)
    aggregate_type: Mapped[str] = mapped_column(String(100), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(26), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[OutboxStatus] = mapped_column(
        Enum(OutboxStatus, name="outbox_status"), nullable=False, default=OutboxStatus.PENDING
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_attempt_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_attempt_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_outbox_pending", "status", "next_attempt_at"),
    )


# ──────────────────────────────────────────────
# RISK & INVESTIGATION (PaymentGraph — Phase 3)
# ──────────────────────────────────────────────

class RiskAssessment(TimestampMixin, TenantMixin, Base):
    """
    Risk evaluation for a payment attempt.
    NOTE: Phase 3 feature. Scores are deterministic rules + calibrated ML baseline.
    Do not claim production-grade fraud prevention.
    """
    __tablename__ = "risk_assessments"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    # organization_id from TenantMixin
    payment_attempt_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("payment_attempts.id"), nullable=False, index=True
    )
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel, name="risk_level"), nullable=False
    )
    # Score is a calibrated probability (0.0-1.0) — not a raw model output
    score: Mapped[Optional[float]] = mapped_column(nullable=True)
    signals: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    model_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    human_reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewer_id: Mapped[Optional[str]] = mapped_column(String(26), nullable=True)
    review_decision: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Investigation(TimestampMixin, TenantMixin, Base):
    """
    AI-assisted investigation of a payment outcome.
    LLM output is a PROPOSAL only — never directly mutates payment state.
    """
    __tablename__ = "investigations"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    # organization_id from TenantMixin
    payment_attempt_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("payment_attempts.id"), nullable=False, index=True
    )
    status: Mapped[InvestigationStatus] = mapped_column(
        Enum(InvestigationStatus, name="investigation_status"),
        nullable=False,
        default=InvestigationStatus.PENDING
    )
    triggered_by: Mapped[str] = mapped_column(String(26), nullable=False)  # user_id or "system"
    trigger_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Structured findings from agent
    findings: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    recommendation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Agent run reference
    agent_run_id: Mapped[Optional[str]] = mapped_column(
        String(26), ForeignKey("agent_runs.id"), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    payment_attempt: Mapped["PaymentAttempt"] = relationship(
        "PaymentAttempt", back_populates="investigations"
    )
    agent_run: Mapped[Optional["AgentRun"]] = relationship("AgentRun", back_populates="investigation")


# ──────────────────────────────────────────────
# AGENT RUNS & APPROVALS
# ──────────────────────────────────────────────

class AgentRun(TimestampMixin, TenantMixin, Base):
    """Record of an AI agent execution. All tool calls are logged."""
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    # organization_id from TenantMixin
    agent_type: Mapped[str] = mapped_column(String(100), nullable=False)
    triggered_by: Mapped[str] = mapped_column(String(26), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="running")
    input: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    output: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    token_usage: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    tool_calls: Mapped[list["ToolCall"]] = relationship("ToolCall", back_populates="agent_run")
    investigation: Mapped[Optional["Investigation"]] = relationship(
        "Investigation", back_populates="agent_run"
    )


class ToolCall(TimestampMixin, Base):
    """Individual tool invocation within an agent run."""
    __tablename__ = "tool_calls"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    agent_run_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("agent_runs.id"), nullable=False, index=True
    )
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    input: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    output: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="success")
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    policy_checked: Mapped[bool] = mapped_column(Boolean, default=False)
    policy_approved: Mapped[bool] = mapped_column(Boolean, default=False)

    agent_run: Mapped["AgentRun"] = relationship("AgentRun", back_populates="tool_calls")


class ApprovalRequest(TimestampMixin, TenantMixin, Base):
    """
    Human approval gate for write operations (refunds, retries, agent writes).
    INVARIANT: No write operation executes without an approved ApprovalRequest.
    """
    __tablename__ = "approval_requests"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    # organization_id from TenantMixin
    requested_by: Mapped[str] = mapped_column(String(26), nullable=False)  # user_id or agent_run_id
    operation_type: Mapped[str] = mapped_column(String(100), nullable=False)
    operation_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus, name="approval_status"), nullable=False, default=ApprovalStatus.PENDING
    )
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(26), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


# ──────────────────────────────────────────────
# AUDIT
# ──────────────────────────────────────────────

class AuditEvent(Base):
    """
    Append-only audit log. Events are never updated or deleted.
    Hash-chained for tamper-evidence: each event stores hash of previous event.
    """
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    organization_id: Mapped[Optional[str]] = mapped_column(String(26), nullable=True, index=True)
    actor_id: Mapped[Optional[str]] = mapped_column(String(26), nullable=True)
    actor_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "user", "api_key", "system", "agent"
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(26), nullable=True)
    details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    # Hash chain for tamper evidence
    previous_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    __table_args__ = (
        Index("ix_audit_events_org_occurred", "organization_id", "occurred_at"),
    )


# ──────────────────────────────────────────────
# MERCHANT OPERATIONS (MerchantOS — Phase 5)
# ──────────────────────────────────────────────

class Customer(TimestampMixin, TenantMixin, Base):
    """Merchant's customer. No payment credentials stored here."""
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    # organization_id from TenantMixin
    external_customer_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    extra_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    orders: Mapped[list["Order"]] = relationship("Order", back_populates="customer")


class Invoice(TimestampMixin, TenantMixin, Base):
    """Merchant invoice. Imported from CSV or created via API."""
    __tablename__ = "invoices"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    # organization_id from TenantMixin
    invoice_number: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_id: Mapped[Optional[str]] = mapped_column(
        String(26), ForeignKey("customers.id"), nullable=True
    )
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    line_items: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    extra_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        UniqueConstraint("organization_id", "invoice_number", name="uq_invoice_org_number"),
    )


class Settlement(TimestampMixin, TenantMixin, Base):
    """Provider settlement record. Imported for reconciliation."""
    __tablename__ = "settlements"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    # organization_id from TenantMixin
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_settlement_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    settled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    extra_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)


# ──────────────────────────────────────────────
# COMMERCE (ShopAgent — Phase 6)
# ──────────────────────────────────────────────

class Product(TimestampMixin, TenantMixin, Base):
    """Merchant product from authorized catalog. No autonomous purchases."""
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    # organization_id from TenantMixin
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sku: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    extra_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)


class InventorySnapshot(TimestampMixin, TenantMixin, Base):
    """Point-in-time inventory snapshot for a product."""
    __tablename__ = "inventory_snapshots"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    # organization_id from TenantMixin
    product_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("products.id"), nullable=False, index=True
    )
    quantity_available: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Cart(TimestampMixin, TenantMixin, Base):
    """Customer cart. No charges without explicit buyer confirmation."""
    __tablename__ = "carts"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    # organization_id from TenantMixin
    customer_id: Mapped[Optional[str]] = mapped_column(
        String(26), ForeignKey("customers.id"), nullable=True
    )
    session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    items: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class CheckoutSession(TimestampMixin, TenantMixin, Base):
    """
    Checkout session. Buyer must explicitly confirm before any payment is initiated.
    INVARIANT: No payment attempt without status=confirmed and buyer_confirmed=True.
    """
    __tablename__ = "checkout_sessions"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    # organization_id from TenantMixin
    cart_id: Mapped[str] = mapped_column(String(26), ForeignKey("carts.id"), nullable=False)
    order_id: Mapped[Optional[str]] = mapped_column(
        String(26), ForeignKey("orders.id"), nullable=True
    )
    status: Mapped[CheckoutStatus] = mapped_column(
        Enum(CheckoutStatus, name="checkout_status"), nullable=False, default=CheckoutStatus.OPEN
    )
    # Explicit buyer confirmation required
    buyer_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    buyer_confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    amount: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(3), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_checkout_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extra_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
