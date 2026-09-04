CREATE TABLE factory.lease_sequences (
  task_id uuid PRIMARY KEY REFERENCES factory.tasks(task_id) ON DELETE RESTRICT,
  last_fence bigint NOT NULL DEFAULT 0 CHECK (last_fence >= 0)
);

CREATE TABLE factory.runs (
  run_id uuid PRIMARY KEY,
  task_id uuid NOT NULL REFERENCES factory.tasks(task_id) ON DELETE RESTRICT,
  owner_id text NOT NULL,
  role text NOT NULL CHECK (role IN ('reader','writer')),
  packet_digest char(64) NOT NULL CHECK (packet_digest ~ '^[0-9a-f]{64}$'),
  fence bigint NOT NULL CHECK (fence > 0),
  state text NOT NULL CHECK (state IN ('leased','released','failed','expired','completed')),
  lease_expires_at timestamptz NOT NULL,
  deadline_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  released_at timestamptz,
  UNIQUE (task_id, fence),
  UNIQUE (run_id, task_id)
);
ALTER TABLE factory.tasks ADD CONSTRAINT tasks_current_run_fk FOREIGN KEY (current_run_id, task_id) REFERENCES factory.runs(run_id, task_id) DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX runs_expiry ON factory.runs(lease_expires_at, task_id) WHERE released_at IS NULL;

CREATE TABLE factory.attempts (
  attempt_id uuid PRIMARY KEY,
  task_id uuid NOT NULL,
  run_id uuid NOT NULL,
  attempt_no integer NOT NULL CHECK (attempt_no BETWEEN 1 AND 3),
  failure_class text,
  failure_code text,
  failure_digest char(64),
  created_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz,
  UNIQUE (task_id, attempt_no),
  FOREIGN KEY (run_id, task_id) REFERENCES factory.runs(run_id, task_id) ON DELETE RESTRICT
);

CREATE TABLE factory.capacity_counters (
  scope_key text PRIMARY KEY,
  active_count integer NOT NULL DEFAULT 0 CHECK (active_count >= 0),
  ceiling integer NOT NULL CHECK (ceiling > 0 AND active_count <= ceiling)
);
INSERT INTO factory.capacity_counters(scope_key, ceiling) VALUES ('global:reader',20),('global:writer',1) ON CONFLICT DO NOTHING;

CREATE TABLE factory.capacity_allocations (
  allocation_id uuid PRIMARY KEY,
  run_id uuid NOT NULL UNIQUE REFERENCES factory.runs(run_id) ON DELETE RESTRICT,
  task_id uuid NOT NULL REFERENCES factory.tasks(task_id) ON DELETE RESTRICT,
  repository_id text NOT NULL,
  role text NOT NULL CHECK (role IN ('reader','writer')),
  acquired_at timestamptz NOT NULL DEFAULT now(),
  released_at timestamptz
);
CREATE UNIQUE INDEX capacity_one_live_writer ON factory.capacity_allocations(role) WHERE role = 'writer' AND released_at IS NULL;
CREATE INDEX capacity_live_repo_role ON factory.capacity_allocations(repository_id, role) WHERE released_at IS NULL;

-- Claims use: SELECT ... FROM factory.tasks ... FOR UPDATE SKIP LOCKED.
