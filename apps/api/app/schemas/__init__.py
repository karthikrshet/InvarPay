"""
InvarPay AI — Pydantic Request/Response Schemas

All API contracts are defined here.
Monetary amounts are always integers (minor units) + currency string.
No raw card data, CVV, UPI PIN, or banking credentials in any schema.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field, SecretStr, field_validator

# ── Common ─────────────────────────────────────────────────────────────────────

class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel):
    items: list[Any]
    total: int
    page: int
    page_size: int
    has_next: bool


# ── Organizations ─────────────────────────────────────────────────────────────

class CreateOrganizationRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    slug: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    email: EmailStr
    owner_password: SecretStr = Field(..., min_length=12, max_length=128)
    owner_name: Optional[str] = Field(default=None, min_length=1, max_length=255)

    @field_validator("slug")
    @classmethod
    def slug_lowercase(cls, v: str) -> str:
        return v.lower()


class OrganizationResponse(BaseModel):
    id: str
    name: str
    slug: str
    email: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    organization_id: str


class CreateApiKeyRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    scopes: list[str] = Field(default=["payments:read", "orders:read"])
    is_test_mode: bool = True


class ApiKeyResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    scopes: list[str]
    is_test_mode: bool
    is_active: bool
    created_at: datetime
    # Full key only returned on creation — never shown again
    full_key: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Provider Connections ──────────────────────────────────────────────────────

class TestProviderConnectionRequest(BaseModel):
    provider: str = Field(..., pattern=r"^(razorpay|fake)$")
    display_name: str = Field(default="Test provider connection", min_length=2, max_length=255)
    key_id: Optional[str] = None
    key_secret: Optional[SecretStr] = None
    webhook_secret: Optional[SecretStr] = None
    is_test_mode: bool = True


class CreatePaymentAttemptRequest(BaseModel):
    """Creates a tracking attempt only; it never captures or charges a payment."""

    provider_connection_id: Optional[str] = Field(default=None, min_length=1, max_length=26)
    metadata: Optional[dict[str, Any]] = None


class ProviderConnectionResponse(BaseModel):
    id: str
    provider: str
    display_name: str
    is_test_mode: bool
    is_active: bool
    last_test_status: Optional[str]
    last_tested_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Orders ────────────────────────────────────────────────────────────────────

class CreateOrderRequest(BaseModel):
    amount: int = Field(..., gt=0, description="Amount in minor units (e.g., paise for INR)")
    currency: str = Field(default="INR", min_length=3, max_length=3)
    description: Optional[str] = Field(default=None, max_length=500)
    external_order_id: Optional[str] = Field(default=None, max_length=255)
    customer_id: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None

    @field_validator("currency")
    @classmethod
    def currency_uppercase(cls, v: str) -> str:
        return v.upper()


class OrderResponse(BaseModel):
    id: str
    organization_id: str
    external_order_id: Optional[str]
    provider_order_id: Optional[str]
    description: Optional[str]
    amount: int
    currency: str
    status: str
    is_fulfilled: bool
    payment_attempts: list["PaymentAttemptSummary"] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Payments ──────────────────────────────────────────────────────────────────

class PaymentAttemptSummary(BaseModel):
    id: str
    status: str
    provider_status: Optional[str]
    provider_payment_id: Optional[str]
    amount: int
    currency: str
    is_reconciled: bool
    created_at: datetime
    captured_at: Optional[datetime]
    failed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class ProviderEventSummary(BaseModel):
    id: str
    event_type: str
    provider: str
    provider_event_id: str
    signature_verified: bool
    processed: bool
    received_at: datetime
    raw_payload: dict

    model_config = {"from_attributes": True}


class PaymentAttemptDetailResponse(BaseModel):
    id: str
    organization_id: str
    order_id: str
    status: str
    provider_status: Optional[str]
    provider_payment_id: Optional[str]
    provider_order_id: Optional[str]
    amount: int
    currency: str
    idempotency_key: str
    failure_reason: Optional[str]
    failure_code: Optional[str]
    is_reconciled: bool
    initiated_at: Optional[datetime]
    authorized_at: Optional[datetime]
    captured_at: Optional[datetime]
    failed_at: Optional[datetime]
    reconciled_at: Optional[datetime]
    provider_events: list[ProviderEventSummary] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Investigations ────────────────────────────────────────────────────────────

class StartInvestigationRequest(BaseModel):
    trigger_reason: Optional[str] = Field(default=None, max_length=1000)


class InvestigationResponse(BaseModel):
    id: str
    payment_attempt_id: str
    status: str
    trigger_reason: Optional[str]
    findings: Optional[dict]
    recommendation: Optional[str]
    triggered_by: str
    completed_at: Optional[datetime]
    error: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Reconciliation ────────────────────────────────────────────────────────────

class ReconcilePaymentRequest(BaseModel):
    provider_data: Optional[dict[str, Any]] = Field(
        default=None,
        description="Provider API response to reconcile against. If omitted, fetched automatically."
    )


class ReconciliationItemResponse(BaseModel):
    id: str
    payment_attempt_id: str
    status: str
    our_amount: int
    our_currency: str
    provider_amount: Optional[int]
    provider_currency: Optional[str]
    provider_status: Optional[str]
    discrepancy_reason: Optional[str]
    resolved: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ReconciliationRunResponse(BaseModel):
    id: str
    status: str
    provider: str
    triggered_by: str
    total_items: int
    matched_items: int
    mismatched_items: int
    unresolved_items: int
    started_at: datetime
    completed_at: Optional[datetime]
    items: list[ReconciliationItemResponse] = []

    model_config = {"from_attributes": True}


# ── Audit ─────────────────────────────────────────────────────────────────────

class AuditEventResponse(BaseModel):
    id: str
    organization_id: Optional[str]
    actor_id: Optional[str]
    actor_type: str
    action: str
    resource_type: str
    resource_id: Optional[str]
    details: Optional[dict]
    ip_address: Optional[str]
    event_hash: str
    occurred_at: datetime

    model_config = {"from_attributes": True}


# ── Health ────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    checks: Optional[dict[str, bool]] = None
