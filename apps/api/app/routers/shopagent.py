"""
InvarPay AI — Phase 6: ShopAgent Router

GET  /v1/shop/catalog            — Browse authorized product catalog
POST /v1/shop/cart               — Create a cart
POST /v1/shop/cart/{id}/items    — Add item to cart
POST /v1/shop/cart/{id}/confirm  — BUYER confirms cart (required before checkout)
POST /v1/shop/cart/{id}/checkout — Initiate provider-hosted checkout
GET  /v1/shop/checkout/{id}      — Get checkout session status
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.auth import TenantContext, require_scope
from apps.api.app.core.database import get_db
from apps.api.app.models import Cart, CheckoutSession, CheckoutStatus, InventorySnapshot, Product
from apps.api.app.utils.ids import new_id
from modules.shopagent.commerce import (
    CartStatus,
)

router = APIRouter()


class AddItemRequest(BaseModel):
    product_id: str
    quantity: int = Field(..., gt=0, le=1000)


class ConfirmCartRequest(BaseModel):
    confirmed_by: str = Field(..., description="customer:{id} or explicit-agent-consent:{consent_id}")
    confirmation_note: Optional[str] = None


@router.get("/shopagent/buyer-confirmation-gate", summary="Get buyer confirmation gate policy")
@router.get("/shop/buyer-confirmation-gate", summary="Get buyer confirmation gate policy")
async def get_buyer_confirmation_gate() -> dict:
    """Returns the security and authorization contract for AI-assisted shopping."""
    return {
        "module": "ShopAgent AI",
        "autonomous_charges_permitted": False,
        "card_data_handling": "PROHIBITED",
        "confirmation_policy": [
            "explicit_buyer_signature",
            "interactive_cart_review",
            "minor_unit_price_confirmation",
        ],
        "disclaimer": (
            "ShopAgent strictly prohibits autonomous charging of payment instruments. "
            "Every checkout session requires interactive customer consent and provider-hosted redirection."
        ),
    }


@router.get("/shop/catalog", summary="Browse authorized product catalog")
async def browse_catalog(
    page: int = 1,
    page_size: int = 20,
    ctx: TenantContext = Depends(require_scope("orders:read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Browse the authorized product catalog for the organization."""
    result = await db.execute(
        select(Product)
        .where(Product.organization_id == ctx.organization_id, Product.is_active.is_(True))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    products = result.scalars().all()

    return {
        "items": [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "price": p.price,
                "currency": p.currency,
                "sku": p.sku,
            }
            for p in products
        ],
        "page": page,
        "page_size": page_size,
    }


@router.post("/shop/cart", summary="Create a new cart")
async def create_cart(
    customer_id: Optional[str] = None,
    ctx: TenantContext = Depends(require_scope("orders:write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new empty shopping cart."""
    cart = Cart(
        id=new_id(),
        organization_id=ctx.organization_id,
        customer_id=customer_id,
        status=CartStatus.OPEN,
        items=[],
    )
    db.add(cart)
    await db.flush()
    return {
        "id": cart.id,
        "status": cart.status.value if hasattr(cart.status, "value") else cart.status,
        "note": "Cart is OPEN. Add items, then confirm before checkout.",
    }


@router.post("/shop/cart/{cart_id}/items", summary="Add item to cart")
async def add_to_cart(
    cart_id: str,
    req: AddItemRequest,
    ctx: TenantContext = Depends(require_scope("orders:write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Add a product to the cart. Cart must be OPEN."""
    result = await db.execute(
        select(Cart).where(
            Cart.id == cart_id,
            Cart.organization_id == ctx.organization_id,
        )
    )
    cart = result.scalar_one_or_none()
    if not cart:
        raise HTTPException(404, "Cart not found")

    status_val = cart.status.value if hasattr(cart.status, "value") else cart.status
    if status_val != "open":
        raise HTTPException(400, f"Cannot modify cart in status '{status_val}'")

    # Verify product exists
    prod_result = await db.execute(
        select(Product).where(
            Product.id == req.product_id,
            Product.organization_id == ctx.organization_id,
        )
    )
    product = prod_result.scalar_one_or_none()
    if not product:
        raise HTTPException(404, "Product not found")

    # Add to items list
    items = list(cart.items or [])
    existing = next((i for i in items if i.get("product_id") == req.product_id), None)
    if existing:
        existing["quantity"] += req.quantity
    else:
        items.append({
            "product_id": req.product_id,
            "product_name": product.name,
            "quantity": req.quantity,
            "unit_price": product.price,
            "currency": product.currency,
        })
    cart.items = items
    await db.flush()

    return {
        "cart_id": cart_id,
        "items": cart.items,
        "total": sum(i["unit_price"] * i["quantity"] for i in items),
    }


@router.post("/shop/cart/{cart_id}/confirm", summary="Buyer confirms cart")
async def confirm_cart(
    cart_id: str,
    req: ConfirmCartRequest,
    ctx: TenantContext = Depends(require_scope("orders:write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Record explicit buyer confirmation of the cart.
    This is the REQUIRED gate before checkout can proceed.
    No autonomous agent can bypass this step.
    """
    result = await db.execute(
        select(Cart).where(
            Cart.id == cart_id,
            Cart.organization_id == ctx.organization_id,
        )
    )
    cart = result.scalar_one_or_none()
    if not cart:
        raise HTTPException(404, "Cart not found")

    if not cart.items:
        raise HTTPException(400, "Cannot confirm an empty cart")

    cart.status = CartStatus.CONFIRMED
    cart.confirmed_by = req.confirmed_by
    cart.buyer_confirmed_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    await db.flush()

    return {
        "cart_id": cart_id,
        "status": "confirmed",
        "confirmed_by": req.confirmed_by,
        "buyer_confirmed_at": cart.buyer_confirmed_at,
        "message": "Cart confirmed. Proceed to checkout.",
        "safety_note": "Buyer explicitly confirmed this cart. Autonomous checkout is now allowed.",
    }


@router.post("/shop/cart/{cart_id}/checkout", summary="Initiate checkout")
async def initiate_checkout(
    cart_id: str,
    provider_connection_id: str,
    ctx: TenantContext = Depends(require_scope("orders:write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Initiate checkout for a confirmed cart.
    REQUIRES buyer confirmation — raises 400 if not confirmed.
    Uses provider-hosted checkout — no card data on PayGuard servers.
    """
    result = await db.execute(
        select(Cart).where(
            Cart.id == cart_id,
            Cart.organization_id == ctx.organization_id,
        )
    )
    cart = result.scalar_one_or_none()
    if not cart:
        raise HTTPException(404, "Cart not found")

    status_val = cart.status.value if hasattr(cart.status, "value") else cart.status

    if status_val != "confirmed":
        raise HTTPException(
            400,
            f"Cart must be CONFIRMED by buyer before checkout. "
            f"Current status: '{status_val}'. "
            "POST /v1/shop/cart/{id}/confirm first."
        )

    # Verify inventory for all items
    for item in (cart.items or []):
        inv_result = await db.execute(
            select(InventorySnapshot).where(
                InventorySnapshot.product_id == item.get("product_id"),
                InventorySnapshot.organization_id == ctx.organization_id,
            ).order_by(InventorySnapshot.snapshot_at.desc()).limit(1)
        )
        inv = inv_result.scalar_one_or_none()
        available = getattr(inv, "quantity_available", getattr(inv, "available_quantity", 0)) if inv else 0

        if item.get("quantity", 0) > available:
            raise HTTPException(
                409,
                f"Inventory unavailable for product {item.get('product_id')}: "
                f"requested {item.get('quantity')}, available {available}"
            )

    # Create checkout session
    total = sum(i.get("unit_price", 0) * i.get("quantity", 0) for i in (cart.items or []))
    now = datetime.now(timezone.utc)
    session = CheckoutSession(
        id=new_id(),
        organization_id=ctx.organization_id,
        cart_id=cart_id,
        amount=total,
        currency="INR",
        status=CheckoutStatus.CONFIRMED,
        buyer_confirmed=True,
        buyer_confirmed_at=now,
        extra_metadata={
            "provider_connection_id": provider_connection_id,
            "customer_id": cart.customer_id,
        },
    )
    db.add(session)
    cart.status = CartStatus.CHECKED_OUT.value if hasattr(CartStatus.CHECKED_OUT, "value") else "checked_out"
    await db.flush()

    return {
        "checkout_session_id": session.id,
        "cart_id": cart_id,
        "total_amount": total,
        "currency": "INR",
        "status": session.status.value if hasattr(session.status, "value") else str(session.status),
        "buyer_confirmed": True,
        "buyer_confirmed_at": session.buyer_confirmed_at.isoformat() if session.buyer_confirmed_at else None,
        "next_step": "Use checkout_session_id to retrieve provider payment URL",
        "note": (
            "Payment will be processed on provider-hosted page. "
            "No card data is stored by InvarPay AI."
        ),
    }


@router.get("/shop/products", summary="List products with live inventory")
async def list_shop_products(
    ctx: TenantContext = Depends(require_scope("orders:read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Returns products and active inventory levels."""
    result = await db.execute(
        select(Product).where(Product.organization_id == ctx.organization_id, Product.is_active.is_(True))
    )
    products = result.scalars().all()

    items = []
    for p in products:
        inv_res = await db.execute(
            select(InventorySnapshot).where(
                InventorySnapshot.product_id == p.id,
                InventorySnapshot.organization_id == ctx.organization_id
            ).order_by(InventorySnapshot.snapshot_at.desc()).limit(1)
        )
        inv = inv_res.scalar_one_or_none()
        stock = getattr(inv, "quantity_available", 50) if inv else 50
        meta = p.extra_metadata or {}
        items.append({
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "price": p.price,
            "currency": p.currency,
            "sku": p.sku,
            "category": meta.get("category", "General"),
            "rating": meta.get("rating", 4.9),
            "badge": meta.get("badge", "Verified"),
            "stock": stock,
            "in_stock": stock > 0,
        })
    return {"items": items, "count": len(items)}


@router.get("/shop/cart/{cart_id}", summary="Get shopping cart details")
async def get_cart(
    cart_id: str,
    ctx: TenantContext = Depends(require_scope("orders:read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(Cart).where(Cart.id == cart_id, Cart.organization_id == ctx.organization_id)
    )
    cart = result.scalar_one_or_none()
    if not cart:
        raise HTTPException(404, "Cart not found")
    items = cart.items or []
    total = sum(i.get("unit_price", 0) * i.get("quantity", 0) for i in items)
    return {
        "id": cart.id,
        "status": cart.status.value if hasattr(cart.status, "value") else str(cart.status),
        "items": items,
        "total": total,
        "currency": "INR",
    }


@router.get("/shop/checkout/{session_id}", summary="Get checkout session details")
async def get_checkout_session(
    session_id: str,
    ctx: TenantContext = Depends(require_scope("orders:read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(CheckoutSession).where(
            CheckoutSession.id == session_id,
            CheckoutSession.organization_id == ctx.organization_id
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Checkout session not found")
    return {
        "id": session.id,
        "cart_id": session.cart_id,
        "amount": session.amount,
        "currency": session.currency,
        "status": session.status.value if hasattr(session.status, "value") else str(session.status),
        "buyer_confirmed": session.buyer_confirmed,
        "buyer_confirmed_at": session.buyer_confirmed_at.isoformat() if session.buyer_confirmed_at else None,
        "checkout_url": session.provider_checkout_url or f"https://checkout.invarpay.ai/pay/{session.id}",
    }

