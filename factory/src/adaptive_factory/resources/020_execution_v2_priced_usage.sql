-- Forward-only v2 usage overlay. Keep the immutable v1 procedure for legacy bodies.
ALTER FUNCTION factory.execution_propose(uuid,uuid,text,bigint,char,char,bigint,char,text,jsonb)
  RENAME TO execution_propose_v1;

CREATE FUNCTION factory.execution_propose_v2(
  p_task_id uuid,p_run_id uuid,p_owner text,p_fence bigint,p_legacy_packet_digest char(64),
  p_packet_digest char(64),p_sequence bigint,p_idempotency_key char(64),p_kind text,p_body jsonb
) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE
  v_role text; v_packet jsonb; v_max_events bigint; v_expected_key text; v_existing boolean;
  v_cost bigint; v_tokens bigint; v_price_table jsonb;
BEGIN
  IF p_kind<>'usage' OR p_body IS NULL OR jsonb_typeof(p_body)<>'object'
    OR NOT factory.execution_object_has_exact_keys(p_body,ARRAY[
      'task_id','run_id','packet_digest','fence','sequence','author_role','provider_call_id',
      'price_table','price_table_digest','input_tokens','output_tokens','reasoning_tokens',
      'cached_input_tokens','cache_write_tokens','cost_usd_micros','output_bytes','idempotency_key'
    ]) THEN RETURN false; END IF;
  SELECT r.role,p.body,(p.body#>>'{limits,max_events}')::bigint
    INTO v_role,v_packet,v_max_events
    FROM factory.tasks t JOIN factory.runs r ON r.run_id=t.current_run_id AND r.task_id=t.task_id
    JOIN factory.capacity_allocations a ON a.run_id=r.run_id AND a.task_id=t.task_id
    JOIN factory.execution_packets p ON p.run_id=r.run_id AND p.task_id=t.task_id
      AND p.packet_digest=p_packet_digest AND p.legacy_packet_digest=p_legacy_packet_digest
    JOIN factory.execution_manifests m ON m.run_id=r.run_id AND m.packet_digest=p.packet_digest
    WHERE t.task_id=p_task_id AND r.run_id=p_run_id AND r.owner_id=p_owner AND r.fence=p_fence
      AND t.current_fence=p_fence AND t.state='leased' AND r.state='leased'
      AND r.released_at IS NULL AND a.released_at IS NULL AND m.terminal_at IS NULL
      AND r.lease_expires_at>clock_timestamp() AND t.deadline_at>clock_timestamp()
    FOR UPDATE OF t,r,m;
  IF NOT FOUND OR p_sequence NOT BETWEEN 1 AND COALESCE(v_max_events,0)
    OR NOT (v_packet#>'{provider,capabilities}' ? 'usage')
    OR p_body->>'task_id' IS DISTINCT FROM p_task_id::text
    OR p_body->>'run_id' IS DISTINCT FROM p_run_id::text
    OR p_body->>'packet_digest' IS DISTINCT FROM trim(p_packet_digest)
    OR p_body->>'fence' IS DISTINCT FROM p_fence::text
    OR p_body->>'sequence' IS DISTINCT FROM p_sequence::text
    OR p_body->>'author_role' IS DISTINCT FROM v_role
    OR p_body->>'idempotency_key' IS DISTINCT FROM trim(p_idempotency_key)
    OR p_body->>'provider_call_id' !~ '^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$'
    OR p_body->>'price_table_digest' !~ '^[0-9a-f]{64}$'
  THEN RETURN false; END IF;
  v_price_table=p_body->'price_table';
  IF NOT factory.execution_object_has_exact_keys(v_price_table,ARRAY[
      'schema_version','input_usd_micros_per_million','output_usd_micros_per_million',
      'reasoning_usd_micros_per_million','cached_input_usd_micros_per_million',
      'cache_write_usd_micros_per_million'
    ]) OR v_price_table->>'schema_version'<>'1'
    OR EXISTS (SELECT 1 FROM jsonb_each(v_price_table) x WHERE x.key<>'schema_version'
      AND (jsonb_typeof(x.value)<>'number' OR x.value#>>'{}' !~ '^(0|[1-9][0-9]{0,18})$'))
    OR EXISTS (SELECT 1 FROM jsonb_each(p_body) x WHERE x.key IN (
      'input_tokens','output_tokens','reasoning_tokens','cached_input_tokens','cache_write_tokens',
      'cost_usd_micros','output_bytes','fence','sequence'
    ) AND (jsonb_typeof(x.value)<>'number' OR x.value#>>'{}' !~ '^(0|[1-9][0-9]{0,18})$'))
  THEN RETURN false; END IF;
  v_tokens=(p_body->>'input_tokens')::bigint+(p_body->>'output_tokens')::bigint+
    (p_body->>'reasoning_tokens')::bigint+(p_body->>'cached_input_tokens')::bigint+
    (p_body->>'cache_write_tokens')::bigint;
  v_cost=(p_body->>'input_tokens')::bigint*(v_price_table->>'input_usd_micros_per_million')::bigint/1000000+
    (p_body->>'output_tokens')::bigint*(v_price_table->>'output_usd_micros_per_million')::bigint/1000000+
    (p_body->>'reasoning_tokens')::bigint*(v_price_table->>'reasoning_usd_micros_per_million')::bigint/1000000+
    (p_body->>'cached_input_tokens')::bigint*(v_price_table->>'cached_input_usd_micros_per_million')::bigint/1000000+
    (p_body->>'cache_write_tokens')::bigint*(v_price_table->>'cache_write_usd_micros_per_million')::bigint/1000000;
  IF v_tokens>(v_packet#>>'{limits,max_token_units}')::bigint
    OR v_cost<>(p_body->>'cost_usd_micros')::bigint
    OR v_cost>(v_packet#>>'{limits,max_cost_usd_micros}')::bigint
    OR (p_body->>'output_bytes')::bigint>(v_packet#>>'{limits,max_output_bytes}')::bigint
    OR encode(sha256(convert_to(factory.execution_canonical_json(v_price_table),'UTF8')),'hex')
       IS DISTINCT FROM p_body->>'price_table_digest'
  THEN RETURN false; END IF;
  v_expected_key=factory.execution_contract_hash(NULL,factory.execution_canonical_json(jsonb_build_object(
    'contract','adaptive-factory.execution-proposal/v1','task_id',p_task_id::text,'run_id',p_run_id::text,
    'packet_digest',trim(p_packet_digest),'fence',p_fence,'author_role',v_role,'sequence',p_sequence,
    'event_type','usage.reported','body',jsonb_build_object(
      'provider_call_id',p_body->>'provider_call_id','price_table',v_price_table,
      'price_table_digest',p_body->>'price_table_digest','input_tokens',(p_body->>'input_tokens')::bigint,
      'output_tokens',(p_body->>'output_tokens')::bigint,'reasoning_tokens',(p_body->>'reasoning_tokens')::bigint,
      'cached_input_tokens',(p_body->>'cached_input_tokens')::bigint,'cache_write_tokens',(p_body->>'cache_write_tokens')::bigint,
      'cost_usd_micros',v_cost,'output_bytes',(p_body->>'output_bytes')::bigint,'author_role',v_role
    )
  )));
  IF trim(p_idempotency_key) IS DISTINCT FROM v_expected_key THEN RETURN false; END IF;
  SELECT task_id=p_task_id AND packet_digest=p_packet_digest AND trim(idempotency_key)=trim(p_idempotency_key)
      AND proposal_kind='usage' AND body=p_body INTO v_existing
    FROM factory.execution_proposals WHERE run_id=p_run_id AND producer_sequence=p_sequence;
  IF FOUND THEN RETURN v_existing; END IF;
  IF EXISTS (SELECT 1 FROM factory.execution_proposals WHERE run_id=p_run_id AND idempotency_key=p_idempotency_key)
    OR EXISTS (SELECT 1 FROM factory.execution_proposals WHERE run_id=p_run_id AND proposal_kind='terminal')
    OR p_sequence<>(SELECT COALESCE(max(producer_sequence),0)+1 FROM factory.execution_proposals WHERE run_id=p_run_id)
  THEN RETURN false; END IF;
  INSERT INTO factory.execution_proposals(proposal_id,task_id,run_id,packet_digest,producer_sequence,idempotency_key,proposal_kind,body)
    VALUES(gen_random_uuid(),p_task_id,p_run_id,p_packet_digest,p_sequence,p_idempotency_key,'usage',p_body);
  RETURN true;
END;
$$;

CREATE FUNCTION factory.execution_propose(
  p_task_id uuid,p_run_id uuid,p_owner text,p_fence bigint,p_legacy_packet_digest char(64),
  p_packet_digest char(64),p_sequence bigint,p_idempotency_key char(64),p_kind text,p_body jsonb
) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
BEGIN
  IF p_kind='usage' AND p_body ? 'price_table' THEN
    RETURN factory.execution_propose_v2(p_task_id,p_run_id,p_owner,p_fence,p_legacy_packet_digest,p_packet_digest,p_sequence,p_idempotency_key,p_kind,p_body);
  END IF;
  RETURN factory.execution_propose_v1(p_task_id,p_run_id,p_owner,p_fence,p_legacy_packet_digest,p_packet_digest,p_sequence,p_idempotency_key,p_kind,p_body);
END;
$$;

REVOKE ALL ON FUNCTION factory.execution_propose_v2(uuid,uuid,text,bigint,char,char,bigint,char,text,jsonb) FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.execution_propose(uuid,uuid,text,bigint,char,char,bigint,char,text,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION factory.execution_propose(uuid,uuid,text,bigint,char,char,bigint,char,text,jsonb) TO factory_runtime;
