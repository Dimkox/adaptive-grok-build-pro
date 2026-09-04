CREATE TABLE factory.m0_authority_observations (
  observation_id uuid PRIMARY KEY,
  observed_at timestamptz NOT NULL,
  check_name text NOT NULL CHECK (check_name ~ '^adaptive-trust-ci/verified@[0-9a-f]{12}$'),
  exact_head_sha char(40) NOT NULL CHECK (exact_head_sha ~ '^[0-9a-f]{40}$'),
  issuer text NOT NULL,
  evidence_digest char(64) UNIQUE NOT NULL CHECK (evidence_digest ~ '^[0-9a-f]{64}$'),
  revoked_at timestamptz,
  UNIQUE (observed_at, check_name, exact_head_sha)
);

CREATE TABLE factory.m0_bootstrap_exceptions (
  exception_id text PRIMARY KEY,
  issuer text NOT NULL,
  scope text NOT NULL,
  expires_at timestamptz NOT NULL,
  approval_digest char(64) UNIQUE NOT NULL CHECK (approval_digest ~ '^[0-9a-f]{64}$'),
  revoked_at timestamptz
);

CREATE TABLE factory.command_results (
  idempotency_key char(64) PRIMARY KEY CHECK (idempotency_key ~ '^[0-9a-f]{64}$'),
  actor_id text NOT NULL,
  action text NOT NULL,
  request_digest char(64) NOT NULL CHECK (request_digest ~ '^[0-9a-f]{64}$'),
  correlation_id text NOT NULL,
  result jsonb NOT NULL CHECK (octet_length(result::text) <= 65536),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE factory.metric_counters (
  metric_name text NOT NULL,
  outcome text NOT NULL,
  value bigint NOT NULL DEFAULT 0 CHECK (value >= 0),
  PRIMARY KEY (metric_name, outcome)
);

ALTER TABLE factory.tasks
  ADD COLUMN wall_limit_seconds integer NOT NULL DEFAULT 14400 CHECK (wall_limit_seconds BETWEEN 0 AND 14400),
  ADD COLUMN wall_reserved_seconds bigint NOT NULL DEFAULT 0 CHECK (wall_reserved_seconds >= 0);
UPDATE factory.tasks SET wall_limit_seconds=LEAST(14400, EXTRACT(EPOCH FROM (deadline_at-accepted_at))::integer);

ALTER TABLE factory.capacity_allocations
  ADD CONSTRAINT capacity_allocations_run_task_fk FOREIGN KEY (run_id,task_id)
  REFERENCES factory.runs(run_id,task_id) ON DELETE RESTRICT;
ALTER TABLE factory.budget_reservations
  ADD CONSTRAINT budget_reservations_run_task_fk FOREIGN KEY (run_id,task_id)
  REFERENCES factory.runs(run_id,task_id) ON DELETE RESTRICT;
ALTER TABLE factory.usage_observations
  ADD CONSTRAINT usage_observations_run_task_fk FOREIGN KEY (run_id,task_id)
  REFERENCES factory.runs(run_id,task_id) ON DELETE RESTRICT;
ALTER TABLE factory.audit_log
  ADD CONSTRAINT audit_log_run_fk FOREIGN KEY (run_id) REFERENCES factory.runs(run_id) ON DELETE RESTRICT;

CREATE INDEX tasks_repository_keyset ON factory.tasks(repository_id,task_id);
CREATE INDEX runs_reconcile_keyset ON factory.runs(task_id,lease_expires_at) WHERE released_at IS NULL;

REVOKE UPDATE ON factory.accepted_intents, factory.task_events, factory.usage_observations,
  factory.kill_switches, factory.audit_log FROM factory_runtime;
REVOKE UPDATE ON factory.runs, factory.attempts, factory.capacity_allocations,
  factory.budget_reservations, factory.tasks FROM factory_runtime;
GRANT UPDATE (state,current_run_id,current_fence,accounting_blocked,cost_reserved_micros,
  cost_observed_micros,tokens_reserved,tokens_observed,wall_reserved_seconds,repair_count,
  updated_at,terminal_at) ON factory.tasks TO factory_runtime;
GRANT UPDATE (lease_expires_at,state,released_at) ON factory.runs TO factory_runtime;
GRANT UPDATE (failure_class,failure_code,failure_digest,finished_at) ON factory.attempts TO factory_runtime;
GRANT UPDATE (released_at) ON factory.capacity_allocations, factory.budget_reservations TO factory_runtime;
GRANT SELECT ON factory.m0_authority_observations, factory.m0_bootstrap_exceptions TO factory_runtime;
GRANT SELECT ON factory.schema_migrations TO factory_runtime;
GRANT SELECT, INSERT ON factory.command_results TO factory_runtime;
GRANT SELECT, INSERT, UPDATE ON factory.metric_counters TO factory_runtime;
