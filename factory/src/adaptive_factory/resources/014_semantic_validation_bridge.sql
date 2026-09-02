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
  operation text NOT NULL CHECK (operation IN (
    'publish_subject','create_assignment','append_evidence','append_verdict'
  )),
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
  finding_identity_digest char(64) NOT NULL
    CHECK (finding_identity_digest ~ '^[0-9a-f]{64}$'),
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

CREATE FUNCTION factory.semantic_create_assignment(
  p_idempotency_key char(64),p_request_digest char(64),p_request_canonical text,
  p_assignment_digest char(64),p_assignment_canonical text
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE
  v_request jsonb;
  v_assignment jsonb;
  v_validator jsonb;
  v_subject factory.semantic_subjects%ROWTYPE;
  v_existing factory.semantic_assignments%ROWTYPE;
  v_prior factory.semantic_command_results%ROWTYPE;
  v_response jsonb;
BEGIN
  IF current_setting('transaction_isolation') IS DISTINCT FROM 'read committed'
    OR p_idempotency_key IS NULL OR p_idempotency_key !~ '^[0-9a-f]{64}$'
    OR p_request_digest IS NULL OR p_assignment_digest IS NULL
    OR p_request_canonical IS NULL OR octet_length(p_request_canonical)>262144
    OR p_assignment_canonical IS NULL OR octet_length(p_assignment_canonical)>262144
  THEN RETURN NULL; END IF;

  v_request=p_request_canonical::jsonb;
  v_assignment=p_assignment_canonical::jsonb;
  IF trim(factory.execution_contract_hash(NULL,p_request_canonical))
      IS DISTINCT FROM trim(p_request_digest)
    OR trim(factory.execution_contract_hash(NULL,p_assignment_canonical))
      IS DISTINCT FROM trim(p_assignment_digest)
    OR jsonb_typeof(v_request) IS DISTINCT FROM 'object'
    OR (SELECT count(*) FROM jsonb_object_keys(v_request))<>4
    OR v_request->>'contract' IS DISTINCT FROM
      'adaptive-factory.semantic-assignment-command/v1'
    OR v_request->>'idempotency_key' IS DISTINCT FROM trim(p_idempotency_key)
    OR v_request->>'assignment_digest' IS DISTINCT FROM trim(p_assignment_digest)
    OR v_request->>'subject_digest' IS NULL
    OR jsonb_typeof(v_assignment) IS DISTINCT FROM 'object'
    OR (SELECT count(*) FROM jsonb_object_keys(v_assignment))<>3
    OR v_assignment->>'schema_version' IS DISTINCT FROM '1'
    OR v_assignment->>'subject_digest' IS DISTINCT FROM v_request->>'subject_digest'
    OR jsonb_typeof(v_assignment->'validator') IS DISTINCT FROM 'object'
  THEN RETURN NULL; END IF;

  v_validator=v_assignment->'validator';
  IF (SELECT count(*) FROM jsonb_object_keys(v_validator))<>6
    OR v_validator->>'role' IS DISTINCT FROM 'semantic_validator'
    OR octet_length(COALESCE(v_validator->>'validator_id','')) NOT BETWEEN 1 AND 128
    OR COALESCE(v_validator->>'definition_digest','') !~ '^[0-9a-f]{64}$'
    OR COALESCE(v_validator->>'model_digest','') !~ '^[0-9a-f]{64}$'
    OR COALESCE(v_validator->>'context_digest','') !~ '^[0-9a-f]{64}$'
    OR jsonb_typeof(v_validator->'capabilities') IS DISTINCT FROM 'array'
    OR jsonb_array_length(v_validator->'capabilities') NOT BETWEEN 2 AND 256
    OR NOT (v_validator->'capabilities' ?& ARRAY['repository_read','semantic_validate'])
    OR v_validator->'capabilities' ?| ARRAY[
      'application_write','adjudicate','external_write','network','credential_read'
    ]
    OR EXISTS (
      SELECT 1 FROM (
        SELECT value,ordinality,
          lag(value) OVER (ORDER BY ordinality) AS previous
        FROM jsonb_array_elements_text(v_validator->'capabilities')
          WITH ORDINALITY AS capability(value,ordinality)
      ) ordered WHERE previous IS NOT NULL AND value<=previous
    )
  THEN RETURN NULL; END IF;

  SELECT * INTO v_prior FROM factory.semantic_command_results
    WHERE operation='create_assignment' AND idempotency_key=p_idempotency_key;
  IF FOUND THEN
    RETURN CASE WHEN v_prior.request_digest=p_request_digest
      THEN v_prior.response_body ELSE NULL END;
  END IF;

  SELECT * INTO v_subject FROM factory.semantic_subjects
    WHERE subject_digest=(v_assignment->>'subject_digest')::char(64) FOR UPDATE;
  IF NOT FOUND
    OR v_validator->>'validator_id' IS NOT DISTINCT FROM v_subject.owner_id
    OR v_validator->>'context_digest' IS NOT DISTINCT FROM
      v_subject.subject_body->>'original_writer_context_digest'
  THEN RETURN NULL; END IF;

  SELECT * INTO v_prior FROM factory.semantic_command_results
    WHERE operation='create_assignment' AND idempotency_key=p_idempotency_key;
  IF FOUND THEN
    RETURN CASE WHEN v_prior.request_digest=p_request_digest
      THEN v_prior.response_body ELSE NULL END;
  END IF;

  SELECT * INTO v_existing FROM factory.semantic_assignments
    WHERE assignment_digest=p_assignment_digest
      OR (
        subject_digest=(v_assignment->>'subject_digest')::char(64)
        AND validator_id=v_validator->>'validator_id'
        AND validator_context_digest=(v_validator->>'context_digest')::char(64)
      );
  IF FOUND THEN
    IF v_existing.assignment_digest IS DISTINCT FROM p_assignment_digest
      OR v_existing.subject_digest IS DISTINCT FROM
        (v_assignment->>'subject_digest')::char(64)
      OR v_existing.body IS DISTINCT FROM v_assignment
    THEN RETURN NULL; END IF;
  ELSE
    INSERT INTO factory.semantic_assignments(
      assignment_digest,subject_digest,validator_id,validator_context_digest,
      request_digest,body
    ) VALUES (
      p_assignment_digest,(v_assignment->>'subject_digest')::char(64),
      v_validator->>'validator_id',(v_validator->>'context_digest')::char(64),
      p_request_digest,v_assignment
    );
  END IF;

  v_response=jsonb_build_object(
    'assignment_digest',trim(p_assignment_digest),
    'subject_digest',v_assignment->>'subject_digest',
    'validator_id',v_validator->>'validator_id'
  );
  INSERT INTO factory.semantic_command_results(
    operation,idempotency_key,request_digest,resource_digest,response_body
  ) VALUES (
    'create_assignment',p_idempotency_key,p_request_digest,p_assignment_digest,v_response
  );
  RETURN v_response;
EXCEPTION WHEN unique_violation OR check_violation OR foreign_key_violation
  OR invalid_text_representation OR numeric_value_out_of_range OR data_exception THEN
  RETURN NULL;
END;
$$;

CREATE FUNCTION factory.semantic_append_evidence(
  p_idempotency_key char(64),p_request_digest char(64),p_request_canonical text,
  p_subject_digest char(64),p_assignment_digest char(64),
  p_evidence_set_digest char(64),p_evidence_canonical text
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE
  v_request jsonb;
  v_evidence jsonb;
  v_assignment factory.semantic_assignments%ROWTYPE;
  v_subject factory.semantic_subjects%ROWTYPE;
  v_prior factory.semantic_command_results%ROWTYPE;
  v_item jsonb;
  v_finding jsonb;
  v_identity jsonb;
  v_coverage_record jsonb;
  v_coverage jsonb;
  v_existing_finding factory.semantic_findings%ROWTYPE;
  v_existing_coverage factory.semantic_coverage%ROWTYPE;
  v_finding_digests jsonb;
  v_response jsonb;
BEGIN
  IF current_setting('transaction_isolation') IS DISTINCT FROM 'read committed'
    OR p_idempotency_key IS NULL OR p_idempotency_key !~ '^[0-9a-f]{64}$'
    OR p_request_digest IS NULL OR p_subject_digest IS NULL
    OR p_assignment_digest IS NULL OR p_evidence_set_digest IS NULL
    OR p_request_canonical IS NULL OR octet_length(p_request_canonical)>262144
    OR p_evidence_canonical IS NULL OR octet_length(p_evidence_canonical)>1048576
  THEN RETURN NULL; END IF;

  v_request=p_request_canonical::jsonb;
  v_evidence=p_evidence_canonical::jsonb;
  IF trim(factory.execution_contract_hash(NULL,p_request_canonical))
      IS DISTINCT FROM trim(p_request_digest)
    OR trim(factory.execution_contract_hash(NULL,p_evidence_canonical))
      IS DISTINCT FROM trim(p_evidence_set_digest)
    OR jsonb_typeof(v_request) IS DISTINCT FROM 'object'
    OR (SELECT count(*) FROM jsonb_object_keys(v_request))<>4
    OR v_request->>'contract' IS DISTINCT FROM
      'adaptive-factory.semantic-evidence-command/v1'
    OR v_request->>'idempotency_key' IS DISTINCT FROM trim(p_idempotency_key)
    OR v_request->>'assignment_digest' IS DISTINCT FROM trim(p_assignment_digest)
    OR v_request->>'evidence_set_digest' IS DISTINCT FROM trim(p_evidence_set_digest)
    OR jsonb_typeof(v_evidence) IS DISTINCT FROM 'object'
    OR (SELECT count(*) FROM jsonb_object_keys(v_evidence))<>5
    OR v_evidence->>'contract' IS DISTINCT FROM
      'adaptive-factory.semantic-evidence-submission/v1'
    OR v_evidence->>'subject_digest' IS DISTINCT FROM trim(p_subject_digest)
    OR v_evidence->>'assignment_digest' IS DISTINCT FROM trim(p_assignment_digest)
    OR jsonb_typeof(v_evidence->'findings') IS DISTINCT FROM 'array'
    OR jsonb_array_length(v_evidence->'findings')>256
    OR jsonb_typeof(v_evidence->'coverage') IS DISTINCT FROM 'object'
  THEN RETURN NULL; END IF;

  IF EXISTS (
    SELECT 1 FROM (
      SELECT item->>'finding_digest' AS digest,ordinality,
        lag(item->>'finding_digest') OVER (ORDER BY ordinality) AS previous
      FROM jsonb_array_elements(v_evidence->'findings')
        WITH ORDINALITY AS finding(item,ordinality)
    ) ordered
    WHERE digest IS NULL OR digest !~ '^[0-9a-f]{64}$'
      OR (previous IS NOT NULL AND digest<=previous)
  ) THEN RETURN NULL; END IF;

  SELECT * INTO v_prior FROM factory.semantic_command_results
    WHERE operation='append_evidence' AND idempotency_key=p_idempotency_key;
  IF FOUND THEN
    RETURN CASE WHEN v_prior.request_digest=p_request_digest
      THEN v_prior.response_body ELSE NULL END;
  END IF;

  SELECT * INTO v_assignment FROM factory.semantic_assignments
    WHERE assignment_digest=p_assignment_digest AND subject_digest=p_subject_digest
    FOR UPDATE;
  IF NOT FOUND THEN RETURN NULL; END IF;
  SELECT * INTO v_subject FROM factory.semantic_subjects
    WHERE subject_digest=p_subject_digest;
  IF NOT FOUND THEN RETURN NULL; END IF;

  SELECT * INTO v_prior FROM factory.semantic_command_results
    WHERE operation='append_evidence' AND idempotency_key=p_idempotency_key;
  IF FOUND THEN
    RETURN CASE WHEN v_prior.request_digest=p_request_digest
      THEN v_prior.response_body ELSE NULL END;
  END IF;

  FOR v_item IN SELECT value FROM jsonb_array_elements(v_evidence->'findings') LOOP
    IF jsonb_typeof(v_item) IS DISTINCT FROM 'object'
      OR (SELECT count(*) FROM jsonb_object_keys(v_item))<>4
      OR COALESCE(v_item->>'finding_digest','') !~ '^[0-9a-f]{64}$'
      OR COALESCE(v_item->>'identity_digest','') !~ '^[0-9a-f]{64}$'
      OR v_item->>'canonical' IS NULL
      OR octet_length(v_item->>'canonical')>1048576
      OR v_item->>'identity_canonical' IS NULL
      OR octet_length(v_item->>'identity_canonical')>262144
      OR trim(factory.execution_contract_hash(NULL,v_item->>'canonical'))
        IS DISTINCT FROM v_item->>'finding_digest'
      OR trim(factory.execution_contract_hash(NULL,v_item->>'identity_canonical'))
        IS DISTINCT FROM v_item->>'identity_digest'
    THEN RETURN NULL; END IF;
    v_finding=(v_item->>'canonical')::jsonb;
    v_identity=(v_item->>'identity_canonical')::jsonb;
    IF jsonb_typeof(v_finding) IS DISTINCT FROM 'object'
      OR (SELECT count(*) FROM jsonb_object_keys(v_finding))<>13
      OR v_finding->>'schema_version' IS DISTINCT FROM '1'
      OR v_finding->>'subject_digest' IS DISTINCT FROM trim(p_subject_digest)
      OR octet_length(COALESCE(v_finding->>'finding_id','')) NOT BETWEEN 1 AND 128
      OR v_finding->>'severity' NOT IN ('minor','major','critical','blocker')
      OR v_finding->>'category' NOT IN (
        'requirement_unsatisfied','evidence_gap','test_gap','architecture_violation',
        'security_boundary','authority_violation','contradiction'
      )
      OR octet_length(COALESCE(v_finding->>'rule_id','')) NOT BETWEEN 1 AND 128
      OR octet_length(COALESCE(v_finding->>'message','')) NOT BETWEEN 1 AND 4096
      OR octet_length(COALESCE(v_finding->>'reproduction','')) NOT BETWEEN 1 AND 4096
      OR jsonb_typeof(v_finding->'repairable') IS DISTINCT FROM 'boolean'
      OR jsonb_typeof(v_finding->'requirement') IS DISTINCT FROM 'object'
      OR NOT (v_subject.subject_body->'requirements' @> jsonb_build_array(v_finding->'requirement'))
      OR jsonb_typeof(v_finding->'evidence_refs') IS DISTINCT FROM 'array'
      OR jsonb_array_length(v_finding->'evidence_refs')>256
      OR v_finding->'validator' IS DISTINCT FROM v_assignment.body->'validator'
      OR jsonb_typeof(v_finding->'created_at') IS DISTINCT FROM 'string'
      OR jsonb_typeof(v_identity) IS DISTINCT FROM 'object'
      OR (SELECT count(*) FROM jsonb_object_keys(v_identity))<>5
      OR v_identity->>'contract' IS DISTINCT FROM
        'adaptive-factory.semantic-finding-identity/v1'
      OR v_identity->'requirement' IS DISTINCT FROM v_finding->'requirement'
      OR v_identity->>'severity' IS DISTINCT FROM v_finding->>'severity'
      OR v_identity->>'category' IS DISTINCT FROM v_finding->>'category'
      OR v_identity->>'rule_id' IS DISTINCT FROM v_finding->>'rule_id'
      OR EXISTS (
        SELECT 1 FROM (
          SELECT value,ordinality,lag(value) OVER (ORDER BY ordinality) AS previous
          FROM jsonb_array_elements_text(v_finding->'evidence_refs')
            WITH ORDINALITY AS ref(value,ordinality)
        ) ordered WHERE octet_length(value) NOT BETWEEN 1 AND 256
          OR (previous IS NOT NULL AND value<=previous)
      )
    THEN RETURN NULL; END IF;
  END LOOP;

  v_coverage_record=v_evidence->'coverage';
  IF (SELECT count(*) FROM jsonb_object_keys(v_coverage_record))<>2
    OR COALESCE(v_coverage_record->>'coverage_digest','') !~ '^[0-9a-f]{64}$'
    OR v_coverage_record->>'canonical' IS NULL
    OR octet_length(v_coverage_record->>'canonical')>1048576
    OR trim(factory.execution_contract_hash(NULL,v_coverage_record->>'canonical'))
      IS DISTINCT FROM v_coverage_record->>'coverage_digest'
  THEN RETURN NULL; END IF;
  v_coverage=(v_coverage_record->>'canonical')::jsonb;
  IF jsonb_typeof(v_coverage) IS DISTINCT FROM 'object'
    OR (SELECT count(*) FROM jsonb_object_keys(v_coverage))<>5
    OR v_coverage->>'schema_version' IS DISTINCT FROM '1'
    OR v_coverage->>'subject_digest' IS DISTINCT FROM trim(p_subject_digest)
    OR v_coverage->'validator' IS DISTINCT FROM v_assignment.body->'validator'
    OR v_coverage->>'coverage_millionths' IS DISTINCT FROM '1000000'
    OR jsonb_typeof(v_coverage->'entries') IS DISTINCT FROM 'array'
    OR jsonb_array_length(v_coverage->'entries') NOT BETWEEN 1 AND 256
    OR (SELECT jsonb_agg(entry->'requirement' ORDER BY ordinality)
        FROM jsonb_array_elements(v_coverage->'entries')
          WITH ORDINALITY AS coverage_entry(entry,ordinality))
      IS DISTINCT FROM v_subject.subject_body->'requirements'
    OR EXISTS (
      SELECT 1 FROM jsonb_array_elements(v_coverage->'entries') entry
      WHERE jsonb_typeof(entry) IS DISTINCT FROM 'object'
        OR (SELECT count(*) FROM jsonb_object_keys(entry))<>3
        OR entry->>'status' NOT IN ('proven','unproven','contradicted','out_of_scope')
        OR jsonb_typeof(entry->'evidence_refs') IS DISTINCT FROM 'array'
        OR jsonb_array_length(entry->'evidence_refs')>256
        OR EXISTS (
          SELECT 1 FROM (
            SELECT value,ordinality,lag(value) OVER (ORDER BY ordinality) AS previous
            FROM jsonb_array_elements_text(entry->'evidence_refs')
              WITH ORDINALITY AS ref(value,ordinality)
          ) ordered WHERE octet_length(value) NOT BETWEEN 1 AND 256
            OR (previous IS NOT NULL AND value<=previous)
        )
    )
  THEN RETURN NULL; END IF;

  FOR v_item IN SELECT value FROM jsonb_array_elements(v_evidence->'findings') LOOP
    v_finding=(v_item->>'canonical')::jsonb;
    SELECT * INTO v_existing_finding FROM factory.semantic_findings
      WHERE finding_digest=(v_item->>'finding_digest')::char(64);
    IF FOUND THEN
      IF v_existing_finding.subject_digest IS DISTINCT FROM p_subject_digest
        OR v_existing_finding.assignment_digest IS DISTINCT FROM p_assignment_digest
        OR v_existing_finding.finding_identity_digest IS DISTINCT FROM
          (v_item->>'identity_digest')::char(64)
        OR v_existing_finding.body IS DISTINCT FROM v_finding
      THEN RETURN NULL; END IF;
    ELSE
      INSERT INTO factory.semantic_findings(
        finding_digest,finding_identity_digest,subject_digest,assignment_digest,
        request_digest,body
      ) VALUES (
        (v_item->>'finding_digest')::char(64),(v_item->>'identity_digest')::char(64),
        p_subject_digest,p_assignment_digest,p_request_digest,v_finding
      );
    END IF;
  END LOOP;

  SELECT * INTO v_existing_coverage FROM factory.semantic_coverage
    WHERE coverage_digest=(v_coverage_record->>'coverage_digest')::char(64)
      OR (subject_digest=p_subject_digest AND assignment_digest=p_assignment_digest);
  IF FOUND THEN
    IF v_existing_coverage.coverage_digest IS DISTINCT FROM
        (v_coverage_record->>'coverage_digest')::char(64)
      OR v_existing_coverage.subject_digest IS DISTINCT FROM p_subject_digest
      OR v_existing_coverage.assignment_digest IS DISTINCT FROM p_assignment_digest
      OR v_existing_coverage.body IS DISTINCT FROM v_coverage
    THEN RETURN NULL; END IF;
  ELSE
    INSERT INTO factory.semantic_coverage(
      coverage_digest,subject_digest,assignment_digest,request_digest,body
    ) VALUES (
      (v_coverage_record->>'coverage_digest')::char(64),p_subject_digest,
      p_assignment_digest,p_request_digest,v_coverage
    );
  END IF;

  SELECT COALESCE(jsonb_agg(item->>'finding_digest' ORDER BY item->>'finding_digest'),'[]'::jsonb)
    INTO v_finding_digests FROM jsonb_array_elements(v_evidence->'findings') item;
  v_response=jsonb_build_object(
    'evidence_set_digest',trim(p_evidence_set_digest),
    'subject_digest',trim(p_subject_digest),
    'assignment_digest',trim(p_assignment_digest),
    'finding_digests',v_finding_digests,
    'coverage_digest',v_coverage_record->>'coverage_digest'
  );
  INSERT INTO factory.semantic_command_results(
    operation,idempotency_key,request_digest,resource_digest,response_body
  ) VALUES (
    'append_evidence',p_idempotency_key,p_request_digest,p_evidence_set_digest,v_response
  );
  RETURN v_response;
EXCEPTION WHEN unique_violation OR check_violation OR foreign_key_violation
  OR invalid_text_representation OR numeric_value_out_of_range OR data_exception THEN
  RETURN NULL;
END;
$$;

CREATE FUNCTION factory.semantic_adjudication_material(
  p_task_id uuid,p_subject_digest char(64)
) RETURNS jsonb
LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
  SELECT jsonb_build_object(
    'subject_digest',trim(subject.subject_digest),
    'subject',subject.subject_body,
    'assignments',COALESCE((
      SELECT jsonb_agg(jsonb_build_object(
        'assignment_digest',trim(assignment.assignment_digest),
        'body',assignment.body
      ) ORDER BY assignment.assignment_digest)
      FROM factory.semantic_assignments assignment
      WHERE assignment.subject_digest=subject.subject_digest
    ),'[]'::jsonb),
    'findings',COALESCE((
      SELECT jsonb_agg(jsonb_build_object(
        'finding_digest',trim(finding.finding_digest),
        'assignment_digest',trim(finding.assignment_digest),
        'body',finding.body
      ) ORDER BY finding.finding_digest)
      FROM factory.semantic_findings finding
      WHERE finding.subject_digest=subject.subject_digest
    ),'[]'::jsonb),
    'coverages',COALESCE((
      SELECT jsonb_agg(jsonb_build_object(
        'coverage_digest',trim(coverage.coverage_digest),
        'assignment_digest',trim(coverage.assignment_digest),
        'body',coverage.body
      ) ORDER BY coverage.coverage_digest)
      FROM factory.semantic_coverage coverage
      WHERE coverage.subject_digest=subject.subject_digest
    ),'[]'::jsonb)
  )
  FROM factory.semantic_subjects subject
  WHERE subject.task_id=p_task_id AND subject.subject_digest=p_subject_digest
$$;

CREATE FUNCTION factory.semantic_expected_verdict(
  p_subject_digest char(64)
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE
  v_subject jsonb;
  v_identities jsonb;
  v_duplicates jsonb;
  v_correlations jsonb;
  v_contradictions jsonb;
  v_unsupported jsonb;
  v_human boolean;
  v_repair boolean;
  v_decision text;
  v_residual text;
BEGIN
  SELECT subject_body INTO v_subject FROM factory.semantic_subjects
    WHERE subject_digest=p_subject_digest;
  IF NOT FOUND THEN RETURN NULL; END IF;

  SELECT COALESCE(jsonb_agg(identity ORDER BY identity),'[]'::jsonb)
    INTO v_identities
  FROM (
    SELECT trim(finding_identity_digest) AS identity
    FROM factory.semantic_findings WHERE subject_digest=p_subject_digest
    GROUP BY finding_identity_digest
  ) identities;
  SELECT COALESCE(jsonb_agg(identity ORDER BY identity),'[]'::jsonb)
    INTO v_duplicates
  FROM (
    SELECT trim(finding_identity_digest) AS identity
    FROM factory.semantic_findings WHERE subject_digest=p_subject_digest
    GROUP BY finding_identity_digest HAVING count(*)>1
  ) duplicates;
  SELECT COALESCE(jsonb_agg(requirement_key ORDER BY requirement_key),'[]'::jsonb)
    INTO v_correlations
  FROM (
    SELECT (body#>>'{requirement,kind}') || ':' ||
        (body#>>'{requirement,requirement_id}') AS requirement_key
    FROM factory.semantic_findings WHERE subject_digest=p_subject_digest
    GROUP BY body#>>'{requirement,kind}',body#>>'{requirement,requirement_id}'
    HAVING count(DISTINCT finding_identity_digest)>1
  ) correlations;
  SELECT COALESCE(jsonb_agg(requirement_key ORDER BY requirement_key),'[]'::jsonb)
    INTO v_contradictions
  FROM (
    SELECT (entry#>>'{requirement,kind}') || ':' ||
        (entry#>>'{requirement,requirement_id}') AS requirement_key
    FROM factory.semantic_coverage coverage,
      jsonb_array_elements(coverage.body->'entries') entry
    WHERE coverage.subject_digest=p_subject_digest
    GROUP BY entry#>>'{requirement,kind}',entry#>>'{requirement,requirement_id}'
    HAVING count(DISTINCT entry->>'status')>1
      OR bool_or(entry->>'status'='contradicted')
  ) contradictions;
  SELECT COALESCE(jsonb_agg(requirement_key ORDER BY requirement_key),'[]'::jsonb)
    INTO v_unsupported
  FROM (
    SELECT DISTINCT (entry#>>'{requirement,kind}') || ':' ||
        (entry#>>'{requirement,requirement_id}') AS requirement_key
    FROM factory.semantic_coverage coverage,
      jsonb_array_elements(coverage.body->'entries') entry
    WHERE coverage.subject_digest=p_subject_digest AND (
      entry->>'status'='out_of_scope'
      OR (
        entry->>'status'='proven' AND (
          jsonb_array_length(entry->'evidence_refs')=0
          OR EXISTS (
            SELECT 1 FROM factory.semantic_findings finding
            WHERE finding.subject_digest=p_subject_digest
              AND finding.body->'requirement'=entry->'requirement'
          )
        )
      )
    )
  ) unsupported;
  SELECT EXISTS (
    SELECT 1 FROM factory.semantic_findings
    WHERE subject_digest=p_subject_digest AND (
      body->>'repairable'='false'
      OR body->>'category' IN ('security_boundary','authority_violation','contradiction')
    )
  ) INTO v_human;
  SELECT EXISTS (
    SELECT 1 FROM factory.semantic_findings WHERE subject_digest=p_subject_digest
  ) OR EXISTS (
    SELECT 1 FROM factory.semantic_coverage coverage,
      jsonb_array_elements(coverage.body->'entries') entry
    WHERE coverage.subject_digest=p_subject_digest AND entry->>'status'<>'proven'
  ) INTO v_repair;

  IF jsonb_array_length(v_contradictions)>0
    OR jsonb_array_length(v_unsupported)>0 OR v_human
  THEN
    v_decision='needs_human';
    v_residual=CASE WHEN v_subject->>'risk_level'='critical' THEN 'critical' ELSE 'high' END;
  ELSIF v_repair THEN
    v_decision='repair';
    v_residual=v_subject->>'risk_level';
  ELSE
    v_decision='pass';
    v_residual='none';
  END IF;
  RETURN jsonb_build_object(
    'schema_version',1,
    'subject_digest',trim(p_subject_digest),
    'decision',v_decision,
    'decision_source','deterministic_adjudicator',
    'finding_identity_digests',v_identities,
    'duplicate_identity_digests',v_duplicates,
    'correlated_requirement_keys',v_correlations,
    'contradicted_requirement_keys',v_contradictions,
    'unsupported_pass_requirement_keys',v_unsupported,
    'residual_risk',v_residual
  );
END;
$$;

CREATE FUNCTION factory.semantic_append_verdict(
  p_idempotency_key char(64),p_request_digest char(64),p_request_canonical text,
  p_evidence_set_digest char(64),p_evidence_canonical text,
  p_verdict_digest char(64),p_verdict_canonical text
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE
  v_request jsonb;
  v_evidence jsonb;
  v_actual_evidence jsonb;
  v_verdict jsonb;
  v_expected jsonb;
  v_subject factory.semantic_subjects%ROWTYPE;
  v_existing factory.semantic_verdicts%ROWTYPE;
  v_prior factory.semantic_command_results%ROWTYPE;
  v_response jsonb;
  v_assignment_count integer;
BEGIN
  IF current_setting('transaction_isolation') IS DISTINCT FROM 'read committed'
    OR p_idempotency_key IS NULL OR p_idempotency_key !~ '^[0-9a-f]{64}$'
    OR p_request_digest IS NULL OR p_evidence_set_digest IS NULL
    OR p_verdict_digest IS NULL
    OR p_request_canonical IS NULL OR octet_length(p_request_canonical)>262144
    OR p_evidence_canonical IS NULL OR octet_length(p_evidence_canonical)>1048576
    OR p_verdict_canonical IS NULL OR octet_length(p_verdict_canonical)>1048576
  THEN RETURN NULL; END IF;

  v_request=p_request_canonical::jsonb;
  v_evidence=p_evidence_canonical::jsonb;
  v_verdict=p_verdict_canonical::jsonb;
  IF trim(factory.execution_contract_hash(NULL,p_request_canonical))
      IS DISTINCT FROM trim(p_request_digest)
    OR trim(factory.execution_contract_hash(NULL,p_evidence_canonical))
      IS DISTINCT FROM trim(p_evidence_set_digest)
    OR trim(factory.execution_contract_hash(NULL,p_verdict_canonical))
      IS DISTINCT FROM trim(p_verdict_digest)
    OR jsonb_typeof(v_request) IS DISTINCT FROM 'object'
    OR (SELECT count(*) FROM jsonb_object_keys(v_request))<>5
    OR v_request->>'contract' IS DISTINCT FROM
      'adaptive-factory.semantic-adjudication-command/v1'
    OR v_request->>'idempotency_key' IS DISTINCT FROM trim(p_idempotency_key)
    OR v_request->>'subject_digest' IS NULL
    OR v_request->>'evidence_set_digest' IS DISTINCT FROM trim(p_evidence_set_digest)
    OR v_request->>'verdict_digest' IS DISTINCT FROM trim(p_verdict_digest)
    OR jsonb_typeof(v_evidence) IS DISTINCT FROM 'object'
    OR (SELECT count(*) FROM jsonb_object_keys(v_evidence))<>3
    OR v_evidence->>'contract' IS DISTINCT FROM
      'adaptive-factory.semantic-adjudication-evidence-set/v1'
    OR v_evidence->>'subject_digest' IS DISTINCT FROM v_request->>'subject_digest'
    OR jsonb_typeof(v_evidence->'assignments') IS DISTINCT FROM 'array'
    OR jsonb_array_length(v_evidence->'assignments') NOT BETWEEN 1 AND 256
    OR jsonb_typeof(v_verdict) IS DISTINCT FROM 'object'
    OR (SELECT count(*) FROM jsonb_object_keys(v_verdict))<>10
    OR v_verdict->>'schema_version' IS DISTINCT FROM '1'
    OR v_verdict->>'subject_digest' IS DISTINCT FROM v_request->>'subject_digest'
  THEN RETURN NULL; END IF;

  SELECT * INTO v_prior FROM factory.semantic_command_results
    WHERE operation='append_verdict' AND idempotency_key=p_idempotency_key;
  IF FOUND THEN
    RETURN CASE WHEN v_prior.request_digest=p_request_digest
      THEN v_prior.response_body ELSE NULL END;
  END IF;

  SELECT * INTO v_subject FROM factory.semantic_subjects
    WHERE subject_digest=(v_request->>'subject_digest')::char(64) FOR UPDATE;
  IF NOT FOUND THEN RETURN NULL; END IF;
  SELECT count(*) INTO v_assignment_count FROM factory.semantic_assignments
    WHERE subject_digest=v_subject.subject_digest;
  IF v_assignment_count NOT BETWEEN 1 AND 256 THEN RETURN NULL; END IF;

  SELECT jsonb_build_object(
    'contract','adaptive-factory.semantic-adjudication-evidence-set/v1',
    'subject_digest',trim(v_subject.subject_digest),
    'assignments',COALESCE((
      SELECT jsonb_agg(jsonb_build_object(
        'assignment_digest',trim(assignment.assignment_digest),
        'finding_digests',COALESCE((
          SELECT jsonb_agg(trim(finding.finding_digest) ORDER BY finding.finding_digest)
          FROM factory.semantic_findings finding
          WHERE finding.assignment_digest=assignment.assignment_digest
        ),'[]'::jsonb),
        'coverage_digest',trim(coverage.coverage_digest)
      ) ORDER BY assignment.assignment_digest)
      FROM factory.semantic_assignments assignment
      JOIN factory.semantic_coverage coverage
        ON coverage.assignment_digest=assignment.assignment_digest
          AND coverage.subject_digest=assignment.subject_digest
      WHERE assignment.subject_digest=v_subject.subject_digest
    ),'[]'::jsonb)
  ) INTO v_actual_evidence;
  IF jsonb_array_length(v_actual_evidence->'assignments')<>v_assignment_count
    OR v_actual_evidence IS DISTINCT FROM v_evidence
  THEN RETURN NULL; END IF;

  v_expected=factory.semantic_expected_verdict(v_subject.subject_digest);
  IF v_expected IS NULL OR v_expected IS DISTINCT FROM v_verdict
  THEN RETURN NULL; END IF;

  SELECT * INTO v_prior FROM factory.semantic_command_results
    WHERE operation='append_verdict' AND idempotency_key=p_idempotency_key;
  IF FOUND THEN
    RETURN CASE WHEN v_prior.request_digest=p_request_digest
      THEN v_prior.response_body ELSE NULL END;
  END IF;

  SELECT * INTO v_existing FROM factory.semantic_verdicts
    WHERE subject_digest=v_subject.subject_digest OR verdict_digest=p_verdict_digest;
  IF FOUND THEN
    IF v_existing.subject_digest IS DISTINCT FROM v_subject.subject_digest
      OR v_existing.verdict_digest IS DISTINCT FROM p_verdict_digest
      OR v_existing.evidence_set_digest IS DISTINCT FROM p_evidence_set_digest
      OR v_existing.body IS DISTINCT FROM v_verdict
    THEN RETURN NULL; END IF;
  ELSE
    INSERT INTO factory.semantic_verdicts(
      verdict_digest,subject_digest,evidence_set_digest,request_digest,body
    ) VALUES (
      p_verdict_digest,v_subject.subject_digest,p_evidence_set_digest,p_request_digest,v_verdict
    );
    INSERT INTO factory.semantic_metric_events(metric_name,label)
      VALUES ('semantic_validation_outcome',v_verdict->>'decision');
  END IF;

  v_response=jsonb_build_object(
    'verdict_digest',trim(p_verdict_digest),
    'evidence_set_digest',trim(p_evidence_set_digest),
    'subject_digest',trim(v_subject.subject_digest),
    'verdict',v_verdict
  );
  INSERT INTO factory.semantic_command_results(
    operation,idempotency_key,request_digest,resource_digest,response_body
  ) VALUES (
    'append_verdict',p_idempotency_key,p_request_digest,p_verdict_digest,v_response
  );
  RETURN v_response;
EXCEPTION WHEN unique_violation OR check_violation OR foreign_key_violation
  OR invalid_text_representation OR numeric_value_out_of_range OR data_exception THEN
  RETURN NULL;
END;
$$;

CREATE FUNCTION factory.semantic_verdict_by_subject(
  p_task_id uuid,p_subject_digest char(64)
) RETURNS jsonb
LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
  SELECT jsonb_build_object(
    'verdict_digest',trim(verdict.verdict_digest),
    'evidence_set_digest',trim(verdict.evidence_set_digest),
    'subject_digest',trim(verdict.subject_digest),
    'verdict',verdict.body
  )
  FROM factory.semantic_verdicts verdict
  JOIN factory.semantic_subjects subject
    ON subject.subject_digest=verdict.subject_digest
  WHERE subject.task_id=p_task_id AND subject.subject_digest=p_subject_digest
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
REVOKE ALL ON FUNCTION factory.semantic_create_assignment(
  char,char,text,char,text
) FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.semantic_append_evidence(
  char,char,text,char,char,char,text
) FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.semantic_adjudication_material(uuid,char) FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.semantic_expected_verdict(char) FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.semantic_append_verdict(
  char,char,text,char,text,char,text
) FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.semantic_verdict_by_subject(uuid,char) FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.semantic_subject_by_digest(uuid,char) FROM PUBLIC;

GRANT USAGE ON SCHEMA factory TO factory_semantic_coordinator,
  factory_semantic_validator,factory_semantic_adjudicator;
GRANT EXECUTE ON FUNCTION factory.semantic_execution_material(uuid,char)
  TO factory_semantic_coordinator;
GRANT EXECUTE ON FUNCTION factory.semantic_publish_subject(
  char,char,text,char,text,char,text,char,text,char,text,char,text
) TO factory_semantic_coordinator;
GRANT EXECUTE ON FUNCTION factory.semantic_create_assignment(
  char,char,text,char,text
) TO factory_semantic_coordinator;
GRANT EXECUTE ON FUNCTION factory.semantic_append_evidence(
  char,char,text,char,char,char,text
) TO factory_semantic_validator;
GRANT EXECUTE ON FUNCTION factory.semantic_adjudication_material(uuid,char)
  TO factory_semantic_adjudicator;
GRANT EXECUTE ON FUNCTION factory.semantic_append_verdict(
  char,char,text,char,text,char,text
) TO factory_semantic_adjudicator;
GRANT EXECUTE ON FUNCTION factory.semantic_verdict_by_subject(uuid,char)
  TO factory_semantic_coordinator;
GRANT EXECUTE ON FUNCTION factory.semantic_subject_by_digest(uuid,char)
  TO factory_semantic_coordinator;
