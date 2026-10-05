"""
InvarPay AI — InvarInvestigator Schemas
Defines structured schemas for evidence collection, AI investigation findings,
deterministic policy evaluation, and audit reporting.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class IncidentType(str, Enum):
    AMBIGUOUS_PAYMENT = "AMBIGUOUS_PAYMENT"
    PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
    WEBHOOK_INTEGRITY_FAILURE = "WEBHOOK_INTEGRITY_FAILURE"
    HIGH_RISK_FRAUD = "HIGH_RISK_FRAUD"
    LEDGER_IMBALANCE = "LEDGER_IMBALANCE"
    CAPTURED_PAYMENT = "CAPTURED_PAYMENT"
    FAILED_PAYMENT = "FAILED_PAYMENT"
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    UNKNOWN_INCIDENT = "UNKNOWN_INCIDENT"


class SeverityLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RecommendedAction(str, Enum):
    RECONCILE = "RECONCILE"
    AUTOMATIC_RETRY = "AUTOMATIC_RETRY"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    FLAG_FRAUD = "FLAG_FRAUD"
    HOLD_SETTLEMENT = "HOLD_SETTLEMENT"
    NO_ACTION_REQUIRED = "NO_ACTION_REQUIRED"
    UNCERTAIN = "UNCERTAIN"


class EvidenceFact(BaseModel):
    """A verified fact cited from authoritative evidence."""
    source: str = Field(..., description="Source component (e.g., payment_state, provider, webhook, ledger, risk)")
    fact: str = Field(..., description="Fact statement strictly grounded in supplied evidence")
    timestamp: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")


class InvestigationEvidence(BaseModel):
    """
    Authoritative evidence gathered exclusively from application state.
    Strictly tenant-scoped. Untrusted external strings are explicitly fenced.
    """
    payment_attempt_id: str
    organization_id: str
    order_id: Optional[str] = None
    amount: int = Field(..., description="Amount in integer minor units (paise/cents)")
    currency: str = "INR"
    current_status: str = Field(..., description="Current state machine status")
    provider_status: Optional[str] = None
    provider_payment_id: Optional[str] = None
    is_reconciled: bool = False
    state_transitions: list[dict[str, Any]] = Field(default_factory=list)
    provider_events: list[dict[str, Any]] = Field(default_factory=list)
    webhook_events: list[dict[str, Any]] = Field(default_factory=list)
    risk_signals: dict[str, Any] = Field(default_factory=dict)
    ledger_entries: list[dict[str, Any]] = Field(default_factory=list)
    audit_events: list[dict[str, Any]] = Field(default_factory=list)
    untrusted_data: dict[str, str] = Field(
        default_factory=dict,
        description="External customer/merchant text fenced as untrusted data"
    )
    collected_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    evidence_hash: str = Field(default="", description="SHA-256 hash of canonical evidence")

    model_config = ConfigDict(extra="ignore")


class InvestigationResult(BaseModel):
    """
    Structured finding produced by AI Investigator or deterministic fallback.
    Must conform to strict validation before being passed to Policy Engine.
    """
    incident_type: str = Field(..., description="Classified incident type")
    severity: str = Field(..., description="Severity level: LOW, MEDIUM, HIGH, CRITICAL")
    summary: str = Field(..., description="Human-readable incident summary")
    evidence: list[EvidenceFact] = Field(default_factory=list, description="Authoritative cited evidence facts")
    root_cause: str = Field(..., description="Root cause identified from evidence")
    recommendation: str = Field(..., description="Advisory recommendation (e.g., RECONCILE, AUTOMATIC_RETRY)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    blocked_actions: list[str] = Field(default_factory=list, description="Actions identified as unsafe to execute")
    allowed_actions: list[str] = Field(default_factory=list, description="Actions identified as safe under investigation")
    uncertainty: bool = Field(default=False, description="True if evidence was insufficient to conclude")
    model_metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata on model/fallback execution")

    model_config = ConfigDict(extra="ignore")


class PolicyDecision(BaseModel):
    """Deterministic evaluation of a single proposed action."""
    action: str
    allowed: bool
    blocked_reason: Optional[str] = None
    policy_rule: str

    model_config = ConfigDict(extra="ignore")


class PolicyEvaluationResult(BaseModel):
    """
    Final authoritative decision produced by deterministic policy engine.
    The LLM recommendation never overrides this decision.
    """
    recommendation: str
    policy_approved: bool
    final_action: str
    decisions: list[PolicyDecision] = Field(default_factory=list)
    blocked_actions: list[str] = Field(default_factory=list)
    allowed_actions: list[str] = Field(default_factory=list)
    explanation: str

    model_config = ConfigDict(extra="ignore")


class InvestigationReport(BaseModel):
    """Complete end-to-end investigation artifact linking evidence, AI output, policy, and audit."""
    investigation_id: str
    payment_attempt_id: str
    organization_id: str
    status: str
    evidence: InvestigationEvidence
    ai_result: InvestigationResult
    policy_evaluation: PolicyEvaluationResult
    audit_event_id: Optional[str] = None
    audit_event_hash: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(extra="ignore")
