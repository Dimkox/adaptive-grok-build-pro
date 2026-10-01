-- Immutable, task-bound observations for optional Factory v1.5 runtimes.
CREATE TABLE factory.v15_runtime_evaluations (
  task_id uuid PRIMARY KEY REFERENCES factory.tasks(task_id) ON DELETE RESTRICT,
  repository_id text NOT NULL,
  candidate_sha char(40) NOT NULL CHECK (candidate_sha ~ '^[0-9a-f]{40}$'),
  config_digest char(64) NOT NULL CHECK (config_digest ~ '^[0-9a-f]{64}$'),
  evidence_digest char(64) UNIQUE NOT NULL CHECK (evidence_digest ~ '^[0-9a-f]{64}$'),
  body jsonb NOT NULL CHECK (octet_length(body::text) <= 1048576),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE FUNCTION factory.v15_record_runtime_evaluation(p_body jsonb) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE v_task uuid; v_repository text; v_prior jsonb; v_intent jsonb;
BEGIN
  IF NOT factory.execution_object_has_exact_keys(p_body,ARRAY[
    'schema_version','tenant_id','repository_id','task_id','candidate_sha','config_digest',
    'fpf_status','vibevm_status','prediction_status','timing','qualification','evidence_digest'])
    OR p_body->'schema_version' IS DISTINCT FROM '1'::jsonb
    OR jsonb_typeof(p_body->'tenant_id') IS DISTINCT FROM 'string'
    OR jsonb_typeof(p_body->'repository_id') IS DISTINCT FROM 'string'
    OR jsonb_typeof(p_body->'task_id') IS DISTINCT FROM 'string'
    OR jsonb_typeof(p_body->'candidate_sha') IS DISTINCT FROM 'string'
    OR jsonb_typeof(p_body->'config_digest') IS DISTINCT FROM 'string'
    OR jsonb_typeof(p_body->'evidence_digest') IS DISTINCT FROM 'string'
    OR jsonb_typeof(p_body->'timing') IS DISTINCT FROM 'object'
    OR jsonb_typeof(p_body->'qualification') IS DISTINCT FROM 'object'
    OR p_body->>'tenant_id'<>p_body->>'repository_id'
    OR p_body->>'candidate_sha'!~'^[0-9a-f]{40}$'
    OR p_body->>'config_digest'!~'^[0-9a-f]{64}$'
    OR p_body->>'evidence_digest'!~'^[0-9a-f]{64}$'
    OR p_body->>'fpf_status' NOT IN ('supported','not_evaluated','unavailable')
    OR p_body->>'vibevm_status' NOT IN ('supported','not_evaluated','unavailable')
    OR p_body->>'prediction_status' NOT IN ('available','not_qualified','unavailable')
  THEN RETURN false; END IF;
  v_task=(p_body->>'task_id')::uuid;
  SELECT task.repository_id,intent.body INTO v_repository,v_intent
  FROM factory.tasks task JOIN factory.accepted_intents intent ON intent.intent_id=task.intent_id
  WHERE task.task_id=v_task;
  IF NOT FOUND OR p_body->>'repository_id'<>v_repository
    OR p_body->>'candidate_sha'<>v_intent#>>'{m0_authority,exact_head_sha}'
    OR p_body->>'evidence_digest'<>factory.execution_contract_hash(
      NULL::text,factory.execution_canonical_json(p_body-'evidence_digest'))
  THEN RETURN false; END IF;
  SELECT body INTO v_prior FROM factory.v15_runtime_evaluations WHERE task_id=v_task;
  IF FOUND THEN RETURN v_prior=p_body; END IF;
  INSERT INTO factory.v15_runtime_evaluations(
    task_id,repository_id,candidate_sha,config_digest,evidence_digest,body)
  VALUES(v_task,v_repository,p_body->>'candidate_sha',p_body->>'config_digest',
    p_body->>'evidence_digest',p_body);
  RETURN true;
EXCEPTION WHEN invalid_text_representation OR check_violation OR unique_violation THEN RETURN false;
END $$;

CREATE FUNCTION factory.v15_runtime_evaluation(p_task uuid) RETURNS jsonb
LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
  SELECT body FROM factory.v15_runtime_evaluations WHERE task_id=p_task
$$;

REVOKE ALL ON TABLE factory.v15_runtime_evaluations FROM PUBLIC,factory_runtime,factory_migrator;
REVOKE ALL ON FUNCTION factory.v15_record_runtime_evaluation(jsonb),
  factory.v15_runtime_evaluation(uuid) FROM PUBLIC,factory_runtime,factory_migrator;
GRANT EXECUTE ON FUNCTION factory.v15_record_runtime_evaluation(jsonb),
  factory.v15_runtime_evaluation(uuid) TO factory_runtime;
