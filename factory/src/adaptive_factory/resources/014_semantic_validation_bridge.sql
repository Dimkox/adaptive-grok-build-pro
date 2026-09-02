DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='factory_semantic_coordinator') THEN
    CREATE ROLE factory_semantic_coordinator NOLOGIN NOINHERIT;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='factory_semantic_validator') THEN
    CREATE ROLE factory_semantic_validator NOLOGIN NOINHERIT;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='factory_semantic_adjudicator') THEN
    CREATE ROLE factory_semantic_adjudicator NOLOGIN NOINHERIT;
  END IF;
  IF EXISTS (
    SELECT 1 FROM pg_roles r
    WHERE r.rolname IN (
      'factory_semantic_coordinator','factory_semantic_validator','factory_semantic_adjudicator'
    ) AND (
      r.rolcanlogin OR r.rolinherit OR r.rolsuper OR r.rolcreaterole OR r.rolcreatedb
      OR r.rolreplication OR r.rolbypassrls
      OR COALESCE(array_length(r.rolconfig,1),0)>0
    )
  ) OR EXISTS (
    SELECT 1 FROM pg_auth_members m JOIN pg_roles member ON member.oid=m.member
    WHERE member.rolname IN (
      'factory_semantic_coordinator','factory_semantic_validator','factory_semantic_adjudicator'
    )
  ) THEN
    RAISE EXCEPTION 'unsafe semantic capability role';
  END IF;
END $$;

CREATE TABLE factory.semantic_command_results (
  operation text NOT NULL CHECK (operation='publish_subject'),
  idempotency_key char(64) NOT NULL CHECK (idempotency_key ~ '^[0-9a-f]{64}$'),
  request_digest char(64) NOT NULL CHECK (request_digest ~ '^[0-9a-f]{64}$'),
  resource_digest char(64) NOT NULL CHECK (resource_digest ~ '^[0-9a-f]{64}$'),
  response_body jsonb NOT NULL CHECK (octet_length(response_body::text)<=262144),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (operation,idempotency_key)
);

CREATE TABLE factory.semantic_subjects (
  subject_digest char(64) PRIMARY KEY CHECK (subject_digest ~ '^[0-9a-f]{64}$'),
  envelope_digest char(64) NOT NULL UNIQUE CHECK (envelope_digest ~ '^[0-9a-f]{64}$'),
  execution_binding_digest char(64) NOT NULL UNIQUE
    CHECK (execution_binding_digest ~ '^[0-9a-f]{64}$'),
  validation_inputs_digest char(64) NOT NULL CHECK (validation_inputs_digest ~ '^[0-9a-f]{64}$'),
  workspace_result_digest char(64) NOT NULL UNIQUE
    REFERENCES factory.workspace_results(workspace_result_digest) ON DELETE RESTRICT,
  task_id uuid NOT NULL,
  run_id uuid NOT NULL,
  fence bigint NOT NULL CHECK (fence>0),
  owner_id text NOT NULL CHECK (octet_length(owner_id) BETWEEN 1 AND 128),
  repository_id text NOT NULL CHECK (octet_length(repository_id) BETWEEN 1 AND 128),
  task_packet_digest char(64) NOT NULL,
  run_manifest_digest char(64) NOT NULL,
  workspace_snapshot_digest char(64) NOT NULL CHECK (workspace_snapshot_digest ~ '^[0-9a-f]{64}$'),
  terminal_proposal_digest char(64) NOT NULL CHECK (terminal_proposal_digest ~ '^[0-9a-f]{64}$'),
  exact_base_sha char(40) NOT NULL CHECK (exact_base_sha ~ '^[0-9a-f]{40}$'),
  input_head_sha char(40) NOT NULL CHECK (input_head_sha ~ '^[0-9a-f]{40}$'),
  exact_head_sha char(40) NOT NULL CHECK (exact_head_sha ~ '^[0-9a-f]{40}$'),
  publish_request_digest char(64) NOT NULL CHECK (publish_request_digest ~ '^[0-9a-f]{64}$'),
  execution_binding_body jsonb NOT NULL CHECK (octet_length(execution_binding_body::text)<=1048576),
  validation_inputs_body jsonb NOT NULL CHECK (octet_length(validation_inputs_body::text)<=1048576),
  subject_body jsonb NOT NULL CHECK (octet_length(subject_body::text)<=1048576),
  envelope_body jsonb NOT NULL CHECK (octet_length(envelope_body::text)<=262144),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  FOREIGN KEY (task_packet_digest,run_id)
    REFERENCES factory.execution_packets(packet_digest,run_id) ON DELETE RESTRICT,
  FOREIGN KEY (run_manifest_digest,run_id)
    REFERENCES factory.execution_manifests(manifest_digest,run_id) ON DELETE RESTRICT,
  FOREIGN KEY (run_id,terminal_proposal_digest)
    REFERENCES factory.execution_proposals(run_id,idempotency_key) ON DELETE RESTRICT
);
CREATE INDEX semantic_subjects_task_created
  ON factory.semantic_subjects(task_id,created_at,subject_digest);

CREATE TABLE factory.semantic_assignments (
  assignment_digest char(64) PRIMARY KEY CHECK (assignment_digest ~ '^[0-9a-f]{64}$'),
  subject_digest char(64) NOT NULL REFERENCES factory.semantic_subjects(subject_digest) ON DELETE RESTRICT,
  validator_id text NOT NULL CHECK (octet_length(validator_id) BETWEEN 1 AND 128),
  validator_context_digest char(64) NOT NULL CHECK (validator_context_digest ~ '^[0-9a-f]{64}$'),
  request_digest char(64) NOT NULL CHECK (request_digest ~ '^[0-9a-f]{64}$'),
  body jsonb NOT NULL CHECK (octet_length(body::text)<=262144),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  UNIQUE(subject_digest,validator_id,validator_context_digest)
);

CREATE TABLE factory.semantic_findings (
  finding_digest char(64) PRIMARY KEY CHECK (finding_digest ~ '^[0-9a-f]{64}$'),
  subject_digest char(64) NOT NULL REFERENCES factory.semantic_subjects(subject_digest) ON DELETE RESTRICT,
  assignment_digest char(64) NOT NULL REFERENCES factory.semantic_assignments(assignment_digest) ON DELETE RESTRICT,
  request_digest char(64) NOT NULL CHECK (request_digest ~ '^[0-9a-f]{64}$'),
  body jsonb NOT NULL CHECK (octet_length(body::text)<=1048576),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE factory.semantic_coverage (
  coverage_digest char(64) PRIMARY KEY CHECK (coverage_digest ~ '^[0-9a-f]{64}$'),
  subject_digest char(64) NOT NULL REFERENCES factory.semantic_subjects(subject_digest) ON DELETE RESTRICT,
  assignment_digest char(64) NOT NULL REFERENCES factory.semantic_assignments(assignment_digest) ON DELETE RESTRICT,
  request_digest char(64) NOT NULL CHECK (request_digest ~ '^[0-9a-f]{64}$'),
  body jsonb NOT NULL CHECK (octet_length(body::text)<=1048576),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  UNIQUE(subject_digest,assignment_digest)
);

CREATE TABLE factory.semantic_verdicts (
  verdict_digest char(64) PRIMARY KEY CHECK (verdict_digest ~ '^[0-9a-f]{64}$'),
  subject_digest char(64) NOT NULL UNIQUE
    REFERENCES factory.semantic_subjects(subject_digest) ON DELETE RESTRICT,
  evidence_set_digest char(64) NOT NULL CHECK (evidence_set_digest ~ '^[0-9a-f]{64}$'),
  request_digest char(64) NOT NULL CHECK (request_digest ~ '^[0-9a-f]{64}$'),
  body jsonb NOT NULL CHECK (octet_length(body::text)<=1048576),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE factory.semantic_directives (
  directive_digest char(64) PRIMARY KEY CHECK (directive_digest ~ '^[0-9a-f]{64}$'),
  subject_digest char(64) NOT NULL REFERENCES factory.semantic_subjects(subject_digest) ON DELETE RESTRICT,
  verdict_digest char(64) NOT NULL UNIQUE REFERENCES factory.semantic_verdicts(verdict_digest) ON DELETE RESTRICT,
  request_digest char(64) NOT NULL CHECK (request_digest ~ '^[0-9a-f]{64}$'),
  body jsonb NOT NULL CHECK (octet_length(body::text)<=1048576),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE factory.semantic_child_proposals (
  child_proposal_digest char(64) PRIMARY KEY CHECK (child_proposal_digest ~ '^[0-9a-f]{64}$'),
  subject_digest char(64) NOT NULL REFERENCES factory.semantic_subjects(subject_digest) ON DELETE RESTRICT,
  directive_digest char(64) NOT NULL REFERENCES factory.semantic_directives(directive_digest) ON DELETE RESTRICT,
  parent_task_id uuid NOT NULL,
  parent_run_id uuid NOT NULL,
  parent_fence bigint NOT NULL CHECK (parent_fence>0),
  cycle integer NOT NULL CHECK (cycle BETWEEN 1 AND 3),
  request_digest char(64) NOT NULL CHECK (request_digest ~ '^[0-9a-f]{64}$'),
  body jsonb NOT NULL CHECK (octet_length(body::text)<=1048576),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  UNIQUE(subject_digest,cycle)
);

CREATE TABLE factory.semantic_recovery_records (
  recovery_digest char(64) PRIMARY KEY CHECK (recovery_digest ~ '^[0-9a-f]{64}$'),
  subject_digest char(64) NOT NULL REFERENCES factory.semantic_subjects(subject_digest) ON DELETE RESTRICT,
  lifecycle_state text NOT NULL CHECK (lifecycle_state IN (
    'subject_published','assignment_pending','evidence_pending','adjudication_pending',
    'repair_pending','complete','needs_human'
  )),
  recovery_outcome text NOT NULL CHECK (recovery_outcome IN (
    'resumed','already_complete','stale','deadline','budget','fence','needs_human'
  )),
  request_digest char(64) NOT NULL CHECK (request_digest ~ '^[0-9a-f]{64}$'),
  body jsonb NOT NULL CHECK (octet_length(body::text)<=262144),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE factory.semantic_metric_events (
  metric_event_id bigserial PRIMARY KEY,
  metric_name text NOT NULL CHECK (metric_name IN (
    'semantic_subject_lifecycle','semantic_validation_outcome','semantic_recovery_outcome'
  )),
  label text NOT NULL CHECK (label IN (
    'published','pass','repair','needs_human','resumed','already_complete',
    'stale','deadline','budget','fence'
  )),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE FUNCTION factory.semantic_reject_mutation() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,factory AS $$
BEGIN
  RAISE EXCEPTION 'semantic records are append-only';
END;
$$;

CREATE TRIGGER semantic_command_results_immutable BEFORE UPDATE OR DELETE
  ON factory.semantic_command_results FOR EACH ROW EXECUTE FUNCTION factory.semantic_reject_mutation();
CREATE TRIGGER semantic_subjects_immutable BEFORE UPDATE OR DELETE
  ON factory.semantic_subjects FOR EACH ROW EXECUTE FUNCTION factory.semantic_reject_mutation();
CREATE TRIGGER semantic_assignments_immutable BEFORE UPDATE OR DELETE
  ON factory.semantic_assignments FOR EACH ROW EXECUTE FUNCTION factory.semantic_reject_mutation();
CREATE TRIGGER semantic_findings_immutable BEFORE UPDATE OR DELETE
  ON factory.semantic_findings FOR EACH ROW EXECUTE FUNCTION factory.semantic_reject_mutation();
CREATE TRIGGER semantic_coverage_immutable BEFORE UPDATE OR DELETE
  ON factory.semantic_coverage FOR EACH ROW EXECUTE FUNCTION factory.semantic_reject_mutation();
CREATE TRIGGER semantic_verdicts_immutable BEFORE UPDATE OR DELETE
  ON factory.semantic_verdicts FOR EACH ROW EXECUTE FUNCTION factory.semantic_reject_mutation();
CREATE TRIGGER semantic_directives_immutable BEFORE UPDATE OR DELETE
  ON factory.semantic_directives FOR EACH ROW EXECUTE FUNCTION factory.semantic_reject_mutation();
CREATE TRIGGER semantic_child_proposals_immutable BEFORE UPDATE OR DELETE
  ON factory.semantic_child_proposals FOR EACH ROW EXECUTE FUNCTION factory.semantic_reject_mutation();
CREATE TRIGGER semantic_recovery_records_immutable BEFORE UPDATE OR DELETE
  ON factory.semantic_recovery_records FOR EACH ROW EXECUTE FUNCTION factory.semantic_reject_mutation();
CREATE TRIGGER semantic_metric_events_immutable BEFORE UPDATE OR DELETE
  ON factory.semantic_metric_events FOR EACH ROW EXECUTE FUNCTION factory.semantic_reject_mutation();

CREATE FUNCTION factory.semantic_execution_material(
  p_task_id uuid,p_workspace_result_digest char(64)
) RETURNS jsonb
LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
  SELECT jsonb_build_object(
    'result',w.body,
    'snapshot',w.workspace_snapshot,
    'packet',p.body,
    'manifest',m.body,
    'terminal_proposal',terminal.body,
    'artifact_proposals',COALESCE((
      SELECT jsonb_agg(proposal.body ORDER BY proposal.idempotency_key)
      FROM factory.execution_proposals proposal
      WHERE proposal.run_id=w.run_id AND proposal.proposal_kind='artifact'
    ),'[]'::jsonb),
    'artifact_attestations',COALESCE((
      SELECT jsonb_agg(attestation.body ORDER BY attestation.artifact_attestation_digest)
      FROM factory.execution_artifact_attestations attestation
      WHERE attestation.run_id=w.run_id
    ),'[]'::jsonb)
  )
  FROM factory.workspace_results w
  JOIN factory.execution_packets p
    ON p.run_id=w.run_id AND p.packet_digest=w.task_packet_digest
  JOIN factory.execution_manifests m
    ON m.run_id=w.run_id AND m.manifest_digest=w.run_manifest_digest
  JOIN factory.execution_proposals terminal
    ON terminal.run_id=w.run_id AND terminal.idempotency_key=w.terminal_proposal_digest
      AND terminal.proposal_kind='terminal'
  WHERE w.task_id=p_task_id AND w.workspace_result_digest=p_workspace_result_digest
    AND w.terminal_stage='completed' AND w.m4_status='ready_for_human'
    AND w.failure_class IS NULL AND w.failure_reason IS NULL
    AND p.body->>'role'='writer'
$$;

CREATE FUNCTION factory.semantic_publish_subject(
  p_idempotency_key char(64),
  p_request_digest char(64),p_request_canonical text,
  p_binding_digest char(64),p_binding_canonical text,
  p_validation_inputs_digest char(64),p_validation_inputs_canonical text,
  p_subject_digest char(64),p_subject_canonical text,
  p_envelope_digest char(64),p_envelope_canonical text,
  p_authority_digest char(64),p_authority_canonical text
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE
  v_request jsonb;
  v_binding_document jsonb;
  v_binding jsonb;
  v_inputs_document jsonb;
  v_inputs jsonb;
  v_subject jsonb;
  v_envelope jsonb;
  v_authority_document jsonb;
  v_existing factory.semantic_subjects%ROWTYPE;
  v_prior factory.semantic_command_results%ROWTYPE;
  v_packet jsonb;
  v_manifest jsonb;
  v_snapshot jsonb;
  v_result jsonb;
  v_terminal jsonb;
  v_artifact_digests jsonb;
  v_attestation_digests jsonb;
  v_task_id uuid;
  v_run_id uuid;
  v_response jsonb;
BEGIN
  IF current_setting('transaction_isolation') IS DISTINCT FROM 'read committed'
    OR p_idempotency_key IS NULL OR p_idempotency_key !~ '^[0-9a-f]{64}$'
    OR p_request_digest IS NULL OR p_binding_digest IS NULL
    OR p_validation_inputs_digest IS NULL OR p_subject_digest IS NULL
    OR p_envelope_digest IS NULL OR p_authority_digest IS NULL
    OR p_request_canonical IS NULL OR octet_length(p_request_canonical)>262144
    OR p_binding_canonical IS NULL OR octet_length(p_binding_canonical)>1048576
    OR p_validation_inputs_canonical IS NULL OR octet_length(p_validation_inputs_canonical)>1048576
    OR p_subject_canonical IS NULL OR octet_length(p_subject_canonical)>1048576
    OR p_envelope_canonical IS NULL OR octet_length(p_envelope_canonical)>262144
    OR p_authority_canonical IS NULL OR octet_length(p_authority_canonical)>262144
  THEN RETURN NULL; END IF;

  v_request=p_request_canonical::jsonb;
  v_binding_document=p_binding_canonical::jsonb;
  v_binding=v_binding_document-'contract';
  v_inputs_document=p_validation_inputs_canonical::jsonb;
  v_inputs=v_inputs_document-'contract';
  v_subject=p_subject_canonical::jsonb;
  v_envelope=p_envelope_canonical::jsonb;
  v_authority_document=p_authority_canonical::jsonb;

  IF trim(factory.execution_contract_hash(NULL,p_request_canonical)) IS DISTINCT FROM trim(p_request_digest)
    OR trim(factory.execution_contract_hash(NULL,p_binding_canonical)) IS DISTINCT FROM trim(p_binding_digest)
    OR trim(factory.execution_contract_hash(NULL,p_validation_inputs_canonical)) IS DISTINCT FROM trim(p_validation_inputs_digest)
    OR trim(factory.execution_contract_hash(NULL,p_subject_canonical)) IS DISTINCT FROM trim(p_subject_digest)
    OR trim(factory.execution_contract_hash(NULL,p_envelope_canonical)) IS DISTINCT FROM trim(p_envelope_digest)
    OR trim(factory.execution_contract_hash(NULL,p_authority_canonical)) IS DISTINCT FROM trim(p_authority_digest)
    OR jsonb_typeof(v_request) IS DISTINCT FROM 'object'
    OR (SELECT count(*) FROM jsonb_object_keys(v_request))<>6
    OR v_request->>'contract' IS DISTINCT FROM 'adaptive-factory.semantic-subject-publication/v1'
    OR v_request->>'idempotency_key' IS DISTINCT FROM trim(p_idempotency_key)
    OR v_request->>'binding_digest' IS DISTINCT FROM trim(p_binding_digest)
    OR v_request->>'validation_inputs_digest' IS DISTINCT FROM trim(p_validation_inputs_digest)
    OR v_request->>'subject_digest' IS DISTINCT FROM trim(p_subject_digest)
    OR v_request->>'envelope_digest' IS DISTINCT FROM trim(p_envelope_digest)
    OR jsonb_typeof(v_binding_document) IS DISTINCT FROM 'object'
    OR (SELECT count(*) FROM jsonb_object_keys(v_binding_document))<>28
    OR v_binding_document->>'contract' IS DISTINCT FROM 'adaptive-factory.semantic-execution-binding/v1'
    OR jsonb_typeof(v_inputs_document) IS DISTINCT FROM 'object'
    OR (SELECT count(*) FROM jsonb_object_keys(v_inputs_document))<>9
    OR v_inputs_document->>'contract' IS DISTINCT FROM 'adaptive-factory.semantic-validation-inputs/v1'
    OR jsonb_typeof(v_subject) IS DISTINCT FROM 'object'
    OR (SELECT count(*) FROM jsonb_object_keys(v_subject))<>17
    OR jsonb_typeof(v_envelope) IS DISTINCT FROM 'object'
    OR (SELECT count(*) FROM jsonb_object_keys(v_envelope))<>4
    OR v_envelope->>'contract' IS DISTINCT FROM 'adaptive-factory.semantic-subject-envelope/v1'
    OR v_envelope->>'binding_digest' IS DISTINCT FROM trim(p_binding_digest)
    OR v_envelope->>'validation_inputs_digest' IS DISTINCT FROM trim(p_validation_inputs_digest)
    OR v_envelope->>'subject_digest' IS DISTINCT FROM trim(p_subject_digest)
    OR jsonb_typeof(v_authority_document) IS DISTINCT FROM 'object'
    OR (SELECT count(*) FROM jsonb_object_keys(v_authority_document))<>2
    OR v_authority_document->>'contract' IS DISTINCT FROM 'adaptive-factory.semantic-authority-binding/v1'
    OR jsonb_typeof(v_authority_document->'authority') IS DISTINCT FROM 'object'
    OR v_binding->>'schema_version' IS DISTINCT FROM '1'
    OR v_inputs->>'schema_version' IS DISTINCT FROM '1'
    OR v_subject->>'schema_version' IS DISTINCT FROM '1'
    OR jsonb_typeof(v_binding->'artifact_proposal_digests') IS DISTINCT FROM 'array'
    OR jsonb_array_length(v_binding->'artifact_proposal_digests')>256
    OR jsonb_typeof(v_binding->'artifact_attestation_digests') IS DISTINCT FROM 'array'
    OR jsonb_array_length(v_binding->'artifact_attestation_digests')>256
    OR jsonb_typeof(v_inputs->'requirements') IS DISTINCT FROM 'array'
    OR jsonb_array_length(v_inputs->'requirements') NOT BETWEEN 1 AND 256
    OR v_subject->'requirements' IS DISTINCT FROM v_inputs->'requirements'
    OR v_inputs->>'workspace_result_digest' IS DISTINCT FROM v_binding->>'workspace_result_digest'
    OR v_subject->>'deterministic_evidence_digest' IS DISTINCT FROM trim(p_binding_digest)
    OR v_subject->>'holdout_evidence_digest' IS DISTINCT FROM v_inputs->>'holdout_evidence_digest'
    OR v_subject->>'review_evidence_digest' IS DISTINCT FROM v_inputs->>'review_evidence_digest'
    OR v_subject->>'original_writer_context_digest' IS DISTINCT FROM v_inputs->>'original_writer_context_digest'
    OR v_subject->>'risk_level' IS DISTINCT FROM v_inputs->>'risk_level'
    OR v_subject->>'diff_limit' IS DISTINCT FROM v_inputs->>'diff_limit'
    OR v_subject->>'authority_digest' IS DISTINCT FROM trim(p_authority_digest)
  THEN RETURN NULL; END IF;

  SELECT * INTO v_prior FROM factory.semantic_command_results
    WHERE operation='publish_subject' AND idempotency_key=p_idempotency_key;
  IF FOUND THEN
    RETURN CASE WHEN v_prior.request_digest=p_request_digest
      THEN v_prior.response_body ELSE NULL END;
  END IF;

  BEGIN
    v_task_id=(v_binding->>'task_id')::uuid;
    v_run_id=(v_binding->>'run_id')::uuid;
  EXCEPTION WHEN invalid_text_representation OR numeric_value_out_of_range THEN
    RETURN NULL;
  END;

  PERFORM 1 FROM factory.workspace_results w
    WHERE w.task_id=v_task_id AND w.run_id=v_run_id
      AND w.workspace_result_digest=v_binding->>'workspace_result_digest'
    FOR UPDATE;
  IF NOT FOUND THEN RETURN NULL; END IF;

  SELECT * INTO v_prior FROM factory.semantic_command_results
    WHERE operation='publish_subject' AND idempotency_key=p_idempotency_key;
  IF FOUND THEN
    RETURN CASE WHEN v_prior.request_digest=p_request_digest
      THEN v_prior.response_body ELSE NULL END;
  END IF;

  SELECT p.body,m.body,w.workspace_snapshot,w.body,terminal.body,
    COALESCE((
      SELECT jsonb_agg(trim(proposal.idempotency_key) ORDER BY proposal.idempotency_key)
      FROM factory.execution_proposals proposal
      WHERE proposal.run_id=w.run_id AND proposal.proposal_kind='artifact'
    ),'[]'::jsonb),
    COALESCE((
      SELECT jsonb_agg(trim(attestation.artifact_attestation_digest)
        ORDER BY attestation.artifact_attestation_digest)
      FROM factory.execution_artifact_attestations attestation
      WHERE attestation.run_id=w.run_id
    ),'[]'::jsonb)
    INTO v_packet,v_manifest,v_snapshot,v_result,v_terminal,
      v_artifact_digests,v_attestation_digests
  FROM factory.workspace_results w
  JOIN factory.execution_packets p
    ON p.run_id=w.run_id AND p.packet_digest=w.task_packet_digest
  JOIN factory.execution_manifests m
    ON m.run_id=w.run_id AND m.manifest_digest=w.run_manifest_digest
  JOIN factory.execution_proposals terminal
    ON terminal.run_id=w.run_id AND terminal.idempotency_key=w.terminal_proposal_digest
      AND terminal.proposal_kind='terminal'
  JOIN factory.runs r ON r.run_id=w.run_id AND r.task_id=w.task_id
  JOIN factory.tasks t ON t.task_id=w.task_id
  WHERE w.task_id=v_task_id AND w.run_id=v_run_id
    AND w.workspace_result_digest=v_binding->>'workspace_result_digest'
    AND w.terminal_stage='completed' AND w.m4_status='ready_for_human'
    AND w.failure_class IS NULL AND w.failure_reason IS NULL
    AND t.state='ready_for_human'
    AND r.role='writer' AND r.owner_id=v_binding->>'owner'
    AND r.fence=(v_binding->>'fence')::bigint;
  IF NOT FOUND THEN RETURN NULL; END IF;

  IF v_packet->>'task_id' IS DISTINCT FROM v_binding->>'task_id'
    OR v_packet->>'run_id' IS DISTINCT FROM v_binding->>'run_id'
    OR v_packet->>'owner' IS DISTINCT FROM v_binding->>'owner'
    OR v_packet->>'fence' IS DISTINCT FROM v_binding->>'fence'
    OR v_packet->>'role' IS DISTINCT FROM 'writer'
    OR v_binding->>'role' IS DISTINCT FROM 'writer'
    OR v_packet->>'repository_id' IS DISTINCT FROM v_binding->>'repository_id'
    OR v_packet->>'workspace_handle' IS DISTINCT FROM v_binding->>'workspace_handle'
    OR v_packet->>'legacy_intent_digest' IS DISTINCT FROM v_binding->>'legacy_intent_digest'
    OR v_packet->>'packet_digest' IS DISTINCT FROM v_binding->>'task_packet_digest'
    OR v_manifest->>'manifest_digest' IS DISTINCT FROM v_binding->>'run_manifest_digest'
    OR v_manifest->>'packet_digest' IS DISTINCT FROM v_binding->>'task_packet_digest'
    OR v_manifest->>'run_id' IS DISTINCT FROM v_binding->>'run_id'
    OR v_manifest->>'workspace_handle' IS DISTINCT FROM v_binding->>'workspace_handle'
    OR v_result->>'workspace_result_digest' IS DISTINCT FROM v_binding->>'workspace_result_digest'
    OR v_result->>'task_packet_digest' IS DISTINCT FROM v_binding->>'task_packet_digest'
    OR v_result->>'run_manifest_digest' IS DISTINCT FROM v_binding->>'run_manifest_digest'
    OR v_result->>'workspace_snapshot_digest' IS DISTINCT FROM v_binding->>'workspace_snapshot_digest'
    OR v_result->>'terminal_proposal_digest' IS DISTINCT FROM v_binding->>'terminal_proposal_digest'
    OR v_result->>'artifact_manifest_digest' IS DISTINCT FROM v_binding->>'artifact_manifest_digest'
    OR v_result->>'note_manifest_digest' IS DISTINCT FROM v_binding->>'note_manifest_digest'
    OR v_result->>'usage_evidence_digest' IS DISTINCT FROM v_binding->>'usage_evidence_digest'
    OR v_result->>'diagnostics_digest' IS DISTINCT FROM v_binding->>'diagnostics_digest'
    OR v_result->>'terminal_stage' IS DISTINCT FROM 'completed'
    OR v_result->>'m4_status' IS DISTINCT FROM 'ready_for_human'
    OR v_result->'failure_class' IS DISTINCT FROM 'null'::jsonb
    OR v_result->'failure_reason' IS DISTINCT FROM 'null'::jsonb
    OR v_snapshot->>'workspace_snapshot_digest' IS DISTINCT FROM v_binding->>'workspace_snapshot_digest'
    OR v_snapshot->>'input_head_sha' IS DISTINCT FROM v_binding->>'input_head_sha'
    OR v_snapshot->>'result_head_sha' IS DISTINCT FROM v_binding->>'exact_head_sha'
    OR v_packet#>>'{authority,exact_base_sha}' IS DISTINCT FROM v_binding->>'exact_base_sha'
    OR v_packet#>>'{authority,exact_head_sha}' IS DISTINCT FROM v_binding->>'input_head_sha'
    OR v_result->>'exact_head_sha' IS DISTINCT FROM v_binding->>'exact_head_sha'
    OR v_terminal->>'idempotency_key' IS DISTINCT FROM v_binding->>'terminal_proposal_digest'
    OR v_terminal->>'terminal_type' IS DISTINCT FROM 'run.completed'
    OR v_terminal->>'author_role' IS DISTINCT FROM 'writer'
    OR v_binding->'artifact_proposal_digests' IS DISTINCT FROM v_artifact_digests
    OR v_binding->'artifact_attestation_digests' IS DISTINCT FROM v_attestation_digests
    OR v_authority_document->'authority' IS DISTINCT FROM v_packet->'authority'
    OR v_subject->>'subject_id' IS DISTINCT FROM
      'semantic:' || (v_binding->>'workspace_result_digest')
    OR v_subject->>'exact_base_sha' IS DISTINCT FROM v_binding->>'exact_base_sha'
    OR v_subject->>'exact_head_sha' IS DISTINCT FROM v_binding->>'exact_head_sha'
    OR v_subject->>'spec_digest' IS DISTINCT FROM v_packet#>>'{authority,spec_digest}'
    OR v_subject->>'architecture_digest' IS DISTINCT FROM v_packet#>>'{authority,architecture_digest}'
    OR v_subject->>'diff_digest' IS DISTINCT FROM v_snapshot->>'diff_digest'
    OR v_subject->>'diff_lines' IS DISTINCT FROM v_snapshot->>'diff_lines'
    OR v_subject->>'original_writer_id' IS DISTINCT FROM v_binding->>'owner'
    OR EXISTS (
      (SELECT value FROM jsonb_array_elements_text(v_packet->'acceptance_ids'))
      EXCEPT
      (SELECT item->>'requirement_id' FROM jsonb_array_elements(v_inputs->'requirements') item
        WHERE item->>'kind'='acceptance_criterion')
    )
    OR EXISTS (
      (SELECT item->>'requirement_id' FROM jsonb_array_elements(v_inputs->'requirements') item
        WHERE item->>'kind'='acceptance_criterion')
      EXCEPT
      (SELECT value FROM jsonb_array_elements_text(v_packet->'acceptance_ids'))
    )
  THEN RETURN NULL; END IF;

  SELECT * INTO v_existing FROM factory.semantic_subjects
    WHERE subject_digest=p_subject_digest
      OR workspace_result_digest=v_binding->>'workspace_result_digest';
  IF FOUND THEN
    IF v_existing.subject_digest IS DISTINCT FROM p_subject_digest
      OR v_existing.envelope_digest IS DISTINCT FROM p_envelope_digest
      OR v_existing.execution_binding_digest IS DISTINCT FROM p_binding_digest
      OR v_existing.validation_inputs_digest IS DISTINCT FROM p_validation_inputs_digest
      OR v_existing.execution_binding_body IS DISTINCT FROM v_binding
      OR v_existing.validation_inputs_body IS DISTINCT FROM v_inputs
      OR v_existing.subject_body IS DISTINCT FROM v_subject
      OR v_existing.envelope_body IS DISTINCT FROM v_envelope
    THEN RETURN NULL; END IF;
    v_response=v_existing.envelope_body;
  ELSE
    INSERT INTO factory.semantic_subjects(
      subject_digest,envelope_digest,execution_binding_digest,validation_inputs_digest,
      workspace_result_digest,task_id,run_id,fence,owner_id,repository_id,
      task_packet_digest,run_manifest_digest,workspace_snapshot_digest,
      terminal_proposal_digest,exact_base_sha,input_head_sha,exact_head_sha,
      publish_request_digest,execution_binding_body,validation_inputs_body,
      subject_body,envelope_body
    ) VALUES (
      p_subject_digest,p_envelope_digest,p_binding_digest,p_validation_inputs_digest,
      (v_binding->>'workspace_result_digest')::char(64),v_task_id,v_run_id,
      (v_binding->>'fence')::bigint,v_binding->>'owner',v_binding->>'repository_id',
      (v_binding->>'task_packet_digest')::char(64),(v_binding->>'run_manifest_digest')::char(64),
      (v_binding->>'workspace_snapshot_digest')::char(64),
      (v_binding->>'terminal_proposal_digest')::char(64),
      (v_binding->>'exact_base_sha')::char(40),(v_binding->>'input_head_sha')::char(40),
      (v_binding->>'exact_head_sha')::char(40),p_request_digest,
      v_binding,v_inputs,v_subject,v_envelope
    );
    INSERT INTO factory.semantic_metric_events(metric_name,label)
      VALUES ('semantic_subject_lifecycle','published');
    v_response=v_envelope;
  END IF;

  INSERT INTO factory.semantic_command_results(
    operation,idempotency_key,request_digest,resource_digest,response_body
  ) VALUES ('publish_subject',p_idempotency_key,p_request_digest,p_subject_digest,v_response);
  RETURN v_response;
EXCEPTION WHEN unique_violation OR check_violation OR foreign_key_violation
  OR invalid_text_representation OR numeric_value_out_of_range OR data_exception THEN
  RETURN NULL;
END;
$$;

CREATE FUNCTION factory.semantic_subject_by_digest(
  p_task_id uuid,p_subject_digest char(64)
) RETURNS jsonb
LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
  SELECT jsonb_build_object(
    'envelope_digest',trim(envelope_digest),
    'binding_digest',trim(execution_binding_digest),
    'validation_inputs_digest',trim(validation_inputs_digest),
    'subject_digest',trim(subject_digest),
    'binding',execution_binding_body,
    'validation_inputs',validation_inputs_body,
    'subject',subject_body
  )
  FROM factory.semantic_subjects
  WHERE task_id=p_task_id AND subject_digest=p_subject_digest
$$;

REVOKE ALL ON TABLE factory.semantic_command_results,factory.semantic_subjects,
  factory.semantic_assignments,factory.semantic_findings,factory.semantic_coverage,
  factory.semantic_verdicts,factory.semantic_directives,factory.semantic_child_proposals,
  factory.semantic_recovery_records,factory.semantic_metric_events FROM PUBLIC;
REVOKE ALL ON TABLE factory.semantic_command_results,factory.semantic_subjects,
  factory.semantic_assignments,factory.semantic_findings,factory.semantic_coverage,
  factory.semantic_verdicts,factory.semantic_directives,factory.semantic_child_proposals,
  factory.semantic_recovery_records,factory.semantic_metric_events
  FROM factory_runtime,factory_artifact_attestor,factory_semantic_coordinator,
    factory_semantic_validator,factory_semantic_adjudicator;
REVOKE INSERT, UPDATE, DELETE ON TABLE factory.semantic_command_results,
  factory.semantic_subjects,factory.semantic_assignments,factory.semantic_findings,
  factory.semantic_coverage,factory.semantic_verdicts,factory.semantic_directives,
  factory.semantic_child_proposals,factory.semantic_recovery_records,
  factory.semantic_metric_events FROM PUBLIC,factory_runtime,factory_artifact_attestor,
    factory_semantic_coordinator,factory_semantic_validator,factory_semantic_adjudicator;
REVOKE ALL ON SEQUENCE factory.semantic_metric_events_metric_event_id_seq FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.semantic_reject_mutation() FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.semantic_execution_material(uuid,char) FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.semantic_publish_subject(
  char,char,text,char,text,char,text,char,text,char,text,char,text
) FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.semantic_subject_by_digest(uuid,char) FROM PUBLIC;

GRANT USAGE ON SCHEMA factory TO factory_semantic_coordinator,
  factory_semantic_validator,factory_semantic_adjudicator;
GRANT EXECUTE ON FUNCTION factory.semantic_execution_material(uuid,char)
  TO factory_semantic_coordinator;
GRANT EXECUTE ON FUNCTION factory.semantic_publish_subject(
  char,char,text,char,text,char,text,char,text,char,text,char,text
) TO factory_semantic_coordinator;
GRANT EXECUTE ON FUNCTION factory.semantic_subject_by_digest(uuid,char)
  TO factory_semantic_coordinator;
