-- Correct the migration030 run-owner binding and expose only the bound pre-model context.
DROP FUNCTION factory.execution_record_native_sidecar(jsonb);
DROP FUNCTION factory.execution_consume_analysis_budget(uuid,uuid,text,bigint,char,integer,integer,char,char);

CREATE FUNCTION factory.execution_record_native_sidecar(p_sidecar jsonb) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE v_run uuid; v_task uuid; v_fence bigint; v_packet char(64); v_context jsonb;
  v_budget jsonb; v_packet_body jsonb; v_repository text; v_prior jsonb; v_entry jsonb;
BEGIN
  IF NOT factory.execution_object_has_exact_keys(p_sidecar,ARRAY[
    'schema_version','task_id','run_id','packet_digest','fence','repository_id',
    'context_digest','context_manifest','analysis_budget','sidecar_digest'])
    OR p_sidecar->'schema_version' IS DISTINCT FROM '1'::jsonb
    OR jsonb_typeof(p_sidecar->'task_id') IS DISTINCT FROM 'string'
    OR jsonb_typeof(p_sidecar->'run_id') IS DISTINCT FROM 'string'
    OR jsonb_typeof(p_sidecar->'packet_digest') IS DISTINCT FROM 'string'
    OR jsonb_typeof(p_sidecar->'fence') IS DISTINCT FROM 'number'
    OR jsonb_typeof(p_sidecar->'repository_id') IS DISTINCT FROM 'string'
    OR jsonb_typeof(p_sidecar->'context_digest') IS DISTINCT FROM 'string'
    OR jsonb_typeof(p_sidecar->'sidecar_digest') IS DISTINCT FROM 'string'
    OR jsonb_typeof(p_sidecar->'context_manifest') IS DISTINCT FROM 'object'
    OR jsonb_typeof(p_sidecar->'analysis_budget') IS DISTINCT FROM 'object'
  THEN RETURN false; END IF;
  v_context=p_sidecar->'context_manifest'; v_budget=p_sidecar->'analysis_budget';
  IF NOT factory.execution_object_has_exact_keys(v_budget,ARRAY['schema_version','max_rounds','max_tool_operations'])
    OR v_budget->'schema_version' IS DISTINCT FROM '1'::jsonb
    OR jsonb_typeof(v_budget->'max_rounds') IS DISTINCT FROM 'number'
    OR jsonb_typeof(v_budget->'max_tool_operations') IS DISTINCT FROM 'number'
    OR (v_budget->>'max_rounds')::numeric<>trunc((v_budget->>'max_rounds')::numeric)
    OR (v_budget->>'max_tool_operations')::numeric<>trunc((v_budget->>'max_tool_operations')::numeric)
  THEN RETURN false; END IF;
  IF NOT factory.execution_object_has_exact_keys(v_context,ARRAY[
    'schema_version','builder_version','tenant_id','repository_id','source_snapshot','change_id',
    'route_id','change_spec_digest','observed_at','mandatory_sources','selected_sources','rule_bindings'])
    OR v_context->'schema_version' IS DISTINCT FROM '1'::jsonb
    OR NOT factory.execution_object_has_exact_keys(v_context->'source_snapshot',ARRAY['base_sha','head_sha','dirty_fingerprint'])
    OR jsonb_typeof(v_context->'mandatory_sources') IS DISTINCT FROM 'array'
    OR jsonb_array_length(v_context->'mandatory_sources')=0
    OR jsonb_typeof(v_context->'selected_sources') IS DISTINCT FROM 'array'
    OR jsonb_typeof(v_context->'rule_bindings') IS DISTINCT FROM 'array'
  THEN RETURN false; END IF;
  v_run=(p_sidecar->>'run_id')::uuid; v_task=(p_sidecar->>'task_id')::uuid;
  v_fence=(p_sidecar->>'fence')::bigint; v_packet=p_sidecar->>'packet_digest';
  SELECT e.body,t.repository_id INTO v_packet_body,v_repository
  FROM factory.runs r JOIN factory.execution_packets e ON e.run_id=r.run_id
  JOIN factory.tasks t ON t.task_id=r.task_id
  WHERE r.run_id=v_run AND r.task_id=v_task AND r.owner_id=e.body->>'owner'
    AND r.fence=v_fence AND r.state='leased' AND r.lease_expires_at>clock_timestamp()
    AND e.packet_digest=v_packet FOR UPDATE OF r;
  IF NOT FOUND OR p_sidecar->>'repository_id'<>v_repository
    OR v_context->>'tenant_id'<>v_repository OR v_context->>'repository_id'<>v_repository
    OR v_context->>'change_id'<>v_packet_body->'authority'->>'change_id'
    OR v_context->>'route_id'<>v_packet_body->'authority'->>'route_id'
    OR v_context->>'change_spec_digest'<>v_packet_body->'authority'->>'spec_digest'
    OR v_context->'source_snapshot'->>'base_sha'<>v_packet_body->'authority'->>'exact_base_sha'
    OR v_context->'source_snapshot'->>'head_sha'<>v_packet_body->'authority'->>'exact_head_sha'
    OR EXISTS (SELECT 1 FROM factory.kill_switch_heads WHERE enabled AND scope_key IN ('global','repository:'||v_repository))
  THEN RETURN false; END IF;
  FOR v_entry IN SELECT value FROM jsonb_array_elements((v_context->'mandatory_sources')||(v_context->'selected_sources')) LOOP
    IF NOT factory.execution_object_has_exact_keys(v_entry,ARRAY['path','kind','content','sha256','reason'])
      OR v_entry->>'sha256'<>encode(sha256(convert_to(v_entry->>'content','UTF8')),'hex')
    THEN RETURN false; END IF;
  END LOOP;
  IF p_sidecar->>'context_digest'<>factory.execution_contract_hash(NULL::text,factory.execution_canonical_json(v_context-'observed_at'))
    OR p_sidecar->>'sidecar_digest'<>factory.execution_contract_hash(NULL::text,factory.execution_canonical_json(p_sidecar-'sidecar_digest'))
  THEN RETURN false; END IF;
  SELECT body INTO v_prior FROM factory.execution_native_contexts WHERE run_id=v_run;
  IF FOUND THEN RETURN v_prior=p_sidecar; END IF;
  INSERT INTO factory.execution_native_contexts
    (run_id,task_id,packet_digest,fence,repository_id,context_digest,sidecar_digest,body)
  VALUES (v_run,v_task,v_packet,v_fence,v_repository,p_sidecar->>'context_digest',p_sidecar->>'sidecar_digest',p_sidecar);
  INSERT INTO factory.execution_analysis_budgets(run_id,max_rounds,max_tool_operations)
  VALUES (v_run,(v_budget->>'max_rounds')::integer,(v_budget->>'max_tool_operations')::integer);
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
    WHERE r.task_id=p_task AND r.run_id=p_run AND r.owner_id=p_owner AND r.fence=p_fence
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

CREATE FUNCTION factory.execution_native_context(
  p_task uuid,p_run uuid,p_owner text,p_fence bigint,p_packet char(64)
) RETURNS jsonb
LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
  SELECT c.body FROM factory.execution_native_contexts c JOIN factory.runs r ON r.run_id=c.run_id
  WHERE r.task_id=p_task AND r.run_id=p_run AND r.owner_id=p_owner AND r.fence=p_fence
    AND c.packet_digest=p_packet
$$;

REVOKE ALL ON FUNCTION
  factory.execution_record_native_sidecar(jsonb),
  factory.execution_consume_analysis_budget(uuid,uuid,text,bigint,char,integer,integer,char,char),
  factory.execution_native_context(uuid,uuid,text,bigint,char)
FROM PUBLIC,factory_runtime,factory_migrator;
GRANT EXECUTE ON FUNCTION
  factory.execution_record_native_sidecar(jsonb),
  factory.execution_consume_analysis_budget(uuid,uuid,text,bigint,char,integer,integer,char,char),
  factory.execution_native_context(uuid,uuid,text,bigint,char)
TO factory_runtime;
