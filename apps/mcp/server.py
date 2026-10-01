"""
InvarPay AI — Phase 2: MCP Server (Model Context Protocol)

Exposes read-only PayGuard tools as MCP tools for AI assistants.
Implements the MCP spec (JSON-RPC 2.0 over stdio or HTTP).

ALL tools are READ-ONLY. No MCP tool can:
- Initiate payments
- Trigger refunds
- Modify payment state

Write operations require creating an ApprovalRequest via the API,
which then requires explicit human review.

Spec: https://spec.modelcontextprotocol.io/
"""
from __future__ import annotations

import json
import logging
import sys
from typing import Any

logger = logging.getLogger(__name__)

MCP_VERSION = "2024-11-05"
SERVER_INFO = {
    "name": "invarpay",
    "version": "0.1.0",
    "description": (
        "InvarPay AI MCP Server — read-only payment operations tools. "
        "Independent open-source project. Not affiliated with Razorpay. "
        "All provider access is in TEST MODE only."
    ),
}

# Tool definitions following MCP spec
MCP_TOOLS = [
    {
        "name": "get_payment_status",
        "description": (
            "Get the current status and timeline of a payment attempt. "
            "Returns status, timestamps, and provider event summary. "
            "READ-ONLY — no state mutation."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "payment_id": {
                    "type": "string",
                    "description": "PayGuard payment attempt ID (ULID format)",
                },
                "organization_id": {
                    "type": "string",
                    "description": "Organization ID for tenant isolation",
                },
            },
            "required": ["payment_id", "organization_id"],
        },
    },
    {
        "name": "check_retry_safety",
        "description": (
            "Check whether it is safe to retry a payment. "
            "Returns False for unknown/pending/captured payments. "
            "CRITICAL: Never retry without checking this first."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "payment_id": {
                    "type": "string",
                    "description": "Payment attempt ID",
                },
                "organization_id": {"type": "string"},
            },
            "required": ["payment_id", "organization_id"],
        },
    },
    {
        "name": "get_reconciliation_history",
        "description": "Get reconciliation runs for a payment. READ-ONLY.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "payment_id": {"type": "string"},
                "organization_id": {"type": "string"},
            },
            "required": ["payment_id", "organization_id"],
        },
    },
    {
        "name": "get_audit_events",
        "description": (
            "Get audit trail for a resource. Hash-chained, tamper-evident. READ-ONLY."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "resource_id": {"type": "string"},
                "organization_id": {"type": "string"},
                "limit": {"type": "integer", "default": 20},
            },
            "required": ["resource_id", "organization_id"],
        },
    },
    {
        "name": "get_recovery_recommendation",
        "description": (
            "Get a deterministic recovery recommendation for a payment. "
            "Returns action, safety level, and required approval status. "
            "Note: recommendations are proposals — human approval required for execution."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "payment_id": {"type": "string"},
                "organization_id": {"type": "string"},
            },
            "required": ["payment_id", "organization_id"],
        },
    },
]


class MCPServer:
    """MCP server exposing read-only PayGuard tools."""

    def __init__(self, api_key: str, api_url: str = "http://localhost:8000") -> None:
        self.api_key = api_key
        self.api_url = api_url

    def handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle a JSON-RPC 2.0 MCP request."""
        method = request.get("method", "")
        req_id = request.get("id")

        try:
            if method == "initialize":
                return self._ok(req_id, {
                    "protocolVersion": MCP_VERSION,
                    "serverInfo": SERVER_INFO,
                    "capabilities": {"tools": {"listChanged": False}},
                })

            elif method == "tools/list":
                return self._ok(req_id, {"tools": MCP_TOOLS})

            elif method == "tools/call":
                return self._handle_tool_call(req_id, request.get("params", {}))

            else:
                return self._error(req_id, -32601, f"Method not found: {method}")

        except Exception as e:
            logger.exception("MCP handler error")
            return self._error(req_id, -32603, str(e))

    def _handle_tool_call(self, req_id: Any, params: dict) -> dict:
        """Route and execute a tool call."""
        tool_name = params.get("name")
        args = params.get("arguments", {})

        # All tools require organization_id for tenant isolation
        org_id = args.get("organization_id")
        if not org_id:
            return self._error(req_id, -32602, "organization_id is required for all tools")

        if tool_name == "get_payment_status":
            result = self._call_api(f"/v1/payments/{args['payment_id']}", org_id)
        elif tool_name == "check_retry_safety":
            payment = self._call_api(f"/v1/payments/{args['payment_id']}", org_id)
            status = payment.get("status", "unknown")
            safe = status in ("failed", "cancelled")
            result = {
                "payment_id": args["payment_id"],
                "status": status,
                "safe_to_retry": safe,
                "reason": (
                    "Definitively failed — new attempt is safe" if safe
                    else f"Status '{status}' — do NOT retry without reconciliation"
                ),
            }
        elif tool_name == "get_reconciliation_history":
            result = self._call_api(f"/v1/payments/{args['payment_id']}", org_id)
        elif tool_name == "get_audit_events":
            result = self._call_api(
                f"/v1/audit-events?resource_id={args['resource_id']}&page_size={args.get('limit', 20)}",
                org_id
            )
        elif tool_name == "get_recovery_recommendation":
            payment = self._call_api(f"/v1/payments/{args['payment_id']}", org_id)
            from modules.payguard.recovery import recommend_recovery
            rec = recommend_recovery(
                payment_status=payment.get("status", "unknown"),
                provider_status=payment.get("provider_status"),
                is_reconciled=payment.get("is_reconciled", False),
                provider_payment_id=payment.get("provider_payment_id"),
                initiated_at=None,
                minutes_since_initiation=None,
                failure_code=None,
            )
            result = {
                "action": rec.action.value,
                "safety": rec.safety.value,
                "reason": rec.reason,
                "requires_approval": rec.requires_approval,
                "estimated_risk": rec.estimated_risk,
            }
        else:
            return self._error(req_id, -32602, f"Unknown tool: {tool_name}")

        return self._ok(req_id, {
            "content": [{"type": "text", "text": json.dumps(result, indent=2)}],
            "isError": False,
        })

    def _call_api(self, path: str, org_id: str) -> dict:
        """Call the PayGuard API synchronously."""
        import urllib.request
        url = f"{self.api_url}{path}"
        req = urllib.request.Request(
            url,
            headers={
                "X-API-Key": self.api_key,
                "X-Organization-Id": org_id,
            }
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())

    def _ok(self, req_id: Any, result: Any) -> dict:
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    def _error(self, req_id: Any, code: int, message: str) -> dict:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def run_stdio_server(api_key: str, api_url: str = "http://localhost:8000") -> None:
    """Run MCP server over stdio (standard MCP transport)."""
    server = MCPServer(api_key=api_key, api_url=api_url)
    logger.info("InvarPay AI MCP server starting (stdio transport)")

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = server.handle_request(request)
            print(json.dumps(response), flush=True)
        except json.JSONDecodeError as e:
            error_resp = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(e)}}
            print(json.dumps(error_resp), flush=True)


if __name__ == "__main__":
    import os
    key = os.environ.get("PAYGUARD_API_KEY", "")
    url = os.environ.get("PAYGUARD_API_URL", "http://localhost:8000")
    run_stdio_server(api_key=key, api_url=url)
