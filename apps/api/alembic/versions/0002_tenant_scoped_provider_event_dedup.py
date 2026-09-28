"""Scope provider event inbox deduplication to a tenant.

Revision ID: 0002_provider_event_tenant_dedup
Revises: 0001_initial
"""
from alembic import op


revision = "0002_provider_event_tenant_dedup"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("uq_provider_event_dedup", "provider_events", type_="unique")
    op.create_unique_constraint(
        "uq_provider_event_dedup", "provider_events",
        ["organization_id", "provider", "provider_event_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_provider_event_dedup", "provider_events", type_="unique")
    op.create_unique_constraint(
        "uq_provider_event_dedup", "provider_events", ["provider", "provider_event_id"]
    )
