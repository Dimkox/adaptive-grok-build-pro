-- Immutable result admission and durable hand-off to the future 04B dispatcher.
CREATE TABLE factory.result_sources_v1 (
  envelope_digest char(64) PRIMARY KEY CHECK (envelope_digest ~ '^[0-9a-f]{64}$'),
  repository_id text NOT NULL,
  task_id uuid NOT NULL,
  run_id uuid NOT NULL,
  fence bigint NOT NULL CHECK (fence > 0),
  packet_digest char(64) NOT NULL CHECK (packet_digest ~ '^[0-9a-f]{64}$'),
  attempt_id uuid NOT NULL,
  source_operation text NOT NULL CHECK (octet_length(source_operation) BETWEEN 1 AND 128),
  source_digest char(64) NOT NULL CHECK (source_digest ~ '^[0-9a-f]{64}$'),
  outcome text NOT NULL CHECK (outcome IN ('allow','redacted','rejected','unavailable')),
  envelope jsonb NOT NULL CHECK (octet_length(envelope::text) <= 1100000),
  admitted_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  UNIQUE (repository_id,task_id,run_id,attempt_id,source_operation,source_digest),
  FOREIGN KEY (run_id,task_id) REFERENCES factory.runs(run_id,task_id) ON DELETE RESTRICT,
  FOREIGN KEY (attempt_id) REFERENCES factory.attempts(attempt_id) ON DELETE RESTRICT
);

CREATE TABLE factory.result_admission_commands_v1 (
  actor_id text NOT NULL,
  action text NOT NULL CHECK (action='result_admission'),
  idempotency_key char(64) NOT NULL CHECK (idempotency_key ~ '^[0-9a-f]{64}$'),
  request_digest char(64) NOT NULL CHECK (request_digest ~ '^[0-9a-f]{64}$'),
  envelope_digest char(64) NOT NULL REFERENCES factory.result_sources_v1(envelope_digest) ON DELETE RESTRICT,
  correlation_id text NOT NULL CHECK (correlation_id ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$'),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (actor_id,action,idempotency_key)
);

CREATE TABLE factory.next_model_request_outbox_v1 (
  request_digest char(64) PRIMARY KEY CHECK (request_digest ~ '^[0-9a-f]{64}$'),
  envelope_digest char(64) NOT NULL UNIQUE REFERENCES factory.result_sources_v1(envelope_digest) ON DELETE RESTRICT,
  task_id uuid NOT NULL REFERENCES factory.tasks(task_id) ON DELETE RESTRICT,
  run_id uuid NOT NULL,
  attempt_id uuid NOT NULL REFERENCES factory.attempts(attempt_id) ON DELETE RESTRICT,
  state text NOT NULL DEFAULT 'pending' CHECK (state IN ('pending','claimed','delivered','failed')),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  FOREIGN KEY (run_id,task_id) REFERENCES factory.runs(run_id,task_id) ON DELETE RESTRICT
);
CREATE INDEX next_model_request_outbox_v1_pending
  ON factory.next_model_request_outbox_v1(created_at,request_digest) WHERE state='pending';

REVOKE ALL ON factory.result_sources_v1, factory.result_admission_commands_v1, factory.next_model_request_outbox_v1 FROM PUBLIC;
REVOKE INSERT,UPDATE,DELETE ON factory.result_sources_v1, factory.result_admission_commands_v1, factory.next_model_request_outbox_v1 FROM factory_runtime;
GRANT SELECT ON factory.result_sources_v1, factory.result_admission_commands_v1, factory.next_model_request_outbox_v1 TO factory_runtime;

CREATE FUNCTION factory.admit_result_v1(
  p_envelope_canonical text,
  p_envelope_digest char(64),
  p_owner_id text,
  p_idempotency_key text,
  p_request_digest char(64),
  p_request_canonical text,
  p_correlation_id text
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path=pg_catalog,pg_temp
AS $$
DECLARE
  v jsonb; v_request jsonb; v_payload jsonb; v_payload_json json;
  v_task factory.tasks%ROWTYPE; v_run factory.runs%ROWTYPE;
  v_existing char(64); v_created boolean := false; v_command factory.result_admission_commands_v1%ROWTYPE;
  v_pem_pattern text := '-----(BEGIN|END) [A-Z0-9 ]*PRIVATE KEY-----';
  v_sensitive_key_pattern text := '(^|[_-])(authorization|api[_-]?key|access[_-]?token|session[_-]?token|client[_-]?secret|refresh[_-]?token|password|credentials?|secret[_-]?key|private[_-]?key|token|secret)([_-]|$)';
  v_secret_pattern text := regexp_replace($result_secret$
    ((^|[^A-Za-z0-9_])Bearer[ 	]+[A-Za-z0-9._~+/=-]+
    |(^|[^A-Za-z0-9_-])([A-Za-z0-9]+[_-])*Authorization[ 	]*[=:][ 	]*[^\r\n]*
    |(sk-|ghp_|github_pat_)[A-Za-z0-9_-]+
    |(^|[^A-Za-z0-9_])(AKIA|ASIA)[A-Z0-9]{16}([^A-Za-z0-9_]|$)
    |(^|[^A-Za-z0-9_-])["']?([a-z0-9]+[_-])*(api[_-]?key|access[_-]?token|session[_-]?token|client[_-]?secret|refresh[_-]?token|password|credential|secret[_-]?key|private[_-]?key|token|secret)([_-][a-z0-9]+)*["']?[ 	]*[:=][ 	]*("[^"\r\n]+"|'[^'\r\n]+'|[^[:space:],;}]+))
  $result_secret$, E'[\\n\\r]+[ ]*', '', 'g');
BEGIN
  IF p_owner_id IS NULL OR p_idempotency_key IS NULL OR p_correlation_id IS NULL
    OR octet_length(p_owner_id) NOT BETWEEN 1 AND 128
    OR p_idempotency_key !~ '^[0-9a-f]{64}$'
    OR p_correlation_id !~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$'
    OR normalize(p_owner_id,NFC)<>p_owner_id OR normalize(p_idempotency_key,NFC)<>p_idempotency_key
    OR normalize(p_correlation_id,NFC)<>p_correlation_id
    OR factory.execution_contract_hash(NULL,p_request_canonical) IS DISTINCT FROM trim(p_request_digest)
  THEN RAISE EXCEPTION 'invalid result command'; END IF;
  BEGIN v_request:=p_request_canonical::jsonb;
  EXCEPTION WHEN others THEN RAISE EXCEPTION 'invalid result command'; END;
  IF factory.execution_canonical_json(v_request)<>p_request_canonical
    OR jsonb_typeof(v_request)<>'object' OR (SELECT count(*) FROM jsonb_object_keys(v_request))<>6
    OR NOT v_request ?& ARRAY['contract','action','actor_id','idempotency_key','envelope_digest','correlation_id']
    OR EXISTS (SELECT 1 FROM jsonb_object_keys(v_request) k WHERE jsonb_typeof(v_request->k)<>'string')
    OR v_request->>'contract'<>'adaptive-factory.result-admission-command/v1'
    OR v_request->>'action'<>'result_admission' OR v_request->>'actor_id'<>p_owner_id
    OR v_request->>'idempotency_key'<>p_idempotency_key
    OR v_request->>'envelope_digest'<>trim(p_envelope_digest)
    OR v_request->>'correlation_id'<>p_correlation_id
  THEN RAISE EXCEPTION 'invalid result command'; END IF;
  IF p_envelope_canonical IS NULL OR octet_length(p_envelope_canonical)>1100000
    OR trim(factory.execution_contract_hash(NULL,p_envelope_canonical)) IS DISTINCT FROM trim(p_envelope_digest)
  THEN RAISE EXCEPTION 'invalid result digest'; END IF;
  BEGIN v:=p_envelope_canonical::jsonb;
  EXCEPTION WHEN others THEN RAISE EXCEPTION 'invalid result json'; END;
  IF factory.execution_canonical_json(v)<>p_envelope_canonical
  THEN RAISE EXCEPTION 'noncanonical result json'; END IF;
  IF jsonb_typeof(v)<>'object' OR (SELECT count(*) FROM jsonb_object_keys(v))<>17
    OR NOT v ?& ARRAY['schema_version','repository_id','task_id','run_id','fence','packet_digest','attempt_id','source_operation','source_digest','channel','content_type','outcome','reason_code','completeness','policy_version','sanitized_payload','sanitized_payload_digest']
    OR jsonb_typeof(v->'schema_version')<>'number' OR jsonb_typeof(v->'fence')<>'number'
    OR EXISTS (SELECT 1 FROM unnest(ARRAY['repository_id','task_id','run_id','packet_digest','attempt_id','source_operation','source_digest','channel','content_type','outcome','reason_code','completeness','policy_version','sanitized_payload_digest']) k
      WHERE jsonb_typeof(v->k)<>'string')
    OR jsonb_typeof(v->'sanitized_payload') NOT IN ('string','null')
    OR v->>'schema_version'<>'2'
    OR v->>'fence' !~ '^[1-9][0-9]*$'
    OR v->>'outcome' NOT IN ('allow','redacted','rejected','unavailable')
    OR v->>'completeness' NOT IN ('complete','missing')
    OR ((v->>'outcome' IN ('allow','redacted')) IS DISTINCT FROM (v->'sanitized_payload'<>'null'::jsonb))
    OR ((v->>'outcome' IN ('allow','redacted')) IS DISTINCT FROM (v->>'completeness'='complete'))
    OR v->>'packet_digest' !~ '^[0-9a-f]{64}$' OR v->>'source_digest' !~ '^[0-9a-f]{64}$'
    OR v->>'sanitized_payload_digest' !~ '^[0-9a-f]{64}$'
    OR trim(factory.execution_contract_hash(NULL,factory.execution_canonical_json(v->'sanitized_payload')))
       IS DISTINCT FROM v->>'sanitized_payload_digest'
    OR v->>'repository_id' !~ '^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$'
    OR v->>'source_operation' !~ '^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$'
    OR v->>'channel' NOT IN ('native_tool_result','synthetic_child_report','attachment','artifact_cache','resume','external_cli','unknown')
    OR (v->'sanitized_payload'<>'null'::jsonb AND v->>'channel'='unknown')
    OR (v->'sanitized_payload'<>'null'::jsonb
      AND v->>'content_type' NOT IN ('application/json','text/plain'))
    OR octet_length(v->>'content_type') NOT BETWEEN 1 AND 128
    OR octet_length(v->>'reason_code') NOT BETWEEN 1 AND 128
    OR octet_length(v->>'policy_version') NOT BETWEEN 1 AND 128
    OR EXISTS (SELECT 1 FROM unnest(ARRAY['repository_id','task_id','run_id','packet_digest','attempt_id','source_operation','source_digest','channel','content_type','outcome','reason_code','completeness','policy_version','sanitized_payload_digest']) k
      WHERE normalize(v->>k,NFC)<>v->>k)
    OR (jsonb_typeof(v->'sanitized_payload')='string' AND normalize(v->>'sanitized_payload',NFC)<>v->>'sanitized_payload')
    OR (jsonb_typeof(v->'sanitized_payload')='string' AND (
      octet_length(v->>'sanitized_payload')>1000000
      OR (v->>'sanitized_payload') ~ E'[\\x01-\\x08\\x0B-\\x0D\\x0E-\\x1F]'
      OR (v->>'sanitized_payload') ~ v_pem_pattern
      OR (v->>'sanitized_payload') ~* v_secret_pattern
    ))
    OR EXISTS (SELECT 1 FROM unnest(ARRAY['content_type','reason_code','policy_version']) k
      WHERE (v->>k) ~ E'[\\x01-\\x1F]'
        OR (v->>k) ~ v_pem_pattern OR (v->>k) ~* v_secret_pattern)
  THEN RAISE EXCEPTION 'invalid result shape'; END IF;
  IF v->'sanitized_payload'<>'null'::jsonb AND v->>'content_type'='application/json' THEN
    BEGIN v_payload_json:=(v->>'sanitized_payload')::json;
    EXCEPTION WHEN others THEN RAISE EXCEPTION 'invalid structured result payload'; END;
    IF EXISTS (
      WITH RECURSIVE payload_nodes(value,depth) AS (
        SELECT v_payload_json,1
        UNION ALL
        SELECT children.value,payload_nodes.depth+1
        FROM payload_nodes
        CROSS JOIN LATERAL (
          SELECT item AS value
          FROM json_array_elements(
            CASE WHEN json_typeof(payload_nodes.value)='array'
              THEN payload_nodes.value ELSE '[]'::json END
          ) item
          UNION ALL
          SELECT child_value AS value
          FROM json_each(
            CASE WHEN json_typeof(payload_nodes.value)='object'
              THEN payload_nodes.value ELSE '{}'::json END
          ) object_item(child_key,child_value)
        ) children
      )
      SELECT 1 FROM payload_nodes node
      WHERE json_typeof(node.value)='object' AND EXISTS (
        SELECT 1 FROM json_each(node.value) member
        GROUP BY member.key HAVING count(*)>1
      )
      UNION ALL
      SELECT 1 FROM payload_nodes
      GROUP BY () HAVING max(depth)>64 OR count(*)>100001
    ) THEN RAISE EXCEPTION 'invalid structured result bounds or duplicate key'; END IF;
    v_payload:=v_payload_json::jsonb;
    IF EXISTS (
      WITH RECURSIVE payload_nodes(value,depth) AS (
        SELECT v_payload,1
        UNION ALL
        SELECT children.value,payload_nodes.depth+1
        FROM payload_nodes
        CROSS JOIN LATERAL (
          SELECT item AS value
          FROM jsonb_array_elements(
            CASE WHEN jsonb_typeof(payload_nodes.value)='array'
              THEN payload_nodes.value ELSE '[]'::jsonb END
          ) item
          UNION ALL
          SELECT child_value AS value
          FROM jsonb_each(
            CASE WHEN jsonb_typeof(payload_nodes.value)='object'
              THEN payload_nodes.value ELSE '{}'::jsonb END
          ) object_item(child_key,child_value)
        ) children
      ), payload_text(value,is_key) AS (
        SELECT object_key,true
        FROM payload_nodes
        CROSS JOIN LATERAL jsonb_object_keys(
          CASE WHEN jsonb_typeof(payload_nodes.value)='object'
            THEN payload_nodes.value ELSE '{}'::jsonb END
        ) object_key
        UNION ALL
        SELECT payload_nodes.value #>> '{}',false
        FROM payload_nodes WHERE jsonb_typeof(payload_nodes.value)='string'
      )
      SELECT 1 FROM payload_text
      WHERE octet_length(value)>1000000
        OR normalize(value,NFC)<>value
        OR value ~ E'[\\x01-\\x08\\x0B-\\x1F]'
        OR value ~ v_pem_pattern
        OR value ~* v_secret_pattern
        OR (is_key AND value ~* v_sensitive_key_pattern)
    ) THEN RAISE EXCEPTION 'invalid structured result text'; END IF;
  END IF;
  BEGIN
    PERFORM (v->>'task_id')::uuid,(v->>'run_id')::uuid,(v->>'attempt_id')::uuid,(v->>'fence')::bigint;
  EXCEPTION WHEN others THEN RAISE EXCEPTION 'invalid result identity'; END;
  IF ((v->>'task_id')::uuid)::text<>v->>'task_id'
    OR ((v->>'run_id')::uuid)::text<>v->>'run_id'
    OR ((v->>'attempt_id')::uuid)::text<>v->>'attempt_id'
  THEN RAISE EXCEPTION 'noncanonical result identity'; END IF;

  PERFORM pg_advisory_xact_lock(hashtextextended(
    (v->>'repository_id')||':'||(v->>'task_id')||':'||(v->>'run_id')||':'||
    (v->>'attempt_id')||':'||(v->>'source_operation')||':'||(v->>'source_digest'),0));
  PERFORM pg_advisory_xact_lock(hashtextextended(p_owner_id||':result_admission:'||p_idempotency_key,0));
  SELECT * INTO v_command FROM factory.result_admission_commands_v1
    WHERE actor_id=p_owner_id AND action='result_admission' AND idempotency_key=p_idempotency_key;
  IF v_command.idempotency_key IS NOT NULL THEN
    IF trim(v_command.request_digest) IS DISTINCT FROM trim(p_request_digest)
      OR trim(v_command.envelope_digest) IS DISTINCT FROM trim(p_envelope_digest)
      OR v_command.correlation_id IS DISTINCT FROM p_correlation_id
    THEN RAISE EXCEPTION 'result command conflict'; END IF;
    RETURN jsonb_build_object('envelope_digest',trim(v_command.envelope_digest),'created',false,'outbox_created',false);
  END IF;
  SELECT * INTO v_run FROM factory.runs WHERE run_id=(v->>'run_id')::uuid FOR UPDATE;
  SELECT * INTO v_task FROM factory.tasks WHERE task_id=(v->>'task_id')::uuid FOR UPDATE;
  IF v_run.run_id IS NULL OR v_task.task_id IS NULL
    OR v_task.repository_id IS DISTINCT FROM v->>'repository_id'
    OR v_task.current_run_id IS DISTINCT FROM v_run.run_id OR v_task.current_fence IS DISTINCT FROM v_run.fence
    OR v_run.task_id IS DISTINCT FROM v_task.task_id OR v_run.fence::text IS DISTINCT FROM v->>'fence'
    OR trim(v_run.packet_digest) IS DISTINCT FROM v->>'packet_digest'
    OR v_run.owner_id IS DISTINCT FROM p_owner_id OR v_run.state<>'leased'
    OR v_run.lease_expires_at<=clock_timestamp() OR v_run.deadline_at<=clock_timestamp()
    OR NOT EXISTS (SELECT 1 FROM factory.attempts a WHERE a.attempt_id=(v->>'attempt_id')::uuid
      AND a.task_id=v_task.task_id AND a.run_id=v_run.run_id AND a.finished_at IS NULL)
  THEN RAISE EXCEPTION 'result authority mismatch'; END IF;

  SELECT envelope_digest INTO v_existing FROM factory.result_sources_v1
    WHERE repository_id=v_task.repository_id AND task_id=v_task.task_id AND run_id=v_run.run_id
      AND attempt_id=(v->>'attempt_id')::uuid AND source_operation=v->>'source_operation'
      AND trim(source_digest)=v->>'source_digest';
  IF v_existing IS NOT NULL THEN
    IF trim(v_existing) IS DISTINCT FROM trim(p_envelope_digest) THEN
      RAISE EXCEPTION 'result replay conflict';
    END IF;
  ELSE
    INSERT INTO factory.result_sources_v1(envelope_digest,repository_id,task_id,run_id,fence,packet_digest,attempt_id,source_operation,source_digest,outcome,envelope)
    VALUES(p_envelope_digest,v_task.repository_id,v_task.task_id,v_run.run_id,v_run.fence,v_run.packet_digest,
      (v->>'attempt_id')::uuid,v->>'source_operation',(v->>'source_digest')::char(64),v->>'outcome',v);
    v_existing:=p_envelope_digest; v_created:=true;
  END IF;
  INSERT INTO factory.result_admission_commands_v1(
    actor_id,action,idempotency_key,request_digest,envelope_digest,correlation_id)
  VALUES(p_owner_id,'result_admission',p_idempotency_key,p_request_digest,v_existing,p_correlation_id);
  -- 04A has no qualified result channel. 04B/025 may enqueue only after durable qualification.
  RETURN jsonb_build_object('envelope_digest',trim(v_existing),'created',v_created,'outbox_created',false);
END $$;
REVOKE ALL ON FUNCTION factory.admit_result_v1(text,char(64),text,text,char(64),text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION factory.admit_result_v1(text,char(64),text,text,char(64),text,text) TO factory_runtime;
