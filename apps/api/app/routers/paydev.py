"""
InvarPay AI — Phase 4: PayDev Router

POST /v1/paydev/analyze  — Analyze a code repository
GET  /v1/paydev/sandbox/test  — Run a sandbox payment test
POST /v1/paydev/webhook-check  — Check a webhook handler implementation
"""
from __future__ import annotations

import hashlib
import hmac
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from apps.api.app.core.auth import TenantContext, require_scope
from modules.paydev.analyzer import analyze_code_string, analyze_repository

router = APIRouter()


class AnalyzeRequest(BaseModel):
    repository_path: str = Field(..., description="Absolute path to the repository root")
    focus_on: Optional[list[str]] = Field(None, description="Specific categories to focus on")


class WebhookCheckRequest(BaseModel):
    handler_code: str = Field(..., description="Webhook handler code to review (Python)")
    provider: str = Field("razorpay", description="Payment provider")
    webhook_secret: str = Field("test-secret-for-review", description="Webhook secret for test")


class ScanCodeRequest(BaseModel):
    code: str = Field(..., description="Python source code snippet to analyze")
    filename: Optional[str] = Field("payment_handler.py", description="Filename or module name")


@router.get("/paydev/rules", summary="List code inspection rules")
async def list_rules() -> list[dict]:
    """List static analysis rules enforced by PayDev for payment integrations."""
    return [
        {
            "id": "SEC001",
            "name": "Hardcoded Secret",
            "severity": "CRITICAL",
            "category": "security",
            "description": "Detects hardcoded API keys, key secrets, and webhook secrets in source code",
        },
        {
            "id": "SIG001",
            "name": "Webhook Signature Verification",
            "severity": "CRITICAL",
            "category": "security",
            "description": "Ensures raw byte body is used for HMAC-SHA256 signature verification to prevent tampering",
        },
        {
            "id": "PCI001",
            "name": "Cardholder PAN/CVV Logging",
            "severity": "CRITICAL",
            "category": "compliance",
            "description": "Flags plaintext logging or printing of credit card PANs, expiry, or CVVs (PCI-DSS 3.3)",
        },
        {
            "id": "FIN001",
            "name": "Float Currency Arithmetic",
            "severity": "HIGH",
            "category": "accuracy",
            "description": "Detects floating-point math for currency amounts; enforces minor integer units (paise/cents)",
        },
        {
            "id": "IDEM001",
            "name": "Missing Idempotency Key",
            "severity": "HIGH",
            "category": "reliability",
            "description": "Flags payment mutation endpoints lacking durable idempotency headers to prevent double charges",
        },
        {
            "id": "REPLAY001",
            "name": "Webhook Timestamp Drift",
            "severity": "MEDIUM",
            "category": "security",
            "description": "Checks for webhook event age verification to prevent replay attacks beyond 300 seconds",
        },
        {
            "id": "ERR001",
            "name": "Error PII Leakage",
            "severity": "MEDIUM",
            "category": "privacy",
            "description": "Checks customer PII is not leaked in raw unhandled exception strings",
        },
        {
            "id": "AUTH001",
            "name": "Missing Tenant Isolation Scopes",
            "severity": "HIGH",
            "category": "multitenancy",
            "description": "Verifies every payment query has tenant-scoped WHERE organization_id filter",
        },
    ]


@router.post("/paydev/scan-code", summary="Live AST scan of payment source code")
async def scan_code_string(
    req: ScanCodeRequest,
    ctx: TenantContext = Depends(require_scope("payments:read")),
) -> dict:
    """Run real AST and regex checks on a code snippet and generate unified diff."""
    return analyze_code_string(req.code, filename=req.filename or "payment_handler.py")



@router.post("/paydev/analyze", summary="Analyze payment integration code")
async def analyze_code(
    request: AnalyzeRequest,
    ctx: TenantContext = Depends(require_scope("payments:read")),
) -> dict:
    """
    Analyze a repository for payment integration issues.
    READ-ONLY — no files are modified.
    All suggested fixes are proposals requiring user approval.
    """
    try:
        report = analyze_repository(request.repository_path)
    except ValueError as e:
        raise HTTPException(400, str(e))

    return {
        "files_analyzed": report.files_analyzed,
        "summary": report.summary,
        "issues": [
            {
                "severity": i.severity,
                "category": i.category,
                "file": i.file_path,
                "line": i.line_number,
                "description": i.description,
                "suggested_fix": i.suggested_fix,
                "reference": i.reference,
            }
            for i in report.issues[:100]  # Limit response size
        ],
        "disclaimer": report.disclaimer,
        "note": "All issues are proposals — review before applying any changes",
    }


@router.post("/paydev/webhook-check", summary="Check webhook handler implementation")
async def check_webhook_handler(
    request: WebhookCheckRequest,
    ctx: TenantContext = Depends(require_scope("payments:read")),
) -> dict:
    """
    Review a webhook handler implementation for common security issues.
    Returns findings and a test signature for the provided handler.
    """
    code = request.handler_code
    issues = []
    suggestions = []

    # Check for signature verification
    if "signature" not in code.lower() and "hmac" not in code.lower():
        issues.append({
            "severity": "CRITICAL",
            "issue": "No signature verification found",
            "fix": "Verify HMAC-SHA256(webhook_secret, raw_body) before parsing JSON",
        })
        suggestions.append(
            "# Add signature verification:\n"
            "import hmac, hashlib\n"
            "def verify_signature(raw_body: bytes, signature: str, secret: str) -> bool:\n"
            "    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()\n"
            "    return hmac.compare_digest(expected, signature)\n"
        )

    # Check for raw body usage
    if "raw_body" not in code and "body.encode()" not in code:
        issues.append({
            "severity": "HIGH",
            "issue": "Signature must be verified on RAW bytes, not parsed JSON",
            "fix": "Capture raw request body before any JSON parsing",
        })

    # Check for replay prevention
    if "timestamp" not in code.lower() and "time" not in code.lower():
        issues.append({
            "severity": "MEDIUM",
            "issue": "No timestamp/replay prevention detected",
            "fix": "Reject webhooks with timestamps older than 5 minutes",
        })

    # Generate test signature
    test_payload = json.dumps({"event": "payment.captured", "test": True}).encode()
    test_sig = hmac.new(
        request.webhook_secret.encode(),
        test_payload,
        hashlib.sha256
    ).hexdigest()

    return {
        "issues_found": len(issues),
        "issues": issues,
        "suggestions": suggestions,
        "test_payload": test_payload.decode(),
        "test_signature": test_sig,
        "test_secret_used": request.webhook_secret,
        "note": "Use test_signature to validate your handler against test_payload",
    }


@router.post("/paydev/sandbox/test-payment", summary="Run a sandbox payment test")
async def test_sandbox_payment(
    amount: int = 10000,
    currency: str = "INR",
    ctx: TenantContext = Depends(require_scope("orders:write")),
) -> dict:
    """
    Run a synthetic payment through the fake provider to test the integration.
    Uses SYNTHETIC data only — no real money.
    """
    from integrations.providers.fake.provider import FakeProvider

    provider = FakeProvider()
    order = provider.create_order(amount, currency)
    payment = provider.initiate_payment(order["id"], outcome="success")
    provider.process_payment(payment["id"])
    webhook_raw, webhook_sig, webhook_payload = provider.generate_webhook(payment["id"])

    return {
        "test": True,
        "synthetic": True,
        "order_id": order["id"],
        "payment_id": payment["id"],
        "payment_status": payment["status"],
        "webhook": {
            "payload": webhook_payload,
            "signature": webhook_sig,
            "header_name": "X-Razorpay-Signature",
            "note": "Use this signature + payload to test your webhook handler",
        },
        "disclaimer": "SYNTHETIC TEST DATA — no real money involved",
    }
