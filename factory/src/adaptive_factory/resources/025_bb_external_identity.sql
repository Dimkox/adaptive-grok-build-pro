-- External BB identity is durable operational ownership, not external authority.
-- No inferred backfill from old digests: full bindings must be explicitly readmitted.
CREATE TABLE factory.bb_external_bindings (
  binding_digest char(64) PRIMARY KEY CHECK(binding_digest ~ '^[0-9a-f]{64}$'),
  identity_key char(64) NOT NULL CHECK(identity_key ~ '^[0-9a-f]{64}$'),
  repository_id text NOT NULL,
  profile_digest char(64) NOT NULL,
  environment_id text NOT NULL,
  host_id text NOT NULL,
  project_id text NOT NULL,
  thread_id text NOT NULL,
  workflow_id text NOT NULL,
  task_id uuid NOT NULL,
  run_id uuid NOT NULL,
  attempt_id uuid NOT NULL REFERENCES factory.attempts(attempt_id) ON DELETE RESTRICT,
  fence bigint NOT NULL CHECK(fence>0),
  binding jsonb NOT NULL CHECK(octet_length(binding::text)<=65536),
  state text NOT NULL DEFAULT 'active' CHECK(state IN ('active','released','quarantined')),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  FOREIGN KEY(run_id,task_id) REFERENCES factory.runs(run_id,task_id) ON DELETE RESTRICT
);
CREATE UNIQUE INDEX bb_external_identity_active ON factory.bb_external_bindings(identity_key)
  WHERE state IN ('active','quarantined');
CREATE INDEX bb_external_binding_run ON factory.bb_external_bindings(run_id,binding_digest);
CREATE TABLE factory.bb_external_binding_receipts (
  binding_digest char(64) PRIMARY KEY REFERENCES factory.bb_external_bindings(binding_digest) ON DELETE RESTRICT,
  disposition text NOT NULL CHECK(disposition IN ('released','quarantined')),
  stop_evidence_digest char(64) NOT NULL CHECK(stop_evidence_digest ~ '^[0-9a-f]{64}$'),
  export_evidence_digest char(64) NOT NULL CHECK(export_evidence_digest ~ '^[0-9a-f]{64}$'),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TRIGGER bb_external_receipts_immutable BEFORE UPDATE OR DELETE
  ON factory.bb_external_binding_receipts FOR EACH ROW EXECUTE FUNCTION factory.semantic_reject_mutation();
CREATE FUNCTION factory.bb_external_reject_mutation() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,factory AS $$
BEGIN
  IF TG_OP='DELETE' OR (to_jsonb(OLD)-'state') IS DISTINCT FROM (to_jsonb(NEW)-'state')
    OR OLD.state<>'active' OR NOT EXISTS(SELECT 1 FROM factory.bb_external_binding_receipts
      WHERE binding_digest=OLD.binding_digest AND disposition=NEW.state) THEN
    RAISE EXCEPTION 'immutable_bb_external_binding';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER bb_external_bindings_immutable BEFORE UPDATE OR DELETE
  ON factory.bb_external_bindings FOR EACH ROW EXECUTE FUNCTION factory.bb_external_reject_mutation();

CREATE FUNCTION factory.bb_claim_external(p_task uuid,p_run uuid,p_owner text,p_fence bigint,
  p_packet char(64),p_digest char(64),p_binding jsonb) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE v_key char(64); v_prior factory.bb_external_bindings%ROWTYPE; v_repo text; v_name text;
BEGIN
  IF jsonb_typeof(p_binding)<>'object' OR octet_length(p_binding::text)>65536
    OR (SELECT count(*) FROM jsonb_object_keys(p_binding))<>28
    OR p_binding-ARRAY['schema_version','repository_id','task_id','run_id','attempt_id','fence',
      'contract_digest','policy_digest','context_digest','profile_digest','base_sha','candidate_sha',
      'branch','workspace','environment_id','host_id','project_id','thread_id','workflow_id',
      'provider','model','reasoning','permission','revision','lease_deadline','snapshots','children',
      'exported_evidence_digest']<>'{}'::jsonb
    OR p_binding->>'schema_version'<>'1'
    OR p_binding->>'task_id'<>p_task::text OR p_binding->>'run_id'<>p_run::text
    OR (p_binding->>'fence')::bigint<>p_fence
    OR factory.execution_contract_hash(NULL::text,factory.execution_canonical_json(p_binding))<>trim(p_digest)
  THEN RETURN 'rejected'; END IF;
  FOREACH v_name IN ARRAY ARRAY['repository_id','environment_id','host_id','project_id','thread_id','workflow_id'] LOOP
    IF jsonb_typeof(p_binding->v_name)<>'string' OR octet_length(p_binding->>v_name) NOT BETWEEN 1 AND 128
      OR (p_binding->>v_name)<>normalize(p_binding->>v_name,NFC) THEN RETURN 'rejected'; END IF;
  END LOOP;
  IF p_binding->>'profile_digest' !~ '^[0-9a-f]{64}$' THEN RETURN 'rejected'; END IF;
  SELECT t.repository_id INTO v_repo FROM factory.runs r JOIN factory.tasks t ON t.task_id=r.task_id
    JOIN factory.attempts a ON a.run_id=r.run_id AND a.task_id=t.task_id
    WHERE r.run_id=p_run AND t.task_id=p_task AND r.owner_id=p_owner AND r.fence=p_fence
      AND r.packet_digest=p_packet AND r.released_at IS NULL AND t.current_run_id=r.run_id
      AND t.current_fence=p_fence AND r.lease_expires_at>clock_timestamp()
      AND r.deadline_at>clock_timestamp() AND a.attempt_id=(p_binding->>'attempt_id')::uuid
    FOR UPDATE OF r,t;
  IF NOT FOUND OR v_repo<>p_binding->>'repository_id' THEN RETURN 'rejected'; END IF;
  v_key=factory.execution_contract_hash(NULL::text,factory.execution_canonical_json(jsonb_build_array(
    v_repo,p_binding->>'profile_digest',p_binding->>'environment_id',p_binding->>'host_id',
    p_binding->>'project_id',p_binding->>'thread_id',p_binding->>'workflow_id')));
  PERFORM pg_advisory_xact_lock(hashtextextended('bb-external:'||v_key,0));
  SELECT * INTO v_prior FROM factory.bb_external_bindings WHERE binding_digest=p_digest;
  IF FOUND THEN
    RETURN CASE WHEN v_prior.state='active' AND v_prior.binding=p_binding THEN 'replayed' ELSE 'conflict' END;
  END IF;
  IF EXISTS(SELECT 1 FROM factory.bb_external_bindings WHERE identity_key=v_key AND state IN ('active','quarantined'))
    THEN RETURN 'conflict'; END IF;
  INSERT INTO factory.bb_external_bindings(binding_digest,identity_key,repository_id,profile_digest,
    environment_id,host_id,project_id,thread_id,workflow_id,task_id,run_id,attempt_id,fence,binding)
    VALUES(p_digest,v_key,v_repo,p_binding->>'profile_digest',p_binding->>'environment_id',p_binding->>'host_id',
      p_binding->>'project_id',p_binding->>'thread_id',p_binding->>'workflow_id',p_task,p_run,
      (p_binding->>'attempt_id')::uuid,p_fence,p_binding);
  RETURN 'claimed';
EXCEPTION WHEN invalid_text_representation OR numeric_value_out_of_range THEN RETURN 'rejected';
END $$;

-- Operator-only; timeout/ACK are not observed stop, and no external effect is reversed.
CREATE FUNCTION factory.bb_resolve_external(p_digest char(64),p_disposition text,p_stop char(64),p_export char(64))
RETURNS boolean LANGUAGE plpgsql SET search_path=pg_catalog,factory AS $$
DECLARE v_key char(64);
BEGIN
  IF p_disposition IS NULL OR p_disposition NOT IN ('released','quarantined') OR p_stop IS NULL OR p_export IS NULL
    OR p_stop !~ '^[0-9a-f]{64}$' OR p_export !~ '^[0-9a-f]{64}$' THEN RETURN false; END IF;
  SELECT identity_key INTO v_key FROM factory.bb_external_bindings WHERE binding_digest=p_digest;
  IF NOT FOUND THEN RETURN false; END IF;
  PERFORM pg_advisory_xact_lock(hashtextextended('bb-external:'||v_key,0));
  PERFORM 1 FROM factory.bb_external_bindings WHERE binding_digest=p_digest FOR UPDATE;
  IF EXISTS(SELECT 1 FROM factory.bb_external_binding_receipts WHERE binding_digest=p_digest) THEN
    RETURN EXISTS(SELECT 1 FROM factory.bb_external_binding_receipts WHERE binding_digest=p_digest
      AND disposition=p_disposition AND stop_evidence_digest=p_stop AND export_evidence_digest=p_export);
  END IF;
  INSERT INTO factory.bb_external_binding_receipts(binding_digest,disposition,stop_evidence_digest,export_evidence_digest)
    VALUES(p_digest,p_disposition,p_stop,p_export);
  UPDATE factory.bb_external_bindings SET state=p_disposition WHERE binding_digest=p_digest;
  RETURN true;
END $$;
REVOKE ALL ON factory.bb_external_bindings,factory.bb_external_binding_receipts FROM PUBLIC;
GRANT SELECT ON factory.bb_external_bindings,factory.bb_external_binding_receipts TO factory_runtime;
REVOKE ALL ON FUNCTION factory.bb_external_reject_mutation(),
  factory.bb_claim_external(uuid,uuid,text,bigint,char,char,jsonb),factory.bb_resolve_external(char,text,char,char) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION factory.bb_claim_external(uuid,uuid,text,bigint,char,char,jsonb) TO factory_runtime;
