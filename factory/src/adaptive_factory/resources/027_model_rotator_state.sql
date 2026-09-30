-- Depends on integrated migration 026. Stores pseudonymous digests, not anonymous identities.
CREATE TABLE factory.model_rotator_registry_policies(
  registry_digest char(64) PRIMARY KEY, token_quota bigint NOT NULL CHECK(token_quota>0),
  request_quota bigint NOT NULL CHECK(request_quota>0), claim_seconds integer NOT NULL CHECK(claim_seconds BETWEEN 1 AND 300)
);
INSERT INTO factory.model_rotator_registry_policies VALUES('b31b1e2a12adb01f2889bd5bfe9dfc0c2cc2908262977a16546646b532de1781',1024,20,30);
CREATE TABLE factory.model_rotator_states(
  tenant_digest char(64) NOT NULL, registry_digest char(64) NOT NULL REFERENCES factory.model_rotator_registry_policies,
  version bigint NOT NULL DEFAULT 0 CHECK(version>=0), cursor integer NOT NULL CHECK(cursor>=0),
  requested_model_digest char(64) NOT NULL,
  held_token_units bigint NOT NULL DEFAULT 0 CHECK(held_token_units>=0), settled_token_units bigint NOT NULL DEFAULT 0 CHECK(settled_token_units>=0),
  held_request_units bigint NOT NULL DEFAULT 0 CHECK(held_request_units>=0), settled_request_units bigint NOT NULL DEFAULT 0 CHECK(settled_request_units>=0),
  cooldowns jsonb NOT NULL DEFAULT '{}'::jsonb CHECK(jsonb_typeof(cooldowns)='object' AND octet_length(cooldowns::text)<=16384),
  quarantined boolean NOT NULL DEFAULT false, updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY(tenant_digest,registry_digest)
);
CREATE TABLE factory.model_rotator_operations(
  binding_digest char(64) PRIMARY KEY, operation_digest char(64) UNIQUE NOT NULL,
  task_id uuid NOT NULL REFERENCES factory.tasks, run_id uuid NOT NULL REFERENCES factory.runs,
  attempt_id uuid NOT NULL REFERENCES factory.attempts, reservation_id uuid NOT NULL REFERENCES factory.budget_reservations,
  fence bigint NOT NULL CHECK(fence>0), tenant_digest char(64) NOT NULL, registry_digest char(64) NOT NULL,
  state_version bigint NOT NULL CHECK(state_version>=0), claim_token char(64) UNIQUE NOT NULL,
  claim_expires_at timestamptz NOT NULL, reserved_token_units bigint NOT NULL DEFAULT 0 CHECK(reserved_token_units>=0),
  reserved_request_units bigint NOT NULL DEFAULT 0 CHECK(reserved_request_units>=0),
  state text NOT NULL CHECK(state IN ('claimed','complete','quarantined')),
  evidence jsonb CHECK(evidence IS NULL OR octet_length(evidence::text)<=131072),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(), completed_at timestamptz,
  FOREIGN KEY(tenant_digest,registry_digest) REFERENCES factory.model_rotator_states
);

CREATE FUNCTION factory.model_rotator_claim_v1(p_binding jsonb,p_wire text,p_binding_digest char(64),p_registry char(64),p_cursor integer,p_requested char(64),p_now bigint) RETURNS jsonb
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,factory AS $$
DECLARE v_operation char(64); v_token char(64); v_tenant char(64); v_budget char(64);
  v_prior factory.model_rotator_operations%ROWTYPE; v_state factory.model_rotator_states%ROWTYPE;
BEGIN
  IF p_binding IS NULL OR octet_length(p_wire)>16384 OR p_wire::jsonb<>p_binding
    OR encode(digest(convert_to(p_wire,'UTF8'),'sha256'),'hex')<>p_binding_digest
    OR p_registry!~'^[0-9a-f]{64}$' OR p_cursor<0 OR p_requested!~'^[0-9a-f]{64}$' OR p_now<0
    OR p_binding-ARRAY['schema_version','tenant_id','repository_id','task_id','run_id','attempt_id','fence','budget_reservation_id','budget_digest','registry_digest','operation_id','requested_provider_id','requested_model_id','remaining_token_units','remaining_request_units']<>'{}'::jsonb
    OR p_binding->>'registry_digest'<>trim(p_registry) THEN RETURN jsonb_build_object('error','binding_digest_mismatch'); END IF;
  v_operation=encode(digest(convert_to(p_binding->>'operation_id','UTF8'),'sha256'),'hex');
  SELECT encode(digest(convert_to(t.repository_id,'UTF8'),'sha256'),'hex'),
    encode(digest(convert_to(concat_ws('|',b.reservation_id,b.task_id,b.run_id,b.token_units,b.cost_usd_micros,b.wall_seconds,b.reason_digest),'UTF8'),'sha256'),'hex')
    INTO v_tenant,v_budget FROM factory.tasks t JOIN factory.runs r ON r.run_id=(p_binding->>'run_id')::uuid AND r.task_id=t.task_id
    JOIN factory.attempts a ON a.attempt_id=(p_binding->>'attempt_id')::uuid AND a.task_id=t.task_id AND a.run_id=r.run_id
    JOIN factory.budget_reservations b ON b.reservation_id=(p_binding->>'budget_reservation_id')::uuid AND b.task_id=t.task_id AND b.run_id=r.run_id
    WHERE t.task_id=(p_binding->>'task_id')::uuid AND t.repository_id=p_binding->>'repository_id'
      AND p_binding->>'tenant_id'=t.repository_id AND t.current_run_id=r.run_id AND t.current_fence=(p_binding->>'fence')::bigint
      AND r.fence=t.current_fence AND r.state='leased' AND r.released_at IS NULL AND r.lease_expires_at>clock_timestamp()
      AND b.released_at IS NULL FOR UPDATE OF t,r,a,b;
  IF NOT FOUND OR v_budget<>p_binding->>'budget_digest' THEN RETURN jsonb_build_object('error','authority_not_granted'); END IF;
  PERFORM pg_advisory_xact_lock(hashtextextended('model-rotator:'||v_tenant||':'||trim(p_registry),0));
  SELECT * INTO v_prior FROM factory.model_rotator_operations WHERE operation_digest=v_operation FOR UPDATE;
  IF FOUND THEN
    IF v_prior.binding_digest<>p_binding_digest THEN RETURN jsonb_build_object('error','idempotency_conflict'); END IF;
    IF v_prior.state='complete' THEN RETURN jsonb_build_object('replay',v_prior.evidence); END IF;
    RETURN jsonb_build_object('error',CASE WHEN v_prior.state='quarantined' OR v_prior.claim_expires_at<=clock_timestamp() THEN 'reconciliation_required' ELSE 'operation_already_claimed' END);
  END IF;
  INSERT INTO factory.model_rotator_states(tenant_digest,registry_digest,cursor,requested_model_digest)
    VALUES(v_tenant,p_registry,p_cursor,p_requested) ON CONFLICT DO NOTHING;
  SELECT * INTO STRICT v_state FROM factory.model_rotator_states WHERE tenant_digest=v_tenant AND registry_digest=p_registry FOR UPDATE;
  IF v_state.quarantined THEN RETURN jsonb_build_object('error','reconciliation_required'); END IF;
  IF v_state.cursor<>p_cursor OR v_state.requested_model_digest<>p_requested THEN RETURN jsonb_build_object('error','requested_cursor_mismatch'); END IF;
  IF EXISTS(SELECT 1 FROM factory.model_rotator_operations WHERE tenant_digest=v_tenant AND registry_digest=p_registry AND state='claimed' AND claim_expires_at>clock_timestamp())
    THEN RETURN jsonb_build_object('error','operation_already_claimed'); END IF;
  IF EXISTS(SELECT 1 FROM factory.model_rotator_operations WHERE tenant_digest=v_tenant AND registry_digest=p_registry AND state='claimed' AND claim_expires_at<=clock_timestamp()) THEN
    UPDATE factory.model_rotator_states SET quarantined=true WHERE tenant_digest=v_tenant AND registry_digest=p_registry;
    UPDATE factory.model_rotator_operations SET state='quarantined' WHERE tenant_digest=v_tenant AND registry_digest=p_registry AND state='claimed';
    RETURN jsonb_build_object('error','reconciliation_required');
  END IF;
  v_token=encode(digest(convert_to(p_binding_digest||':'||v_state.version||':'||p_now,'UTF8'),'sha256'),'hex');
  INSERT INTO factory.model_rotator_operations(binding_digest,operation_digest,task_id,run_id,attempt_id,reservation_id,fence,tenant_digest,registry_digest,state_version,claim_token,claim_expires_at,state)
    VALUES(p_binding_digest,v_operation,(p_binding->>'task_id')::uuid,(p_binding->>'run_id')::uuid,(p_binding->>'attempt_id')::uuid,(p_binding->>'budget_reservation_id')::uuid,(p_binding->>'fence')::bigint,v_tenant,p_registry,v_state.version,v_token,clock_timestamp()+interval '30 seconds','claimed');
  RETURN jsonb_build_object('replay',NULL,'claim_token',v_token,'cooldowns',v_state.cooldowns,'cursor',v_state.cursor,'version',v_state.version);
END $$;

CREATE FUNCTION factory.model_rotator_reserve_v1(p_binding char(64),p_claim char(64),p_mode text,p_units bigint) RETURNS boolean
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,factory AS $$
DECLARE v_op factory.model_rotator_operations%ROWTYPE; v_state factory.model_rotator_states%ROWTYPE; v_policy factory.model_rotator_registry_policies%ROWTYPE; v_budget bigint;
BEGIN
  SELECT * INTO v_op FROM factory.model_rotator_operations WHERE binding_digest=p_binding AND claim_token=p_claim AND state='claimed' AND claim_expires_at>clock_timestamp() FOR UPDATE;
  IF NOT FOUND OR p_mode NOT IN ('token','request') OR p_units<=0 THEN RETURN false; END IF;
  SELECT * INTO STRICT v_state FROM factory.model_rotator_states WHERE tenant_digest=v_op.tenant_digest AND registry_digest=v_op.registry_digest FOR UPDATE;
  SELECT * INTO STRICT v_policy FROM factory.model_rotator_registry_policies WHERE registry_digest=v_op.registry_digest;
  SELECT token_units INTO STRICT v_budget FROM factory.budget_reservations WHERE reservation_id=v_op.reservation_id AND released_at IS NULL FOR UPDATE;
  IF p_mode='token' THEN
    IF v_state.held_token_units+v_state.settled_token_units+p_units>least(v_budget,v_policy.token_quota) THEN RETURN false; END IF;
    UPDATE factory.model_rotator_states SET held_token_units=held_token_units+p_units WHERE tenant_digest=v_op.tenant_digest AND registry_digest=v_op.registry_digest;
    UPDATE factory.model_rotator_operations SET reserved_token_units=reserved_token_units+p_units WHERE binding_digest=p_binding;
  ELSE
    IF p_units<>1 OR v_state.held_request_units+v_state.settled_request_units+1>v_policy.request_quota THEN RETURN false; END IF;
    UPDATE factory.model_rotator_states SET held_request_units=held_request_units+1 WHERE tenant_digest=v_op.tenant_digest AND registry_digest=v_op.registry_digest;
    UPDATE factory.model_rotator_operations SET reserved_request_units=reserved_request_units+1 WHERE binding_digest=p_binding;
  END IF;
  RETURN true;
END $$;

CREATE FUNCTION factory.model_rotator_finish_v1(p_binding char(64),p_claim char(64),p_evidence jsonb,p_cooldowns jsonb,p_cursor integer,p_version bigint) RETURNS boolean
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,factory AS $$
DECLARE v_op factory.model_rotator_operations%ROWTYPE;
BEGIN
  SELECT * INTO v_op FROM factory.model_rotator_operations WHERE binding_digest=p_binding AND claim_token=p_claim AND state='claimed' AND state_version=p_version AND claim_expires_at>clock_timestamp() FOR UPDATE;
  IF NOT FOUND OR p_evidence IS NULL OR p_cursor<0 OR jsonb_typeof(p_cooldowns)<>'object' THEN RETURN false; END IF;
  UPDATE factory.model_rotator_states SET cursor=p_cursor,requested_model_digest=p_evidence->>'next_model_digest',cooldowns=p_cooldowns,
    held_token_units=held_token_units-v_op.reserved_token_units,settled_token_units=settled_token_units+v_op.reserved_token_units,
    held_request_units=held_request_units-v_op.reserved_request_units,settled_request_units=settled_request_units+v_op.reserved_request_units,
    version=version+1,updated_at=clock_timestamp()
    WHERE tenant_digest=v_op.tenant_digest AND registry_digest=v_op.registry_digest AND version=p_version;
  IF NOT FOUND THEN RETURN false; END IF;
  UPDATE factory.model_rotator_operations SET state='complete',evidence=p_evidence,completed_at=clock_timestamp() WHERE binding_digest=p_binding;
  RETURN true;
END $$;

CREATE FUNCTION factory.model_rotator_reconcile_v1(p_binding char(64),p_outcome text) RETURNS boolean
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,factory AS $$
DECLARE v_op factory.model_rotator_operations%ROWTYPE;
BEGIN
  SELECT * INTO v_op FROM factory.model_rotator_operations WHERE binding_digest=p_binding AND state='quarantined' FOR UPDATE;
  IF NOT FOUND OR p_outcome NOT IN ('settle','release') THEN RETURN false; END IF;
  UPDATE factory.model_rotator_states SET
    held_token_units=held_token_units-v_op.reserved_token_units,
    settled_token_units=settled_token_units+CASE WHEN p_outcome='settle' THEN v_op.reserved_token_units ELSE 0 END,
    held_request_units=held_request_units-v_op.reserved_request_units,
    settled_request_units=settled_request_units+CASE WHEN p_outcome='settle' THEN v_op.reserved_request_units ELSE 0 END,
    quarantined=false,version=version+1,updated_at=clock_timestamp()
    WHERE tenant_digest=v_op.tenant_digest AND registry_digest=v_op.registry_digest AND quarantined=true;
  UPDATE factory.model_rotator_operations SET state='complete',completed_at=clock_timestamp() WHERE binding_digest=p_binding;
  RETURN FOUND;
END $$;

CREATE FUNCTION factory.model_rotator_quarantine_v1(p_binding char(64),p_claim char(64),p_evidence jsonb) RETURNS boolean
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,factory AS $$
DECLARE v_op factory.model_rotator_operations%ROWTYPE;
BEGIN
  SELECT * INTO v_op FROM factory.model_rotator_operations WHERE binding_digest=p_binding AND claim_token=p_claim AND state='claimed' FOR UPDATE;
  IF NOT FOUND THEN RETURN false; END IF;
  UPDATE factory.model_rotator_states SET quarantined=true,updated_at=clock_timestamp() WHERE tenant_digest=v_op.tenant_digest AND registry_digest=v_op.registry_digest;
  UPDATE factory.model_rotator_operations SET state='quarantined',evidence=p_evidence,completed_at=clock_timestamp() WHERE binding_digest=p_binding;
  RETURN true;
END $$;
REVOKE ALL ON factory.model_rotator_registry_policies,factory.model_rotator_states,factory.model_rotator_operations FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.model_rotator_claim_v1(jsonb,text,char,char,integer,char,bigint),factory.model_rotator_reserve_v1(char,char,text,bigint),factory.model_rotator_finish_v1(char,char,jsonb,jsonb,integer,bigint),factory.model_rotator_quarantine_v1(char,char,jsonb),factory.model_rotator_reconcile_v1(char,text) FROM PUBLIC;
GRANT SELECT ON factory.model_rotator_registry_policies TO factory_runtime;
GRANT SELECT,INSERT,UPDATE ON factory.model_rotator_states,factory.model_rotator_operations TO factory_runtime;
GRANT EXECUTE ON FUNCTION factory.model_rotator_claim_v1(jsonb,text,char,char,integer,char,bigint),factory.model_rotator_reserve_v1(char,char,text,bigint),factory.model_rotator_finish_v1(char,char,jsonb,jsonb,integer,bigint),factory.model_rotator_quarantine_v1(char,char,jsonb),factory.model_rotator_reconcile_v1(char,text) TO factory_runtime;
