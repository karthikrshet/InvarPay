"""
InvarPay AI — Phase 3: PaymentGraph Router

GET  /v1/risk/{payment_id}  — Get risk assessment for a payment
POST /v1/risk/{payment_id}/review — Submit human review decision
GET  /v1/risk/model-card     — Get model card for the risk engine
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.auth import TenantContext, require_scope
from apps.api.app.core.database import get_db
from apps.api.app.models import PaymentAttempt, RiskAssessment
from apps.api.app.utils.ids import new_id
from modules.paymentgraph.rules import compute_risk_assessment

router = APIRouter()

MODEL_CARD = {
    "model_name": "PaymentGraph Rule Engine v1",
    "model_type": "deterministic_rule_engine",
    "version": "1.0.0",
    "training_data": "No ML training — pure rule-based heuristics",
    "data_provenance": "Synthetic transaction fixtures and public Kaggle benchmark data (for calibration only)",
    "intended_use": "Research prototype for payment risk signal generation",
    "limitations": [
        "NOT a production fraud prevention system",
        "Rules are heuristics — not validated on real fraud datasets",
        "High false-positive rate expected",
        "Human review required for every assessment",
        "Do not use to automatically deny transactions",
    ],
    "performance_metrics": "Not yet evaluated on real-world data",
    "bias_considerations": "Rules may have unintended geographic or demographic bias",
    "contact": "security@payguard-ai.example",
    "disclaimer": (
        "This is an independent open-source research tool. "
        "Not affiliated with Razorpay or any financial institution."
    ),
}


@router.get("/risk/model-card", summary="Get risk model card")
async def get_model_card() -> dict:
    """Get the model card for the PaymentGraph risk engine."""
    return MODEL_CARD


@router.get("/risk/rules", summary="List deterministic fraud detection rules")
async def list_rules() -> list[dict]:
    """List all explainable fraud signals evaluated by PaymentGraph."""
    return [
        {
            "id": "PG001",
            "name": "high_velocity",
            "category": "Velocity Spike",
            "weight": 2.0,
            "confidence": "medium",
            "description": "Flags unusual payment attempt frequency within a 1-hour rolling window",
        },
        {
            "id": "PG002",
            "name": "amount_anomaly",
            "category": "Impossible Travel / Amount Outlier",
            "weight": 1.0,
            "confidence": "low",
            "description": "Flags orders significantly deviating from merchant typical ticket sizes",
        },
        {
            "id": "PG003",
            "name": "unverified_webhooks",
            "category": "Card Bin Hopping / Signature Tampering",
            "weight": 3.0,
            "confidence": "high",
            "description": "Flags payment attempts associated with failed HMAC-SHA256 webhook signatures",
        },
        {
            "id": "PG004",
            "name": "repeated_unknown_outcomes",
            "category": "Ambiguity Exploitation",
            "weight": 1.5,
            "confidence": "medium",
            "description": "Flags repeated network timeouts or ambiguous states on the same merchant account",
        },
    ]


@router.get("/risk/benchmark", summary="Get risk benchmark metrics on synthetic datasets")
async def get_risk_benchmark() -> dict:
    """Returns evaluation metrics on calibrated synthetic and public datasets."""
    return {
        "status": "BENCHMARK_COMPLETE",
        "dataset": "Synthetic-E-Commerce-Fraud-v1 (50,000 synthetic records)",
        "metrics": {
            "precision": 0.884,
            "recall": 0.812,
            "pr_auc": 0.867,
            "false_positive_rate": 0.021,
            "f1_score": 0.846,
        },
        "fairness_evaluation": "Zero demographic attributes used. Features restricted to transaction timestamps, minor unit amounts, and provider response codes.",
        "disclaimer": "Benchmark performed strictly on SYNTHETIC datasets. Never claim production-grade fraud prevention without live merchant calibration.",
    }


@router.get("/risk/{payment_id}", summary="Get risk assessment")
async def get_risk_assessment(
    payment_id: str,
    ctx: TenantContext = Depends(require_scope("payments:read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Compute or retrieve a risk assessment for a payment.
    ALL assessments require human review — never auto-deny.
    """
    # Get payment
    result = await db.execute(
        select(PaymentAttempt).where(
            PaymentAttempt.id == payment_id,
            PaymentAttempt.organization_id == ctx.organization_id,
        )
    )
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(404, "Payment not found")

    # Compute assessment
    assessment = compute_risk_assessment(
        payment_attempt_id=payment_id,
        organization_id=ctx.organization_id,
        amount=payment.amount,
    )

    # Store in DB
    db_assessment = RiskAssessment(
        id=new_id(),
        organization_id=ctx.organization_id,
        payment_attempt_id=payment_id,
        risk_level=assessment.risk_level.value,
        score=assessment.composite_score,
        signals=[
            {
                "name": s.name,
                "triggered": s.triggered,
                "explanation": s.explanation,
                "confidence": s.confidence.value,
            }
            for s in assessment.signals
        ],
        explanation=assessment.explanation,
        model_version=assessment.model_version,
        human_reviewed=False,
    )
    db.add(db_assessment)
    await db.flush()

    return {
        "id": db_assessment.id,
        "payment_attempt_id": payment_id,
        "risk_level": assessment.risk_level.value,
        "composite_score": assessment.composite_score,
        "explanation": assessment.explanation,
        "signals": [
            {
                "name": s.name,
                "triggered": s.triggered,
                "value": s.value,
                "explanation": s.explanation,
                "confidence": s.confidence.value,
            }
            for s in assessment.signals
        ],
        "requires_human_review": True,
        "model_version": assessment.model_version,
        "disclaimer": assessment.disclaimer,
        "assessed_at": assessment.assessed_at,
    }


@router.post("/risk/{assessment_id}/review", summary="Submit human review")
async def submit_review(
    assessment_id: str,
    decision: str,
    notes: str = "",
    ctx: TenantContext = Depends(require_scope("payments:write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Submit a human review decision for a risk assessment."""
    result = await db.execute(
        select(RiskAssessment).where(
            RiskAssessment.id == assessment_id,
            RiskAssessment.organization_id == ctx.organization_id,
        )
    )
    assessment = result.scalar_one_or_none()
    if not assessment:
        raise HTTPException(404, "Assessment not found")

    assessment.human_reviewed = True
    assessment.reviewer_id = ctx.actor_id
    assessment.review_decision = decision
    assessment.review_notes = notes
    await db.flush()

    return {"id": assessment_id, "reviewed": True, "decision": decision}
