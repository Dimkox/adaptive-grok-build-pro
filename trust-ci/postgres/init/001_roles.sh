#!/usr/bin/env bash
set -Eeuo pipefail

for name in \
  TRUST_CI_API_DB_PASSWORD \
  TRUST_CI_WORKER_DB_PASSWORD \
  TRUST_CI_MIGRATOR_DB_PASSWORD \
  TRUST_CI_BACKUP_DB_PASSWORD \
  TRUST_CI_DEPLOYER_DB_PASSWORD; do
  [[ -n "${!name:-}" ]] || {
    printf 'required PostgreSQL role password is missing: %s\n' "$name" >&2
    exit 1
  }
done

psql \
  --set=ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" <<'SQL'
\getenv api_pw TRUST_CI_API_DB_PASSWORD
\getenv worker_pw TRUST_CI_WORKER_DB_PASSWORD
\getenv migrator_pw TRUST_CI_MIGRATOR_DB_PASSWORD
\getenv backup_pw TRUST_CI_BACKUP_DB_PASSWORD
\getenv deployer_pw TRUST_CI_DEPLOYER_DB_PASSWORD

SELECT format('CREATE ROLE trust_ci_api LOGIN PASSWORD %L', :'api_pw')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'trust_ci_api')
\gexec
SELECT format('CREATE ROLE trust_ci_worker LOGIN PASSWORD %L', :'worker_pw')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'trust_ci_worker')
\gexec
SELECT format('CREATE ROLE trust_ci_migrator LOGIN PASSWORD %L', :'migrator_pw')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'trust_ci_migrator')
\gexec
SELECT format('CREATE ROLE trust_ci_backup LOGIN PASSWORD %L', :'backup_pw')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'trust_ci_backup')
\gexec
SELECT format('CREATE ROLE trust_ci_deployer LOGIN PASSWORD %L', :'deployer_pw')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'trust_ci_deployer')
\gexec

ALTER ROLE trust_ci_api PASSWORD :'api_pw';
ALTER ROLE trust_ci_worker PASSWORD :'worker_pw';
ALTER ROLE trust_ci_migrator PASSWORD :'migrator_pw';
ALTER ROLE trust_ci_backup PASSWORD :'backup_pw';
ALTER ROLE trust_ci_deployer PASSWORD :'deployer_pw';

ALTER ROLE trust_ci_api NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOINHERIT CONNECTION LIMIT 20;
ALTER ROLE trust_ci_worker NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOINHERIT CONNECTION LIMIT 50;
ALTER ROLE trust_ci_migrator NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOINHERIT CONNECTION LIMIT 3;
ALTER ROLE trust_ci_backup NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOINHERIT CONNECTION LIMIT 2;
ALTER ROLE trust_ci_deployer NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOINHERIT CONNECTION LIMIT 5;

ALTER ROLE trust_ci_api SET statement_timeout = '30s';
ALTER ROLE trust_ci_api SET idle_in_transaction_session_timeout = '30s';
ALTER ROLE trust_ci_worker SET statement_timeout = '15min';
ALTER ROLE trust_ci_worker SET idle_in_transaction_session_timeout = '2min';
ALTER ROLE trust_ci_migrator SET statement_timeout = '0';
ALTER ROLE trust_ci_backup SET statement_timeout = '0';
ALTER ROLE trust_ci_deployer SET statement_timeout = '30s';
ALTER ROLE trust_ci_deployer SET idle_in_transaction_session_timeout = '30s';

REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT CREATE ON SCHEMA public TO trust_ci_migrator;
GRANT USAGE ON SCHEMA public TO trust_ci_api, trust_ci_worker, trust_ci_backup;
GRANT USAGE ON SCHEMA public TO trust_ci_deployer;

SELECT format('REVOKE CONNECT ON DATABASE %I FROM PUBLIC', current_database())
\gexec
SELECT format('GRANT CONNECT ON DATABASE %I TO trust_ci_api, trust_ci_worker, trust_ci_migrator, trust_ci_backup, trust_ci_deployer', current_database())
\gexec
SQL
