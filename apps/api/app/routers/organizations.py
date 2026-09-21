"""
PayGuard AI — Organization Router

POST /v1/organizations — Create a new organization + owner user + demo API key
GET  /v1/organizations/me — Get current organization
POST /v1/auth/login — JWT login
POST /v1/auth/api-keys — Create API key
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.auth import TenantContext, get_tenant_context, require_scope
from apps.api.app.core.database import get_db
from apps.api.app.core.security import (
    create_access_token,
    encrypt_credential,
    generate_api_key,
    hash_password,
    verify_password,
)
from apps.api.app.models import ApiKey, Membership, Organization, ProviderConnection, User, UserRole
from apps.api.app.schemas import (
    ApiKeyResponse,
    CreateApiKeyRequest,
    CreateOrganizationRequest,
    LoginRequest,
    OrganizationResponse,
    ProviderConnectionResponse,
    TestProviderConnectionRequest,
    TokenResponse,
)
from apps.api.app.utils.ids import new_id

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/organizations",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create organization",
    description="Bootstrap a new organization with an owner user and a test API key.",
)
async def create_organization(
    body: CreateOrganizationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> OrganizationResponse:
    # Check organization and owner-email uniqueness before writing either record.
    existing = await db.execute(
        select(Organization).where(Organization.slug == body.slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Organization slug '{body.slug}' already taken.",
        )

    existing_user = await db.execute(select(User).where(User.email == str(body.email)))
    if existing_user.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Owner email already registered.")

    org_id = new_id()
    org = Organization(
        id=org_id,
        name=body.name,
        slug=body.slug,
        email=str(body.email),
        is_active=True,
    )
    db.add(org)
    await db.flush()

    owner = User(
        id=new_id(),
        organization_id=org_id,
        email=str(body.email),
        hashed_password=hash_password(body.owner_password.get_secret_value()),
        full_name=body.owner_name,
        is_active=True,
    )
    db.add(owner)
    db.add(Membership(
        id=new_id(), organization_id=org_id, user_id=owner.id, role=UserRole.OWNER, is_active=True
    ))

    from apps.api.app.core.audit import record_audit_event
    await record_audit_event(
        db=db,
        organization_id=org_id,
        actor_id=owner.id,
        actor_type="user",
        action="organization.created",
        resource_type="organization",
        resource_id=org_id,
    )

    logger.info("Created organization %s (%s)", org.id, org.slug)
    return OrganizationResponse.model_validate(org)


@router.post(
    "/provider-connections/test",
    response_model=ProviderConnectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update a test-mode provider connection",
)
async def create_test_provider_connection(
    body: TestProviderConnectionRequest,
    ctx: TenantContext = Depends(require_scope("provider_connections:write")),
    db: AsyncSession = Depends(get_db),
) -> ProviderConnectionResponse:
    """Store a test-only provider configuration; credentials are encrypted at rest."""
    if not body.is_test_mode:
        raise HTTPException(status_code=422, detail="Only test-mode provider connections are supported.")
    if body.provider == "razorpay":
        if not body.key_id or not body.key_id.startswith("rzp_test_"):
            raise HTTPException(status_code=422, detail="Razorpay test connections require an rzp_test_* key ID.")
        if not body.key_secret or not body.webhook_secret:
            raise HTTPException(status_code=422, detail="Razorpay test connections require key and webhook secrets.")

    result = await db.execute(select(ProviderConnection).where(
        ProviderConnection.organization_id == ctx.organization_id,
        ProviderConnection.provider == body.provider,
    ))
    connection = result.scalar_one_or_none()
    if connection is None:
        connection = ProviderConnection(
            id=new_id(), organization_id=ctx.organization_id, provider=body.provider,
            display_name=body.display_name, is_test_mode=True, is_active=True,
        )
        db.add(connection)
    else:
        connection.display_name = body.display_name
        connection.is_active = True

    if body.key_secret:
        connection.encrypted_credentials = encrypt_credential(body.key_secret.get_secret_value())
    if body.webhook_secret:
        connection.encrypted_webhook_secret = encrypt_credential(body.webhook_secret.get_secret_value())
    connection.last_test_status = "configured"
    connection.last_tested_at = datetime.now(timezone.utc)
    await db.flush()

    from apps.api.app.core.audit import record_audit_event
    await record_audit_event(
        db=db, organization_id=ctx.organization_id, actor_id=ctx.actor_id, actor_type=ctx.actor_type,
        action="provider_connection.test_configured", resource_type="provider_connection",
        resource_id=connection.id, details={"provider": body.provider, "test_mode": True},
    )
    return ProviderConnectionResponse.model_validate(connection)


@router.post(
    "/auth/login",
    response_model=TokenResponse,
    summary="Login with email/password",
)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    result = await db.execute(
        select(User).where(User.email == str(body.email), User.is_active == True)  # noqa
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    user.last_login_at = datetime.now(timezone.utc)

    token = create_access_token(
        subject=user.id,
        extra_claims={"org_id": user.organization_id},
    )

    from apps.api.app.core.config import get_settings
    s = get_settings()
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=s.jwt_access_token_expire_minutes * 60,
        organization_id=user.organization_id,
    )


@router.post(
    "/auth/api-keys",
    response_model=ApiKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create API key",
)
async def create_api_key(
    body: CreateApiKeyRequest,
    ctx: TenantContext = Depends(require_scope("api_keys:write")),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyResponse:
    from apps.api.app.core.config import get_settings
    s = get_settings()

    full_key, key_hash = generate_api_key(test_mode=body.is_test_mode)
    prefix = s.api_key_test_prefix if body.is_test_mode else s.api_key_prefix

    api_key = ApiKey(
        id=new_id(),
        organization_id=ctx.organization_id,
        name=body.name,
        key_prefix=prefix,
        key_hash=key_hash,
        scopes=",".join(body.scopes),
        is_test_mode=body.is_test_mode,
        is_active=True,
    )
    db.add(api_key)
    await db.flush()

    resp = ApiKeyResponse.model_validate(api_key)
    resp.full_key = full_key  # Only shown once
    resp.scopes = body.scopes
    return resp


@router.get(
    "/organizations/me",
    response_model=OrganizationResponse,
    summary="Get current organization",
)
async def get_my_organization(
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> OrganizationResponse:
    result = await db.execute(
        select(Organization).where(Organization.id == ctx.organization_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return OrganizationResponse.model_validate(org)
