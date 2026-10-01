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
REVOKE INSERT ON factory.decision_records_v1 FROM factory_runtime;
GRANT SELECT ON factory.decision_records_v1 TO factory_runtime;
-- UPDATE/DELETE are deliberately absent. Corrections append superseding records.

CREATE FUNCTION factory.append_decision_v1(
  p_record_canonical text,
  p_record_digest char(64),
  p_run_id uuid,
  p_fence bigint
) RETURNS char(64)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path=pg_catalog,pg_temp
AS $$
DECLARE
  v_record jsonb;
  v_task factory.tasks%ROWTYPE;
  v_run factory.runs%ROWTYPE;
  v_intent factory.accepted_intents%ROWTYPE;
  v_existing char(64);
  v_unavailable constant text := 'cc37cbe49cbf74f722413d345a76197162a263353554ae3eb463da8fc249c14d';
BEGIN
  IF p_record_canonical IS NULL OR octet_length(p_record_canonical)>65536
    OR trim(factory.execution_contract_hash(NULL,p_record_canonical)) IS DISTINCT FROM trim(p_record_digest)
  THEN RAISE EXCEPTION 'invalid decision digest'; END IF;
  BEGIN v_record := p_record_canonical::jsonb;
  EXCEPTION WHEN others THEN RAISE EXCEPTION 'invalid decision json'; END;

  IF jsonb_typeof(v_record)<>'object' OR (SELECT count(*) FROM jsonb_object_keys(v_record))<>23
    OR NOT v_record ?& ARRAY['schema_version','decision_id','repository_id','task_id','run_id','attempt_id','fence','observed_at','decision_kind','rule_id','rule_version','facts','outcome','reason_code','base_sha','head_sha','context_digest','spec_digest','profile_digest','evidence_refs','constraints','next_step','supersedes']
    OR v_record->>'schema_version'<>'1'
    OR v_record->>'decision_kind' NOT IN ('scope','retry','state','validation','qualification','prediction')
    OR v_record->>'outcome' NOT IN ('observed','blocked','unknown','rejected','allowed')
    OR v_record->>'next_step' NOT IN ('analyze','verify','reconcile','await_human','none')
    OR jsonb_typeof(v_record->'facts')<>'array' OR jsonb_array_length(v_record->'facts')>32
    OR jsonb_typeof(v_record->'evidence_refs')<>'array' OR jsonb_array_length(v_record->'evidence_refs')>32
    OR jsonb_typeof(v_record->'constraints')<>'array' OR jsonb_array_length(v_record->'constraints')>32
  THEN RAISE EXCEPTION 'invalid decision shape'; END IF;

  IF v_record->>'decision_id' !~ '^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$'
    OR v_record->>'repository_id' !~ '^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$'
    OR v_record->>'rule_id' !~ '^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$'
    OR v_record->>'rule_version' !~ '^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$'
    OR v_record->>'reason_code' !~ '^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$'
    OR v_record->>'base_sha' !~ '^[0-9a-f]{40}$' OR v_record->>'head_sha' !~ '^[0-9a-f]{40}$'
    OR v_record->>'context_digest' !~ '^[0-9a-f]{64}$'
    OR v_record->>'spec_digest' !~ '^[0-9a-f]{64}$'
    OR v_record->>'profile_digest' !~ '^[0-9a-f]{64}$'
    OR (v_record->>'supersedes') IS NOT NULL AND v_record->>'supersedes' !~ '^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$'
  THEN RAISE EXCEPTION 'invalid decision scalar'; END IF;
  BEGIN
    PERFORM (v_record->>'task_id')::uuid, (v_record->>'run_id')::uuid,
      (v_record->>'attempt_id')::uuid, (v_record->>'observed_at')::timestamptz,
      (v_record->>'fence')::bigint;
  EXCEPTION WHEN others THEN RAISE EXCEPTION 'invalid decision scalar'; END;

  SELECT * INTO v_run FROM factory.runs WHERE run_id=p_run_id FOR UPDATE;
  SELECT * INTO v_task FROM factory.tasks WHERE task_id=v_run.task_id FOR UPDATE;
  SELECT * INTO v_intent FROM factory.accepted_intents WHERE intent_id=v_task.intent_id;
  IF NOT FOUND OR v_task.current_run_id IS DISTINCT FROM p_run_id
    OR v_task.current_fence IS DISTINCT FROM p_fence OR v_run.fence IS DISTINCT FROM p_fence
    OR v_run.state<>'leased'
    OR v_run.lease_expires_at<=clock_timestamp() OR v_run.deadline_at<=clock_timestamp()
    OR v_record->>'repository_id' IS DISTINCT FROM v_task.repository_id
    OR v_record->>'task_id' IS DISTINCT FROM v_task.task_id::text
    OR v_record->>'run_id' IS DISTINCT FROM v_run.run_id::text
    OR v_record->>'fence' IS DISTINCT FROM p_fence::text
    OR NOT EXISTS (SELECT 1 FROM factory.attempts a WHERE a.attempt_id=(v_record->>'attempt_id')::uuid AND a.task_id=v_task.task_id AND a.run_id=v_run.run_id)
    OR v_record->>'base_sha' IS DISTINCT FROM trim(v_intent.exact_base_sha)
    OR v_record->>'head_sha' IS DISTINCT FROM v_intent.body->'m0_authority'->>'exact_head_sha'
    OR v_record->>'spec_digest' IS DISTINCT FROM trim(v_intent.spec_digest)
  THEN RAISE EXCEPTION 'decision authority mismatch'; END IF;

  SELECT record_digest INTO v_existing FROM factory.decision_records_v1
    WHERE repository_id=v_task.repository_id AND decision_id=v_record->>'decision_id';
  IF v_existing IS NOT NULL THEN
    IF trim(v_existing)=trim(p_record_digest) THEN RETURN v_existing; END IF;
    RETURN NULL;
  END IF;

  -- Context/profile registries, evidence manifests, prediction sources and a general
  -- rule registry arrive in later contours. This contour fails closed: only the
  -- state-transition rule, empty evidence and the explicit unavailable binding
  -- digest can be persisted.
  IF v_record->>'decision_kind'<>'state'
    OR v_record->>'rule_id'<>'FACTORY-STATE-TRANSITION' OR v_record->>'rule_version'<>'1'
    OR v_record->>'context_digest'<>v_unavailable OR v_record->>'profile_digest'<>v_unavailable
    OR v_record->'evidence_refs'<>'[]'::jsonb
    OR v_record->'constraints'<>'["scope_bound"]'::jsonb
  THEN RAISE EXCEPTION 'decision source unavailable'; END IF;
  IF jsonb_array_length(v_record->'facts')<>2
    OR EXISTS (SELECT 1 FROM jsonb_array_elements(v_record->'facts') f
      WHERE jsonb_typeof(f)<>'object' OR (SELECT count(*) FROM jsonb_object_keys(f))<>2
        OR NOT f ?& ARRAY['name','value'] OR jsonb_typeof(f->'name')<>'string'
        OR jsonb_typeof(f->'value')<>'string')
    OR (SELECT count(DISTINCT f->>'name') FROM jsonb_array_elements(v_record->'facts') f)<>2
    OR NOT EXISTS (SELECT 1 FROM jsonb_array_elements(v_record->'facts') f
      WHERE f->>'name'='from_state' AND f->>'value'=v_task.state)
    OR NOT EXISTS (SELECT 1 FROM jsonb_array_elements(v_record->'facts') f
      WHERE f->>'name'='target' AND f->>'value' IN
        ('inbox','triaged','waiting_design_approval','queued','leased','analyzing','implementing','verifying','reviewing','ready_for_human','retry','needs_human','dead','cancelled','superseded'))
  THEN RAISE EXCEPTION 'invalid state decision facts'; END IF;
  IF (v_record->>'supersedes') IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM factory.decision_records_v1 d
    WHERE d.repository_id=v_task.repository_id AND d.decision_id=v_record->>'supersedes'
      AND d.task_id=v_task.task_id AND d.run_id=v_run.run_id
  ) THEN RAISE EXCEPTION 'decision supersession mismatch'; END IF;

  INSERT INTO factory.decision_records_v1(repository_id,decision_id,task_id,run_id,record_digest,record,supersedes)
  VALUES(v_task.repository_id,v_record->>'decision_id',v_task.task_id,v_run.run_id,p_record_digest,v_record,v_record->>'supersedes')
  ON CONFLICT DO NOTHING;
  SELECT record_digest INTO v_existing FROM factory.decision_records_v1
    WHERE repository_id=v_task.repository_id AND decision_id=v_record->>'decision_id';
  IF trim(v_existing) IS DISTINCT FROM trim(p_record_digest) THEN RETURN NULL; END IF;
  RETURN v_existing;
END $$;
REVOKE ALL ON FUNCTION factory.append_decision_v1(text,char(64),uuid,bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION factory.append_decision_v1(text,char(64),uuid,bigint) TO factory_runtime;
