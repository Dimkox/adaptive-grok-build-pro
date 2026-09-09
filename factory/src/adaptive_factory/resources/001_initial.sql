DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'factory_migrator') THEN CREATE ROLE factory_migrator NOLOGIN NOINHERIT; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'factory_runtime') THEN CREATE ROLE factory_runtime NOLOGIN NOINHERIT; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'factory_audit_reader') THEN CREATE ROLE factory_audit_reader NOLOGIN NOINHERIT; END IF;
END $$;

CREATE SCHEMA IF NOT EXISTS factory;
REVOKE ALL ON SCHEMA factory FROM PUBLIC;

CREATE TABLE IF NOT EXISTS factory.intake_identities (
  repository_id text NOT NULL CHECK (octet_length(repository_id) BETWEEN 1 AND 128),
  source_type text NOT NULL CHECK (source_type IN ('manual','api','github_issue_projection')),
  source_id text NOT NULL CHECK (octet_length(source_id) BETWEEN 1 AND 128),
  PRIMARY KEY (repository_id, source_type, source_id)
);

CREATE TABLE factory.accepted_intents (
  intent_id uuid PRIMARY KEY,
  intent_digest char(64) UNIQUE NOT NULL CHECK (intent_digest ~ '^[0-9a-f]{64}$'),
  idempotency_key char(64) UNIQUE NOT NULL CHECK (idempotency_key ~ '^[0-9a-f]{64}$'),
  repository_id text NOT NULL,
  source_type text NOT NULL,
  source_id text NOT NULL,
  source_digest char(64) NOT NULL CHECK (source_digest ~ '^[0-9a-f]{64}$'),
  exact_base_sha char(40) NOT NULL CHECK (exact_base_sha ~ '^[0-9a-f]{40}$'),
  spec_digest char(64) NOT NULL CHECK (spec_digest ~ '^[0-9a-f]{64}$'),
  architecture_digest char(64) NOT NULL CHECK (architecture_digest ~ '^[0-9a-f]{64}$'),
  governance_digest char(64) NOT NULL CHECK (governance_digest ~ '^[0-9a-f]{64}$'),
  policy_digest char(64) NOT NULL CHECK (policy_digest ~ '^[0-9a-f]{64}$'),
  body jsonb NOT NULL CHECK (octet_length(body::text) <= 1048576),
  accepted_at timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (repository_id, source_type, source_id) REFERENCES factory.intake_identities(repository_id, source_type, source_id) ON DELETE RESTRICT
);

CREATE TABLE factory.tasks (
  task_id uuid PRIMARY KEY,
  intent_id uuid UNIQUE NOT NULL REFERENCES factory.accepted_intents(intent_id) ON DELETE RESTRICT,
  repository_id text NOT NULL,
  source_type text NOT NULL,
  source_id text NOT NULL,
  state text NOT NULL CHECK (state IN ('inbox','triaged','waiting_design_approval','queued','leased','analyzing','implementing','verifying','reviewing','ready_for_human','retry','needs_human','dead','cancelled','superseded')),
  generation integer NOT NULL CHECK (generation > 0),
  packet_digest char(64) NOT NULL CHECK (packet_digest ~ '^[0-9a-f]{64}$'),
  current_run_id uuid,
  current_fence bigint CHECK (current_fence IS NULL OR current_fence > 0),
  accepted_at timestamptz NOT NULL DEFAULT now(),
  deadline_at timestamptz NOT NULL,
  cost_limit_micros bigint NOT NULL CHECK (cost_limit_micros BETWEEN 0 AND 25000000),
  token_limit bigint NOT NULL CHECK (token_limit BETWEEN 0 AND 2000000),
  output_limit_bytes bigint NOT NULL CHECK (output_limit_bytes BETWEEN 0 AND 10000000),
  event_limit bigint NOT NULL CHECK (event_limit BETWEEN 0 AND 100000),
  cost_reserved_micros bigint NOT NULL DEFAULT 0 CHECK (cost_reserved_micros >= 0),
  cost_observed_micros bigint NOT NULL DEFAULT 0 CHECK (cost_observed_micros >= 0),
  tokens_reserved bigint NOT NULL DEFAULT 0 CHECK (tokens_reserved >= 0),
  tokens_observed bigint NOT NULL DEFAULT 0 CHECK (tokens_observed >= 0),
  accounting_blocked boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  terminal_at timestamptz,
  CHECK (deadline_at <= accepted_at + interval '4 hours'),
  UNIQUE (repository_id, source_type, source_id, generation)
);
CREATE UNIQUE INDEX tasks_one_active_identity ON factory.tasks(repository_id, source_type, source_id) WHERE state NOT IN ('ready_for_human','dead','cancelled','superseded');
CREATE INDEX tasks_claim_queue ON factory.tasks(created_at, task_id) WHERE state IN ('queued','retry');
CREATE INDEX tasks_list ON factory.tasks(repository_id, created_at, task_id);

CREATE TABLE factory.task_events (
  event_id uuid PRIMARY KEY,
  task_id uuid NOT NULL REFERENCES factory.tasks(task_id) ON DELETE RESTRICT,
  event_sequence bigint NOT NULL CHECK (event_sequence > 0),
  idempotency_key char(64) NOT NULL CHECK (idempotency_key ~ '^[0-9a-f]{64}$'),
  actor_id text NOT NULL,
  action text NOT NULL,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (octet_length(metadata::text) <= 65536),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (task_id, event_sequence),
  UNIQUE (task_id, idempotency_key)
);

CREATE TABLE factory.audit_heads (
  task_id uuid PRIMARY KEY REFERENCES factory.tasks(task_id) ON DELETE RESTRICT,
  last_digest char(64) NOT NULL CHECK (last_digest ~ '^[0-9a-f]{64}$')
);

CREATE TABLE factory.audit_log (
  audit_id bigserial PRIMARY KEY,
  task_id uuid NOT NULL REFERENCES factory.tasks(task_id) ON DELETE RESTRICT,
  run_id uuid,
  previous_digest char(64) NOT NULL CHECK (previous_digest ~ '^[0-9a-f]{64}$'),
  current_digest char(64) NOT NULL UNIQUE CHECK (current_digest ~ '^[0-9a-f]{64}$'),
  actor_id text NOT NULL,
  action text NOT NULL,
  resource text NOT NULL,
  reason text NOT NULL,
  correlation_id text NOT NULL,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (octet_length(metadata::text) <= 65536),
  created_at timestamptz NOT NULL DEFAULT now()
);
