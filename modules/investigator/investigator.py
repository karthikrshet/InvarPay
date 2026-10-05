"""
InvarPay AI — InvarInvestigator Engine
Evidence-grounded AI payment incident investigation system.
Supports:
1. LLM-based investigation with strict JSON schema enforcement (when API key is present).
2. Deterministic rule-based fallback when LLM is unavailable or outputs malformed text.
3. Strict prompt-injection boundary isolation (untrusted text treated purely as data).
4. Evidence-grounded fact citations only.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

from apps.api.app.core.config import get_settings
from apps.api.app.utils.ids import new_id
from modules.investigator.policy import InvestigatorPolicyEngine
from modules.investigator.prompts import INVESTIGATOR_SYSTEM_PROMPT, build_investigation_user_prompt
from modules.investigator.schemas import (
    EvidenceFact,
    IncidentType,
    InvestigationEvidence,
    InvestigationReport,
    InvestigationResult,
    RecommendedAction,
    SeverityLevel,
)

logger = logging.getLogger(__name__)
settings = get_settings()

# Known prompt injection signatures
INJECTION_PATTERNS = [
    re.compile(r"(?i)ignore\s+(all\s+)?(previous|prior)\s+instructions"),
    re.compile(r"(?i)you\s+are\s+now\s+(an?\s+)?admin"),
    re.compile(r"(?i)system\s*:\s*"),
    re.compile(r"(?i)approve\s+(this\s+)?payment"),
    re.compile(r"(?i)execute\s+(direct\s+)?refund"),
    re.compile(r"(?i)disregard\s+(the\s+)?(above|rules|policy)"),
    re.compile(r"(?i)override\s+(security|policy|invariants?)"),
]


class InvarInvestigator:
    """
    Core Investigator engine.
    Processes authoritative InvestigationEvidence and produces structured InvestigationResult.
    """

    def __init__(self, organization_id: str) -> None:
        self.organization_id = organization_id
        self.policy_engine = InvestigatorPolicyEngine(organization_id=organization_id)

    def detect_prompt_injection(self, text: str) -> bool:
        """Checks if text contains hostile prompt-injection phrases."""
        return any(pattern.search(text) for pattern in INJECTION_PATTERNS)

    def scan_untrusted_data(self, evidence: InvestigationEvidence) -> tuple[bool, list[str]]:
        """Scans untrusted_data fields for injection attempts."""
        injections_found: list[str] = []
        for key, val in evidence.untrusted_data.items():
            if self.detect_prompt_injection(val):
                injections_found.append(f"{key}: suspicious instruction detected")
        return len(injections_found) > 0, injections_found

    async def _call_llm(self, prompt: str) -> Optional[dict[str, Any]]:
        """
        Executes configured LLM client with system prompt and JSON format instructions.
        Returns parsed dictionary if successful, or None on failure/timeout.
        """
        if settings.llm_provider not in ("openai", "google") or not settings.llm_configured:
            return None

        # Try OpenAI if configured with a real API key
        if settings.llm_provider == "openai" and settings.openai_api_key.get_secret_value():
            key = settings.openai_api_key.get_secret_value()
            if not key or key.startswith("dummy") or key.startswith("test") or key.startswith("change-me") or key.startswith("sk-placeholder") or "your-" in key:
                return None
            try:
                import urllib.request
                url = "https://api.openai.com/v1/chat/completions"
                payload = {
                    "model": settings.llm_model or "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": INVESTIGATOR_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.0,
                }
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {settings.openai_api_key.get_secret_value()}",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=settings.agent_timeout_seconds) as response:
                    body = json.loads(response.read().decode("utf-8"))
                    content = body["choices"][0]["message"]["content"]
                    return json.loads(content)
            except Exception as e:
                logger.warning("OpenAI investigation call failed or timed out: %s", e)
                return None

        return None

    def _run_deterministic_fallback(
        self,
        evidence: InvestigationEvidence,
        injection_detected: bool,
    ) -> InvestigationResult:
        """
        Authoritative deterministic rule engine when LLM is unavailable or for fallback.
        Strictly enforces UNKNOWN != FAILED and evidence grounding.
        """
        status = (evidence.current_status or "").lower()
        facts: list[EvidenceFact] = []

        # 1. State grounding fact
        facts.append(
            EvidenceFact(
                source="payment_state",
                fact=f"Payment attempt '{evidence.payment_attempt_id}' is in state '{status.upper()}'. Amount: ₹{evidence.amount / 100:.2f} {evidence.currency}.",
            )
        )

        # 2. Check for missing/insufficient evidence
        if not evidence.provider_events and not evidence.state_transitions and status in ("created", "initiated"):
            facts.append(
                EvidenceFact(
                    source="telemetry",
                    fact="No provider events, transitions, or webhook logs recorded for this attempt.",
                )
            )
            return InvestigationResult(
                incident_type=IncidentType.MISSING_EVIDENCE.value,
                severity=SeverityLevel.MEDIUM.value,
                summary="Insufficient authoritative evidence available to determine root cause.",
                evidence=facts,
                root_cause="Absence of provider callback or state transition telemetry.",
                recommendation=RecommendedAction.UNCERTAIN.value,
                confidence=0.25,
                blocked_actions=[RecommendedAction.AUTOMATIC_RETRY.value],
                allowed_actions=[RecommendedAction.MANUAL_REVIEW.value],
                uncertainty=True,
                model_metadata={
                    "provider": "deterministic_fallback",
                    "fallback_used": True,
                    "prompt_injection_detected": injection_detected,
                },
            )

        # 3. Check for ledger imbalances
        ledger_imbalance = False
        if evidence.ledger_entries:
            debits = sum(e.get("amount", 0) for e in evidence.ledger_entries if e.get("entry_type") == "debit")
            credits = sum(e.get("amount", 0) for e in evidence.ledger_entries if e.get("entry_type") == "credit")
            if debits != credits:
                ledger_imbalance = True
                facts.append(
                    EvidenceFact(
                        source="ledger",
                        fact=f"Double-entry ledger imbalance detected: Debits ({debits}) != Credits ({credits}).",
                    )
                )

        if ledger_imbalance:
            return InvestigationResult(
                incident_type=IncidentType.LEDGER_IMBALANCE.value,
                severity=SeverityLevel.HIGH.value,
                summary="Dual-entry ledger accounts are out of balance for this transaction.",
                evidence=facts,
                root_cause="Debit and credit amounts do not net to zero paise.",
                recommendation=RecommendedAction.HOLD_SETTLEMENT.value,
                confidence=0.98,
                blocked_actions=[RecommendedAction.AUTOMATIC_RETRY.value],
                allowed_actions=[RecommendedAction.HOLD_SETTLEMENT.value, RecommendedAction.MANUAL_REVIEW.value],
                uncertainty=False,
                model_metadata={
                    "provider": "deterministic_fallback",
                    "fallback_used": True,
                    "prompt_injection_detected": injection_detected,
                },
            )

        # 4. Check for high fraud risk signals
        risk = evidence.risk_signals or {}
        is_fraud = risk.get("disposable_email") or risk.get("is_tor") or (risk.get("risk_score", 0) > 75)
        if is_fraud:
            facts.append(
                EvidenceFact(
                    source="risk",
                    fact=f"Fraud risk indicators triggered: risk_score={risk.get('risk_score', 0)}, is_tor={risk.get('is_tor', False)}, disposable_email={risk.get('disposable_email', False)}.",
                )
            )
            return InvestigationResult(
                incident_type=IncidentType.HIGH_RISK_FRAUD.value,
                severity=SeverityLevel.CRITICAL.value,
                summary="Critical fraud indicators detected by PaymentGraph risk heuristics.",
                evidence=facts,
                root_cause="High transaction risk score or untrusted infrastructure flag (Tor / Disposable ID).",
                recommendation=RecommendedAction.FLAG_FRAUD.value,
                confidence=0.94,
                blocked_actions=[RecommendedAction.AUTOMATIC_RETRY.value],
                allowed_actions=[RecommendedAction.FLAG_FRAUD.value, RecommendedAction.MANUAL_REVIEW.value],
                uncertainty=False,
                model_metadata={
                    "provider": "deterministic_fallback",
                    "fallback_used": True,
                    "prompt_injection_detected": injection_detected,
                },
            )

        # 5. Check for Webhook Signature / Integrity failures
        unverified_events = [pe for pe in evidence.provider_events if not pe.get("signature_verified", True)]
        if unverified_events:
            facts.append(
                EvidenceFact(
                    source="webhook",
                    fact=f"{len(unverified_events)} provider events failed cryptographic HMAC-SHA256 signature verification.",
                )
            )
            return InvestigationResult(
                incident_type=IncidentType.WEBHOOK_INTEGRITY_FAILURE.value,
                severity=SeverityLevel.HIGH.value,
                summary="Webhook integrity failure: Unsigned or tampered provider event received.",
                evidence=facts,
                root_cause="HMAC-SHA256 signature verification mismatch against merchant secret.",
                recommendation=RecommendedAction.RECONCILE.value,
                confidence=0.95,
                blocked_actions=[RecommendedAction.AUTOMATIC_RETRY.value],
                allowed_actions=[RecommendedAction.RECONCILE.value, RecommendedAction.MANUAL_REVIEW.value],
                uncertainty=False,
                model_metadata={
                    "provider": "deterministic_fallback",
                    "fallback_used": True,
                    "prompt_injection_detected": injection_detected,
                },
            )

        # 6. UNKNOWN Status (CRITICAL INVARIANT: UNKNOWN IS NOT FAILED)
        if status == "unknown":
            facts.append(
                EvidenceFact(
                    source="payment_state",
                    fact="Payment outcome is UNKNOWN. Network timeout or dropped provider connection occurred.",
                )
            )
            if evidence.provider_payment_id:
                facts.append(
                    EvidenceFact(
                        source="provider",
                        fact=f"Provider payment reference exists: {evidence.provider_payment_id}.",
                    )
                )

            return InvestigationResult(
                incident_type=IncidentType.AMBIGUOUS_PAYMENT.value,
                severity=SeverityLevel.HIGH.value,
                summary="Payment outcome is ambiguous after provider network timeout (UNKNOWN ≠ FAILED).",
                evidence=facts,
                root_cause="Gateway request timeout or unconfirmed provider callback.",
                recommendation=RecommendedAction.RECONCILE.value,
                confidence=0.96,
                blocked_actions=[RecommendedAction.AUTOMATIC_RETRY.value],
                allowed_actions=[RecommendedAction.RECONCILE.value, RecommendedAction.MANUAL_REVIEW.value],
                uncertainty=False,
                model_metadata={
                    "provider": "deterministic_fallback",
                    "fallback_used": True,
                    "prompt_injection_detected": injection_detected,
                },
            )

        # 7. CAPTURED Status
        if status == "captured":
            facts.append(
                EvidenceFact(
                    source="payment_state",
                    fact="Payment is settled in terminal status CAPTURED.",
                )
            )
            return InvestigationResult(
                incident_type=IncidentType.CAPTURED_PAYMENT.value,
                severity=SeverityLevel.LOW.value,
                summary="Payment successfully captured and confirmed by gateway rail.",
                evidence=facts,
                root_cause="Normal payment lifecycle completion.",
                recommendation=RecommendedAction.NO_ACTION_REQUIRED.value,
                confidence=0.99,
                blocked_actions=[RecommendedAction.AUTOMATIC_RETRY.value],
                allowed_actions=[RecommendedAction.NO_ACTION_REQUIRED.value],
                uncertainty=False,
                model_metadata={
                    "provider": "deterministic_fallback",
                    "fallback_used": True,
                    "prompt_injection_detected": injection_detected,
                },
            )

        # 8. FAILED Status
        if status in ("failed", "cancelled"):
            failure_reason = evidence.untrusted_data.get("failure_reason", "Payment failed at rail")
            facts.append(
                EvidenceFact(
                    source="provider",
                    fact=f"Payment failed deterministically: {failure_reason}.",
                )
            )
            return InvestigationResult(
                incident_type=IncidentType.FAILED_PAYMENT.value,
                severity=SeverityLevel.LOW.value,
                summary="Payment definitively failed at payment gateway.",
                evidence=facts,
                root_cause=f"Definitive gateway failure: {failure_reason}.",
                recommendation=RecommendedAction.AUTOMATIC_RETRY.value,
                confidence=0.97,
                blocked_actions=[],
                allowed_actions=[RecommendedAction.AUTOMATIC_RETRY.value, RecommendedAction.MANUAL_REVIEW.value],
                uncertainty=False,
                model_metadata={
                    "provider": "deterministic_fallback",
                    "fallback_used": True,
                    "prompt_injection_detected": injection_detected,
                },
            )

        # 9. Default catch-all
        return InvestigationResult(
            incident_type=IncidentType.UNKNOWN_INCIDENT.value,
            severity=SeverityLevel.MEDIUM.value,
            summary=f"Payment attempt in transitional state '{status.upper()}'.",
            evidence=facts,
            root_cause="In-flight transaction awaiting completion.",
            recommendation=RecommendedAction.RECONCILE.value,
            confidence=0.85,
            blocked_actions=[RecommendedAction.AUTOMATIC_RETRY.value],
            allowed_actions=[RecommendedAction.RECONCILE.value],
            uncertainty=False,
            model_metadata={
                "provider": "deterministic_fallback",
                "fallback_used": True,
                "prompt_injection_detected": injection_detected,
            },
        )

    async def investigate(self, evidence: InvestigationEvidence) -> InvestigationResult:
        """
        Executes investigation over the provided evidence.
        Uses configured LLM with prompt fences if available; falls back cleanly to deterministic rule engine.
        """
        # 1. Scan untrusted fields for prompt injection
        injection_detected, injection_findings = self.scan_untrusted_data(evidence)
        if injection_detected:
            logger.warning(
                "Prompt injection pattern detected in untrusted data for payment %s: %s",
                evidence.payment_attempt_id, injection_findings
            )

        # 2. If LLM is configured, attempt model inference
        if settings.llm_configured:
            prompt = build_investigation_user_prompt(evidence)
            llm_response = await self._call_llm(prompt)
            if llm_response:
                try:
                    result = InvestigationResult(**llm_response)
                    # Verify model metadata labels
                    result.model_metadata["provider"] = settings.llm_provider
                    result.model_metadata["model"] = settings.llm_model
                    result.model_metadata["fallback_used"] = False
                    result.model_metadata["prompt_injection_detected"] = injection_detected
                    return result
                except Exception as val_err:
                    logger.warning("LLM response failed schema validation: %s. Falling back to deterministic engine.", val_err)

        # 3. Deterministic rule-based fallback
        result = self._run_deterministic_fallback(evidence, injection_detected)
        if injection_detected:
            # Append prompt injection finding without following the injection's instruction
            result.evidence.append(
                EvidenceFact(
                    source="security_firewall",
                    fact="Hostile prompt injection patterns detected in untrusted fields. Treated strictly as raw data.",
                )
            )
        return result

    async def investigate_and_evaluate(
        self,
        evidence: InvestigationEvidence,
        investigation_id: Optional[str] = None,
    ) -> InvestigationReport:
        """
        Full end-to-end investigation pipeline:
        1. AI / Deterministic Investigation
        2. Strict Deterministic Policy Evaluation
        3. Packaging of verified InvestigationReport
        """
        inv_id = investigation_id or f"inv_{new_id()}"

        # Step 1: Run Investigation
        ai_result = await self.investigate(evidence)

        # Step 2: Authoritative Policy Evaluation
        policy_eval = self.policy_engine.evaluate(evidence, ai_result)

        # Step 3: Package complete report
        return InvestigationReport(
            investigation_id=inv_id,
            payment_attempt_id=evidence.payment_attempt_id,
            organization_id=self.organization_id,
            status="completed" if policy_eval.policy_approved else "policy_blocked",
            evidence=evidence,
            ai_result=ai_result,
            policy_evaluation=policy_eval,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
