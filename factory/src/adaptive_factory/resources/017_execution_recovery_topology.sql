-- Forward-only M5 recovery overlay. Migrations 001-016 remain immutable.
-- Counters begin at the schema-17 epoch: existing rows are deliberately not scanned.
-- Quiesce execution writers before applying because trigger installation takes table locks.
DO $$
BEGIN
  IF current_setting('server_version_num')::integer < 170000 THEN
    RAISE EXCEPTION 'M5 execution recovery requires PostgreSQL 17 or newer';
  END IF;
END;
$$;

LOCK TABLE factory.execution_packets, factory.execution_manifests,
  factory.execution_stage_events, factory.execution_proposals
  IN SHARE ROW EXCLUSIVE MODE;

CREATE TABLE factory.execution_recovery_jobs (
  run_id uuid PRIMARY KEY REFERENCES factory.runs(run_id) ON DELETE RESTRICT,
  task_id uuid NOT NULL,
  manifest_digest char(64) NOT NULL UNIQUE,
  workspace_handle text NOT NULL CHECK (workspace_handle ~ '^workspace:[0-9a-f]{64}$'),
  candidate_updated_at timestamptz NOT NULL,
  terminal_stage text NOT NULL CHECK (terminal_stage IN ('orphaned','cancelled')),
  status text NOT NULL CHECK (status IN ('pending','claimed','failed','succeeded')),
  claim_token uuid,
  claim_fence bigint NOT NULL DEFAULT 0 CHECK (claim_fence >= 0),
  claim_expires_at timestamptz,
  next_claim_at timestamptz,
  attempt_count integer NOT NULL DEFAULT 0 CHECK (attempt_count BETWEEN 0 AND 1000000),
  failure_count integer NOT NULL DEFAULT 0 CHECK (failure_count BETWEEN 0 AND 1000000),
  last_failure_code text CHECK (
    last_failure_code IS NULL OR last_failure_code='workspace_cleanup_failed'
  ),
  last_failed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  completed_at timestamptz,
  FOREIGN KEY (run_id,task_id) REFERENCES factory.runs(run_id,task_id) ON DELETE RESTRICT,
  FOREIGN KEY (manifest_digest,run_id)
    REFERENCES factory.execution_manifests(manifest_digest,run_id) ON DELETE RESTRICT,
  UNIQUE (run_id,task_id,manifest_digest,workspace_handle,candidate_updated_at),
  CHECK ((status='claimed')=(claim_token IS NOT NULL AND claim_expires_at IS NOT NULL)),
  CHECK ((status='succeeded')=(completed_at IS NOT NULL)),
  CHECK ((status='succeeded')=(next_claim_at IS NULL)),
  CHECK (status='claimed' OR claim_token IS NULL),
  CHECK (status='claimed' OR claim_expires_at IS NULL),
  CHECK (status='succeeded' OR next_claim_at IS NOT NULL),
  CHECK (
    (failure_count=0 AND last_failure_code IS NULL AND last_failed_at IS NULL)
    OR (failure_count>0 AND last_failure_code IS NOT NULL AND last_failed_at IS NOT NULL)
  )
);

CREATE INDEX execution_recovery_jobs_claimable
  ON factory.execution_recovery_jobs(next_claim_at,updated_at,run_id)
  WHERE status<>'succeeded';

CREATE TABLE factory.execution_recovery_claims (
  run_id uuid NOT NULL REFERENCES factory.execution_recovery_jobs(run_id) ON DELETE RESTRICT,
  task_id uuid NOT NULL,
  manifest_digest char(64) NOT NULL,
  workspace_handle text NOT NULL CHECK (workspace_handle ~ '^workspace:[0-9a-f]{64}$'),
  candidate_updated_at timestamptz NOT NULL,
  claim_fence bigint NOT NULL CHECK (claim_fence > 0),
  claim_token uuid NOT NULL UNIQUE,
  transition text NOT NULL CHECK (transition IN ('orphaned','cancelled','cleanup_retry')),
  source text NOT NULL CHECK (source IN ('fresh','cleanup_retry')),
  advances_discovery_cursor boolean NOT NULL,
  claimed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  claim_expires_at timestamptz NOT NULL,
  PRIMARY KEY (run_id,claim_fence),
  FOREIGN KEY (
    run_id,task_id,manifest_digest,workspace_handle,candidate_updated_at
  ) REFERENCES factory.execution_recovery_jobs(
    run_id,task_id,manifest_digest,workspace_handle,candidate_updated_at
  ) ON DELETE RESTRICT,
  CHECK (claim_expires_at > claimed_at),
  CHECK (
    (source='fresh' AND advances_discovery_cursor
      AND transition IN ('orphaned','cancelled'))
    OR (source='cleanup_retry' AND NOT advances_discovery_cursor
      AND transition IN ('cancelled','cleanup_retry'))
  )
);

CREATE TABLE factory.execution_recovery_outcomes (
  run_id uuid NOT NULL,
  claim_fence bigint NOT NULL,
  outcome text NOT NULL CHECK (outcome IN ('succeeded','failed')),
  failure_code text,
  recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (run_id,claim_fence),
  FOREIGN KEY (run_id,claim_fence)
    REFERENCES factory.execution_recovery_claims(run_id,claim_fence) ON DELETE RESTRICT,
  CHECK (
    (outcome='failed' AND failure_code='workspace_cleanup_failed')
    OR (outcome='succeeded' AND failure_code IS NULL)
  )
);

CREATE TABLE factory.execution_metric_counters (
  singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
  execution_claimed bigint NOT NULL DEFAULT 0 CHECK (execution_claimed >= 0),
  stage_prepared bigint NOT NULL DEFAULT 0 CHECK (stage_prepared >= 0),
  stage_running bigint NOT NULL DEFAULT 0 CHECK (stage_running >= 0),
  stage_collecting bigint NOT NULL DEFAULT 0 CHECK (stage_collecting >= 0),
  stage_completed bigint NOT NULL DEFAULT 0 CHECK (stage_completed >= 0),
  stage_failed bigint NOT NULL DEFAULT 0 CHECK (stage_failed >= 0),
  stage_needs_human bigint NOT NULL DEFAULT 0 CHECK (stage_needs_human >= 0),
  stage_cancelled bigint NOT NULL DEFAULT 0 CHECK (stage_cancelled >= 0),
  stage_orphaned bigint NOT NULL DEFAULT 0 CHECK (stage_orphaned >= 0),
  proposal_note bigint NOT NULL DEFAULT 0 CHECK (proposal_note >= 0),
  proposal_artifact bigint NOT NULL DEFAULT 0 CHECK (proposal_artifact >= 0),
  proposal_usage bigint NOT NULL DEFAULT 0 CHECK (proposal_usage >= 0),
  proposal_terminal bigint NOT NULL DEFAULT 0 CHECK (proposal_terminal >= 0),
  recovery_claimed bigint NOT NULL DEFAULT 0 CHECK (recovery_claimed >= 0),
  recovery_orphaned bigint NOT NULL DEFAULT 0 CHECK (recovery_orphaned >= 0),
  recovery_cancelled bigint NOT NULL DEFAULT 0 CHECK (recovery_cancelled >= 0),
  cleanup_succeeded bigint NOT NULL DEFAULT 0 CHECK (cleanup_succeeded >= 0),
  cleanup_failed bigint NOT NULL DEFAULT 0 CHECK (cleanup_failed >= 0)
);

INSERT INTO factory.execution_metric_counters(singleton) VALUES (true);

CREATE FUNCTION factory.execution_metric_increment(p_column text) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
BEGIN
  IF p_column='execution_claimed' THEN
    UPDATE factory.execution_metric_counters SET execution_claimed=CASE
      WHEN execution_claimed<9223372036854775807 THEN execution_claimed+1 ELSE execution_claimed END
      WHERE singleton;
  ELSIF p_column='stage_prepared' THEN
    UPDATE factory.execution_metric_counters SET stage_prepared=CASE
      WHEN stage_prepared<9223372036854775807 THEN stage_prepared+1 ELSE stage_prepared END WHERE singleton;
  ELSIF p_column='stage_running' THEN
    UPDATE factory.execution_metric_counters SET stage_running=CASE
      WHEN stage_running<9223372036854775807 THEN stage_running+1 ELSE stage_running END WHERE singleton;
  ELSIF p_column='stage_collecting' THEN
    UPDATE factory.execution_metric_counters SET stage_collecting=CASE
      WHEN stage_collecting<9223372036854775807 THEN stage_collecting+1 ELSE stage_collecting END WHERE singleton;
  ELSIF p_column='stage_completed' THEN
    UPDATE factory.execution_metric_counters SET stage_completed=CASE
      WHEN stage_completed<9223372036854775807 THEN stage_completed+1 ELSE stage_completed END WHERE singleton;
  ELSIF p_column='stage_failed' THEN
    UPDATE factory.execution_metric_counters SET stage_failed=CASE
      WHEN stage_failed<9223372036854775807 THEN stage_failed+1 ELSE stage_failed END WHERE singleton;
  ELSIF p_column='stage_needs_human' THEN
    UPDATE factory.execution_metric_counters SET stage_needs_human=CASE
      WHEN stage_needs_human<9223372036854775807 THEN stage_needs_human+1 ELSE stage_needs_human END WHERE singleton;
  ELSIF p_column='stage_cancelled' THEN
    UPDATE factory.execution_metric_counters SET stage_cancelled=CASE
      WHEN stage_cancelled<9223372036854775807 THEN stage_cancelled+1 ELSE stage_cancelled END WHERE singleton;
  ELSIF p_column='stage_orphaned' THEN
    UPDATE factory.execution_metric_counters SET stage_orphaned=CASE
      WHEN stage_orphaned<9223372036854775807 THEN stage_orphaned+1 ELSE stage_orphaned END WHERE singleton;
  ELSIF p_column='proposal_note' THEN
    UPDATE factory.execution_metric_counters SET proposal_note=CASE
      WHEN proposal_note<9223372036854775807 THEN proposal_note+1 ELSE proposal_note END WHERE singleton;
  ELSIF p_column='proposal_artifact' THEN
    UPDATE factory.execution_metric_counters SET proposal_artifact=CASE
      WHEN proposal_artifact<9223372036854775807 THEN proposal_artifact+1 ELSE proposal_artifact END WHERE singleton;
  ELSIF p_column='proposal_usage' THEN
    UPDATE factory.execution_metric_counters SET proposal_usage=CASE
      WHEN proposal_usage<9223372036854775807 THEN proposal_usage+1 ELSE proposal_usage END WHERE singleton;
  ELSIF p_column='proposal_terminal' THEN
    UPDATE factory.execution_metric_counters SET proposal_terminal=CASE
      WHEN proposal_terminal<9223372036854775807 THEN proposal_terminal+1 ELSE proposal_terminal END WHERE singleton;
  ELSE
    RAISE EXCEPTION 'unsupported execution metric';
  END IF;
END;
$$;

CREATE FUNCTION factory.execution_metric_row_delta() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
BEGIN
  IF TG_TABLE_NAME='execution_packets' THEN
    PERFORM factory.execution_metric_increment('execution_claimed');
  ELSIF TG_TABLE_NAME='execution_stage_events' THEN
    PERFORM factory.execution_metric_increment('stage_' || NEW.stage);
  ELSIF TG_TABLE_NAME='execution_proposals' THEN
    PERFORM factory.execution_metric_increment('proposal_' || NEW.proposal_kind);
  ELSE
    RAISE EXCEPTION 'unsupported execution metric source';
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER execution_packets_metric_delta AFTER INSERT ON factory.execution_packets
  FOR EACH ROW EXECUTE FUNCTION factory.execution_metric_row_delta();
CREATE TRIGGER execution_stage_events_metric_delta AFTER INSERT ON factory.execution_stage_events
  FOR EACH ROW EXECUTE FUNCTION factory.execution_metric_row_delta();
CREATE TRIGGER execution_proposals_metric_delta AFTER INSERT ON factory.execution_proposals
  FOR EACH ROW EXECUTE FUNCTION factory.execution_metric_row_delta();

CREATE FUNCTION factory.execution_recovery_require_bounds() RETURNS void
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
BEGIN
  IF current_setting('statement_timeout')::interval='0 seconds'::interval
    OR current_setting('statement_timeout')::interval>'5 seconds'::interval
  THEN RAISE EXCEPTION 'bounded recovery statement timeout required'; END IF;
  IF current_setting('lock_timeout')::interval='0 seconds'::interval
    OR current_setting('lock_timeout')::interval>'500 milliseconds'::interval
  THEN RAISE EXCEPTION 'bounded recovery lock timeout required'; END IF;
  IF current_setting('transaction_timeout')::interval='0 seconds'::interval
    OR current_setting('transaction_timeout')::interval>'3 seconds'::interval
  THEN RAISE EXCEPTION 'bounded recovery transaction timeout required'; END IF;
END;
$$;

CREATE FUNCTION factory.execution_recovery_context(
  p_task_id uuid,p_run_id uuid,p_manifest_digest char(64),p_workspace_handle text,
  p_updated_at timestamptz
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE
  v_run_released_at timestamptz;
  v_allocation_released_at timestamptz;
  v_context record;
BEGIN
  PERFORM factory.execution_recovery_require_bounds();
  IF p_task_id IS NULL OR p_run_id IS NULL OR p_manifest_digest IS NULL
    OR p_workspace_handle IS NULL OR p_updated_at IS NULL
  THEN RETURN NULL; END IF;
  IF EXISTS(
    SELECT 1 FROM factory.execution_recovery_jobs job
    WHERE job.run_id=p_run_id AND job.task_id=p_task_id
      AND job.manifest_digest=p_manifest_digest
      AND job.workspace_handle=p_workspace_handle
      AND job.candidate_updated_at=p_updated_at
  ) THEN
    RETURN jsonb_build_object('existing_job',true);
  END IF;
  SELECT run.released_at,allocation.released_at
    INTO v_run_released_at,v_allocation_released_at
    FROM factory.runs run
    JOIN factory.capacity_allocations allocation
      ON allocation.run_id=run.run_id AND allocation.task_id=run.task_id
    JOIN factory.execution_manifests manifest
      ON manifest.run_id=run.run_id AND manifest.task_id=run.task_id
    WHERE run.task_id=p_task_id AND run.run_id=p_run_id
      AND manifest.manifest_digest=p_manifest_digest
      AND manifest.workspace_handle=p_workspace_handle
      AND manifest.updated_at=p_updated_at;
  IF NOT FOUND THEN RETURN NULL; END IF;
  IF (v_run_released_at IS NULL) IS DISTINCT FROM
    (v_allocation_released_at IS NULL)
  THEN
    RAISE EXCEPTION USING ERRCODE='22000',
      MESSAGE='execution recovery release state is inconsistent';
  END IF;
  IF v_run_released_at IS NOT NULL THEN
    RETURN jsonb_build_object('released',true);
  END IF;
  IF v_run_released_at IS NULL
    AND NOT factory.capacity_lock_run(p_run_id)
  THEN RETURN NULL; END IF;
  SELECT task.state AS task_state,task.current_run_id,task.current_fence,
    task.repair_count,task.repair_limit,run.owner_id,run.role,run.fence,
    run.lease_expires_at,run.packet_digest,run.state AS run_state,
    run.released_at AS run_released_at,
    allocation.released_at AS allocation_released_at,
    (run.lease_expires_at<=clock_timestamp()
      OR task.deadline_at<=clock_timestamp()) AS recovery_due
    INTO v_context
    FROM factory.tasks task
    JOIN factory.runs run ON run.task_id=task.task_id
    JOIN factory.capacity_allocations allocation
      ON allocation.run_id=run.run_id AND allocation.task_id=task.task_id
    JOIN factory.execution_manifests manifest
      ON manifest.run_id=run.run_id AND manifest.task_id=task.task_id
    WHERE task.task_id=p_task_id AND run.run_id=p_run_id
      AND manifest.manifest_digest=p_manifest_digest
      AND manifest.workspace_handle=p_workspace_handle
      AND manifest.updated_at=p_updated_at
    FOR UPDATE OF task,run,allocation,manifest;
  IF NOT FOUND THEN RETURN NULL; END IF;
  IF (v_context.run_released_at IS NULL) IS DISTINCT FROM
    (v_context.allocation_released_at IS NULL)
  THEN
    RAISE EXCEPTION USING ERRCODE='22000',
      MESSAGE='execution recovery release state changed inconsistently';
  END IF;
  RETURN jsonb_build_object(
    'task_state',v_context.task_state,
    'current_run_id',to_jsonb(v_context.current_run_id),
    'current_fence',to_jsonb(v_context.current_fence),
    'repair_count',v_context.repair_count,'repair_limit',v_context.repair_limit,
    'owner',v_context.owner_id,'role',v_context.role,'fence',v_context.fence,
    'expires_at',to_jsonb(v_context.lease_expires_at),
    'packet_digest',trim(v_context.packet_digest),'run_state',v_context.run_state,
    'run_released',v_context.run_released_at IS NOT NULL,
    'allocation_released',v_context.allocation_released_at IS NOT NULL,
    'recovery_due',v_context.recovery_due,'released',false
  );
END;
$$;

CREATE FUNCTION factory.execution_recovery_candidates(
  p_limit integer,p_updated_at timestamptz,p_run_id uuid
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE
  v_now timestamptz := clock_timestamp();
  v_page jsonb;
BEGIN
  PERFORM factory.execution_recovery_require_bounds();
  IF p_limit IS NULL OR p_limit NOT BETWEEN 2 AND 100
    OR ((p_updated_at IS NULL) IS DISTINCT FROM (p_run_id IS NULL))
  THEN RETURN NULL; END IF;
  IF p_updated_at IS NULL THEN
    WITH retry_base AS MATERIALIZED (
      SELECT job.task_id,job.run_id,job.manifest_digest,job.workspace_handle,
        job.candidate_updated_at AS updated_at,job.next_claim_at AS available_at,
        job.updated_at AS queue_updated_at,
        row_number() OVER (
          ORDER BY job.next_claim_at,job.updated_at,job.run_id
        ) AS lane_rank,'cleanup_retry'::text AS source,1 AS source_order
      FROM factory.execution_recovery_jobs job
      WHERE job.status<>'succeeded' AND job.next_claim_at<=v_now
        AND (job.status<>'claimed' OR job.claim_expires_at<=v_now)
      ORDER BY job.next_claim_at,job.updated_at,job.run_id LIMIT p_limit/2
    ), fresh_raw AS MATERIALIZED (
      SELECT manifest.task_id,manifest.run_id,manifest.manifest_digest,
        manifest.workspace_handle,manifest.updated_at,
        manifest.updated_at AS available_at,manifest.updated_at AS queue_updated_at
      FROM factory.execution_manifests manifest
      WHERE manifest.terminal_at IS NULL
        AND NOT EXISTS (
          SELECT 1 FROM factory.execution_recovery_jobs job
          WHERE job.run_id=manifest.run_id
        )
      ORDER BY manifest.updated_at,manifest.run_id
      LIMIT p_limit-(SELECT count(*) FROM retry_base)
    ), fresh_candidates AS MATERIALIZED (
      SELECT fresh.*,row_number() OVER (
        ORDER BY fresh.updated_at,fresh.run_id
      ) AS lane_rank,'fresh'::text AS source,0 AS source_order
      FROM fresh_raw fresh
    ), retry_extra AS MATERIALIZED (
      SELECT job.task_id,job.run_id,job.manifest_digest,job.workspace_handle,
        job.candidate_updated_at AS updated_at,job.next_claim_at AS available_at,
        job.updated_at AS queue_updated_at,
        (SELECT count(*) FROM retry_base)+row_number() OVER (
          ORDER BY job.next_claim_at,job.updated_at,job.run_id
        ) AS lane_rank,'cleanup_retry'::text AS source,1 AS source_order
      FROM factory.execution_recovery_jobs job
      WHERE job.status<>'succeeded' AND job.next_claim_at<=v_now
        AND (job.status<>'claimed' OR job.claim_expires_at<=v_now)
        AND (job.next_claim_at,job.updated_at,job.run_id)>(
          SELECT base.available_at,base.queue_updated_at,base.run_id
          FROM retry_base base
          ORDER BY base.available_at DESC,base.queue_updated_at DESC,
            base.run_id DESC LIMIT 1
        )
      ORDER BY job.next_claim_at,job.updated_at,job.run_id
      LIMIT p_limit-(SELECT count(*) FROM retry_base)
        -(SELECT count(*) FROM fresh_raw)
    ), interleaved AS (
      SELECT * FROM fresh_candidates UNION ALL SELECT * FROM retry_base
      UNION ALL SELECT * FROM retry_extra
    )
    SELECT jsonb_build_object(
      'candidates',COALESCE((
        SELECT jsonb_agg(jsonb_build_object(
          'task_id',candidate.task_id::text,'run_id',candidate.run_id::text,
          'manifest_digest',trim(candidate.manifest_digest),
          'workspace_handle',candidate.workspace_handle,
          'updated_at',to_jsonb(candidate.updated_at),'source',candidate.source
        ) ORDER BY CASE WHEN candidate.lane_rank=1 THEN 0 ELSE 1 END,
          CASE WHEN candidate.lane_rank=1 THEN candidate.source_order ELSE 0 END,
          candidate.available_at,candidate.source_order,candidate.run_id)
        FROM interleaved candidate
      ),'[]'::jsonb),
      'scanned_through',(
        SELECT jsonb_build_object(
          'updated_at',to_jsonb(candidate.updated_at),
          'run_id',candidate.run_id::text
        ) FROM interleaved candidate WHERE candidate.source='fresh'
        ORDER BY candidate.updated_at DESC,candidate.run_id DESC LIMIT 1
      ),
      'exhausted',(SELECT count(*) FROM fresh_raw)<
        p_limit-(SELECT count(*) FROM retry_base)
    ) INTO v_page;
  ELSE
    WITH retry_base AS MATERIALIZED (
      SELECT job.task_id,job.run_id,job.manifest_digest,job.workspace_handle,
        job.candidate_updated_at AS updated_at,job.next_claim_at AS available_at,
        job.updated_at AS queue_updated_at,
        row_number() OVER (
          ORDER BY job.next_claim_at,job.updated_at,job.run_id
        ) AS lane_rank,'cleanup_retry'::text AS source,1 AS source_order
      FROM factory.execution_recovery_jobs job
      WHERE job.status<>'succeeded' AND job.next_claim_at<=v_now
        AND (job.status<>'claimed' OR job.claim_expires_at<=v_now)
      ORDER BY job.next_claim_at,job.updated_at,job.run_id LIMIT p_limit/2
    ), fresh_raw AS MATERIALIZED (
      SELECT manifest.task_id,manifest.run_id,manifest.manifest_digest,
        manifest.workspace_handle,manifest.updated_at,
        manifest.updated_at AS available_at,manifest.updated_at AS queue_updated_at
      FROM factory.execution_manifests manifest
      WHERE manifest.terminal_at IS NULL
        AND (manifest.updated_at,manifest.run_id)>(p_updated_at,p_run_id)
        AND NOT EXISTS (
          SELECT 1 FROM factory.execution_recovery_jobs job
          WHERE job.run_id=manifest.run_id
        )
      ORDER BY manifest.updated_at,manifest.run_id
      LIMIT p_limit-(SELECT count(*) FROM retry_base)
    ), fresh_candidates AS MATERIALIZED (
      SELECT fresh.*,row_number() OVER (
        ORDER BY fresh.updated_at,fresh.run_id
      ) AS lane_rank,'fresh'::text AS source,0 AS source_order
      FROM fresh_raw fresh
    ), retry_extra AS MATERIALIZED (
      SELECT job.task_id,job.run_id,job.manifest_digest,job.workspace_handle,
        job.candidate_updated_at AS updated_at,job.next_claim_at AS available_at,
        job.updated_at AS queue_updated_at,
        (SELECT count(*) FROM retry_base)+row_number() OVER (
          ORDER BY job.next_claim_at,job.updated_at,job.run_id
        ) AS lane_rank,'cleanup_retry'::text AS source,1 AS source_order
      FROM factory.execution_recovery_jobs job
      WHERE job.status<>'succeeded' AND job.next_claim_at<=v_now
        AND (job.status<>'claimed' OR job.claim_expires_at<=v_now)
        AND (job.next_claim_at,job.updated_at,job.run_id)>(
          SELECT base.available_at,base.queue_updated_at,base.run_id
          FROM retry_base base
          ORDER BY base.available_at DESC,base.queue_updated_at DESC,
            base.run_id DESC LIMIT 1
        )
      ORDER BY job.next_claim_at,job.updated_at,job.run_id
      LIMIT p_limit-(SELECT count(*) FROM retry_base)
        -(SELECT count(*) FROM fresh_raw)
    ), interleaved AS (
      SELECT * FROM fresh_candidates UNION ALL SELECT * FROM retry_base
      UNION ALL SELECT * FROM retry_extra
    )
    SELECT jsonb_build_object(
      'candidates',COALESCE((
        SELECT jsonb_agg(jsonb_build_object(
          'task_id',candidate.task_id::text,'run_id',candidate.run_id::text,
          'manifest_digest',trim(candidate.manifest_digest),
          'workspace_handle',candidate.workspace_handle,
          'updated_at',to_jsonb(candidate.updated_at),'source',candidate.source
        ) ORDER BY CASE WHEN candidate.lane_rank=1 THEN 0 ELSE 1 END,
          CASE WHEN candidate.lane_rank=1 THEN candidate.source_order ELSE 0 END,
          candidate.available_at,candidate.source_order,candidate.run_id)
        FROM interleaved candidate
      ),'[]'::jsonb),
      'scanned_through',(
        SELECT jsonb_build_object(
          'updated_at',to_jsonb(candidate.updated_at),
          'run_id',candidate.run_id::text
        ) FROM interleaved candidate WHERE candidate.source='fresh'
        ORDER BY candidate.updated_at DESC,candidate.run_id DESC LIMIT 1
      ),
      'exhausted',(SELECT count(*) FROM fresh_raw)<
        p_limit-(SELECT count(*) FROM retry_base)
    ) INTO v_page;
  END IF;
  RETURN v_page;
END;
$$;

CREATE FUNCTION factory.execution_recovery_claim(
  p_task_id uuid,p_run_id uuid,p_manifest_digest char(64),p_workspace_handle text,
  p_updated_at timestamptz,p_claim_seconds integer
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE
  v_job factory.execution_recovery_jobs%ROWTYPE;
  v_context record;
  v_transition text;
  v_terminal_stage text;
  v_token uuid;
  v_claim_fence bigint;
  v_claim_expires_at timestamptz;
  v_next_sequence bigint;
  v_run_released_at timestamptz;
  v_allocation_released_at timestamptz;
  v_discovery_fresh boolean := false;
  v_existing_job boolean;
BEGIN
  PERFORM factory.execution_recovery_require_bounds();
  IF p_task_id IS NULL OR p_run_id IS NULL OR p_manifest_digest IS NULL
    OR p_workspace_handle IS NULL OR p_updated_at IS NULL
    OR p_claim_seconds IS NULL OR p_claim_seconds NOT BETWEEN 1 AND 300
  THEN RETURN NULL; END IF;
  SELECT EXISTS(
    SELECT 1 FROM factory.execution_recovery_jobs job
    WHERE job.run_id=p_run_id AND job.task_id=p_task_id
      AND job.manifest_digest=p_manifest_digest
      AND job.workspace_handle=p_workspace_handle
      AND job.candidate_updated_at=p_updated_at
  ) INTO v_existing_job;
  IF NOT v_existing_job THEN
    SELECT run.released_at,allocation.released_at
      INTO v_run_released_at,v_allocation_released_at
      FROM factory.runs run
      JOIN factory.capacity_allocations allocation
        ON allocation.run_id=run.run_id AND allocation.task_id=run.task_id
      JOIN factory.execution_manifests manifest
        ON manifest.run_id=run.run_id AND manifest.task_id=run.task_id
      WHERE run.task_id=p_task_id AND run.run_id=p_run_id
        AND manifest.manifest_digest=p_manifest_digest
        AND manifest.workspace_handle=p_workspace_handle
        AND manifest.updated_at=p_updated_at;
    IF NOT FOUND THEN RETURN NULL; END IF;
    IF (v_run_released_at IS NULL) IS DISTINCT FROM
      (v_allocation_released_at IS NULL)
    THEN
      RAISE EXCEPTION USING ERRCODE='22000',
        MESSAGE='execution recovery release state is inconsistent';
    END IF;
    -- A live M4 lease must first be closed through the canonical M4 store path.
    IF v_run_released_at IS NULL THEN RETURN NULL; END IF;
  END IF;
  SELECT task.state AS task_state,run.state AS run_state,
    run.released_at AS run_released_at,
    allocation.released_at AS allocation_released_at,
    manifest.task_id,manifest.run_id,manifest.manifest_digest,
    manifest.workspace_handle,manifest.updated_at,manifest.stage,manifest.terminal_at
    INTO v_context
    FROM factory.tasks task
    JOIN factory.runs run ON run.task_id=task.task_id
    JOIN factory.capacity_allocations allocation
      ON allocation.run_id=run.run_id AND allocation.task_id=task.task_id
    JOIN factory.execution_manifests manifest
      ON manifest.run_id=run.run_id AND manifest.task_id=task.task_id
    WHERE task.task_id=p_task_id AND run.run_id=p_run_id
      AND manifest.manifest_digest=p_manifest_digest
      AND manifest.workspace_handle=p_workspace_handle
      AND (v_existing_job OR manifest.updated_at=p_updated_at)
    FOR UPDATE OF task,run,allocation,manifest SKIP LOCKED;
  IF NOT FOUND OR v_context.run_released_at IS NULL
    OR v_context.allocation_released_at IS NULL
  THEN RETURN NULL; END IF;

  SELECT * INTO v_job FROM factory.execution_recovery_jobs job
    WHERE job.run_id=p_run_id AND job.task_id=p_task_id
      AND job.manifest_digest=p_manifest_digest
      AND job.workspace_handle=p_workspace_handle
      AND job.candidate_updated_at=p_updated_at
    FOR UPDATE SKIP LOCKED;
  IF FOUND THEN
    IF v_job.status='succeeded' OR v_job.next_claim_at>clock_timestamp()
      OR (v_job.status='claimed' AND v_job.claim_expires_at>clock_timestamp())
    THEN RETURN NULL; END IF;
    IF v_context.stage<>v_job.terminal_stage OR v_context.terminal_at IS NULL
      OR EXISTS(
        SELECT 1 FROM factory.workspace_results result
        WHERE result.run_id=v_job.run_id
      )
    THEN RETURN NULL; END IF;
    v_transition=CASE
      WHEN v_job.status='pending' AND v_job.attempt_count=0
        THEN v_job.terminal_stage
      ELSE 'cleanup_retry'
    END;
    v_terminal_stage=v_job.terminal_stage;
    v_claim_fence=CASE
      WHEN v_job.status='pending' AND v_job.attempt_count=0 THEN 1
      ELSE v_job.claim_fence+1
    END;
  ELSE
    IF v_context.terminal_at IS NOT NULL OR EXISTS(
        SELECT 1 FROM factory.workspace_results result WHERE result.run_id=p_run_id
      )
    THEN RETURN NULL; END IF;
    v_transition=CASE
      WHEN v_context.task_state IN ('cancelled','superseded')
        AND v_context.run_state='released' THEN 'cancelled'
      ELSE 'orphaned'
    END;
    v_terminal_stage=v_transition;
    v_discovery_fresh=true;
    SELECT COALESCE(max(event.stage_sequence),0)+1 INTO v_next_sequence
      FROM factory.execution_stage_events event
      WHERE event.manifest_digest=p_manifest_digest;
    UPDATE factory.execution_manifests SET stage=v_terminal_stage,
      terminal_at=clock_timestamp(),updated_at=clock_timestamp()
      WHERE manifest_digest=p_manifest_digest AND terminal_at IS NULL;
    IF NOT FOUND THEN
      RAISE EXCEPTION 'recovery manifest transition lost after authoritative lock';
    END IF;
    INSERT INTO factory.execution_stage_events(manifest_digest,stage_sequence,stage)
      VALUES (p_manifest_digest,v_next_sequence,v_terminal_stage);
    v_claim_fence=1;
  END IF;

  v_token=gen_random_uuid();
  v_claim_expires_at=clock_timestamp()+(p_claim_seconds * interval '1 second');
  IF v_job.run_id IS NOT NULL THEN
    UPDATE factory.execution_recovery_jobs SET status='claimed',claim_token=v_token,
      claim_fence=v_claim_fence,claim_expires_at=v_claim_expires_at,
      next_claim_at=v_claim_expires_at,attempt_count=attempt_count+1,
      updated_at=clock_timestamp()
      WHERE run_id=p_run_id;
    IF NOT FOUND THEN
      RAISE EXCEPTION 'recovery cleanup claim disappeared after authoritative lock';
    END IF;
  ELSE
    INSERT INTO factory.execution_recovery_jobs(
      run_id,task_id,manifest_digest,workspace_handle,candidate_updated_at,
      terminal_stage,status,claim_token,claim_fence,claim_expires_at,next_claim_at,
      attempt_count
    ) VALUES (
      p_run_id,p_task_id,p_manifest_digest,p_workspace_handle,p_updated_at,
      v_terminal_stage,'claimed',v_token,v_claim_fence,v_claim_expires_at,
      v_claim_expires_at,1
    );
    UPDATE factory.execution_metric_counters SET
      recovery_orphaned=CASE
        WHEN v_transition='orphaned' AND recovery_orphaned<9223372036854775807
          THEN recovery_orphaned+1 ELSE recovery_orphaned END,
      recovery_cancelled=CASE
        WHEN v_transition='cancelled' AND recovery_cancelled<9223372036854775807
          THEN recovery_cancelled+1 ELSE recovery_cancelled END
      WHERE singleton;
  END IF;
  INSERT INTO factory.execution_recovery_claims(
    run_id,task_id,manifest_digest,workspace_handle,candidate_updated_at,
    claim_fence,claim_token,transition,source,advances_discovery_cursor,
    claim_expires_at
  ) VALUES (
    p_run_id,p_task_id,p_manifest_digest,p_workspace_handle,p_updated_at,
    v_claim_fence,v_token,v_transition,
    CASE WHEN v_discovery_fresh THEN 'fresh' ELSE 'cleanup_retry' END,
    v_discovery_fresh,v_claim_expires_at
  );
  UPDATE factory.execution_metric_counters SET recovery_claimed=CASE
    WHEN recovery_claimed<9223372036854775807 THEN recovery_claimed+1
    ELSE recovery_claimed END WHERE singleton;
  RETURN jsonb_build_object(
    'task_id',p_task_id::text,'run_id',p_run_id::text,
    'manifest_digest',trim(p_manifest_digest),
    'workspace_handle',p_workspace_handle,'updated_at',to_jsonb(p_updated_at),
    'claim_token',v_token::text,'claim_fence',v_claim_fence,
    'claim_expires_at',to_jsonb(v_claim_expires_at),'transition',v_transition,
    'advances_discovery_cursor',v_discovery_fresh,
    'source',CASE WHEN v_discovery_fresh THEN 'fresh' ELSE 'cleanup_retry' END
  );
END;
$$;

CREATE FUNCTION factory.execution_recovery_cancel_task(p_task_id uuid) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE
  v_context record;
  v_next_sequence bigint;
BEGIN
  PERFORM factory.execution_recovery_require_bounds();
  IF p_task_id IS NULL THEN RETURN 'not_eligible'; END IF;
  SELECT run.run_id,run.state AS run_state,run.released_at AS run_released_at,
    allocation.released_at AS allocation_released_at,
    manifest.manifest_digest,manifest.workspace_handle,
    manifest.updated_at AS manifest_updated_at
    INTO v_context
    FROM factory.tasks task
    JOIN factory.runs run ON run.task_id=task.task_id
    JOIN factory.capacity_allocations allocation ON allocation.run_id=run.run_id
    JOIN factory.execution_manifests manifest ON manifest.run_id=run.run_id
    WHERE task.task_id=p_task_id AND task.state IN ('cancelled','superseded')
      AND run.state='released' AND run.released_at IS NOT NULL
      AND allocation.released_at IS NOT NULL AND manifest.terminal_at IS NULL
    ORDER BY run.created_at DESC,run.run_id DESC LIMIT 1
    FOR UPDATE OF task,run,allocation,manifest;
  IF NOT FOUND THEN
    RETURN 'no_execution';
  END IF;
  IF EXISTS(
      SELECT 1 FROM factory.workspace_results result
      WHERE result.run_id=v_context.run_id
    ) THEN RETURN 'already_terminal'; END IF;
  SELECT COALESCE(max(event.stage_sequence),0)+1 INTO v_next_sequence
    FROM factory.execution_stage_events event
    WHERE event.manifest_digest=v_context.manifest_digest;
  UPDATE factory.execution_manifests SET stage='cancelled',terminal_at=clock_timestamp(),
    updated_at=clock_timestamp() WHERE manifest_digest=v_context.manifest_digest
    AND terminal_at IS NULL;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'cancel recovery manifest transition lost after authoritative lock';
  END IF;
  INSERT INTO factory.execution_stage_events(manifest_digest,stage_sequence,stage)
    VALUES (v_context.manifest_digest,v_next_sequence,'cancelled');
  INSERT INTO factory.execution_recovery_jobs(
    run_id,task_id,manifest_digest,workspace_handle,candidate_updated_at,
    terminal_stage,status,next_claim_at
  ) VALUES (
    v_context.run_id,p_task_id,v_context.manifest_digest,v_context.workspace_handle,
    v_context.manifest_updated_at,'cancelled','pending',clock_timestamp()
  );
  UPDATE factory.execution_metric_counters SET recovery_cancelled=CASE
    WHEN recovery_cancelled<9223372036854775807 THEN recovery_cancelled+1
    ELSE recovery_cancelled END WHERE singleton;
  RETURN 'cancelled';
END;
$$;

CREATE FUNCTION factory.execution_recovery_cleanup_succeeded(
  p_task_id uuid,p_run_id uuid,p_manifest_digest char(64),p_workspace_handle text,
  p_updated_at timestamptz,p_source text,p_claim_token uuid,p_claim_fence bigint,
  p_transition text,p_advances_discovery_cursor boolean
) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
BEGIN
  PERFORM factory.execution_recovery_require_bounds();
  IF p_task_id IS NULL OR p_run_id IS NULL OR p_manifest_digest IS NULL
    OR p_workspace_handle IS NULL OR p_updated_at IS NULL OR p_source IS NULL
    OR p_claim_token IS NULL OR p_claim_fence IS NULL OR p_claim_fence<=0
    OR p_transition IS NULL OR p_advances_discovery_cursor IS NULL
  THEN RETURN false; END IF;
  PERFORM 1 FROM factory.execution_recovery_jobs job
    JOIN factory.execution_recovery_claims claim
      ON claim.run_id=job.run_id AND claim.claim_fence=job.claim_fence
    WHERE job.run_id=p_run_id AND job.task_id=p_task_id
      AND job.manifest_digest=p_manifest_digest
      AND job.workspace_handle=p_workspace_handle
      AND job.candidate_updated_at=p_updated_at
      AND job.status='claimed' AND job.claim_token=p_claim_token
      AND job.claim_fence=p_claim_fence
      AND claim.claim_token=p_claim_token AND claim.source=p_source
      AND claim.transition=p_transition
      AND claim.advances_discovery_cursor=p_advances_discovery_cursor
    FOR UPDATE OF job;
  IF NOT FOUND THEN RETURN false; END IF;
  INSERT INTO factory.execution_recovery_outcomes(
    run_id,claim_fence,outcome,failure_code
  ) VALUES (p_run_id,p_claim_fence,'succeeded',NULL);
  UPDATE factory.execution_recovery_jobs SET status='succeeded',claim_token=NULL,
    claim_expires_at=NULL,next_claim_at=NULL,
    completed_at=clock_timestamp(),updated_at=clock_timestamp()
    WHERE run_id=p_run_id;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'recovery success target disappeared after authoritative lock';
  END IF;
  UPDATE factory.execution_metric_counters SET cleanup_succeeded=CASE
    WHEN cleanup_succeeded<9223372036854775807 THEN cleanup_succeeded+1
    ELSE cleanup_succeeded END WHERE singleton;
  RETURN true;
END;
$$;

CREATE FUNCTION factory.execution_recovery_cleanup_failed(
  p_task_id uuid,p_run_id uuid,p_manifest_digest char(64),p_workspace_handle text,
  p_updated_at timestamptz,p_source text,p_claim_token uuid,p_claim_fence bigint,
  p_transition text,p_advances_discovery_cursor boolean
) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
BEGIN
  PERFORM factory.execution_recovery_require_bounds();
  IF p_task_id IS NULL OR p_run_id IS NULL OR p_manifest_digest IS NULL
    OR p_workspace_handle IS NULL OR p_updated_at IS NULL OR p_source IS NULL
    OR p_claim_token IS NULL OR p_claim_fence IS NULL OR p_claim_fence<=0
    OR p_transition IS NULL OR p_advances_discovery_cursor IS NULL
  THEN RETURN false; END IF;
  PERFORM 1 FROM factory.execution_recovery_jobs job
    JOIN factory.execution_recovery_claims claim
      ON claim.run_id=job.run_id AND claim.claim_fence=job.claim_fence
    WHERE job.run_id=p_run_id AND job.task_id=p_task_id
      AND job.manifest_digest=p_manifest_digest
      AND job.workspace_handle=p_workspace_handle
      AND job.candidate_updated_at=p_updated_at
      AND job.status='claimed' AND job.claim_token=p_claim_token
      AND job.claim_fence=p_claim_fence
      AND claim.claim_token=p_claim_token AND claim.source=p_source
      AND claim.transition=p_transition
      AND claim.advances_discovery_cursor=p_advances_discovery_cursor
    FOR UPDATE OF job;
  IF NOT FOUND THEN RETURN false; END IF;
  INSERT INTO factory.execution_recovery_outcomes(
    run_id,claim_fence,outcome,failure_code
  ) VALUES (p_run_id,p_claim_fence,'failed','workspace_cleanup_failed');
  UPDATE factory.execution_recovery_jobs SET status='failed',claim_token=NULL,
    claim_expires_at=NULL,next_claim_at=clock_timestamp()+interval '1 second',
    failure_count=failure_count+1,last_failure_code='workspace_cleanup_failed',
    last_failed_at=clock_timestamp(),updated_at=clock_timestamp()
    WHERE run_id=p_run_id;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'recovery failure target disappeared after authoritative lock';
  END IF;
  UPDATE factory.execution_metric_counters SET cleanup_failed=CASE
    WHEN cleanup_failed<9223372036854775807 THEN cleanup_failed+1
    ELSE cleanup_failed END WHERE singleton;
  RETURN true;
END;
$$;

CREATE FUNCTION factory.read_combined_metrics_snapshot() RETURNS jsonb
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE
  v_snapshot jsonb;
BEGIN
  IF current_setting('statement_timeout')::interval='0 seconds'::interval
    OR current_setting('statement_timeout')::interval>'5 seconds'::interval
  THEN RAISE EXCEPTION 'bounded combined metrics statement timeout required'; END IF;
  IF current_setting('lock_timeout')::interval='0 seconds'::interval
    OR current_setting('lock_timeout')::interval>'500 milliseconds'::interval
  THEN RAISE EXCEPTION 'bounded combined metrics lock timeout required'; END IF;
  IF current_setting('transaction_timeout')::interval='0 seconds'::interval
    OR current_setting('transaction_timeout')::interval>'3 seconds'::interval
  THEN RAISE EXCEPTION 'bounded combined metrics transaction timeout required'; END IF;
  SELECT jsonb_build_object(
    'legacy',to_jsonb(legacy),'execution',to_jsonb(execution)
  ) INTO v_snapshot
    FROM factory.metric_counters legacy
    CROSS JOIN factory.execution_metric_counters execution
    WHERE legacy.singleton AND execution.singleton;
  RETURN v_snapshot;
END;
$$;

REVOKE ALL ON factory.execution_recovery_jobs,
  factory.execution_recovery_claims,factory.execution_recovery_outcomes,
  factory.execution_metric_counters
  FROM PUBLIC,factory_runtime,factory_artifact_attestor;
REVOKE ALL ON FUNCTION factory.execution_metric_increment(text) FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.execution_metric_row_delta() FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.execution_recovery_require_bounds() FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.execution_recovery_context(uuid,uuid,char,text,timestamptz)
  FROM PUBLIC,factory_artifact_attestor;
REVOKE ALL ON FUNCTION factory.execution_recovery_candidates(integer,timestamptz,uuid)
  FROM PUBLIC,factory_artifact_attestor;
REVOKE ALL ON FUNCTION factory.execution_recovery_claim(uuid,uuid,char,text,timestamptz,integer)
  FROM PUBLIC,factory_artifact_attestor;
REVOKE ALL ON FUNCTION factory.execution_recovery_cancel_task(uuid)
  FROM PUBLIC,factory_artifact_attestor;
REVOKE ALL ON FUNCTION factory.execution_recovery_cleanup_succeeded(
  uuid,uuid,char,text,timestamptz,text,uuid,bigint,text,boolean)
  FROM PUBLIC,factory_artifact_attestor;
REVOKE ALL ON FUNCTION factory.execution_recovery_cleanup_failed(
  uuid,uuid,char,text,timestamptz,text,uuid,bigint,text,boolean)
  FROM PUBLIC,factory_artifact_attestor;
REVOKE ALL ON FUNCTION factory.read_combined_metrics_snapshot()
  FROM PUBLIC,factory_artifact_attestor;
GRANT EXECUTE ON FUNCTION factory.execution_recovery_candidates(integer,timestamptz,uuid)
  TO factory_runtime;
GRANT EXECUTE ON FUNCTION factory.execution_recovery_context(uuid,uuid,char,text,timestamptz)
  TO factory_runtime;
GRANT EXECUTE ON FUNCTION factory.execution_recovery_claim(uuid,uuid,char,text,timestamptz,integer)
  TO factory_runtime;
GRANT EXECUTE ON FUNCTION factory.execution_recovery_cancel_task(uuid) TO factory_runtime;
GRANT EXECUTE ON FUNCTION factory.execution_recovery_cleanup_succeeded(
  uuid,uuid,char,text,timestamptz,text,uuid,bigint,text,boolean)
  TO factory_runtime;
GRANT EXECUTE ON FUNCTION factory.execution_recovery_cleanup_failed(
  uuid,uuid,char,text,timestamptz,text,uuid,bigint,text,boolean)
  TO factory_runtime;
GRANT EXECUTE ON FUNCTION factory.read_combined_metrics_snapshot() TO factory_runtime;
