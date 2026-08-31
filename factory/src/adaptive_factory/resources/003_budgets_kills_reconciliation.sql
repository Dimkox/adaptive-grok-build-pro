CREATE TABLE factory.budget_reservations (
  reservation_id uuid PRIMARY KEY,
  task_id uuid NOT NULL REFERENCES factory.tasks(task_id) ON DELETE RESTRICT,
  run_id uuid NOT NULL REFERENCES factory.runs(run_id) ON DELETE RESTRICT,
  idempotency_key char(64) UNIQUE NOT NULL CHECK (idempotency_key ~ '^[0-9a-f]{64}$'),
  cost_usd_micros bigint NOT NULL CHECK (cost_usd_micros >= 0),
  token_units bigint NOT NULL CHECK (token_units >= 0),
  wall_seconds integer NOT NULL CHECK (wall_seconds >= 0),
  reason_digest char(64) NOT NULL CHECK (reason_digest ~ '^[0-9a-f]{64}$'),
  created_at timestamptz NOT NULL DEFAULT now(),
  released_at timestamptz
);

CREATE TABLE factory.usage_observations (
  observation_id uuid PRIMARY KEY,
  task_id uuid NOT NULL REFERENCES factory.tasks(task_id) ON DELETE RESTRICT,
  run_id uuid NOT NULL REFERENCES factory.runs(run_id) ON DELETE RESTRICT,
  provider_call_id text NOT NULL,
  price_table_digest char(64) NOT NULL CHECK (price_table_digest ~ '^[0-9a-f]{64}$'),
  cost_usd_micros bigint NOT NULL CHECK (cost_usd_micros >= 0),
  token_units bigint NOT NULL CHECK (token_units >= 0),
  output_bytes bigint NOT NULL CHECK (output_bytes >= 0),
  observed_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (run_id, provider_call_id)
);

CREATE TABLE factory.kill_switches (
  switch_id uuid PRIMARY KEY,
  scope_key text NOT NULL,
  enabled boolean NOT NULL,
  actor_id text NOT NULL,
  reason text NOT NULL,
  idempotency_key char(64) UNIQUE NOT NULL CHECK (idempotency_key ~ '^[0-9a-f]{64}$'),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX kill_current ON factory.kill_switches(scope_key, created_at DESC);

CREATE TABLE factory.reconciliation_runs (
  reconciliation_id uuid PRIMARY KEY,
  cursor_task_id uuid,
  status text NOT NULL CHECK (status IN ('running','completed','failed')),
  candidates integer NOT NULL DEFAULT 0 CHECK (candidates BETWEEN 0 AND 100),
  repaired integer NOT NULL DEFAULT 0 CHECK (repaired BETWEEN 0 AND candidates),
  started_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz
);

REVOKE ALL ON ALL TABLES IN SCHEMA factory FROM PUBLIC;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA factory FROM PUBLIC;
GRANT USAGE ON SCHEMA factory TO factory_runtime, factory_audit_reader;
GRANT SELECT, INSERT, UPDATE ON factory.intake_identities, factory.accepted_intents, factory.tasks, factory.task_events, factory.audit_heads, factory.lease_sequences, factory.runs, factory.attempts, factory.capacity_counters, factory.capacity_allocations, factory.budget_reservations, factory.usage_observations, factory.kill_switches, factory.reconciliation_runs TO factory_runtime;
GRANT INSERT, SELECT ON factory.audit_log TO factory_runtime;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA factory TO factory_runtime;
GRANT SELECT ON factory.tasks, factory.task_events, factory.audit_log, factory.runs, factory.attempts, factory.reconciliation_runs TO factory_audit_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA factory REVOKE ALL ON TABLES FROM PUBLIC;
ALTER DEFAULT PRIVILEGES IN SCHEMA factory REVOKE ALL ON SEQUENCES FROM PUBLIC;
ALTER ROLE factory_runtime SET search_path = factory, pg_catalog;
ALTER ROLE factory_audit_reader SET search_path = factory, pg_catalog;
