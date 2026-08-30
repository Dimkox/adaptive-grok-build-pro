CREATE TABLE trust_ci_merge_facts (
    merge_fact_id uuid PRIMARY KEY,
    delivery_id text NOT NULL UNIQUE
        CHECK (octet_length(delivery_id) BETWEEN 1 AND 128 AND delivery_id !~ '[[:cntrl:]]'),
    payload_sha256 char(64) NOT NULL
        CHECK (payload_sha256 ~ '^[0-9a-f]{64}$'),
    repository_id bigint NOT NULL CHECK (repository_id > 0),
    repository text NOT NULL
        CHECK (repository ~ '^[a-z0-9][a-z0-9._-]{0,99}/[a-z0-9][a-z0-9._-]{0,99}$'),
    installation_id bigint NOT NULL CHECK (installation_id > 0),
    pr_number bigint NOT NULL CHECK (pr_number > 0),
    head_sha char(40) NOT NULL CHECK (head_sha ~ '^[0-9a-f]{40}$'),
    base_sha char(40) NOT NULL CHECK (base_sha ~ '^[0-9a-f]{40}$'),
    protected_ref text NOT NULL
        CHECK (octet_length(protected_ref) BETWEEN 12 AND 255 AND protected_ref LIKE 'refs/heads/%'),
    merged_commit_sha char(40) NOT NULL CHECK (merged_commit_sha ~ '^[0-9a-f]{40}$'),
    merged_at timestamptz NOT NULL,
    received_at timestamptz NOT NULL,
    processing_status text NOT NULL DEFAULT 'pending'
        CHECK (processing_status IN ('pending', 'leased', 'completed', 'dead')),
    processing_attempt integer NOT NULL DEFAULT 0 CHECK (processing_attempt BETWEEN 0 AND 20),
    claim_id uuid UNIQUE,
    lease_owner text,
    lease_expires_at timestamptz,
    next_attempt_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    last_error text CHECK (last_error IS NULL OR octet_length(last_error) <= 512),
    processed_at timestamptz,
    CHECK (
        (processing_status = 'leased' AND claim_id IS NOT NULL
            AND lease_owner IS NOT NULL AND lease_expires_at IS NOT NULL)
        OR
        (processing_status <> 'leased' AND claim_id IS NULL
            AND lease_owner IS NULL AND lease_expires_at IS NULL)
    )
);

CREATE INDEX trust_ci_merge_facts_pending_idx
    ON trust_ci_merge_facts (processing_status, next_attempt_at, received_at, merge_fact_id)
    WHERE processing_status IN ('pending', 'leased');
CREATE INDEX trust_ci_merge_facts_exact_idx
    ON trust_ci_merge_facts (repository, protected_ref, merged_commit_sha, pr_number);

CREATE TABLE trust_ci_reconciliation_watermarks (
    repository text PRIMARY KEY
        CHECK (repository ~ '^[a-z0-9][a-z0-9._-]{0,99}/[a-z0-9][a-z0-9._-]{0,99}$'),
    updated_at timestamptz NOT NULL,
    pr_number bigint NOT NULL CHECK (pr_number >= 0),
    saved_at timestamptz NOT NULL
);

CREATE TABLE trust_ci_active_policy (
    singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
    policy_epoch char(64) NOT NULL CHECK (policy_epoch ~ '^[0-9a-f]{64}$'),
    activated_at timestamptz NOT NULL DEFAULT statement_timestamp()
);

CREATE TABLE trust_ci_protected_branch_evidence (
    source_attestation_id uuid PRIMARY KEY,
    merge_fact_id uuid NOT NULL
        REFERENCES trust_ci_merge_facts(merge_fact_id) ON DELETE RESTRICT,
    repository text NOT NULL
        CHECK (repository ~ '^[a-z0-9][a-z0-9._-]{0,99}/[a-z0-9][a-z0-9._-]{0,99}$'),
    protected_ref text NOT NULL
        CHECK (octet_length(protected_ref) BETWEEN 12 AND 255 AND protected_ref LIKE 'refs/heads/%'),
    merged_commit_sha char(40) NOT NULL CHECK (merged_commit_sha ~ '^[0-9a-f]{40}$'),
    policy_epoch char(64) NOT NULL CHECK (policy_epoch ~ '^[0-9a-f]{64}$'),
    runner_digest char(64) NOT NULL CHECK (runner_digest ~ '^[0-9a-f]{64}$'),
    holdout_digest char(64) NOT NULL CHECK (holdout_digest ~ '^[0-9a-f]{64}$'),
    image_digest char(64) NOT NULL CHECK (image_digest ~ '^[0-9a-f]{64}$'),
    artifact_sha256 char(64) NOT NULL CHECK (artifact_sha256 ~ '^[0-9a-f]{64}$'),
    result text NOT NULL CHECK (result = 'passed'),
    issued_at timestamptz NOT NULL,
    key_id text NOT NULL CHECK (octet_length(key_id) BETWEEN 1 AND 128),
    envelope jsonb NOT NULL CHECK (jsonb_typeof(envelope) = 'object'),
    signature text NOT NULL CHECK (octet_length(signature) BETWEEN 1 AND 128),
    recorded_at timestamptz NOT NULL,
    UNIQUE (repository, protected_ref, merged_commit_sha, policy_epoch, artifact_sha256)
);

CREATE INDEX trust_ci_protected_evidence_merge_idx
    ON trust_ci_protected_branch_evidence (merge_fact_id, source_attestation_id);

CREATE TABLE trust_ci_promotions (
    promotion_id uuid PRIMARY KEY,
    nonce text NOT NULL UNIQUE CHECK (octet_length(nonce) = 43),
    actor text NOT NULL CHECK (octet_length(actor) BETWEEN 1 AND 128),
    key_id text NOT NULL CHECK (octet_length(key_id) BETWEEN 1 AND 128),
    repository text NOT NULL
        CHECK (repository ~ '^[a-z0-9][a-z0-9._-]{0,99}/[a-z0-9][a-z0-9._-]{0,99}$'),
    merged_commit_sha char(40) NOT NULL CHECK (merged_commit_sha ~ '^[0-9a-f]{40}$'),
    artifact_sha256 char(64) NOT NULL CHECK (artifact_sha256 ~ '^[0-9a-f]{64}$'),
    target_environment text NOT NULL
        CHECK (target_environment ~ '^[a-z][a-z0-9-]{0,62}$'),
    policy_epoch char(64) NOT NULL CHECK (policy_epoch ~ '^[0-9a-f]{64}$'),
    source_attestation_id uuid NOT NULL
        REFERENCES trust_ci_protected_branch_evidence(source_attestation_id) ON DELETE RESTRICT,
    reason text NOT NULL CHECK (octet_length(reason) BETWEEN 1 AND 512),
    issued_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL,
    payload jsonb NOT NULL CHECK (jsonb_typeof(payload) = 'object'),
    envelope jsonb NOT NULL CHECK (jsonb_typeof(envelope) = 'object'),
    signature text NOT NULL CHECK (octet_length(signature) = 86),
    payload_sha256 char(64) NOT NULL UNIQUE CHECK (payload_sha256 ~ '^[0-9a-f]{64}$'),
    request_sha256 char(64) NOT NULL CHECK (request_sha256 ~ '^[0-9a-f]{64}$'),
    idempotency_key text NOT NULL UNIQUE
        CHECK (octet_length(idempotency_key) BETWEEN 16 AND 128),
    accepted_at timestamptz NOT NULL,
    CHECK (expires_at > issued_at)
);

CREATE TABLE trust_ci_promotion_idempotency (
    idempotency_key text PRIMARY KEY
        CHECK (octet_length(idempotency_key) BETWEEN 16 AND 128),
    request_sha256 char(64) NOT NULL
        CHECK (request_sha256 ~ '^[0-9a-f]{64}$'),
    promotion_id uuid NOT NULL,
    accepted_at timestamptz NOT NULL
);

CREATE TABLE trust_ci_promotion_consumptions (
    promotion_id uuid PRIMARY KEY
        REFERENCES trust_ci_promotions(promotion_id) ON DELETE RESTRICT,
    operation_id text NOT NULL UNIQUE
        CHECK (operation_id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
    repository text NOT NULL,
    merged_commit_sha char(40) NOT NULL CHECK (merged_commit_sha ~ '^[0-9a-f]{40}$'),
    artifact_sha256 char(64) NOT NULL CHECK (artifact_sha256 ~ '^[0-9a-f]{64}$'),
    target_environment text NOT NULL,
    policy_epoch char(64) NOT NULL CHECK (policy_epoch ~ '^[0-9a-f]{64}$'),
    source_attestation_id uuid NOT NULL
        REFERENCES trust_ci_protected_branch_evidence(source_attestation_id) ON DELETE RESTRICT,
    consumed_at timestamptz NOT NULL DEFAULT statement_timestamp()
);

CREATE TABLE trust_ci_promotion_events (
    event_sequence bigserial UNIQUE NOT NULL,
    event_id uuid PRIMARY KEY,
    event_type text NOT NULL CHECK (event_type IN (
        'promotion.accepted', 'promotion.rejected', 'promotion.consumed',
        'deployment.completed', 'deployment.failed', 'deployment.reconciled'
    )),
    occurred_at timestamptz NOT NULL,
    promotion_id uuid REFERENCES trust_ci_promotions(promotion_id) ON DELETE RESTRICT,
    correlation_id text NOT NULL CHECK (octet_length(correlation_id) BETWEEN 1 AND 128),
    operation_id text CHECK (operation_id IS NULL OR operation_id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
    actor text CHECK (actor IS NULL OR octet_length(actor) BETWEEN 1 AND 128),
    key_id text CHECK (key_id IS NULL OR octet_length(key_id) BETWEEN 1 AND 128),
    repository text,
    merged_commit_sha char(40)
        CHECK (merged_commit_sha IS NULL OR merged_commit_sha ~ '^[0-9a-f]{40}$'),
    artifact_sha256 char(64)
        CHECK (artifact_sha256 IS NULL OR artifact_sha256 ~ '^[0-9a-f]{64}$'),
    target_environment text,
    policy_epoch char(64)
        CHECK (policy_epoch IS NULL OR policy_epoch ~ '^[0-9a-f]{64}$'),
    outcome text NOT NULL CHECK (outcome IN (
        'accepted', 'rejected', 'consumed', 'completed', 'failed', 'reconciled'
    )),
    reason_code text NOT NULL
        CHECK (reason_code ~ '^[a-z][a-z0-9_]{0,127}$'),
    details jsonb NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(details) = 'object' AND pg_column_size(details) <= 8192)
);

CREATE INDEX trust_ci_promotions_consume_idx
    ON trust_ci_promotions (
        promotion_id, repository, merged_commit_sha, artifact_sha256,
        target_environment, policy_epoch, source_attestation_id, expires_at
    );
CREATE INDEX trust_ci_promotions_unconsumed_idx
    ON trust_ci_promotions (target_environment, expires_at, promotion_id);
CREATE INDEX trust_ci_promotion_events_order_idx
    ON trust_ci_promotion_events (promotion_id, event_sequence);

CREATE FUNCTION trust_ci_record_merge_fact(
    p_merge_fact_id uuid,
    p_delivery_id text,
    p_payload_sha256 text,
    p_repository_id bigint,
    p_repository text,
    p_installation_id bigint,
    p_pr_number bigint,
    p_head_sha text,
    p_base_sha text,
    p_protected_ref text,
    p_merged_commit_sha text,
    p_merged_at timestamptz,
    p_received_at timestamptz
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    existing_digest text;
    inserted_id uuid;
BEGIN
    SELECT payload_sha256::text
    INTO existing_digest
    FROM public.trust_ci_merge_facts
    WHERE delivery_id = p_delivery_id
    FOR SHARE;

    IF FOUND THEN
        IF existing_digest <> p_payload_sha256 THEN
            RAISE EXCEPTION 'delivery digest conflict' USING ERRCODE = '23505';
        END IF;
        RETURN false;
    END IF;

    INSERT INTO public.trust_ci_merge_facts (
        merge_fact_id, delivery_id, payload_sha256, repository_id, repository,
        installation_id, pr_number, head_sha, base_sha, protected_ref,
        merged_commit_sha, merged_at, received_at
    ) VALUES (
        p_merge_fact_id, p_delivery_id, p_payload_sha256, p_repository_id, p_repository,
        p_installation_id, p_pr_number, p_head_sha, p_base_sha, p_protected_ref,
        p_merged_commit_sha, p_merged_at, p_received_at
    )
    ON CONFLICT (merge_fact_id) DO NOTHING
    RETURNING merge_fact_id INTO inserted_id;

    RETURN inserted_id IS NOT NULL;
END;
$$;

CREATE FUNCTION trust_ci_claim_merge_fact(
    p_worker_id text,
    p_lease_seconds integer
)
RETURNS SETOF trust_ci_merge_facts
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    IF p_worker_id IS NULL OR length(trim(p_worker_id)) = 0
       OR p_lease_seconds NOT BETWEEN 1 AND 3600 THEN
        RAISE EXCEPTION 'invalid merge fact lease request';
    END IF;

    UPDATE public.trust_ci_merge_facts
    SET processing_status = 'dead',
        claim_id = NULL,
        lease_owner = NULL,
        lease_expires_at = NULL,
        last_error = 'attempts-exhausted',
        processed_at = statement_timestamp()
    WHERE processing_status = 'leased'
      AND lease_expires_at < statement_timestamp()
      AND processing_attempt >= 20;

    RETURN QUERY
    WITH candidate AS (
        SELECT merge_fact_id
        FROM public.trust_ci_merge_facts
        WHERE processing_attempt < 20
          AND next_attempt_at <= statement_timestamp()
          AND (
            processing_status = 'pending'
            OR (
                processing_status = 'leased'
                AND lease_expires_at < statement_timestamp()
            )
          )
        ORDER BY received_at, merge_fact_id
        FOR UPDATE SKIP LOCKED
        LIMIT 1
    )
    UPDATE public.trust_ci_merge_facts AS facts
    SET processing_status = 'leased',
        processing_attempt = facts.processing_attempt + 1,
        claim_id = gen_random_uuid(),
        lease_owner = p_worker_id,
        lease_expires_at = statement_timestamp() + make_interval(secs => p_lease_seconds),
        last_error = NULL
    FROM candidate
    WHERE facts.merge_fact_id = candidate.merge_fact_id
    RETURNING facts.*;
END;
$$;

CREATE FUNCTION trust_ci_retry_merge_fact(
    p_merge_fact_id uuid,
    p_claim_id uuid,
    p_attempt integer,
    p_error text
)
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
    UPDATE public.trust_ci_merge_facts
    SET processing_status = CASE WHEN processing_attempt >= 20 THEN 'dead' ELSE 'pending' END,
        claim_id = NULL,
        lease_owner = NULL,
        lease_expires_at = NULL,
        next_attempt_at = statement_timestamp() + make_interval(
            secs => LEAST(300, 5 * (2 ^ GREATEST(0, processing_attempt - 1)))::integer
        ),
        last_error = CASE WHEN processing_attempt >= 20
            THEN left('retry-exhausted:' || p_error, 512) ELSE left(p_error, 512) END,
        processed_at = CASE WHEN processing_attempt >= 20 THEN statement_timestamp() ELSE NULL END
    WHERE merge_fact_id = p_merge_fact_id
      AND claim_id = p_claim_id
      AND processing_attempt = p_attempt
      AND processing_status = 'leased'
      AND lease_expires_at >= statement_timestamp()
    RETURNING true
$$;

CREATE FUNCTION trust_ci_requeue_merge_fact(p_merge_fact_id uuid)
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
    UPDATE public.trust_ci_merge_facts
    SET processing_status = 'pending',
        processing_attempt = 0,
        claim_id = NULL,
        lease_owner = NULL,
        lease_expires_at = NULL,
        next_attempt_at = statement_timestamp(),
        last_error = 'requeued-by-reconciliation',
        processed_at = NULL
    WHERE merge_fact_id = p_merge_fact_id
      AND processing_status = 'dead'
      AND (last_error LIKE 'attempts-exhausted%' OR last_error LIKE 'retry-exhausted:%')
    RETURNING true
$$;

CREATE FUNCTION trust_ci_fail_merge_fact(
    p_merge_fact_id uuid,
    p_claim_id uuid,
    p_attempt integer,
    p_error text
)
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
    UPDATE public.trust_ci_merge_facts
    SET processing_status = 'dead', claim_id = NULL, lease_owner = NULL,
        lease_expires_at = NULL, last_error = left('permanent:' || p_error, 512),
        processed_at = statement_timestamp()
    WHERE merge_fact_id = p_merge_fact_id AND claim_id = p_claim_id
      AND processing_attempt = p_attempt AND processing_status = 'leased'
      AND lease_expires_at >= statement_timestamp()
    RETURNING true
$$;

CREATE FUNCTION trust_ci_complete_merge_fact(
    p_merge_fact_id uuid,
    p_claim_id uuid,
    p_attempt integer
)
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
    UPDATE public.trust_ci_merge_facts
    SET processing_status = 'completed',
        claim_id = NULL,
        lease_owner = NULL,
        lease_expires_at = NULL,
        processed_at = statement_timestamp()
    WHERE merge_fact_id = p_merge_fact_id
      AND claim_id = p_claim_id
      AND processing_attempt = p_attempt
      AND processing_status = 'leased'
      AND lease_expires_at >= statement_timestamp()
    RETURNING true
$$;

CREATE FUNCTION trust_ci_save_reconciliation_watermark(
    p_repository text,
    p_updated_at timestamptz,
    p_pr_number bigint
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    current_updated_at timestamptz;
    current_pr_number bigint;
BEGIN
    SELECT updated_at, pr_number
    INTO current_updated_at, current_pr_number
    FROM public.trust_ci_reconciliation_watermarks
    WHERE repository = p_repository
    FOR UPDATE;

    IF FOUND AND (p_updated_at, p_pr_number) < (current_updated_at, current_pr_number) THEN
        RAISE EXCEPTION 'reconciliation watermark cannot move backwards';
    END IF;

    INSERT INTO public.trust_ci_reconciliation_watermarks (
        repository, updated_at, pr_number, saved_at
    ) VALUES (
        p_repository, p_updated_at, p_pr_number, statement_timestamp()
    )
    ON CONFLICT (repository) DO UPDATE
    SET updated_at = EXCLUDED.updated_at,
        pr_number = EXCLUDED.pr_number,
        saved_at = EXCLUDED.saved_at;
    RETURN true;
END;
$$;

CREATE FUNCTION trust_ci_get_reconciliation_watermark(p_repository text)
RETURNS SETOF trust_ci_reconciliation_watermarks
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
    SELECT *
    FROM public.trust_ci_reconciliation_watermarks
    WHERE repository = p_repository
$$;

CREATE FUNCTION trust_ci_record_protected_branch_evidence(
    p_source_attestation_id uuid,
    p_merge_fact_id uuid,
    p_repository text,
    p_protected_ref text,
    p_merged_commit_sha text,
    p_policy_epoch text,
    p_runner_digest text,
    p_holdout_digest text,
    p_image_digest text,
    p_artifact_sha256 text,
    p_issued_at timestamptz,
    p_key_id text,
    p_envelope jsonb,
    p_signature text,
    p_recorded_at timestamptz
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    inserted_id uuid;
    existing_envelope jsonb;
BEGIN
    INSERT INTO public.trust_ci_protected_branch_evidence (
        source_attestation_id, merge_fact_id, repository, protected_ref,
        merged_commit_sha, policy_epoch, runner_digest, holdout_digest,
        image_digest, artifact_sha256, result, issued_at, key_id,
        envelope, signature, recorded_at
    )
    SELECT
        p_source_attestation_id, p_merge_fact_id, p_repository, p_protected_ref,
        p_merged_commit_sha, p_policy_epoch, p_runner_digest, p_holdout_digest,
        p_image_digest, p_artifact_sha256, 'passed', p_issued_at, p_key_id,
        p_envelope, p_signature, p_recorded_at
    FROM public.trust_ci_merge_facts
    WHERE merge_fact_id = p_merge_fact_id
      AND repository = p_repository
      AND protected_ref = p_protected_ref
      AND merged_commit_sha = p_merged_commit_sha
    ON CONFLICT (source_attestation_id) DO NOTHING
    RETURNING source_attestation_id INTO inserted_id;

    IF inserted_id IS NOT NULL THEN
        RETURN true;
    END IF;

    SELECT envelope INTO existing_envelope
    FROM public.trust_ci_protected_branch_evidence
    WHERE source_attestation_id = p_source_attestation_id;
    IF FOUND AND existing_envelope = p_envelope THEN
        RETURN false;
    END IF;
    RAISE EXCEPTION 'protected-branch provenance mismatch or conflict';
END;
$$;

CREATE FUNCTION trust_ci_record_or_get_protected_branch_evidence(
    p_source_attestation_id uuid,
    p_merge_fact_id uuid,
    p_repository text,
    p_protected_ref text,
    p_merged_commit_sha text,
    p_policy_epoch text,
    p_runner_digest text,
    p_holdout_digest text,
    p_image_digest text,
    p_artifact_sha256 text,
    p_issued_at timestamptz,
    p_key_id text,
    p_envelope jsonb,
    p_signature text,
    p_recorded_at timestamptz
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    existing public.trust_ci_protected_branch_evidence%ROWTYPE;
BEGIN
    INSERT INTO public.trust_ci_protected_branch_evidence (
        source_attestation_id, merge_fact_id, repository, protected_ref,
        merged_commit_sha, policy_epoch, runner_digest, holdout_digest,
        image_digest, artifact_sha256, result, issued_at, key_id,
        envelope, signature, recorded_at
    )
    SELECT
        p_source_attestation_id, p_merge_fact_id, p_repository, p_protected_ref,
        p_merged_commit_sha, p_policy_epoch, p_runner_digest, p_holdout_digest,
        p_image_digest, p_artifact_sha256, 'passed', p_issued_at, p_key_id,
        p_envelope, p_signature, p_recorded_at
    FROM public.trust_ci_merge_facts
    WHERE merge_fact_id = p_merge_fact_id
      AND repository = p_repository
      AND protected_ref = p_protected_ref
      AND merged_commit_sha = p_merged_commit_sha
    ON CONFLICT DO NOTHING;

    SELECT * INTO existing
    FROM public.trust_ci_protected_branch_evidence
    WHERE repository = p_repository
      AND protected_ref = p_protected_ref
      AND merged_commit_sha = p_merged_commit_sha
      AND policy_epoch = p_policy_epoch
      AND artifact_sha256 = p_artifact_sha256;

    IF NOT FOUND
       OR existing.merge_fact_id <> p_merge_fact_id
       OR existing.runner_digest <> p_runner_digest
       OR existing.holdout_digest <> p_holdout_digest
       OR existing.image_digest <> p_image_digest
       OR existing.key_id <> p_key_id
       OR existing.result <> 'passed' THEN
        RAISE EXCEPTION 'protected-branch exact tuple mismatch or conflict';
    END IF;
    RETURN existing.envelope;
END;
$$;

CREATE FUNCTION trust_ci_activate_policy(p_policy_epoch text)
RETURNS timestamptz
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    result_activated_at timestamptz;
BEGIN
    IF p_policy_epoch !~ '^[0-9a-f]{64}$' THEN
        RAISE EXCEPTION 'invalid active policy epoch';
    END IF;
    INSERT INTO public.trust_ci_active_policy (singleton, policy_epoch, activated_at)
    VALUES (true, p_policy_epoch, statement_timestamp())
    ON CONFLICT (singleton) DO UPDATE
    SET policy_epoch = EXCLUDED.policy_epoch,
        activated_at = EXCLUDED.activated_at
    WHERE public.trust_ci_active_policy.policy_epoch <> EXCLUDED.policy_epoch
    RETURNING activated_at INTO result_activated_at;
    IF result_activated_at IS NULL THEN
        SELECT activated_at
        INTO result_activated_at
        FROM public.trust_ci_active_policy
        WHERE singleton;
    END IF;
    RETURN result_activated_at;
END;
$$;

CREATE FUNCTION trust_ci_get_active_policy_epoch()
RETURNS text
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
    SELECT policy_epoch::text
    FROM public.trust_ci_active_policy
    WHERE singleton
$$;

CREATE FUNCTION trust_ci_accept_promotion(
    p_promotion_id uuid,
    p_nonce text,
    p_actor text,
    p_key_id text,
    p_repository text,
    p_merged_commit_sha text,
    p_artifact_sha256 text,
    p_target_environment text,
    p_policy_epoch text,
    p_source_attestation_id uuid,
    p_reason text,
    p_issued_at timestamptz,
    p_expires_at timestamptz,
    p_payload jsonb,
    p_envelope jsonb,
    p_signature text,
    p_payload_sha256 text,
    p_request_sha256 text,
    p_idempotency_key text,
    p_correlation_id text,
    p_event_id uuid,
    p_accepted_at timestamptz
)
RETURNS TABLE(result_promotion_id uuid, result_accepted_at timestamptz, result_created boolean)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    existing_id uuid;
    existing_digest text;
    existing_accepted_at timestamptz;
    active_policy_epoch text;
BEGIN
    SELECT policy_epoch::text
    INTO active_policy_epoch
    FROM public.trust_ci_active_policy
    WHERE singleton
    FOR SHARE;
    IF NOT FOUND OR p_policy_epoch <> active_policy_epoch THEN
        RAISE EXCEPTION 'promotion current policy mismatch';
    END IF;

    BEGIN
        INSERT INTO public.trust_ci_promotion_idempotency (
            idempotency_key, request_sha256, promotion_id, accepted_at
        ) VALUES (
            p_idempotency_key, p_request_sha256, p_promotion_id, p_accepted_at
        );
    EXCEPTION WHEN unique_violation THEN
        SELECT promotion_id, request_sha256::text, accepted_at
        INTO existing_id, existing_digest, existing_accepted_at
        FROM public.trust_ci_promotion_idempotency
        WHERE idempotency_key = p_idempotency_key
        FOR SHARE;

        IF NOT FOUND
           OR existing_digest <> p_request_sha256
           OR existing_id <> p_promotion_id THEN
            RAISE EXCEPTION 'idempotency key conflict' USING ERRCODE = '23505';
        END IF;
        RETURN QUERY SELECT existing_id, existing_accepted_at, false;
        RETURN;
    END;

    PERFORM 1
    FROM public.trust_ci_protected_branch_evidence
    WHERE source_attestation_id = p_source_attestation_id
      AND repository = p_repository
      AND merged_commit_sha = p_merged_commit_sha
      AND artifact_sha256 = p_artifact_sha256
      AND policy_epoch = p_policy_epoch
      AND result = 'passed'
    FOR SHARE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'promotion provenance mismatch or unavailable';
    END IF;

    INSERT INTO public.trust_ci_promotions (
        promotion_id, nonce, actor, key_id, repository, merged_commit_sha,
        artifact_sha256, target_environment, policy_epoch, source_attestation_id,
        reason, issued_at, expires_at, payload, envelope, signature,
        payload_sha256, request_sha256, idempotency_key, accepted_at
    ) VALUES (
        p_promotion_id, p_nonce, p_actor, p_key_id, p_repository, p_merged_commit_sha,
        p_artifact_sha256, p_target_environment, p_policy_epoch, p_source_attestation_id,
        p_reason, p_issued_at, p_expires_at, p_payload, p_envelope, p_signature,
        p_payload_sha256, p_request_sha256, p_idempotency_key, p_accepted_at
    );

    INSERT INTO public.trust_ci_promotion_events (
        event_id, event_type, occurred_at, promotion_id, correlation_id,
        actor, key_id, repository, merged_commit_sha, artifact_sha256,
        target_environment, policy_epoch, outcome, reason_code, details
    ) VALUES (
        p_event_id, 'promotion.accepted', p_accepted_at, p_promotion_id, p_correlation_id,
        p_actor, p_key_id, p_repository, p_merged_commit_sha, p_artifact_sha256,
        p_target_environment, p_policy_epoch, 'accepted', 'accepted', '{}'::jsonb
    );

    RETURN QUERY SELECT p_promotion_id, p_accepted_at, true;
END;
$$;

CREATE FUNCTION trust_ci_consume_promotion(
    p_promotion_id uuid,
    p_repository text,
    p_merged_commit_sha text,
    p_artifact_sha256 text,
    p_target_environment text,
    p_policy_epoch text,
    p_source_attestation_id uuid,
    p_operation_id text,
    p_event_id uuid
)
RETURNS timestamptz
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    selected_promotion trust_ci_promotions%ROWTYPE;
    active_policy_epoch text;
    authoritative_now timestamptz := date_trunc('second', statement_timestamp());
BEGIN
    IF p_operation_id !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$' THEN
        RAISE EXCEPTION 'operation_id must be a canonical UUID version 1 through 5';
    END IF;
    SELECT policy_epoch::text
    INTO active_policy_epoch
    FROM public.trust_ci_active_policy
    WHERE singleton
    FOR SHARE;
    IF NOT FOUND OR p_policy_epoch <> active_policy_epoch THEN
        RAISE EXCEPTION 'promotion current policy mismatch';
    END IF;

    SELECT promotion.*
    INTO selected_promotion
    FROM public.trust_ci_promotions AS promotion
    JOIN public.trust_ci_protected_branch_evidence AS evidence
      ON evidence.source_attestation_id = promotion.source_attestation_id
     AND evidence.repository = promotion.repository
     AND evidence.merged_commit_sha = promotion.merged_commit_sha
     AND evidence.artifact_sha256 = promotion.artifact_sha256
     AND evidence.policy_epoch = promotion.policy_epoch
     AND evidence.result = 'passed'
    WHERE promotion.promotion_id = p_promotion_id
      AND promotion.repository = p_repository
      AND promotion.merged_commit_sha = p_merged_commit_sha
      AND promotion.artifact_sha256 = p_artifact_sha256
      AND promotion.target_environment = p_target_environment
      AND promotion.policy_epoch = p_policy_epoch
      AND promotion.source_attestation_id = p_source_attestation_id
      AND promotion.issued_at <= authoritative_now
      AND promotion.expires_at > authoritative_now
    FOR SHARE OF promotion, evidence;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'promotion tuple mismatch or not current';
    END IF;

    BEGIN
        INSERT INTO public.trust_ci_promotion_consumptions (
            promotion_id, operation_id, repository, merged_commit_sha,
            artifact_sha256, target_environment, policy_epoch,
            source_attestation_id, consumed_at
        ) VALUES (
            p_promotion_id, p_operation_id, p_repository, p_merged_commit_sha,
            p_artifact_sha256, p_target_environment, p_policy_epoch,
            p_source_attestation_id, authoritative_now
        );
    EXCEPTION WHEN unique_violation THEN
        PERFORM 1
        FROM public.trust_ci_promotion_consumptions
        WHERE promotion_id = p_promotion_id
          AND operation_id = p_operation_id;
        IF FOUND THEN
            RAISE EXCEPTION 'promotion exact operation already consumed'
                USING ERRCODE = '23505';
        END IF;
        RAISE;
    END;

    INSERT INTO public.trust_ci_promotion_events (
        event_id, event_type, occurred_at, promotion_id, correlation_id,
        operation_id, actor, key_id, repository, merged_commit_sha,
        artifact_sha256, target_environment, policy_epoch, outcome,
        reason_code, details
    ) VALUES (
        p_event_id, 'promotion.consumed', authoritative_now, p_promotion_id, p_operation_id,
        p_operation_id, selected_promotion.actor, selected_promotion.key_id,
        p_repository, p_merged_commit_sha, p_artifact_sha256,
        p_target_environment, p_policy_epoch, 'consumed', 'consumed', '{}'::jsonb
    );

    RETURN authoritative_now;
END;
$$;

CREATE FUNCTION trust_ci_get_promotion_consumption(
    p_promotion_id uuid,
    p_operation_id text
)
RETURNS SETOF trust_ci_promotion_consumptions
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    IF p_operation_id !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$' THEN
        RAISE EXCEPTION 'operation_id must be a canonical UUID version 1 through 5';
    END IF;
    RETURN QUERY
    SELECT *
    FROM public.trust_ci_promotion_consumptions
    WHERE promotion_id = p_promotion_id
      AND operation_id = p_operation_id;
END;
$$;

CREATE UNIQUE INDEX trust_ci_promotion_terminal_once_idx
    ON trust_ci_promotion_events (promotion_id, operation_id)
    WHERE event_type IN (
        'deployment.completed', 'deployment.failed', 'deployment.reconciled'
    );

CREATE FUNCTION trust_ci_record_deployment_terminal(
    p_promotion_id uuid,
    p_operation_id text,
    p_event_id uuid,
    p_event_type text,
    p_reason_code text,
    p_details jsonb
)
RETURNS timestamptz
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    selected_promotion trust_ci_promotions%ROWTYPE;
    selected_outcome text;
    authoritative_now timestamptz := date_trunc('second', statement_timestamp());
BEGIN
    IF p_operation_id !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$' THEN
        RAISE EXCEPTION 'operation_id must be a canonical UUID version 1 through 5';
    END IF;
    selected_outcome := CASE p_event_type
        WHEN 'deployment.completed' THEN 'completed'
        WHEN 'deployment.failed' THEN 'failed'
        WHEN 'deployment.reconciled' THEN 'reconciled'
        ELSE NULL
    END;
    IF selected_outcome IS NULL THEN
        RAISE EXCEPTION 'invalid terminal deployment event type';
    END IF;
    IF p_reason_code !~ '^[a-z][a-z0-9_]{0,127}$' THEN
        RAISE EXCEPTION 'invalid terminal deployment reason code';
    END IF;
    IF jsonb_typeof(p_details) <> 'object' OR length(p_details::text) > 8192 THEN
        RAISE EXCEPTION 'invalid terminal deployment details';
    END IF;

    SELECT promotion.* INTO selected_promotion
    FROM public.trust_ci_promotions AS promotion
    JOIN public.trust_ci_promotion_consumptions AS consumption
      ON consumption.promotion_id = promotion.promotion_id
     AND consumption.operation_id = p_operation_id
    WHERE promotion.promotion_id = p_promotion_id
    FOR SHARE OF promotion, consumption;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'terminal deployment event requires exact consumption';
    END IF;

    INSERT INTO public.trust_ci_promotion_events (
        event_id, event_type, occurred_at, promotion_id, correlation_id,
        operation_id, actor, key_id, repository, merged_commit_sha,
        artifact_sha256, target_environment, policy_epoch, outcome,
        reason_code, details
    ) VALUES (
        p_event_id, p_event_type, authoritative_now, p_promotion_id, p_operation_id,
        p_operation_id, selected_promotion.actor, selected_promotion.key_id,
        selected_promotion.repository, selected_promotion.merged_commit_sha,
        selected_promotion.artifact_sha256, selected_promotion.target_environment,
        selected_promotion.policy_epoch, selected_outcome, p_reason_code, p_details
    );
    RETURN authoritative_now;
EXCEPTION WHEN unique_violation THEN
    RAISE EXCEPTION 'terminal deployment event already exists' USING ERRCODE = '23505';
END;
$$;

CREATE FUNCTION trust_ci_record_promotion_rejection(
    p_event_id uuid,
    p_occurred_at timestamptz,
    p_correlation_id text,
    p_actor text,
    p_key_id text,
    p_repository text,
    p_merged_commit_sha text,
    p_artifact_sha256 text,
    p_target_environment text,
    p_policy_epoch text,
    p_reason_code text,
    p_details jsonb
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    IF p_details IS NULL
       OR jsonb_typeof(p_details) <> 'object'
       OR p_details - 'http_status' <> '{}'::jsonb
       OR jsonb_typeof(p_details -> 'http_status') <> 'number'
       OR (p_details ->> 'http_status')::integer NOT BETWEEN 400 AND 599 THEN
        RAISE EXCEPTION 'invalid promotion rejection audit details';
    END IF;
    INSERT INTO public.trust_ci_promotion_events (
        event_id, event_type, occurred_at, promotion_id, correlation_id,
        operation_id, actor, key_id, repository, merged_commit_sha,
        artifact_sha256, target_environment, policy_epoch, outcome,
        reason_code, details
    ) VALUES (
        p_event_id, 'promotion.rejected', p_occurred_at, NULL, p_correlation_id,
        NULL, p_actor, p_key_id, p_repository, p_merged_commit_sha,
        p_artifact_sha256, p_target_environment, p_policy_epoch, 'rejected',
        p_reason_code, p_details
    );
END;
$$;

CREATE FUNCTION trust_ci_list_promotion_events(p_promotion_id uuid, p_limit integer)
RETURNS SETOF trust_ci_promotion_events
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    IF p_limit NOT BETWEEN 1 AND 1000 THEN
        RAISE EXCEPTION 'event limit must be between 1 and 1000';
    END IF;
    RETURN QUERY
    SELECT *
    FROM public.trust_ci_promotion_events
    WHERE promotion_id = p_promotion_id
    ORDER BY event_sequence
    LIMIT p_limit;
END;
$$;

CREATE FUNCTION trust_ci_promotion_metrics()
RETURNS jsonb
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
    WITH
    outcome_counts AS (
        SELECT outcome, count(*)::bigint AS count
        FROM public.trust_ci_promotion_events
        GROUP BY outcome
    ),
    reason_counts AS (
        SELECT reason_code, count(*)::bigint AS count
        FROM public.trust_ci_promotion_events
        GROUP BY reason_code
    ),
    nonterminal_consumptions AS (
        SELECT consumption.promotion_id, consumption.consumed_at
        FROM public.trust_ci_promotion_consumptions AS consumption
        WHERE NOT EXISTS (
            SELECT 1
            FROM public.trust_ci_promotion_events AS terminal
            WHERE terminal.promotion_id = consumption.promotion_id
              AND terminal.event_type IN (
                  'deployment.completed', 'deployment.failed', 'deployment.reconciled'
              )
        )
    ),
    accept_latency AS (
        SELECT
            COALESCE(sum(GREATEST(0, EXTRACT(EPOCH FROM (accepted_at - issued_at)))), 0) AS total,
            count(*)::bigint AS count
        FROM public.trust_ci_promotions
    ),
    consume_latency AS (
        SELECT
            COALESCE(sum(GREATEST(0, EXTRACT(EPOCH FROM (consumed_at - accepted_at)))), 0) AS total,
            count(*)::bigint AS count
        FROM public.trust_ci_promotion_consumptions AS consumption
        JOIN public.trust_ci_promotions AS promotion USING (promotion_id)
    )
    SELECT jsonb_build_object(
        'promotion_outcomes',
        COALESCE(
            (SELECT jsonb_object_agg(outcome, count) FROM outcome_counts),
            '{}'::jsonb
        ),
        'promotion_reasons',
        COALESCE(
            (SELECT jsonb_object_agg(reason_code, count) FROM reason_counts),
            '{}'::jsonb
        ),
        'dependency_failures',
        jsonb_build_object(
            'authorization', (
                SELECT count(*) FROM public.trust_ci_promotion_events
                WHERE reason_code IN ('authorization_unavailable', 'consume_unavailable')
            ),
            'provenance', (
                SELECT count(*) FROM public.trust_ci_promotion_events
                WHERE reason_code = 'provenance_mismatch'
            ),
            'signature', (
                SELECT count(*) FROM public.trust_ci_promotion_events
                WHERE reason_code = 'signature_invalid'
            )
        ),
        'merge_facts_pending', (
            SELECT count(*)
            FROM public.trust_ci_merge_facts
            WHERE processing_status IN ('pending', 'leased')
        ),
        'merge_fact_oldest_pending_age_seconds',
        COALESCE(
            (
                SELECT GREATEST(
                    0,
                    EXTRACT(EPOCH FROM (statement_timestamp() - min(received_at)))
                )
                FROM public.trust_ci_merge_facts
                WHERE processing_status IN ('pending', 'leased')
            ),
            0
        ),
        'reconciliation_lag_seconds',
        COALESCE(
            (
                SELECT GREATEST(
                    0,
                    EXTRACT(EPOCH FROM (statement_timestamp() - min(updated_at)))
                )
                FROM public.trust_ci_reconciliation_watermarks
            ),
            0
        ),
        'protected_branch_validation_outcomes',
        jsonb_build_object(
            'passed', (
                SELECT count(*) FROM public.trust_ci_protected_branch_evidence
            ),
            'failed', (
                SELECT count(*) FROM public.trust_ci_merge_facts
                WHERE processing_status = 'dead'
            )
        ),
        'expired_promotions', (
            SELECT count(*)
            FROM public.trust_ci_promotions
            WHERE expires_at <= statement_timestamp()
        ),
        'accepted_unconsumed', (
            SELECT count(*)
            FROM public.trust_ci_promotions AS promotion
            WHERE NOT EXISTS (
                SELECT 1
                FROM public.trust_ci_promotion_consumptions AS consumption
                WHERE consumption.promotion_id = promotion.promotion_id
            )
        ),
        'consumed_without_terminal', (SELECT count(*) FROM nonterminal_consumptions),
        'consumed_without_terminal_oldest_age_seconds',
        COALESCE(
            (
                SELECT GREATEST(
                    0,
                    EXTRACT(EPOCH FROM (statement_timestamp() - min(consumed_at)))
                )
                FROM nonterminal_consumptions
            ),
            0
        ),
        'promotion_accept_latency_seconds_sum', (SELECT total FROM accept_latency),
        'promotion_accept_latency_count', (SELECT count FROM accept_latency),
        'promotion_consume_latency_seconds_sum', (SELECT total FROM consume_latency),
        'promotion_consume_latency_count', (SELECT count FROM consume_latency)
    );
$$;

REVOKE ALL ON trust_ci_merge_facts FROM PUBLIC;
REVOKE ALL ON trust_ci_reconciliation_watermarks FROM PUBLIC;
REVOKE ALL ON trust_ci_active_policy FROM PUBLIC;
REVOKE ALL ON trust_ci_protected_branch_evidence FROM PUBLIC;
REVOKE ALL ON trust_ci_promotions FROM PUBLIC;
REVOKE ALL ON trust_ci_promotion_idempotency FROM PUBLIC;
REVOKE ALL ON trust_ci_promotion_consumptions FROM PUBLIC;
REVOKE ALL ON trust_ci_promotion_events FROM PUBLIC;

REVOKE ALL ON FUNCTION trust_ci_record_merge_fact(uuid, text, text, bigint, text, bigint, bigint, text, text, text, text, timestamptz, timestamptz) FROM PUBLIC;
REVOKE ALL ON FUNCTION trust_ci_claim_merge_fact(text, integer) FROM PUBLIC;
REVOKE ALL ON FUNCTION trust_ci_retry_merge_fact(uuid, uuid, integer, text) FROM PUBLIC;
REVOKE ALL ON FUNCTION trust_ci_requeue_merge_fact(uuid) FROM PUBLIC;
REVOKE ALL ON FUNCTION trust_ci_fail_merge_fact(uuid, uuid, integer, text) FROM PUBLIC;
REVOKE ALL ON FUNCTION trust_ci_complete_merge_fact(uuid, uuid, integer) FROM PUBLIC;
REVOKE ALL ON FUNCTION trust_ci_save_reconciliation_watermark(text, timestamptz, bigint) FROM PUBLIC;
REVOKE ALL ON FUNCTION trust_ci_get_reconciliation_watermark(text) FROM PUBLIC;
REVOKE ALL ON FUNCTION trust_ci_record_protected_branch_evidence(uuid, uuid, text, text, text, text, text, text, text, text, timestamptz, text, jsonb, text, timestamptz) FROM PUBLIC;
REVOKE ALL ON FUNCTION trust_ci_record_or_get_protected_branch_evidence(uuid, uuid, text, text, text, text, text, text, text, text, timestamptz, text, jsonb, text, timestamptz) FROM PUBLIC;
REVOKE ALL ON FUNCTION trust_ci_activate_policy(text) FROM PUBLIC;
REVOKE ALL ON FUNCTION trust_ci_get_active_policy_epoch() FROM PUBLIC;
REVOKE ALL ON FUNCTION trust_ci_accept_promotion(uuid, text, text, text, text, text, text, text, text, uuid, text, timestamptz, timestamptz, jsonb, jsonb, text, text, text, text, text, uuid, timestamptz) FROM PUBLIC;
REVOKE ALL ON FUNCTION trust_ci_consume_promotion(uuid, text, text, text, text, text, uuid, text, uuid) FROM PUBLIC;
REVOKE ALL ON FUNCTION trust_ci_get_promotion_consumption(uuid, text) FROM PUBLIC;
REVOKE ALL ON FUNCTION trust_ci_record_deployment_terminal(uuid, text, uuid, text, text, jsonb) FROM PUBLIC;
REVOKE ALL ON FUNCTION trust_ci_record_promotion_rejection(uuid, timestamptz, text, text, text, text, text, text, text, text, text, jsonb) FROM PUBLIC;
REVOKE ALL ON FUNCTION trust_ci_list_promotion_events(uuid, integer) FROM PUBLIC;
REVOKE ALL ON FUNCTION trust_ci_promotion_metrics() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION trust_ci_record_merge_fact(uuid, text, text, bigint, text, bigint, bigint, text, text, text, text, timestamptz, timestamptz) TO trust_ci_api;
GRANT EXECUTE ON FUNCTION trust_ci_get_active_policy_epoch() TO trust_ci_api;
GRANT EXECUTE ON FUNCTION trust_ci_accept_promotion(uuid, text, text, text, text, text, text, text, text, uuid, text, timestamptz, timestamptz, jsonb, jsonb, text, text, text, text, text, uuid, timestamptz) TO trust_ci_api;
GRANT EXECUTE ON FUNCTION trust_ci_list_promotion_events(uuid, integer) TO trust_ci_api;
GRANT EXECUTE ON FUNCTION trust_ci_record_promotion_rejection(uuid, timestamptz, text, text, text, text, text, text, text, text, text, jsonb) TO trust_ci_api;
GRANT EXECUTE ON FUNCTION trust_ci_promotion_metrics() TO trust_ci_api;

GRANT EXECUTE ON FUNCTION trust_ci_claim_merge_fact(text, integer) TO trust_ci_worker;
GRANT EXECUTE ON FUNCTION trust_ci_retry_merge_fact(uuid, uuid, integer, text) TO trust_ci_worker;
GRANT EXECUTE ON FUNCTION trust_ci_requeue_merge_fact(uuid) TO trust_ci_worker;
GRANT EXECUTE ON FUNCTION trust_ci_fail_merge_fact(uuid, uuid, integer, text) TO trust_ci_worker;
GRANT EXECUTE ON FUNCTION trust_ci_complete_merge_fact(uuid, uuid, integer) TO trust_ci_worker;
GRANT EXECUTE ON FUNCTION trust_ci_save_reconciliation_watermark(text, timestamptz, bigint) TO trust_ci_worker;
GRANT EXECUTE ON FUNCTION trust_ci_get_reconciliation_watermark(text) TO trust_ci_worker;
GRANT EXECUTE ON FUNCTION trust_ci_record_protected_branch_evidence(uuid, uuid, text, text, text, text, text, text, text, text, timestamptz, text, jsonb, text, timestamptz) TO trust_ci_worker;
GRANT EXECUTE ON FUNCTION trust_ci_record_or_get_protected_branch_evidence(uuid, uuid, text, text, text, text, text, text, text, text, timestamptz, text, jsonb, text, timestamptz) TO trust_ci_worker;

GRANT EXECUTE ON FUNCTION trust_ci_activate_policy(text) TO trust_ci_migrator;

GRANT EXECUTE ON FUNCTION trust_ci_consume_promotion(uuid, text, text, text, text, text, uuid, text, uuid) TO trust_ci_deployer;
GRANT EXECUTE ON FUNCTION trust_ci_get_promotion_consumption(uuid, text) TO trust_ci_deployer;
GRANT EXECUTE ON FUNCTION trust_ci_record_deployment_terminal(uuid, text, uuid, text, text, jsonb) TO trust_ci_deployer;
GRANT EXECUTE ON FUNCTION trust_ci_list_promotion_events(uuid, integer) TO trust_ci_deployer;

GRANT SELECT ON trust_ci_merge_facts TO trust_ci_backup;
GRANT SELECT ON trust_ci_reconciliation_watermarks TO trust_ci_backup;
GRANT SELECT ON trust_ci_active_policy TO trust_ci_backup;
GRANT SELECT ON trust_ci_protected_branch_evidence TO trust_ci_backup;
GRANT SELECT ON trust_ci_promotions TO trust_ci_backup;
GRANT SELECT ON trust_ci_promotion_idempotency TO trust_ci_backup;
GRANT SELECT ON trust_ci_promotion_consumptions TO trust_ci_backup;
GRANT SELECT ON trust_ci_promotion_events TO trust_ci_backup;
