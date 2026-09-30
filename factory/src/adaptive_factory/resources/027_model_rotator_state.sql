-- Depends on integrated migration 026. No credential, endpoint, prompt or response payload is stored.
CREATE TABLE factory.model_rotator_states (
  tenant_digest char(64) NOT NULL CHECK(tenant_digest~'^[0-9a-f]{64}$'),
  registry_digest char(64) NOT NULL CHECK(registry_digest~'^[0-9a-f]{64}$'),
  cursor integer NOT NULL DEFAULT 0 CHECK(cursor>=0),
  cooldowns jsonb NOT NULL DEFAULT '{}'::jsonb CHECK(jsonb_typeof(cooldowns)='object' AND octet_length(cooldowns::text)<=16384),
  updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY(tenant_digest,registry_digest)
);
CREATE TABLE factory.model_rotator_operations (
  binding_digest char(64) PRIMARY KEY CHECK(binding_digest~'^[0-9a-f]{64}$'),
  operation_digest char(64) UNIQUE NOT NULL CHECK(operation_digest~'^[0-9a-f]{64}$'),
  task_id uuid NOT NULL REFERENCES factory.tasks(task_id) ON DELETE RESTRICT,
  run_id uuid NOT NULL REFERENCES factory.runs(run_id) ON DELETE RESTRICT,
  reservation_id uuid NOT NULL REFERENCES factory.budget_reservations(reservation_id) ON DELETE RESTRICT,
  fence bigint NOT NULL CHECK(fence>0), tenant_digest char(64) NOT NULL,
  registry_digest char(64) NOT NULL, claim_token char(64) UNIQUE NOT NULL,
  state text NOT NULL CHECK(state IN ('claimed','complete')),
  evidence jsonb CHECK(evidence IS NULL OR octet_length(evidence::text)<=131072),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(), completed_at timestamptz
);

CREATE FUNCTION factory.model_rotator_claim_v1(p_binding jsonb,p_binding_digest char(64),p_registry char(64),p_now bigint) RETURNS jsonb
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,factory AS $$
DECLARE v_digest char(64); v_operation char(64); v_token char(64); v_prior factory.model_rotator_operations%ROWTYPE; v_state factory.model_rotator_states%ROWTYPE;
BEGIN
  IF p_binding IS NULL OR p_binding_digest!~'^[0-9a-f]{64}$' OR p_registry!~'^[0-9a-f]{64}$' OR p_now<0
    OR p_binding-ARRAY['schema_version','tenant_id','repository_id','task_id','run_id','attempt_id','fence','budget_reservation_id','budget_digest','registry_digest','operation_id','requested_provider_id','requested_model_id','remaining_token_units']<>'{}'::jsonb
    OR p_binding->>'registry_digest'<>trim(p_registry) THEN RETURN jsonb_build_object('error','registry_binding_mismatch'); END IF;
  v_digest=p_binding_digest;
  v_operation=encode(digest(convert_to(p_binding->>'operation_id','UTF8'),'sha256'),'hex');
  PERFORM pg_advisory_xact_lock(hashtextextended('model-rotator:'||v_digest,0));
  SELECT * INTO v_prior FROM factory.model_rotator_operations WHERE operation_digest=v_operation FOR UPDATE;
  IF FOUND THEN
    IF v_prior.binding_digest<>v_digest THEN RETURN jsonb_build_object('error','idempotency_conflict'); END IF;
    IF v_prior.state='complete' THEN RETURN jsonb_build_object('replay',v_prior.evidence); END IF;
    RETURN jsonb_build_object('error','operation_already_claimed');
  END IF;
  PERFORM 1 FROM factory.tasks t JOIN factory.runs r ON r.run_id=(p_binding->>'run_id')::uuid AND r.task_id=t.task_id
    JOIN factory.budget_reservations b ON b.reservation_id=(p_binding->>'budget_reservation_id')::uuid AND b.task_id=t.task_id AND b.run_id=r.run_id
    WHERE t.task_id=(p_binding->>'task_id')::uuid AND t.repository_id=p_binding->>'repository_id'
      AND t.current_run_id=r.run_id AND t.current_fence=(p_binding->>'fence')::bigint
      AND r.fence=t.current_fence AND r.released_at IS NULL AND r.lease_expires_at>clock_timestamp()
      AND b.released_at IS NULL AND b.token_units>=(p_binding->>'remaining_token_units')::bigint FOR UPDATE OF t,r,b;
  IF NOT FOUND THEN RETURN jsonb_build_object('error','authority_not_granted'); END IF;
  v_token=encode(digest(convert_to(v_digest||':'||p_now::text,'UTF8'),'sha256'),'hex');
  INSERT INTO factory.model_rotator_operations(binding_digest,operation_digest,task_id,run_id,reservation_id,fence,tenant_digest,registry_digest,claim_token,state)
  VALUES(v_digest,v_operation,(p_binding->>'task_id')::uuid,(p_binding->>'run_id')::uuid,(p_binding->>'budget_reservation_id')::uuid,(p_binding->>'fence')::bigint,
    encode(digest(convert_to(p_binding->>'tenant_id','UTF8'),'sha256'),'hex'),p_registry,v_token,'claimed');
  INSERT INTO factory.model_rotator_states(tenant_digest,registry_digest) VALUES(encode(digest(convert_to(p_binding->>'tenant_id','UTF8'),'sha256'),'hex'),p_registry) ON CONFLICT DO NOTHING;
  SELECT * INTO STRICT v_state FROM factory.model_rotator_states WHERE tenant_digest=encode(digest(convert_to(p_binding->>'tenant_id','UTF8'),'sha256'),'hex') AND registry_digest=p_registry FOR UPDATE;
  RETURN jsonb_build_object('replay',NULL,'claim_token',v_token,'cooldowns',v_state.cooldowns,'cursor',v_state.cursor);
END $$;

CREATE FUNCTION factory.model_rotator_finish_v1(p_binding char(64),p_claim char(64),p_evidence jsonb,p_cooldowns jsonb,p_cursor integer) RETURNS boolean
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,factory AS $$
DECLARE v_op factory.model_rotator_operations%ROWTYPE;
BEGIN
  SELECT * INTO v_op FROM factory.model_rotator_operations WHERE binding_digest=p_binding AND claim_token=p_claim AND state='claimed' FOR UPDATE;
  IF NOT FOUND OR p_evidence IS NULL OR p_cursor<0 OR jsonb_typeof(p_cooldowns)<>'object' THEN RETURN false; END IF;
  UPDATE factory.model_rotator_states SET cursor=p_cursor,cooldowns=p_cooldowns,updated_at=clock_timestamp() WHERE tenant_digest=v_op.tenant_digest AND registry_digest=v_op.registry_digest;
  UPDATE factory.model_rotator_operations SET state='complete',evidence=p_evidence,completed_at=clock_timestamp() WHERE binding_digest=p_binding;
  RETURN true;
END $$;
REVOKE ALL ON factory.model_rotator_states,factory.model_rotator_operations FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.model_rotator_claim_v1(jsonb,char,char,bigint),factory.model_rotator_finish_v1(char,char,jsonb,jsonb,integer) FROM PUBLIC;
GRANT SELECT,INSERT,UPDATE ON factory.model_rotator_states,factory.model_rotator_operations TO factory_runtime;
GRANT EXECUTE ON FUNCTION factory.model_rotator_claim_v1(jsonb,char,char,bigint),factory.model_rotator_finish_v1(char,char,jsonb,jsonb,integer) TO factory_runtime;
