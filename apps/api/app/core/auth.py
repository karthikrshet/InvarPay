"""
PayGuard AI — JWT & API Key Authentication
FastAPI dependencies for request authentication and tenant context.

Tenant isolation invariant:
  Every authenticated request sets a TenantContext that ALL queries
  must use to filter by organization_id. Never trust client-provided org IDs.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.database import get_db
from apps.api.app.core.security import decode_access_token, verify_api_key
from apps.api.app.models import ApiKey, User

# ── Security schemes ──────────────────────────────────────────────────────────

bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


# ── Tenant context ─────────────────────────────────────────────────────────────

@dataclass
class TenantContext:
    """
    Authenticated request context. Set once per request after auth.
    All downstream queries must filter by organization_id.
    """
    organization_id: str
    actor_id: str
    actor_type: str  # "user" | "api_key" | "system"
    scopes: list[str]
    is_test_mode: bool = False
    user_id: Optional[str] = None
    api_key_id: Optional[str] = None


# ── Auth dependencies ──────────────────────────────────────────────────────────

async def _authenticate_bearer(
    credentials: Optional[HTTPAuthorizationCredentials],
    db: AsyncSession,
) -> Optional[TenantContext]:
    """Validate JWT bearer token and return TenantContext."""
    if not credentials:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
        user_id: str = payload.get("sub", "")
        org_id: str = payload.get("org_id", "")

        if not user_id or not org_id:
            return None

        result = await db.execute(
            select(User).where(User.id == user_id, User.is_active == True)  # noqa: E712
        )
        user = result.scalar_one_or_none()
        if not user or user.organization_id != org_id:
            return None

        return TenantContext(
            organization_id=org_id,
            actor_id=user_id,
            actor_type="user",
            scopes=["*"],  # JWT-authenticated users have full org scope
            user_id=user_id,
        )
    except JWTError:
        return None


async def _authenticate_api_key(
    key: Optional[str],
    db: AsyncSession,
) -> Optional[TenantContext]:
    """Validate API key and return TenantContext with key-specific scopes."""
    if not key:
        return None

    # Determine key prefix type
    from apps.api.app.core.config import get_settings
    s = get_settings()
    is_test = key.startswith(s.api_key_test_prefix)

    result = await db.execute(
        select(ApiKey).where(
            ApiKey.is_active == True,  # noqa: E712
            ApiKey.key_prefix == (s.api_key_test_prefix if is_test else s.api_key_prefix),
        )
    )
    api_keys = result.scalars().all()

    for api_key in api_keys:
        if verify_api_key(key, api_key.key_hash):
            # Check expiry
            if api_key.expires_at and api_key.expires_at < datetime.utcnow():
                return None

            # Update last used (fire and forget)
            api_key.last_used_at = datetime.utcnow()

            return TenantContext(
                organization_id=api_key.organization_id,
                actor_id=api_key.id,
                actor_type="api_key",
                scopes=api_key.scopes.split(","),
                is_test_mode=is_test,
                api_key_id=api_key.id,
            )
    return None


async def get_tenant_context(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    api_key: Optional[str] = Security(api_key_header),
    db: AsyncSession = Depends(get_db),
) -> TenantContext:
    """
    Master auth dependency. Tries JWT bearer first, then API key.
    Raises 401 if neither succeeds.
    """
    ctx = await _authenticate_bearer(credentials, db)
    if not ctx:
        ctx = await _authenticate_api_key(api_key, db)
    if not ctx:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a Bearer token or X-API-Key header.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Attach to request state for middleware/logging
    request.state.tenant_context = ctx
    return ctx


def require_scope(scope: str):
    """Dependency factory: check that the authenticated context has a required scope."""
    async def _check_scope(ctx: TenantContext = Depends(get_tenant_context)) -> TenantContext:
        if "*" in ctx.scopes or scope in ctx.scopes:
            return ctx
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions. Required scope: {scope}",
        )
    return _check_scope


def get_optional_tenant_context(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    api_key: Optional[str] = Security(api_key_header),
) -> Optional[TenantContext]:
    """For endpoints that work with or without auth (e.g., health)."""
    return None  # Simplified; endpoints requiring auth use get_tenant_context
