"""
Phase 6 tests: ShopAgent buyer confirmation gate and inventory checks.
CRITICAL: No autonomous purchases. Explicit buyer confirmation required.
"""
from __future__ import annotations

import pytest

from apps.api.app.utils.ids import new_id
from modules.shopagent.commerce import (
    BuyerConfirmationError,
    Cart,
    CartItem,
    CartStatus,
    confirm_cart,
    create_checkout_session,
    require_buyer_confirmation,
    verify_inventory,
)


def make_cart(status: CartStatus = CartStatus.OPEN) -> Cart:
    cart = Cart(
        id=new_id(),
        organization_id="org_test",
        customer_id="cust_test",
        status=status,
        items=[CartItem(
            product_id="prod_001",
            product_name="Test Product [SYNTHETIC]",
            quantity=2,
            unit_price=50000,
        )],
    )
    if status == CartStatus.CONFIRMED:
        cart.buyer_confirmed_at = "2024-01-01T12:00:00+00:00"
        cart.confirmed_by = "customer:cust_test"
    return cart


class TestBuyerConfirmationGate:
    """Buyer confirmation is the critical safety invariant for ShopAgent."""

    def test_unconfirmed_cart_blocks_checkout(self) -> None:
        """OPEN cart must not be allowed to checkout."""
        cart = make_cart(CartStatus.OPEN)
        with pytest.raises(BuyerConfirmationError):
            require_buyer_confirmation(cart)

    def test_confirmed_cart_allows_checkout(self) -> None:
        """CONFIRMED cart can proceed to checkout."""
        cart = make_cart(CartStatus.CONFIRMED)
        # Should not raise
        require_buyer_confirmation(cart)

    def test_confirm_cart_sets_status_and_timestamp(self) -> None:
        cart = make_cart(CartStatus.OPEN)
        confirmed = confirm_cart(cart, confirmed_by="customer:cust_test")
        assert confirmed.status == CartStatus.CONFIRMED
        assert confirmed.buyer_confirmed_at is not None
        assert confirmed.confirmed_by == "customer:cust_test"

    def test_abandoned_cart_blocks_checkout(self) -> None:
        cart = make_cart(CartStatus.ABANDONED)
        with pytest.raises(BuyerConfirmationError):
            require_buyer_confirmation(cart)

    def test_empty_confirmed_cart_blocks_checkout(self) -> None:
        """Even confirmed, an empty cart cannot checkout."""
        cart = Cart(
            id=new_id(),
            organization_id="org_test",
            customer_id=None,
            status=CartStatus.CONFIRMED,
            items=[],
            buyer_confirmed_at="2024-01-01T12:00:00+00:00",
        )
        with pytest.raises(BuyerConfirmationError):
            require_buyer_confirmation(cart)


class TestInventoryVerification:
    """Inventory is verified at checkout time — not at cart add time."""

    def test_sufficient_inventory_allowed(self) -> None:
        ok, reason = verify_inventory("prod_001", quantity_requested=2, available_quantity=10)
        assert ok is True
        assert reason == "ok"

    def test_insufficient_inventory_blocked(self) -> None:
        ok, reason = verify_inventory("prod_001", quantity_requested=5, available_quantity=3)
        assert ok is False
        assert "3" in reason

    def test_out_of_stock_blocked(self) -> None:
        ok, reason = verify_inventory("prod_001", quantity_requested=1, available_quantity=0)
        assert ok is False
        assert "out of stock" in reason.lower()


class TestCheckoutSession:
    """Checkout session creation requires confirmed cart."""

    def test_confirmed_cart_creates_session(self) -> None:
        cart = make_cart(CartStatus.CONFIRMED)
        session = create_checkout_session(cart, "conn_fake_001")
        assert session["cart_id"] == cart.id
        assert session["total_amount"] == 100000  # 2 * 50000
        assert "provider" in session["note"].lower() or "provider" in str(session)

    def test_unconfirmed_cart_raises_on_checkout(self) -> None:
        cart = make_cart(CartStatus.OPEN)
        with pytest.raises(BuyerConfirmationError):
            create_checkout_session(cart, "conn_fake_001")

    def test_checkout_note_mentions_provider_hosted(self) -> None:
        """Safety: checkout note must mention provider-hosted payment."""
        cart = make_cart(CartStatus.CONFIRMED)
        session = create_checkout_session(cart, "conn_fake_001")
        note = session.get("note", "")
        assert "provider" in note.lower(), "Checkout must mention provider-hosted payment"
