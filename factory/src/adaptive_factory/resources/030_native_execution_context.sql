-- Persist the native pre-model context and its bounded analysis budget atomically with execution start.
CREATE TABLE factory.execution_native_contexts (
  run_id uuid PRIMARY KEY REFERENCES factory.runs(run_id) ON DELETE RESTRICT,
  task_id uuid NOT NULL REFERENCES factory.tasks(task_id) ON DELETE RESTRICT,
  packet_digest char(64) NOT NULL CHECK (packet_digest ~ '^[0-9a-f]{64}$'),
  fence bigint NOT NULL CHECK (fence > 0),
  repository_id text NOT NULL,
  context_digest char(64) NOT NULL CHECK (context_digest ~ '^[0-9a-f]{64}$'),
  sidecar_digest char(64) NOT NULL UNIQUE CHECK (sidecar_digest ~ '^[0-9a-f]{64}$'),
  body jsonb NOT NULL CHECK (octet_length(body::text) <= 262144),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE factory.execution_analysis_budgets (
  run_id uuid PRIMARY KEY REFERENCES factory.execution_native_contexts(run_id) ON DELETE RESTRICT,
  max_rounds integer NOT NULL CHECK (max_rounds BETWEEN 1 AND 64),
  max_tool_operations integer NOT NULL CHECK (max_tool_operations BETWEEN 1 AND 10000),
  used_rounds integer NOT NULL DEFAULT 0 CHECK (used_rounds >= 0),
  used_tool_operations integer NOT NULL DEFAULT 0 CHECK (used_tool_operations >= 0),
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','exhausted')),
  blocker_digest char(64) CHECK (blocker_digest IS NULL OR blocker_digest ~ '^[0-9a-f]{64}$'),
  facts_digest char(64) CHECK (facts_digest IS NULL OR facts_digest ~ '^[0-9a-f]{64}$'),
  updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE FUNCTION factory.execution_record_native_sidecar(p_sidecar jsonb) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE v_run uuid; v_task uuid; v_fence bigint; v_packet char(64); v_prior jsonb;
BEGIN
  IF p_sidecar IS NULL OR jsonb_typeof(p_sidecar)<>'object'
    OR (SELECT count(*) FROM jsonb_object_keys(p_sidecar))<>10
    OR p_sidecar->'schema_version' IS DISTINCT FROM '1'::jsonb
    OR jsonb_typeof(p_sidecar->'task_id')<>'string'
    OR jsonb_typeof(p_sidecar->'run_id')<>'string'
    OR jsonb_typeof(p_sidecar->'packet_digest')<>'string'
    OR jsonb_typeof(p_sidecar->'fence')<>'number'
    OR jsonb_typeof(p_sidecar->'repository_id')<>'string'
    OR jsonb_typeof(p_sidecar->'context_digest')<>'string'
    OR jsonb_typeof(p_sidecar->'context_manifest')<>'object'
    OR jsonb_typeof(p_sidecar->'analysis_budget')<>'object'
    OR jsonb_typeof(p_sidecar->'sidecar_digest')<>'string'
  THEN RETURN false; END IF;
  v_run := (p_sidecar->>'run_id')::uuid; v_task := (p_sidecar->>'task_id')::uuid;
  v_fence := (p_sidecar->>'fence')::bigint; v_packet := p_sidecar->>'packet_digest';
  IF p_sidecar->'analysis_budget'->'schema_version' IS DISTINCT FROM '1'::jsonb
    OR jsonb_typeof(p_sidecar->'analysis_budget'->'max_rounds')<>'number'
    OR jsonb_typeof(p_sidecar->'analysis_budget'->'max_tool_operations')<>'number'
    OR (p_sidecar->'analysis_budget'->>'max_rounds')::numeric
       <>trunc((p_sidecar->'analysis_budget'->>'max_rounds')::numeric)
    OR (p_sidecar->'analysis_budget'->>'max_tool_operations')::numeric
       <>trunc((p_sidecar->'analysis_budget'->>'max_tool_operations')::numeric)
  THEN RETURN false; END IF;
  SELECT body INTO v_prior FROM factory.execution_native_contexts WHERE run_id=v_run;
  IF FOUND THEN RETURN v_prior=p_sidecar; END IF;
  IF NOT EXISTS (
    SELECT 1 FROM factory.runs r JOIN factory.execution_packets e ON e.run_id=r.run_id
    JOIN factory.tasks t ON t.task_id=r.task_id
    WHERE r.run_id=v_run AND r.task_id=v_task AND r.fence=v_fence
      AND e.packet_digest=v_packet AND t.repository_id=p_sidecar->>'repository_id'
  ) THEN RETURN false; END IF;
  INSERT INTO factory.execution_native_contexts
    (run_id,task_id,packet_digest,fence,repository_id,context_digest,sidecar_digest,body)
  VALUES (v_run,v_task,v_packet,v_fence,p_sidecar->>'repository_id',
    p_sidecar->>'context_digest',p_sidecar->>'sidecar_digest',p_sidecar);
  INSERT INTO factory.execution_analysis_budgets(run_id,max_rounds,max_tool_operations)
  VALUES (v_run,(p_sidecar->'analysis_budget'->>'max_rounds')::integer,
    (p_sidecar->'analysis_budget'->>'max_tool_operations')::integer);
  RETURN true;
EXCEPTION WHEN invalid_text_representation OR numeric_value_out_of_range OR check_violation THEN RETURN false;
END $$;

CREATE FUNCTION factory.execution_consume_analysis_budget(
  p_task uuid,p_run uuid,p_owner text,p_fence bigint,p_packet char(64),
  p_rounds integer,p_tools integer,p_facts char(64),p_blocker char(64)
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE v factory.execution_analysis_budgets%ROWTYPE;
BEGIN
  IF p_rounds<0 OR p_tools<0 OR p_rounds+p_tools=0 THEN RAISE EXCEPTION 'invalid analysis consumption'; END IF;
  IF NOT EXISTS (SELECT 1 FROM factory.runs r JOIN factory.execution_native_contexts c ON c.run_id=r.run_id
    WHERE r.task_id=p_task AND r.run_id=p_run AND r.owner=p_owner AND r.fence=p_fence
      AND c.packet_digest=p_packet) THEN RAISE EXCEPTION 'analysis budget binding mismatch'; END IF;
  SELECT * INTO v FROM factory.execution_analysis_budgets WHERE run_id=p_run FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'analysis budget unavailable'; END IF;
  IF v.status='exhausted' OR v.used_rounds+p_rounds>v.max_rounds
    OR v.used_tool_operations+p_tools>v.max_tool_operations THEN
    IF p_facts IS NULL OR p_blocker IS NULL THEN RAISE EXCEPTION 'exhaustion evidence required'; END IF;
    UPDATE factory.execution_analysis_budgets SET status='exhausted',facts_digest=p_facts,
      blocker_digest=p_blocker,updated_at=clock_timestamp() WHERE run_id=p_run;
    RETURN jsonb_build_object('accepted',false,'status','exhausted','used_rounds',v.used_rounds,
      'used_tool_operations',v.used_tool_operations);
  END IF;
  UPDATE factory.execution_analysis_budgets SET used_rounds=used_rounds+p_rounds,
    used_tool_operations=used_tool_operations+p_tools,updated_at=clock_timestamp() WHERE run_id=p_run;
  RETURN jsonb_build_object('accepted',true,'status','active','used_rounds',v.used_rounds+p_rounds,
    'used_tool_operations',v.used_tool_operations+p_tools);
END $$;

REVOKE ALL ON TABLE factory.execution_native_contexts,factory.execution_analysis_budgets
  FROM PUBLIC,factory_runtime,factory_migrator;
REVOKE ALL ON FUNCTION factory.execution_record_native_sidecar(jsonb),
  factory.execution_consume_analysis_budget(uuid,uuid,text,bigint,char,integer,integer,char,char)
  FROM PUBLIC,factory_runtime,factory_migrator;
GRANT EXECUTE ON FUNCTION factory.execution_record_native_sidecar(jsonb),
  factory.execution_consume_analysis_budget(uuid,uuid,text,bigint,char,integer,integer,char,char) TO factory_runtime;
