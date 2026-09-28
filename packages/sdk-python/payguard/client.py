"""
PayGuard AI Python SDK — Client
"""
from __future__ import annotations

import json
import urllib.request
import urllib.error
from typing import Any, Optional

from payguard.models import PaymentAttempt, RecoveryRecommendation, RiskAssessment


class InvarPayClient:
    """
    Client for interacting with InvarPay AI API.
    Provider-neutral financial operations platform.
    """

    def __init__(self, api_url: str = "http://localhost:8000", api_key: str = "") -> None:
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key

    def _request(self, path: str, method: str = "GET", data: Optional[dict] = None) -> dict[str, Any]:
        url = f"{self.api_url}{path}"
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "InvarPay-Python-SDK/1.0.0",
        }
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        body = json.dumps(data).encode("utf-8") if data else None
        req = urllib.request.Request(url, data=body, headers=headers, method=method)

        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def get_payment(self, payment_id: str) -> PaymentAttempt:
        """Fetch payment attempt details."""
        res = self._request(f"/v1/payments/{payment_id}")
        return PaymentAttempt(
            id=res["id"],
            organization_id=res["organization_id"],
            order_id=res["order_id"],
            amount=res["amount"],
            currency=res["currency"],
            status=res["status"],
            provider=res.get("provider", "fake"),
            provider_payment_id=res.get("provider_payment_id"),
            created_at=res.get("created_at"),
        )

    def get_recovery_recommendation(self, payment_id: str) -> RecoveryRecommendation:
        """Get safe recovery recommendation for an ambiguous or failed payment."""
        res = self._request(f"/v1/payments/{payment_id}/recovery")
        return RecoveryRecommendation(
            action=res["action"],
            safety=res["safety"],
            reason=res["reason"],
            requires_approval=res.get("requires_approval", True),
            estimated_risk=res.get("estimated_risk", "UNKNOWN"),
        )

    def get_risk_assessment(self, payment_id: str) -> RiskAssessment:
        """Get PaymentGraph explainable risk assessment."""
        res = self._request(f"/v1/risk/{payment_id}")
        return RiskAssessment(
            payment_attempt_id=res["payment_attempt_id"],
            risk_level=res["risk_level"],
            composite_score=res["composite_score"],
            explanation=res["explanation"],
            requires_human_review=res.get("requires_human_review", True),
        )


# Backwards-compatible alias
PayGuardClient = InvarPayClient
