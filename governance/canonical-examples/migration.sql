ALTER TABLE task_runs
    ADD COLUMN IF NOT EXISTS correlation_id text;

CREATE INDEX CONCURRENTLY IF NOT EXISTS task_runs_correlation_id_idx
    ON task_runs (correlation_id);
