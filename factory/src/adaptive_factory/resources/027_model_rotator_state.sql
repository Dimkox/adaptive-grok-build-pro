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
  cooldowns jsonb NOT NULL DEFAULT '{}'::jsonb CHECK(jsonb_typeof(cooldowns)='object' AND octet_length(cooldowns::text)<=16384),
  quarantined boolean NOT NULL DEFAULT false, updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY(tenant_digest,registry_digest)
);
CREATE TABLE factory.model_rotator_operations(
  binding_digest char(64) PRIMARY KEY, operation_digest char(64) UNIQUE NOT NULL,
  task_id uuid NOT NULL REFERENCES factory.tasks, run_id uuid NOT NULL REFERENCES factory.runs,
  attempt_id uuid NOT NULL REFERENCES factory.attempts, reservation_id uuid NOT NULL REFERENCES factory.budget_reservations,
  fence bigint NOT NULL CHECK(fence>0), tenant_digest char(64) NOT NULL, budget_digest char(64) NOT NULL, registry_digest char(64) NOT NULL,
  state_version bigint NOT NULL CHECK(state_version>=0), claim_token char(64) UNIQUE NOT NULL,
  claim_expires_at timestamptz NOT NULL, reserved_token_units bigint NOT NULL DEFAULT 0 CHECK(reserved_token_units>=0),
  reserved_request_units bigint NOT NULL DEFAULT 0 CHECK(reserved_request_units>=0),
  binding_token_limit bigint NOT NULL CHECK(binding_token_limit>=0), binding_request_limit bigint NOT NULL CHECK(binding_request_limit>=0),
  state text NOT NULL CHECK(state IN ('claimed','complete','quarantined')),
  evidence jsonb CHECK(evidence IS NULL OR octet_length(evidence::text)<=131072),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(), completed_at timestamptz,
  FOREIGN KEY(tenant_digest,registry_digest) REFERENCES factory.model_rotator_states
);
CREATE TABLE factory.model_rotator_reservation_accounting(
  reservation_id uuid NOT NULL REFERENCES factory.budget_reservations, registry_digest char(64) NOT NULL,
  held_token_units bigint NOT NULL DEFAULT 0 CHECK(held_token_units>=0), settled_token_units bigint NOT NULL DEFAULT 0 CHECK(settled_token_units>=0),
  held_request_units bigint NOT NULL DEFAULT 0 CHECK(held_request_units>=0), settled_request_units bigint NOT NULL DEFAULT 0 CHECK(settled_request_units>=0),
  PRIMARY KEY(reservation_id,registry_digest)
);
CREATE TABLE factory.model_rotator_request_grants(
  reservation_id uuid NOT NULL REFERENCES factory.budget_reservations,
  registry_digest char(64) NOT NULL REFERENCES factory.model_rotator_registry_policies,
  request_units bigint NOT NULL DEFAULT 0 CHECK(request_units>=0),
  grant_digest char(64) NOT NULL CHECK(grant_digest~'^[0-9a-f]{64}$'),
  PRIMARY KEY(reservation_id,registry_digest)
);
CREATE VIEW factory.model_rotator_safe_status AS SELECT tenant_digest,registry_digest,version,cursor,quarantined,
  (SELECT count(*) FROM factory.model_rotator_operations o WHERE o.tenant_digest=s.tenant_digest AND o.registry_digest=s.registry_digest AND o.state='claimed') AS active_claims
  FROM factory.model_rotator_states s;

CREATE FUNCTION factory.model_rotator_claim_v1(p_binding jsonb,p_wire text,p_binding_digest char(64),p_registry char(64),p_cursor integer,p_requested char(64),p_now bigint) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE v_operation char(64); v_token char(64); v_tenant char(64); v_budget char(64); v_server_digest char(64); v_request_units bigint;
  v_prior factory.model_rotator_operations%ROWTYPE; v_state factory.model_rotator_states%ROWTYPE;
BEGIN
  IF p_binding IS NULL OR octet_length(p_wire)>16384 OR p_wire::jsonb<>p_binding
    OR p_registry!~'^[0-9a-f]{64}$' OR p_cursor<0 OR p_requested!~'^[0-9a-f]{64}$' OR p_now<0
    OR p_binding->>'schema_version'<>'1'
    OR p_binding-ARRAY['schema_version','tenant_id','repository_id','task_id','run_id','attempt_id','fence','budget_reservation_id','budget_digest','registry_digest','operation_id','requested_provider_id','requested_model_id','remaining_token_units','remaining_request_units']<>'{}'::jsonb
    OR p_binding->>'registry_digest'<>trim(p_registry) THEN RETURN jsonb_build_object('error','binding_digest_mismatch'); END IF;
  v_operation=encode(digest(convert_to(p_binding->>'operation_id','UTF8'),'sha256'),'hex');
  SELECT encode(digest(convert_to(t.repository_id,'UTF8'),'sha256'),'hex'),
    encode(digest(convert_to(concat_ws('|',b.reservation_id,b.task_id,b.run_id,b.token_units,b.cost_usd_micros,b.wall_seconds,b.reason_digest,g.request_units,g.grant_digest),'UTF8'),'sha256'),'hex'),g.request_units
    INTO v_tenant,v_budget,v_request_units FROM factory.tasks t JOIN factory.runs r ON r.run_id=(p_binding->>'run_id')::uuid AND r.task_id=t.task_id
    JOIN factory.attempts a ON a.attempt_id=(p_binding->>'attempt_id')::uuid AND a.task_id=t.task_id AND a.run_id=r.run_id
    JOIN factory.budget_reservations b ON b.reservation_id=(p_binding->>'budget_reservation_id')::uuid AND b.task_id=t.task_id AND b.run_id=r.run_id
    JOIN factory.model_rotator_request_grants g ON g.reservation_id=b.reservation_id AND g.registry_digest=p_registry
    WHERE t.task_id=(p_binding->>'task_id')::uuid AND t.repository_id=p_binding->>'repository_id'
      AND p_binding->>'tenant_id'=t.repository_id AND t.current_run_id=r.run_id AND t.current_fence=(p_binding->>'fence')::bigint
      AND r.fence=t.current_fence AND r.state='leased' AND r.released_at IS NULL AND r.lease_expires_at>clock_timestamp()
      AND b.released_at IS NULL AND g.request_units>=(p_binding->>'remaining_request_units')::bigint FOR UPDATE OF t,r,a,b,g;
  IF NOT FOUND OR v_budget<>p_binding->>'budget_digest' THEN RETURN jsonb_build_object('error','authority_not_granted'); END IF;
  v_server_digest=encode(digest(convert_to(concat_ws(chr(31),p_binding->>'repository_id',p_binding->>'task_id',p_binding->>'run_id',p_binding->>'attempt_id',p_binding->>'fence',p_binding->>'budget_reservation_id',v_budget,p_registry,p_binding->>'operation_id',p_binding->>'requested_provider_id',p_binding->>'requested_model_id',p_binding->>'remaining_token_units',p_binding->>'remaining_request_units'),'UTF8'),'sha256'),'hex');
  IF v_server_digest<>p_binding_digest THEN RETURN jsonb_build_object('error','binding_digest_mismatch'); END IF;
  PERFORM pg_advisory_xact_lock(hashtextextended('model-rotator:'||v_tenant||':'||trim(p_registry),0));
  SELECT * INTO v_prior FROM factory.model_rotator_operations WHERE operation_digest=v_operation FOR UPDATE;
  IF FOUND THEN
    IF v_prior.binding_digest<>p_binding_digest THEN RETURN jsonb_build_object('error','idempotency_conflict'); END IF;
    IF v_prior.state='complete' THEN RETURN jsonb_build_object('replay',v_prior.evidence); END IF;
    IF v_prior.state='claimed' AND v_prior.claim_expires_at<=clock_timestamp() THEN
      UPDATE factory.model_rotator_operations SET state='quarantined' WHERE binding_digest=v_prior.binding_digest;
      UPDATE factory.model_rotator_states SET quarantined=true WHERE tenant_digest=v_prior.tenant_digest AND registry_digest=v_prior.registry_digest;
    END IF;
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
  INSERT INTO factory.model_rotator_operations(binding_digest,operation_digest,task_id,run_id,attempt_id,reservation_id,fence,tenant_digest,budget_digest,registry_digest,state_version,claim_token,claim_expires_at,binding_token_limit,binding_request_limit,state)
    VALUES(p_binding_digest,v_operation,(p_binding->>'task_id')::uuid,(p_binding->>'run_id')::uuid,(p_binding->>'attempt_id')::uuid,(p_binding->>'budget_reservation_id')::uuid,(p_binding->>'fence')::bigint,v_tenant,v_budget,p_registry,v_state.version,v_token,clock_timestamp()+interval '30 seconds',(p_binding->>'remaining_token_units')::bigint,(p_binding->>'remaining_request_units')::bigint,'claimed');
  INSERT INTO factory.model_rotator_reservation_accounting(reservation_id,registry_digest) VALUES((p_binding->>'budget_reservation_id')::uuid,p_registry) ON CONFLICT DO NOTHING;
  RETURN jsonb_build_object('replay',NULL,'claim_token',v_token,'cooldowns',v_state.cooldowns,'cursor',v_state.cursor,'version',v_state.version);
END $$;

CREATE FUNCTION factory.model_rotator_reserve_v1(p_binding char(64),p_claim char(64),p_mode text,p_units bigint) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE v_op factory.model_rotator_operations%ROWTYPE; v_account factory.model_rotator_reservation_accounting%ROWTYPE; v_policy factory.model_rotator_registry_policies%ROWTYPE; v_budget bigint; v_requests bigint;
BEGIN
  SELECT * INTO v_op FROM factory.model_rotator_operations WHERE binding_digest=p_binding AND claim_token=p_claim AND state='claimed' AND claim_expires_at>clock_timestamp() FOR UPDATE;
  IF NOT FOUND OR p_mode NOT IN ('token','request') OR p_units<=0 THEN RETURN false; END IF;
  PERFORM 1 FROM factory.tasks t JOIN factory.runs r ON r.run_id=v_op.run_id AND r.task_id=t.task_id JOIN factory.attempts a ON a.attempt_id=v_op.attempt_id AND a.run_id=r.run_id
    JOIN factory.budget_reservations b ON b.reservation_id=v_op.reservation_id AND b.run_id=r.run_id JOIN factory.model_rotator_request_grants g ON g.reservation_id=b.reservation_id AND g.registry_digest=v_op.registry_digest WHERE t.task_id=v_op.task_id AND t.current_run_id=r.run_id AND t.current_fence=v_op.fence AND r.fence=v_op.fence AND r.state='leased' AND r.released_at IS NULL AND r.lease_expires_at>clock_timestamp() AND b.released_at IS NULL
      AND encode(digest(convert_to(concat_ws('|',b.reservation_id,b.task_id,b.run_id,b.token_units,b.cost_usd_micros,b.wall_seconds,b.reason_digest,g.request_units,g.grant_digest),'UTF8'),'sha256'),'hex')=v_op.budget_digest FOR UPDATE OF t,r,a,b,g;
  IF NOT FOUND THEN RETURN false; END IF;
  SELECT * INTO STRICT v_account FROM factory.model_rotator_reservation_accounting WHERE reservation_id=v_op.reservation_id AND registry_digest=v_op.registry_digest FOR UPDATE;
  SELECT * INTO STRICT v_policy FROM factory.model_rotator_registry_policies WHERE registry_digest=v_op.registry_digest;
  SELECT token_units INTO STRICT v_budget FROM factory.budget_reservations WHERE reservation_id=v_op.reservation_id AND released_at IS NULL FOR UPDATE;
  SELECT request_units INTO STRICT v_requests FROM factory.model_rotator_request_grants WHERE reservation_id=v_op.reservation_id AND registry_digest=v_op.registry_digest FOR UPDATE;
  IF p_mode='token' THEN
    IF v_account.held_token_units+v_account.settled_token_units+p_units>least(v_budget,v_policy.token_quota,v_op.binding_token_limit) THEN RETURN false; END IF;
    UPDATE factory.model_rotator_reservation_accounting SET held_token_units=held_token_units+p_units WHERE reservation_id=v_op.reservation_id AND registry_digest=v_op.registry_digest;
    UPDATE factory.model_rotator_operations SET reserved_token_units=reserved_token_units+p_units WHERE binding_digest=p_binding;
  ELSE
    IF p_units<>1 OR v_account.held_request_units+v_account.settled_request_units+1>least(v_policy.request_quota,v_op.binding_request_limit,v_requests) THEN RETURN false; END IF;
    UPDATE factory.model_rotator_reservation_accounting SET held_request_units=held_request_units+1 WHERE reservation_id=v_op.reservation_id AND registry_digest=v_op.registry_digest;
    UPDATE factory.model_rotator_operations SET reserved_request_units=reserved_request_units+1 WHERE binding_digest=p_binding;
  END IF;
  RETURN true;
END $$;

CREATE FUNCTION factory.model_rotator_finish_v1(p_binding char(64),p_claim char(64),p_evidence jsonb,p_cooldowns jsonb,p_cursor integer,p_version bigint) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE v_op factory.model_rotator_operations%ROWTYPE;
BEGIN
  SELECT * INTO v_op FROM factory.model_rotator_operations WHERE binding_digest=p_binding AND claim_token=p_claim AND state='claimed' AND state_version=p_version AND claim_expires_at>clock_timestamp() FOR UPDATE;
  IF NOT FOUND OR p_evidence IS NULL OR p_cursor<0 OR jsonb_typeof(p_cooldowns)<>'object' THEN RETURN false; END IF;
  PERFORM 1 FROM factory.tasks t JOIN factory.runs r ON r.run_id=v_op.run_id AND r.task_id=t.task_id JOIN factory.attempts a ON a.attempt_id=v_op.attempt_id AND a.run_id=r.run_id JOIN factory.budget_reservations b ON b.reservation_id=v_op.reservation_id AND b.run_id=r.run_id JOIN factory.model_rotator_request_grants g ON g.reservation_id=b.reservation_id AND g.registry_digest=v_op.registry_digest WHERE t.task_id=v_op.task_id AND t.current_run_id=r.run_id AND t.current_fence=v_op.fence AND r.fence=v_op.fence AND r.state='leased' AND r.released_at IS NULL AND r.lease_expires_at>clock_timestamp() AND b.released_at IS NULL
    AND encode(digest(convert_to(concat_ws('|',b.reservation_id,b.task_id,b.run_id,b.token_units,b.cost_usd_micros,b.wall_seconds,b.reason_digest,g.request_units,g.grant_digest),'UTF8'),'sha256'),'hex')=v_op.budget_digest FOR UPDATE OF t,r,a,b,g;
  IF NOT FOUND THEN RETURN false; END IF;
  UPDATE factory.model_rotator_states SET cursor=p_cursor,requested_model_digest=p_evidence->>'next_model_digest',cooldowns=p_cooldowns,
    version=version+1,updated_at=clock_timestamp()
    WHERE tenant_digest=v_op.tenant_digest AND registry_digest=v_op.registry_digest AND version=p_version;
  IF NOT FOUND THEN RAISE EXCEPTION 'model rotator state version conflict' USING ERRCODE='40001'; END IF;
  UPDATE factory.model_rotator_reservation_accounting SET held_token_units=held_token_units-v_op.reserved_token_units,settled_token_units=settled_token_units+v_op.reserved_token_units,held_request_units=held_request_units-v_op.reserved_request_units,settled_request_units=settled_request_units+v_op.reserved_request_units WHERE reservation_id=v_op.reservation_id AND registry_digest=v_op.registry_digest;
  IF NOT FOUND THEN RAISE EXCEPTION 'model rotator accounting missing' USING ERRCODE='23503'; END IF;
  UPDATE factory.model_rotator_operations SET state='complete',evidence=p_evidence,completed_at=clock_timestamp() WHERE binding_digest=p_binding;
  RETURN true;
END $$;

CREATE FUNCTION factory.model_rotator_reconcile_v1(p_binding char(64),p_outcome text) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE v_op factory.model_rotator_operations%ROWTYPE;
BEGIN
  SELECT * INTO v_op FROM factory.model_rotator_operations WHERE binding_digest=p_binding AND state='quarantined' FOR UPDATE;
  IF NOT FOUND OR p_outcome NOT IN ('settle','release') THEN RETURN false; END IF;
  UPDATE factory.model_rotator_reservation_accounting SET held_token_units=held_token_units-v_op.reserved_token_units,settled_token_units=settled_token_units+CASE WHEN p_outcome='settle' THEN v_op.reserved_token_units ELSE 0 END,held_request_units=held_request_units-v_op.reserved_request_units,settled_request_units=settled_request_units+CASE WHEN p_outcome='settle' THEN v_op.reserved_request_units ELSE 0 END WHERE reservation_id=v_op.reservation_id AND registry_digest=v_op.registry_digest;
  UPDATE factory.model_rotator_states SET quarantined=false,version=version+1,updated_at=clock_timestamp()
    WHERE tenant_digest=v_op.tenant_digest AND registry_digest=v_op.registry_digest AND quarantined=true;
  UPDATE factory.model_rotator_operations SET state='complete',completed_at=clock_timestamp() WHERE binding_digest=p_binding;
  RETURN FOUND;
END $$;

CREATE FUNCTION factory.model_rotator_quarantine_v1(p_binding char(64),p_claim char(64),p_evidence jsonb) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE v_op factory.model_rotator_operations%ROWTYPE;
BEGIN
  SELECT * INTO v_op FROM factory.model_rotator_operations WHERE binding_digest=p_binding AND claim_token=p_claim AND state='claimed' FOR UPDATE;
  IF NOT FOUND THEN RETURN false; END IF;
  UPDATE factory.model_rotator_states SET quarantined=true,updated_at=clock_timestamp() WHERE tenant_digest=v_op.tenant_digest AND registry_digest=v_op.registry_digest;
  UPDATE factory.model_rotator_operations SET state='quarantined',evidence=p_evidence,completed_at=clock_timestamp() WHERE binding_digest=p_binding;
  RETURN true;
END $$;
REVOKE ALL ON factory.model_rotator_registry_policies,factory.model_rotator_states,factory.model_rotator_operations,factory.model_rotator_reservation_accounting,factory.model_rotator_request_grants FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.model_rotator_claim_v1(jsonb,text,char,char,integer,char,bigint),factory.model_rotator_reserve_v1(char,char,text,bigint),factory.model_rotator_finish_v1(char,char,jsonb,jsonb,integer,bigint),factory.model_rotator_quarantine_v1(char,char,jsonb),factory.model_rotator_reconcile_v1(char,text) FROM PUBLIC;
REVOKE ALL ON factory.model_rotator_safe_status FROM PUBLIC;
GRANT SELECT ON factory.model_rotator_safe_status TO factory_runtime,factory_audit_reader;
GRANT EXECUTE ON FUNCTION factory.model_rotator_claim_v1(jsonb,text,char,char,integer,char,bigint),factory.model_rotator_reserve_v1(char,char,text,bigint),factory.model_rotator_finish_v1(char,char,jsonb,jsonb,integer,bigint),factory.model_rotator_quarantine_v1(char,char,jsonb) TO factory_runtime;
GRANT EXECUTE ON FUNCTION factory.model_rotator_reconcile_v1(char,text) TO factory_migrator;
GRANT SELECT,INSERT,UPDATE,DELETE ON factory.model_rotator_request_grants TO factory_migrator;
