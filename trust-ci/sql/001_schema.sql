CREATE TABLE IF NOT EXISTS trust_ci_jobs (
    job_id uuid PRIMARY KEY,
    repository text NOT NULL,
    pr_number bigint NOT NULL CHECK (pr_number > 0),
    base_sha char(40) NOT NULL CHECK (base_sha ~ '^[0-9a-f]{40}$'),
    head_sha char(40) NOT NULL CHECK (head_sha ~ '^[0-9a-f]{40}$'),
    head_ref text NOT NULL CHECK (length(head_ref) > 0),
    base_ref text NOT NULL CHECK (length(base_ref) > 0),
    pipeline text NOT NULL CHECK (length(pipeline) > 0),
    policy_digest char(64) NOT NULL CHECK (policy_digest ~ '^[0-9a-f]{64}$'),
    idempotency_key char(64) NOT NULL UNIQUE CHECK (idempotency_key ~ '^[0-9a-f]{64}$'),
    status text NOT NULL CHECK (status IN (
        'queued', 'leased', 'running', 'passed', 'failed',
        'needs_approval', 'cancelled', 'dead'
    )),
    attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    max_attempts integer NOT NULL CHECK (max_attempts BETWEEN 1 AND 20),
    lease_owner text,
    lease_expires_at timestamptz,
    failure_code text,
    result jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    started_at timestamptz,
    finished_at timestamptz
);

CREATE INDEX IF NOT EXISTS trust_ci_jobs_queue_idx
    ON trust_ci_jobs (status, created_at)
    WHERE status IN ('queued', 'leased', 'running');
CREATE INDEX IF NOT EXISTS trust_ci_jobs_pr_idx
    ON trust_ci_jobs (repository, pr_number, created_at DESC);
CREATE INDEX IF NOT EXISTS trust_ci_jobs_head_idx
    ON trust_ci_jobs (repository, head_sha, created_at DESC);

CREATE TABLE IF NOT EXISTS trust_ci_job_attempts (
    job_id uuid NOT NULL REFERENCES trust_ci_jobs(job_id) ON DELETE CASCADE,
    attempt_no integer NOT NULL CHECK (attempt_no > 0),
    worker_id text NOT NULL CHECK (length(worker_id) > 0),
    started_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    status text NOT NULL DEFAULT 'leased',
    error text,
    result jsonb NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (job_id, attempt_no)
);

CREATE TABLE IF NOT EXISTS trust_ci_approvals (
    approval_id uuid PRIMARY KEY,
    nonce text NOT NULL UNIQUE CHECK (length(nonce) >= 16),
    repository text NOT NULL,
    pr_number bigint NOT NULL CHECK (pr_number > 0),
    base_sha char(40) NOT NULL CHECK (base_sha ~ '^[0-9a-f]{40}$'),
    head_sha char(40) NOT NULL CHECK (head_sha ~ '^[0-9a-f]{40}$'),
    policy_digest char(64) NOT NULL CHECK (policy_digest ~ '^[0-9a-f]{64}$'),
    scope text NOT NULL CHECK (length(scope) > 0),
    actor text NOT NULL CHECK (length(actor) > 0),
    key_id text NOT NULL CHECK (length(key_id) > 0),
    reason text NOT NULL CHECK (length(reason) > 0),
    issued_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL,
    payload jsonb NOT NULL,
    signature text NOT NULL CHECK (length(signature) > 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (expires_at > issued_at)
);

CREATE INDEX IF NOT EXISTS trust_ci_approvals_lookup_idx
    ON trust_ci_approvals (
        repository, pr_number, base_sha, head_sha,
        policy_digest, scope, expires_at DESC
    );

CREATE TABLE IF NOT EXISTS trust_ci_attestations (
    attestation_id uuid PRIMARY KEY,
    job_id uuid NOT NULL UNIQUE REFERENCES trust_ci_jobs(job_id) ON DELETE CASCADE,
    repository text NOT NULL,
    head_sha char(40) NOT NULL CHECK (head_sha ~ '^[0-9a-f]{40}$'),
    status text NOT NULL CHECK (status IN ('passed', 'failed')),
    key_id text NOT NULL CHECK (length(key_id) > 0),
    payload jsonb NOT NULL,
    signature text NOT NULL CHECK (length(signature) > 0),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS trust_ci_events (
    event_id bigserial PRIMARY KEY,
    job_id uuid REFERENCES trust_ci_jobs(job_id) ON DELETE SET NULL,
    event_type text NOT NULL CHECK (length(event_type) > 0),
    actor text,
    details jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS trust_ci_events_job_idx
    ON trust_ci_events (job_id, created_at);

CREATE OR REPLACE FUNCTION trust_ci_claim_job(
    p_worker_id text,
    p_lease_seconds integer
)
RETURNS SETOF trust_ci_jobs
LANGUAGE plpgsql
AS $$
BEGIN
    IF p_worker_id IS NULL OR length(trim(p_worker_id)) = 0 THEN
        RAISE EXCEPTION 'worker id is required';
    END IF;
    IF p_lease_seconds < 1 THEN
        RAISE EXCEPTION 'lease seconds must be positive';
    END IF;

    UPDATE trust_ci_jobs
    SET status = 'dead',
        failure_code = 'attempts-exhausted-after-worker-loss',
        lease_owner = NULL,
        lease_expires_at = NULL,
        updated_at = now(),
        finished_at = now()
    WHERE status IN ('leased', 'running')
      AND lease_expires_at < now()
      AND attempts >= max_attempts;

    RETURN QUERY
    WITH candidate AS (
        SELECT job_id
        FROM trust_ci_jobs
        WHERE attempts < max_attempts
          AND (
              status = 'queued'
              OR (status IN ('leased', 'running') AND lease_expires_at < now())
          )
        ORDER BY created_at
        FOR UPDATE SKIP LOCKED
        LIMIT 1
    ), claimed AS (
        UPDATE trust_ci_jobs AS jobs
        SET status = 'leased',
            attempts = jobs.attempts + 1,
            lease_owner = p_worker_id,
            lease_expires_at = now() + make_interval(secs => p_lease_seconds),
            started_at = COALESCE(jobs.started_at, now()),
            updated_at = now()
        FROM candidate
        WHERE jobs.job_id = candidate.job_id
        RETURNING jobs.*
    ), attempt AS (
        INSERT INTO trust_ci_job_attempts (job_id, attempt_no, worker_id, status)
        SELECT job_id, attempts, p_worker_id, 'leased' FROM claimed
        ON CONFLICT (job_id, attempt_no) DO NOTHING
    )
    SELECT * FROM claimed;
END;
$$;
