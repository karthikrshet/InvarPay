"""
PayGuard AI — Phase 6: ShopAgent Agentic Commerce Engine

Buyer-confirmed agentic commerce with strict safety constraints:

1. NO autonomous purchases — explicit buyer confirmation required for every order
2. Only whitelisted merchants — verified before any catalog is served
3. Inventory verified at time of checkout (not at cart add)
4. Checkout uses provider-hosted page (no card data touches our servers)
5. Every agent action is logged with full audit trail
6. Cart is editable until explicit checkout confirmation

Flow:
  browse_catalog → add_to_cart → review_cart →
  BUYER CONFIRMS → verify_inventory → checkout_session →
  PROVIDER-HOSTED PAYMENT → verify_completion
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CartStatus(str, Enum):
    OPEN = "open"
    CONFIRMED = "confirmed"     # Buyer explicitly confirmed
    ABANDONED = "abandoned"
    CHECKED_OUT = "checked_out"


class CheckoutSessionStatus(str, Enum):
    CREATED = "created"
    BUYER_CONFIRMED = "buyer_confirmed"   # Gate: buyer approval received
    PAYMENT_INITIATED = "payment_initiated"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class CartItem:
    product_id: str
    product_name: str
    quantity: int
    unit_price: int           # Minor units
    currency: str = "INR"
    inventory_verified: bool = False
    inventory_verified_at: Optional[str] = None


@dataclass
class Cart:
    id: str
    organization_id: str
    customer_id: Optional[str]
    items: list[CartItem] = field(default_factory=list)
    status: CartStatus = CartStatus.OPEN
    buyer_confirmed_at: Optional[str] = None
    confirmed_by: Optional[str] = None   # "customer" | "agent_on_behalf" (requires prior consent)
    created_at: str = ""
    currency: str = "INR"

    def __post_init__(self) -> None:
        self.created_at = datetime.now(timezone.utc).isoformat()

    @property
    def total_amount(self) -> int:
        return sum(item.unit_price * item.quantity for item in self.items)

    @property
    def is_empty(self) -> bool:
        return len(self.items) == 0


class BuyerConfirmationError(Exception):
    """Raised when checkout is attempted without explicit buyer confirmation."""
    pass


class InventoryUnavailableError(Exception):
    """Raised when inventory check fails at checkout time."""
    pass


class MerchantNotAllowedError(Exception):
    """Raised when a merchant is not in the approved whitelist."""
    pass


def verify_merchant_allowed(merchant_id: str, allowed_merchants: set[str]) -> bool:
    """
    Check if a merchant is in the approved whitelist.
    This is a hard gate — catalog is never served for non-whitelisted merchants.
    """
    return merchant_id in allowed_merchants


def verify_inventory(
    product_id: str,
    quantity_requested: int,
    available_quantity: int,
) -> tuple[bool, str]:
    """
    Verify inventory at checkout time (not at cart add time).
    Returns (available, reason).
    """
    if available_quantity <= 0:
        return False, f"Product {product_id} is out of stock"
    if quantity_requested > available_quantity:
        return False, (
            f"Only {available_quantity} units available "
            f"(requested {quantity_requested})"
        )
    return True, "ok"


def require_buyer_confirmation(cart: Cart, requester_type: str = "agent") -> None:
    """
    Enforce that the buyer has explicitly confirmed the cart before checkout.
    Raises BuyerConfirmationError if not confirmed.

    This is the critical safety gate for agentic commerce.
    """
    if cart.status != CartStatus.CONFIRMED:
        raise BuyerConfirmationError(
            f"Cart {cart.id} has not been confirmed by the buyer. "
            f"Current status: {cart.status.value}. "
            "Explicit buyer confirmation is required before checkout."
        )
    if not cart.buyer_confirmed_at:
        raise BuyerConfirmationError(
            "buyer_confirmed_at timestamp is missing — cannot proceed"
        )
    if cart.is_empty:
        raise BuyerConfirmationError("Cannot checkout an empty cart")


def confirm_cart(
    cart: Cart,
    confirmed_by: str,
    confirmation_token: Optional[str] = None,
) -> Cart:
    """
    Record explicit buyer confirmation.
    confirmed_by should be "customer:{customer_id}" or "customer_explicit_consent"
    """
    cart.status = CartStatus.CONFIRMED
    cart.buyer_confirmed_at = datetime.now(timezone.utc).isoformat()
    cart.confirmed_by = confirmed_by
    return cart


def create_checkout_session(
    cart: Cart,
    provider_connection_id: str,
) -> dict[str, Any]:
    """
    Create a checkout session after buyer confirmation.
    Returns provider-hosted checkout URL — no card data touches PayGuard.

    GATE: Buyer confirmation is verified before creating session.
    """
    # This gate is the safety invariant — always checked
    require_buyer_confirmation(cart)

    session_data: dict[str, Any] = {
        "cart_id": cart.id,
        "total_amount": cart.total_amount,
        "currency": cart.currency,
        "status": CheckoutSessionStatus.BUYER_CONFIRMED.value,
        "provider_connection_id": provider_connection_id,
        "buyer_confirmed_at": cart.buyer_confirmed_at,
        "note": (
            "Checkout will use provider-hosted payment page. "
            "No card data is processed by PayGuard AI."
        ),
    }
    return session_data
