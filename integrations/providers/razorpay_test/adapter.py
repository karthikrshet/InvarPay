"""
PayGuard AI — Razorpay Test-Mode Provider Adapter

Integrates with Razorpay's test-mode API.
TEST MODE ONLY — never accepts live credentials.

Based on official Razorpay API documentation:
- https://razorpay.com/docs/payments/
- https://razorpay.com/docs/webhooks/

Credentials are read from environment variables, never hardcoded.
If credentials are absent, all methods raise RazorpayNotConfiguredError.
The adapter gracefully degrades to fixture responses in CI if not configured.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from apps.api.app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

RAZORPAY_BASE_URL = "https://api.razorpay.com/v1"
TEST_MODE_MARKER = "[RAZORPAY-TEST-MODE]"


class RazorpayNotConfiguredError(Exception):
    """Raised when Razorpay credentials are not set in environment."""
    pass


class RazorpayAPIError(Exception):
    """Raised when Razorpay API returns an error response."""
    def __init__(self, status_code: int, error: dict) -> None:
        self.status_code = status_code
        self.error = error
        super().__init__(f"Razorpay API error {status_code}: {error.get('description', 'unknown')}")


class RazorpayTestAdapter:
    """
    Razorpay test-mode payment adapter.
    All API calls go to Razorpay's test environment.
    No real money is moved.
    """

    def __init__(
        self,
        key_id: Optional[str] = None,
        key_secret: Optional[str] = None,
    ) -> None:
        self._key_id = key_id or settings.razorpay_key_id
        self._key_secret = key_secret or settings.razorpay_key_secret.get_secret_value()

        if not self._key_id or not self._key_secret:
            raise RazorpayNotConfiguredError(
                "Razorpay credentials not configured. "
                "Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in .env "
                "(test-mode keys only). "
                "Using fake provider for this run."
            )

        # Validate that test-mode keys are used
        if not self._key_id.startswith("rzp_test_"):
            raise RazorpayNotConfiguredError(
                "Only Razorpay TEST-MODE keys (rzp_test_*) are accepted. "
                "Never use live credentials."
            )

        self._client = httpx.AsyncClient(
            base_url=RAZORPAY_BASE_URL,
            auth=(self._key_id, self._key_secret),
            timeout=30.0,
            headers={"Content-Type": "application/json"},
        )

    async def create_order(
        self,
        amount: int,
        currency: str = "INR",
        receipt: Optional[str] = None,
        notes: Optional[dict] = None,
    ) -> dict[str, Any]:
        """
        Create a Razorpay order.
        amount: integer in minor units (paise for INR)
        Reference: https://razorpay.com/docs/payments/orders/create/
        """
        payload: dict[str, Any] = {
            "amount": amount,
            "currency": currency,
        }
        if receipt:
            payload["receipt"] = receipt
        if notes:
            payload["notes"] = {**notes, "_marker": TEST_MODE_MARKER}

        response = await self._client.post("/orders", json=payload)
        return self._handle_response(response)

    async def fetch_payment(self, payment_id: str) -> dict[str, Any]:
        """
        Fetch payment details from Razorpay.
        Reference: https://razorpay.com/docs/payments/view/
        """
        response = await self._client.get(f"/payments/{payment_id}")
        return self._handle_response(response)

    async def fetch_order(self, order_id: str) -> dict[str, Any]:
        """Fetch order details from Razorpay."""
        response = await self._client.get(f"/orders/{order_id}")
        return self._handle_response(response)

    async def capture_payment(
        self,
        payment_id: str,
        amount: int,
        currency: str = "INR",
    ) -> dict[str, Any]:
        """
        Capture an authorized payment.
        Reference: https://razorpay.com/docs/payments/capture/
        NOTE: Requires explicit approval flow in PayGuard — never called autonomously.
        """
        response = await self._client.post(
            f"/payments/{payment_id}/capture",
            json={"amount": amount, "currency": currency},
        )
        return self._handle_response(response)

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        if response.status_code >= 400:
            try:
                error_body = response.json()
                error = error_body.get("error", {})
            except Exception:
                error = {"description": response.text}
            raise RazorpayAPIError(response.status_code, error)
        return response.json()

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "RazorpayTestAdapter":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()


def get_provider_adapter(
    key_id: Optional[str] = None,
    key_secret: Optional[str] = None,
) -> "RazorpayTestAdapter | None":
    """
    Get a Razorpay adapter if configured, else return None.
    Callers should fall back to fake provider if None.
    """
    try:
        return RazorpayTestAdapter(key_id=key_id, key_secret=key_secret)
    except RazorpayNotConfiguredError as e:
        logger.info("Razorpay not configured — using fake provider. Reason: %s", e)
        return None
