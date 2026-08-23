CREATE INDEX IF NOT EXISTS trust_ci_jobs_lease_expiry_idx
    ON trust_ci_jobs (lease_expires_at)
    WHERE status IN ('leased', 'running');

CREATE INDEX IF NOT EXISTS trust_ci_jobs_terminal_finished_idx
    ON trust_ci_jobs (status, finished_at DESC)
    WHERE status IN ('passed', 'failed', 'cancelled', 'dead');

CREATE INDEX IF NOT EXISTS trust_ci_approvals_expiry_idx
    ON trust_ci_approvals (expires_at)
    WHERE expires_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS trust_ci_job_attempts_worker_idx
    ON trust_ci_job_attempts (worker_id, started_at DESC);

CREATE INDEX IF NOT EXISTS trust_ci_attestations_created_idx
    ON trust_ci_attestations (created_at DESC);
