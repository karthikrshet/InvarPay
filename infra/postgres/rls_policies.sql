-- PayGuard AI — Phase 7: PostgreSQL Row Level Security (RLS)
-- Enforces tenant isolation at the database level as a defense-in-depth layer.
-- Even if application-level queries miss the organization_id filter,
-- RLS will prevent cross-tenant data access.
--
-- Usage:
--   psql -d payguard -f infra/postgres/rls_policies.sql
--
-- NOTE: Application must SET LOCAL app.current_org_id = '<org_id>'
--       at the start of each session/transaction.
--       This is done by the database session middleware.
--
-- IMPORTANT: Run AFTER migrations (0001_initial_schema.py)

-- Enable RLS on all tenant tables
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE payment_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE provider_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE provider_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE settlements ENABLE ROW LEVEL SECURITY;
ALTER TABLE investigations ENABLE ROW LEVEL SECURITY;
ALTER TABLE risk_assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE carts ENABLE ROW LEVEL SECURITY;
ALTER TABLE checkout_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE outbox_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE idempotency_records ENABLE ROW LEVEL SECURITY;

-- Helper function to get current org from session variable
CREATE OR REPLACE FUNCTION current_org_id() RETURNS text AS $$
  SELECT current_setting('app.current_org_id', true);
$$ LANGUAGE SQL STABLE;

-- Policy template: organization_id must match session variable
-- (Applied to each table — superuser bypasses for migrations)

CREATE POLICY org_isolation ON orders
  USING (organization_id = current_org_id())
  WITH CHECK (organization_id = current_org_id());

CREATE POLICY org_isolation ON payment_attempts
  USING (organization_id = current_org_id())
  WITH CHECK (organization_id = current_org_id());

CREATE POLICY org_isolation ON provider_events
  USING (organization_id = current_org_id())
  WITH CHECK (organization_id = current_org_id());

CREATE POLICY org_isolation ON audit_events
  USING (organization_id = current_org_id())
  WITH CHECK (organization_id = current_org_id());

CREATE POLICY org_isolation ON api_keys
  USING (organization_id = current_org_id())
  WITH CHECK (organization_id = current_org_id());

CREATE POLICY org_isolation ON provider_connections
  USING (organization_id = current_org_id())
  WITH CHECK (organization_id = current_org_id());

CREATE POLICY org_isolation ON customers
  USING (organization_id = current_org_id())
  WITH CHECK (organization_id = current_org_id());

CREATE POLICY org_isolation ON invoices
  USING (organization_id = current_org_id())
  WITH CHECK (organization_id = current_org_id());

CREATE POLICY org_isolation ON settlements
  USING (organization_id = current_org_id())
  WITH CHECK (organization_id = current_org_id());

CREATE POLICY org_isolation ON investigations
  USING (organization_id = current_org_id())
  WITH CHECK (organization_id = current_org_id());

CREATE POLICY org_isolation ON risk_assessments
  USING (organization_id = current_org_id())
  WITH CHECK (organization_id = current_org_id());

CREATE POLICY org_isolation ON carts
  USING (organization_id = current_org_id())
  WITH CHECK (organization_id = current_org_id());

CREATE POLICY org_isolation ON checkout_sessions
  USING (organization_id = current_org_id())
  WITH CHECK (organization_id = current_org_id());

CREATE POLICY org_isolation ON outbox_events
  USING (organization_id = current_org_id())
  WITH CHECK (organization_id = current_org_id());

CREATE POLICY org_isolation ON idempotency_records
  USING (organization_id = current_org_id())
  WITH CHECK (organization_id = current_org_id());

-- Grant: application role uses RLS, superuser bypasses (for migrations)
-- Run: CREATE ROLE payguard_app LOGIN PASSWORD '...';
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO payguard_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE ON TABLES TO payguard_app;

-- Verify RLS is enabled
SELECT tablename, rowsecurity FROM pg_tables
WHERE schemaname = 'public' AND rowsecurity = true;
