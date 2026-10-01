-- Additive factual sidecars in Factory only; no new event wire enums.
CREATE TABLE factory.decision_records_v1 (
  repository_id text NOT NULL,
  decision_id text NOT NULL CHECK (octet_length(decision_id) BETWEEN 1 AND 128),
  task_id uuid NOT NULL,
  run_id uuid NOT NULL,
  record_digest char(64) NOT NULL CHECK (record_digest ~ '^[0-9a-f]{64}$'),
  record jsonb NOT NULL CHECK (octet_length(record::text) <= 65536),
  supersedes text,
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (repository_id, decision_id),
  FOREIGN KEY (run_id,task_id) REFERENCES factory.runs(run_id,task_id) ON DELETE RESTRICT,
  FOREIGN KEY (repository_id,supersedes) REFERENCES factory.decision_records_v1(repository_id,decision_id) ON DELETE RESTRICT
);
CREATE INDEX decision_records_v1_task ON factory.decision_records_v1(task_id, created_at, decision_id);
REVOKE ALL ON factory.decision_records_v1 FROM PUBLIC;
GRANT SELECT, INSERT ON factory.decision_records_v1 TO factory_runtime;
-- UPDATE/DELETE are deliberately absent. Corrections append superseding records.
