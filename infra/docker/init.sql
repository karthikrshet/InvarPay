-- PayGuard AI — PostgreSQL initialization script
-- Enables extensions required by the application

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Row-level security will be configured per-table in migrations
