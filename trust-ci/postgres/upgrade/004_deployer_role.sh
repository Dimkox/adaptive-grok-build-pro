#!/usr/bin/env bash
set -Eeuo pipefail

: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
: "${TRUST_CI_DEPLOYER_DB_PASSWORD:?TRUST_CI_DEPLOYER_DB_PASSWORD is required}"

export PGHOST="${PGHOST:-postgres}"
export PGPORT="${PGPORT:-5432}"
export PGUSER="$POSTGRES_USER"
export PGDATABASE="$POSTGRES_DB"
export PGPASSWORD=${POSTGRES_PASSWORD}

psql --set=ON_ERROR_STOP=1 <<'SQL'
\getenv deployer_pw TRUST_CI_DEPLOYER_DB_PASSWORD
SELECT format('CREATE ROLE trust_ci_deployer LOGIN PASSWORD %L', :'deployer_pw')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'trust_ci_deployer')
\gexec
ALTER ROLE trust_ci_deployer LOGIN PASSWORD :'deployer_pw'
  NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS NOINHERIT CONNECTION LIMIT 5;
DO $block$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM pg_auth_members memberships
    JOIN pg_roles member_role ON member_role.oid = memberships.member
    WHERE member_role.rolname = 'trust_ci_deployer'
  ) THEN
    RAISE EXCEPTION 'trust_ci_deployer must not be a member of any role';
  END IF;
END
$block$;
ALTER ROLE trust_ci_deployer SET statement_timeout = '30s';
ALTER ROLE trust_ci_deployer SET idle_in_transaction_session_timeout = '30s';
GRANT USAGE ON SCHEMA public TO trust_ci_deployer;
SELECT format('GRANT CONNECT ON DATABASE %I TO trust_ci_deployer', current_database())
\gexec
SQL
