-- Dormant, fenced handoff of already-qualified native results. Migration 024 deliberately
-- never enqueues, so any pre-025 row is unexplained authority and must stop the upgrade.
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM factory.next_model_request_outbox_v1) THEN
    RAISE EXCEPTION 'unexpected pre-025 result outbox rows';
  END IF;
END $$;

ALTER TABLE factory.result_sources_v1
  ADD CONSTRAINT result_sources_v1_dispatch_identity
  UNIQUE (envelope_digest,repository_id,task_id,run_id,fence,packet_digest,attempt_id);

ALTER TABLE factory.next_model_request_outbox_v1
  ADD COLUMN repository_id text NOT NULL,
  ADD COLUMN fence bigint NOT NULL CHECK (fence > 0),
  ADD COLUMN packet_digest char(64) NOT NULL CHECK (packet_digest ~ '^[0-9a-f]{64}$'),
  ADD COLUMN dispatch_phase text NOT NULL DEFAULT 'pending'
    CHECK (dispatch_phase IN ('pending','claimed','sending','unknown','blocked','delivered','failed')),
  ADD COLUMN operation_id text,
  ADD COLUMN claim_token char(64),
  ADD COLUMN dispatcher_id text,
  ADD COLUMN claim_expires_at timestamptz,
  ADD COLUMN send_started_at timestamptz,
  ADD COLUMN observation_deadline timestamptz,
  ADD COLUMN available_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  ADD COLUMN observed_at timestamptz,
  ADD COLUMN reason_code text,
  ADD COLUMN observation_digest char(64),
  ADD COLUMN send_attempts integer NOT NULL DEFAULT 0 CHECK (send_attempts BETWEEN 0 AND 3),
  ADD COLUMN observation_attempts integer NOT NULL DEFAULT 0 CHECK (observation_attempts BETWEEN 0 AND 100),
  ADD CONSTRAINT next_model_request_outbox_v1_source_identity_fk
    FOREIGN KEY (envelope_digest,repository_id,task_id,run_id,fence,packet_digest,attempt_id)
    REFERENCES factory.result_sources_v1(
      envelope_digest,repository_id,task_id,run_id,fence,packet_digest,attempt_id
    ) ON DELETE RESTRICT;

ALTER TABLE factory.next_model_request_outbox_v1
  ALTER COLUMN operation_id SET NOT NULL,
  ALTER COLUMN observation_deadline SET NOT NULL,
  ADD CONSTRAINT next_model_request_outbox_v1_operation_check
    CHECK (operation_id='factory-result:'||trim(request_digest)),
  ADD CONSTRAINT next_model_request_outbox_v1_claim_check CHECK (
    (claim_token IS NULL AND dispatcher_id IS NULL AND claim_expires_at IS NULL)
    OR (claim_token ~ '^[0-9a-f]{64}$'
      AND dispatcher_id ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$'
      AND claim_expires_at IS NOT NULL)
  ),
  ADD CONSTRAINT next_model_request_outbox_v1_observation_check CHECK (
    observation_digest IS NULL OR observation_digest ~ '^[0-9a-f]{64}$'
  );

-- Qualification remains unavailable until a real native callback/interceptor exists. The
-- dispatcher is therefore dormant and only consumes rows written by that future boundary.

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='factory_result_dispatcher') THEN
    CREATE ROLE factory_result_dispatcher NOLOGIN NOINHERIT;
  END IF;
  IF EXISTS (
    SELECT 1 FROM pg_roles WHERE rolname='factory_result_dispatcher' AND
      (rolcanlogin OR rolinherit OR rolsuper OR rolcreaterole OR rolcreatedb OR rolreplication OR rolbypassrls)
  ) OR EXISTS (
    SELECT 1 FROM pg_auth_members m
    JOIN pg_roles member ON member.oid=m.member
    WHERE member.rolname='factory_result_dispatcher'
  ) OR EXISTS (
    SELECT 1 FROM pg_auth_members m
    JOIN pg_roles parent ON parent.oid=m.roleid
    JOIN pg_roles member ON member.oid=m.member
    WHERE parent.rolname='factory_result_dispatcher' AND (
      NOT member.rolcanlogin OR member.rolinherit OR member.rolsuper
      OR member.rolcreaterole OR member.rolcreatedb OR member.rolreplication
      OR member.rolbypassrls
      OR EXISTS (
        SELECT 1 FROM pg_auth_members other
        WHERE other.member=m.member AND other.roleid<>m.roleid
      )
    )
  ) THEN RAISE EXCEPTION 'unsafe factory result dispatcher role'; END IF;
END $$;
GRANT USAGE ON SCHEMA factory TO factory_result_dispatcher;

CREATE INDEX next_model_request_outbox_v1_dispatchable
  ON factory.next_model_request_outbox_v1(available_at,created_at,request_digest)
  WHERE dispatch_phase IN ('pending','unknown');

CREATE FUNCTION factory.claim_model_requests_v1(
  p_dispatcher_id text, p_limit integer, p_lease_seconds integer
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path=pg_catalog,pg_temp
AS $$
DECLARE v_result jsonb;
BEGIN
  IF p_dispatcher_id !~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$'
    OR p_limit NOT BETWEEN 1 AND 100 OR p_lease_seconds NOT BETWEEN 5 AND 300
  THEN RAISE EXCEPTION 'invalid dispatch claim'; END IF;
  WITH candidates AS (
    SELECT request_digest FROM factory.next_model_request_outbox_v1
    WHERE dispatch_phase IN ('pending','unknown') AND available_at<=clock_timestamp()
      AND observation_deadline>clock_timestamp()
      AND ((dispatch_phase='pending' AND send_attempts<3)
        OR (dispatch_phase='unknown' AND observation_attempts<100))
      AND (claim_expires_at IS NULL OR claim_expires_at<=clock_timestamp())
      AND EXISTS (
        SELECT 1 FROM factory.result_sources_v1 s
        JOIN factory.tasks t ON t.task_id=s.task_id
        JOIN factory.runs r ON r.run_id=s.run_id AND r.task_id=s.task_id
        JOIN factory.attempts a ON a.attempt_id=s.attempt_id
          AND a.task_id=s.task_id AND a.run_id=s.run_id
        WHERE s.envelope_digest=next_model_request_outbox_v1.envelope_digest
          AND s.repository_id=next_model_request_outbox_v1.repository_id
          AND s.task_id=next_model_request_outbox_v1.task_id
          AND s.run_id=next_model_request_outbox_v1.run_id
          AND s.fence=next_model_request_outbox_v1.fence
          AND s.packet_digest=next_model_request_outbox_v1.packet_digest
          AND s.attempt_id=next_model_request_outbox_v1.attempt_id
          AND t.repository_id=s.repository_id AND t.current_run_id=s.run_id
          AND t.current_fence=s.fence AND r.fence=s.fence
          AND r.packet_digest=s.packet_digest AND r.state='leased'
          AND r.lease_expires_at>clock_timestamp() AND r.deadline_at>clock_timestamp()
          AND a.finished_at IS NULL
      )
    ORDER BY available_at,created_at,request_digest
    FOR UPDATE SKIP LOCKED LIMIT p_limit
  ), claimed AS (
    UPDATE factory.next_model_request_outbox_v1 o SET
      state='claimed',
      dispatch_phase=CASE WHEN o.dispatch_phase='pending' THEN 'claimed' ELSE 'unknown' END,
      claim_token=factory.execution_contract_hash(NULL,
        trim(o.request_digest)||':'||p_dispatcher_id||':'||gen_random_uuid()::text),
      dispatcher_id=p_dispatcher_id,
      claim_expires_at=clock_timestamp()+make_interval(secs=>p_lease_seconds),
      send_attempts=o.send_attempts+(o.dispatch_phase='pending')::integer,
      observation_attempts=o.observation_attempts+(o.dispatch_phase='unknown')::integer
    FROM candidates c WHERE o.request_digest=c.request_digest
    RETURNING o.*
  ) SELECT COALESCE(jsonb_agg(jsonb_build_object(
      'request_digest',trim(c.request_digest),'operation_id',c.operation_id,
      'envelope_digest',trim(c.envelope_digest),'task_id',c.task_id::text,
      'repository_id',c.repository_id,'run_id',c.run_id::text,'fence',c.fence,
      'packet_digest',trim(c.packet_digest),'attempt_id',c.attempt_id::text,
      'claim_token',trim(c.claim_token),'dispatcher_id',c.dispatcher_id,
      'state',c.dispatch_phase,'payload',s.envelope
    ) ORDER BY c.created_at,c.request_digest),'[]'::jsonb) INTO v_result
    FROM claimed c JOIN factory.result_sources_v1 s ON s.envelope_digest=c.envelope_digest;
  RETURN v_result;
END $$;

CREATE FUNCTION factory.start_model_request_dispatch_v1(
  p_request_digest char(64), p_dispatcher_id text, p_claim_token char(64)
) RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path=pg_catalog,pg_temp
AS $$
BEGIN
  UPDATE factory.next_model_request_outbox_v1 o SET
    state='claimed',dispatch_phase='sending',send_started_at=clock_timestamp()
  WHERE request_digest=p_request_digest AND dispatch_phase='claimed'
    AND dispatcher_id=p_dispatcher_id AND claim_token=p_claim_token
    AND claim_expires_at>clock_timestamp()
    AND EXISTS (
      SELECT 1 FROM factory.result_sources_v1 s
      JOIN factory.tasks t ON t.task_id=s.task_id
      JOIN factory.runs r ON r.run_id=s.run_id AND r.task_id=s.task_id
      JOIN factory.attempts a ON a.attempt_id=s.attempt_id
        AND a.task_id=s.task_id AND a.run_id=s.run_id
      WHERE s.envelope_digest=o.envelope_digest
        AND s.repository_id=o.repository_id AND s.task_id=o.task_id
        AND s.run_id=o.run_id AND s.fence=o.fence
        AND s.packet_digest=o.packet_digest AND s.attempt_id=o.attempt_id
        AND t.repository_id=s.repository_id AND t.current_run_id=s.run_id
        AND t.current_fence=s.fence AND r.fence=s.fence
        AND r.packet_digest=s.packet_digest AND r.state='leased'
        AND r.lease_expires_at>clock_timestamp() AND r.deadline_at>clock_timestamp()
        AND a.finished_at IS NULL
    );
  IF NOT FOUND THEN RAISE EXCEPTION 'stale dispatch claim'; END IF;
END $$;

CREATE FUNCTION factory.record_model_request_dispatch_v1(
  p_request_digest char(64), p_dispatcher_id text, p_claim_token char(64),
  p_state text, p_reason_code text, p_observation_digest char(64)
) RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path=pg_catalog,pg_temp
AS $$
BEGIN
  IF p_state NOT IN ('delivered','failed','unknown')
    OR p_reason_code !~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$'
    OR (p_state='delivered') IS DISTINCT FROM (p_observation_digest IS NOT NULL)
    OR (p_observation_digest IS NOT NULL AND p_observation_digest !~ '^[0-9a-f]{64}$')
  THEN RAISE EXCEPTION 'invalid dispatch observation'; END IF;
  UPDATE factory.next_model_request_outbox_v1 o SET
    state=CASE WHEN p_state IN ('delivered','failed') THEN p_state ELSE 'claimed' END,
    dispatch_phase=p_state,reason_code=p_reason_code,observation_digest=p_observation_digest,
    observed_at=CASE WHEN p_state IN ('delivered','failed') THEN clock_timestamp() ELSE observed_at END,
    available_at=CASE WHEN p_state='unknown' THEN clock_timestamp()+interval '1 second' ELSE available_at END,
    claim_token=NULL,dispatcher_id=NULL,claim_expires_at=NULL
  WHERE request_digest=p_request_digest AND dispatch_phase IN ('sending','unknown')
    AND dispatcher_id=p_dispatcher_id AND claim_token=p_claim_token
    AND claim_expires_at>clock_timestamp()
    AND EXISTS (
      SELECT 1 FROM factory.result_sources_v1 s
      JOIN factory.tasks t ON t.task_id=s.task_id
      JOIN factory.runs r ON r.run_id=s.run_id AND r.task_id=s.task_id
      JOIN factory.attempts a ON a.attempt_id=s.attempt_id
        AND a.task_id=s.task_id AND a.run_id=s.run_id
      WHERE s.envelope_digest=o.envelope_digest
        AND s.repository_id=o.repository_id AND s.task_id=o.task_id
        AND s.run_id=o.run_id AND s.fence=o.fence
        AND s.packet_digest=o.packet_digest AND s.attempt_id=o.attempt_id
        AND t.repository_id=s.repository_id AND t.current_run_id=s.run_id
        AND t.current_fence=s.fence AND r.fence=s.fence
        AND r.packet_digest=s.packet_digest AND r.state='leased'
        AND r.lease_expires_at>clock_timestamp() AND r.deadline_at>clock_timestamp()
        AND a.finished_at IS NULL
    );
  IF NOT FOUND THEN RAISE EXCEPTION 'stale dispatch claim'; END IF;
END $$;

CREATE FUNCTION factory.reconcile_model_requests_v1(
  p_dispatcher_id text, p_limit integer
) RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path=pg_catalog,pg_temp
AS $$
DECLARE v_count integer;
BEGIN
  IF p_dispatcher_id !~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$' OR p_limit NOT BETWEEN 1 AND 100
  THEN RAISE EXCEPTION 'invalid dispatch reconciliation'; END IF;
  WITH expired AS (
    SELECT request_digest,dispatch_phase FROM factory.next_model_request_outbox_v1
    WHERE dispatch_phase IN ('pending','claimed','sending','unknown') AND (
      (claim_expires_at IS NOT NULL AND claim_expires_at<=clock_timestamp())
      OR ((claim_expires_at IS NULL OR claim_expires_at<=clock_timestamp()) AND
          (observation_deadline<=clock_timestamp()
            OR (dispatch_phase='pending' AND send_attempts>=3)
            OR (dispatch_phase='unknown' AND observation_attempts>=100)))
    )
    ORDER BY COALESCE(claim_expires_at,observation_deadline),request_digest
    FOR UPDATE SKIP LOCKED LIMIT p_limit
  ), repaired AS (
    UPDATE factory.next_model_request_outbox_v1 o SET
      state=CASE
        WHEN o.observation_deadline<=clock_timestamp()
          OR (e.dispatch_phase IN ('pending','claimed') AND o.send_attempts>=3)
          OR o.observation_attempts>=100 THEN 'claimed'
        WHEN e.dispatch_phase='claimed' THEN 'pending' ELSE 'claimed' END,
      dispatch_phase=CASE
        WHEN o.observation_deadline<=clock_timestamp()
          OR (e.dispatch_phase IN ('pending','claimed') AND o.send_attempts>=3)
          OR o.observation_attempts>=100 THEN 'blocked'
        WHEN e.dispatch_phase='claimed' THEN 'pending' ELSE 'unknown' END,
      reason_code=CASE
        WHEN o.observation_deadline<=clock_timestamp() THEN 'observation_deadline_exceeded'
        WHEN e.dispatch_phase IN ('pending','claimed') AND o.send_attempts>=3
          THEN 'send_attempts_exhausted'
        WHEN o.observation_attempts>=100 THEN 'observation_attempts_exhausted'
        WHEN e.dispatch_phase='sending' THEN 'post_outcome_ambiguous' ELSE o.reason_code END,
      available_at=clock_timestamp(),claim_token=NULL,dispatcher_id=NULL,claim_expires_at=NULL
    FROM expired e WHERE o.request_digest=e.request_digest RETURNING 1
  ) SELECT count(*) INTO v_count FROM repaired;
  RETURN v_count;
END $$;

REVOKE ALL ON FUNCTION factory.claim_model_requests_v1(text,integer,integer) FROM PUBLIC,factory_runtime;
REVOKE ALL ON FUNCTION factory.start_model_request_dispatch_v1(char(64),text,char(64)) FROM PUBLIC,factory_runtime;
REVOKE ALL ON FUNCTION factory.record_model_request_dispatch_v1(char(64),text,char(64),text,text,char(64)) FROM PUBLIC,factory_runtime;
REVOKE ALL ON FUNCTION factory.reconcile_model_requests_v1(text,integer) FROM PUBLIC,factory_runtime;
GRANT EXECUTE ON FUNCTION factory.claim_model_requests_v1(text,integer,integer) TO factory_result_dispatcher;
GRANT EXECUTE ON FUNCTION factory.start_model_request_dispatch_v1(char(64),text,char(64)) TO factory_result_dispatcher;
GRANT EXECUTE ON FUNCTION factory.record_model_request_dispatch_v1(char(64),text,char(64),text,text,char(64)) TO factory_result_dispatcher;
GRANT EXECUTE ON FUNCTION factory.reconcile_model_requests_v1(text,integer) TO factory_result_dispatcher;
