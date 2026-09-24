"""
PayGuard AI — Agent Policy Engine (Deny-by-Default)

Enforces strict security invariants for all AI agent tool calls:
1. Tenant scope verification (target_org_id == organization_id)
2. Tool permission scope verification (read-only default)
3. Write action approval requirement (no autonomous mutation)
4. Prompt-injection boundary isolation & sanitize helpers
"""
from __future__ import annotations

import re
from enum import Enum
from typing import Optional


class ActionType(str, Enum):
    READ = "READ"
    WRITE = "WRITE"
    ADMIN = "ADMIN"


class PolicyViolationError(Exception):
    """Raised when an agent tool call violates security policy."""
    pass


# Read-only tools allowed without manual approval
DEFAULT_READ_TOOLS: frozenset[str] = frozenset({
    "get_payment_attempt",
    "get_provider_events",
    "get_audit_trail",
    "get_reconciliation_history",
    "get_recovery_recommendation",
    "get_order_details",
    "query_provider_status",
})

# Write tools that strictly require human approval
APPROVAL_REQUIRED_WRITE_TOOLS: frozenset[str] = frozenset({
    "issue_refund",
    "initiate_retry",
    "override_status",
    "create_reconciliation_run",
    "create_approval_request",
    "flag_for_manual_review",
})


class PolicyEngine:
    """
    Enforces authorization and tenant isolation for AI agents.
    Deny-by-default architecture.
    """

    def __init__(self, organization_id: str, allowed_tools: Optional[set[str]] = None) -> None:
        self.organization_id = organization_id
        self.allowed_read_tools = set(DEFAULT_READ_TOOLS) if allowed_tools is None else set(allowed_tools)

    def check_tool_access(
        self,
        tool_name: str,
        tool_action_type: ActionType,
        target_org_id: str,
        requires_human_approval: bool = False,
        is_approved: bool = False,
    ) -> bool:
        """
        Validates tool execution against policy.
        Raises PolicyViolationError on any violation.
        """
        # 1. Tenant boundary check
        if target_org_id != self.organization_id:
            raise PolicyViolationError(
                f"Tenant isolation violation: Actor tenant '{self.organization_id}' "
                f"cannot execute tool on tenant '{target_org_id}'"
            )

        # 2. Write action approval check
        if tool_action_type in (ActionType.WRITE, ActionType.ADMIN):
            if not is_approved or requires_human_approval:
                if not is_approved:
                    raise PolicyViolationError(
                        f"Write action '{tool_name}' requires human approval. "
                        f"Autonomous agent writes are prohibited."
                    )

        # 3. Read tool allowlist check
        if tool_action_type == ActionType.READ:
            if tool_name not in self.allowed_read_tools:
                raise PolicyViolationError(
                    f"Tool '{tool_name}' is not in the allowed read-only toolset (deny-by-default)."
                )

        return True

    def sanitize_agent_input(self, text: str) -> str:
        """
        Neutralizes known prompt-injection prefixes and patterns
        before feeding into agent context.
        """
        # Strip injection markers
        patterns = [
            r"(?i)ignore\s+all\s+(previous\s+)?instructions",
            r"(?i)system\s*:\s*",
            r"(?i)you\s+are\s+now\s+admin",
            r"(?i)disregard\s+prior",
        ]
        cleaned = text
        for p in patterns:
            cleaned = re.sub(p, "[REDACTED_INJECTION_PATTERN]", cleaned)
        return cleaned

    def can_execute_arbitrary_code(self) -> bool:
        """Strict invariant: Agent can NEVER execute arbitrary code."""
        return False
