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

ALTER TABLE factory.tasks
  ADD COLUMN intake_actor_kind text NOT NULL DEFAULT 'legacy'
    CHECK (octet_length(intake_actor_kind) BETWEEN 1 AND 64),
  ADD COLUMN intake_actor_id text NOT NULL DEFAULT 'legacy'
    CHECK (octet_length(intake_actor_id) BETWEEN 1 AND 128);

CREATE TABLE factory.semantic_command_results (
  operation text NOT NULL CHECK (operation IN (
    'publish_subject','create_assignment','append_evidence','append_verdict','plan_repair',
    'bind_repair_child'
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
  previous_child_proposal_digest char(64) NULL
    REFERENCES factory.semantic_child_proposals(child_proposal_digest) ON DELETE RESTRICT,
  proposal_state text NOT NULL CHECK (proposal_state='pending_handoff'),
  request_digest char(64) NOT NULL CHECK (request_digest ~ '^[0-9a-f]{64}$'),
  body jsonb NOT NULL CHECK (octet_length(body::text)<=1048576),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  UNIQUE(subject_digest,cycle)
);

CREATE TABLE factory.semantic_child_task_bindings (
  binding_digest char(64) PRIMARY KEY CHECK (binding_digest ~ '^[0-9a-f]{64}$'),
  child_proposal_digest char(64) NOT NULL UNIQUE
    REFERENCES factory.semantic_child_proposals(child_proposal_digest) ON DELETE RESTRICT,
  child_task_id uuid NOT NULL UNIQUE REFERENCES factory.tasks(task_id) ON DELETE RESTRICT,
  child_intent_digest char(64) NOT NULL UNIQUE
    REFERENCES factory.accepted_intents(intent_digest) ON DELETE RESTRICT,
  body jsonb NOT NULL CHECK (octet_length(body::text)<=262144),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE FUNCTION factory.semantic_repair_intake_status(
  p_repository_id text,
  p_source_type text,
  p_source_id text,
  p_source_digest char(64),
  p_exact_head_sha char(40),
  p_actor_kind text,
  p_actor_id text
) RETURNS text
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
  SELECT CASE
    WHEN NOT (
      p_source_type='api'
      AND p_source_id ~ '^[0-9a-f]{64}$'
    ) THEN 'ordinary'
    WHEN EXISTS (
      SELECT 1 FROM factory.semantic_child_proposals proposal
      WHERE proposal.child_proposal_digest=p_source_id::char(64)
    ) AND p_source_digest<>p_source_id::char(64) THEN 'digest_mismatch'
    WHEN EXISTS (
      SELECT 1 FROM factory.semantic_child_proposals proposal
      WHERE proposal.child_proposal_digest=p_source_id::char(64)
    ) AND (
      p_actor_kind<>'repair_broker'
      OR p_actor_id<>'semantic-repair-child-broker'
    ) THEN 'actor_mismatch'
    WHEN NOT EXISTS (
      SELECT 1
      FROM factory.semantic_child_proposals proposal
      JOIN factory.tasks parent_task ON parent_task.task_id=proposal.parent_task_id
      WHERE proposal.child_proposal_digest=p_source_id::char(64)
        AND proposal.proposal_state='pending_handoff'
        AND proposal.body->>'proposal_state'='pending_handoff'
        AND parent_task.repository_id=p_repository_id
    ) THEN CASE
      WHEN p_actor_kind='repair_broker'
        AND p_actor_id='semantic-repair-child-broker' THEN 'not_pending'
      ELSE 'ordinary'
    END
    WHEN NOT EXISTS (
      SELECT 1 FROM factory.semantic_child_proposals proposal
      WHERE proposal.child_proposal_digest=p_source_id::char(64)
        AND proposal.body->>'parent_exact_head_sha'=trim(p_exact_head_sha)
    ) THEN 'head_mismatch'
    WHEN EXISTS (
      SELECT 1 FROM factory.semantic_child_task_bindings binding
      WHERE binding.child_proposal_digest=p_source_id::char(64)
    ) THEN 'bound'
    ELSE 'allowed'
  END
$$;

CREATE FUNCTION factory.semantic_task_claimable(
  p_task_id uuid,
  p_intent_id uuid,
  p_intake_actor_kind text,
  p_intake_actor_id text,
  p_requested_owner text,
  p_requested_role text
) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
  SELECT COALESCE((
    SELECT CASE
      WHEN (
        p_intake_actor_kind='repair_broker'
        AND p_intake_actor_id='semantic-repair-child-broker'
      ) OR EXISTS (
        SELECT 1
        FROM factory.semantic_child_proposals proposal
        WHERE intent.source_type='api'
          AND intent.source_id=trim(intent.source_digest)
          AND proposal.child_proposal_digest=intent.source_digest
      ) THEN (
        p_intake_actor_kind='repair_broker'
        AND p_intake_actor_id='semantic-repair-child-broker'
        AND p_requested_role='writer'
        AND EXISTS (
          SELECT 1
          FROM factory.semantic_child_task_bindings binding
          JOIN factory.semantic_child_proposals bound_proposal
            ON bound_proposal.child_proposal_digest=binding.child_proposal_digest
          WHERE binding.child_task_id=p_task_id
            AND trim(binding.child_intent_digest)=intent.intent_digest
            AND trim(binding.child_proposal_digest)=intent.source_id
            AND trim(binding.child_proposal_digest)=intent.source_digest
            AND bound_proposal.body->>'writer_id'=p_requested_owner
        )
        AND EXISTS (
          SELECT 1
          FROM factory.tasks claim_task
          JOIN factory.m0_authority_observations observation
            ON observation.observed_at=
              (intent.body#>>'{m0_authority,observed_at}')::timestamptz
            AND observation.check_name=
              intent.body#>>'{m0_authority,check_name}'
            AND observation.exact_head_sha=
              (intent.body#>>'{m0_authority,exact_head_sha}')::char(40)
            AND observation.repository_id=intent.repository_id
            AND observation.policy_digest=intent.policy_digest
          WHERE claim_task.task_id=p_task_id
            AND claim_task.intent_id=intent.intent_id
            AND claim_task.intake_actor_kind=p_intake_actor_kind
            AND claim_task.intake_actor_id=p_intake_actor_id
            AND claim_task.accepted_at-observation.observed_at
              BETWEEN interval '0 seconds' AND interval '300 seconds'
            AND observation.revoked_at IS NULL
        )
      )
      ELSE true
    END
    FROM factory.accepted_intents intent
    WHERE intent.intent_id=p_intent_id
  ),false)
$$;

CREATE TABLE factory.semantic_escalations (
  escalation_digest char(64) PRIMARY KEY CHECK (escalation_digest ~ '^[0-9a-f]{64}$'),
  subject_digest char(64) NOT NULL REFERENCES factory.semantic_subjects(subject_digest) ON DELETE RESTRICT,
  verdict_digest char(64) NOT NULL REFERENCES factory.semantic_verdicts(verdict_digest) ON DELETE RESTRICT,
  requested_cycle integer NOT NULL CHECK (requested_cycle BETWEEN 0 AND 1000000),
  reason text NOT NULL CHECK (reason IN (
    'architecture_changed','authority_changed','base_changed','budget_exhausted',
    'context_not_fresh','deadline_exhausted','diff_changed','diff_limit_exceeded',
    'finding_recurrence','head_changed','original_writer_mismatch',
    'repair_cycle_out_of_bounds','risk_increased','stale_fence',
    'stale_semantic_evidence','unsupported_result_disposition',
    'verdict_not_repair','workspace_result_changed'
  )),
  request_digest char(64) NOT NULL CHECK (request_digest ~ '^[0-9a-f]{64}$'),
  body jsonb NOT NULL CHECK (octet_length(body::text)<=262144),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp()
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
CREATE TRIGGER semantic_child_task_bindings_immutable BEFORE UPDATE OR DELETE
  ON factory.semantic_child_task_bindings FOR EACH ROW EXECUTE FUNCTION factory.semantic_reject_mutation();
CREATE TRIGGER semantic_escalations_immutable BEFORE UPDATE OR DELETE
  ON factory.semantic_escalations FOR EACH ROW EXECUTE FUNCTION factory.semantic_reject_mutation();
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

CREATE FUNCTION factory.semantic_bind_repair_child(
  p_binding_digest char(64),p_binding_canonical text
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE
  v_binding jsonb;
  v_child factory.semantic_child_proposals%ROWTYPE;
  v_child_task factory.tasks%ROWTYPE;
  v_child_intent factory.accepted_intents%ROWTYPE;
  v_parent_task factory.tasks%ROWTYPE;
  v_parent_intent factory.accepted_intents%ROWTYPE;
  v_child_observation factory.m0_authority_observations%ROWTYPE;
  v_parent_observation factory.m0_authority_observations%ROWTYPE;
  v_existing factory.semantic_child_task_bindings%ROWTYPE;
BEGIN
  IF current_setting('transaction_isolation') IS DISTINCT FROM 'read committed'
    OR p_binding_digest IS NULL OR p_binding_digest !~ '^[0-9a-f]{64}$'
    OR p_binding_canonical IS NULL OR octet_length(p_binding_canonical)>262144
  THEN RETURN NULL; END IF;
  v_binding=p_binding_canonical::jsonb;
  IF trim(factory.execution_contract_hash(NULL,p_binding_canonical))
      IS DISTINCT FROM trim(p_binding_digest)
    OR jsonb_typeof(v_binding) IS DISTINCT FROM 'object'
    OR (SELECT count(*) FROM jsonb_object_keys(v_binding))<>4
    OR NOT (v_binding ?& ARRAY[
      'schema_version','child_proposal_digest','child_task_id','child_intent_digest'
    ])
    OR v_binding->>'schema_version' IS DISTINCT FROM '1'
    OR v_binding->>'child_proposal_digest' !~ '^[0-9a-f]{64}$'
    OR v_binding->>'child_intent_digest' !~ '^[0-9a-f]{64}$'
    OR v_binding->>'child_task_id' !~
      '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  THEN RETURN NULL; END IF;

  SELECT * INTO v_child FROM factory.semantic_child_proposals
    WHERE child_proposal_digest=
      (v_binding->>'child_proposal_digest')::char(64) FOR UPDATE;
  IF NOT FOUND OR v_child.body->>'proposal_state' IS DISTINCT FROM 'pending_handoff'
  THEN RETURN NULL; END IF;

  SELECT * INTO v_parent_task FROM factory.tasks
    WHERE task_id=v_child.parent_task_id;
  IF NOT FOUND THEN RETURN NULL; END IF;
  PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(
    v_parent_task.repository_id || chr(31) || 'api' || chr(31) ||
      trim(v_child.child_proposal_digest),0
  ));
  SELECT * INTO v_child_task FROM factory.tasks
    WHERE task_id=(v_binding->>'child_task_id')::uuid FOR UPDATE;
  IF NOT FOUND
    OR v_child_task.state NOT IN ('queued','retry')
    OR EXISTS (
      SELECT 1 FROM factory.tasks newer
      WHERE newer.repository_id=v_child_task.repository_id
        AND newer.source_type=v_child_task.source_type
        AND newer.source_id=v_child_task.source_id
        AND newer.generation>v_child_task.generation
    )
  THEN RETURN NULL; END IF;

  SELECT * INTO v_existing FROM factory.semantic_child_task_bindings
    WHERE child_proposal_digest=v_child.child_proposal_digest;
  IF FOUND THEN
    RETURN CASE WHEN v_existing.binding_digest=p_binding_digest
      AND v_existing.child_task_id=v_child_task.task_id
      AND v_existing.child_intent_digest=
        (v_binding->>'child_intent_digest')::char(64)
      AND v_existing.body IS NOT DISTINCT FROM v_binding
      THEN v_existing.body ELSE NULL END;
  END IF;
  IF EXISTS (
    SELECT 1 FROM factory.semantic_child_task_bindings
    WHERE child_task_id=v_child_task.task_id
      OR child_intent_digest=(v_binding->>'child_intent_digest')::char(64)
  ) THEN RETURN NULL; END IF;

  SELECT * INTO v_child_intent FROM factory.accepted_intents
    WHERE intent_id=v_child_task.intent_id
      AND intent_digest=(v_binding->>'child_intent_digest')::char(64);
  SELECT * INTO v_parent_intent FROM factory.accepted_intents
    WHERE intent_id=v_parent_task.intent_id;
  SELECT * INTO v_child_observation FROM factory.m0_authority_observations
    WHERE observed_at=(v_child_intent.body#>>'{m0_authority,observed_at}')::timestamptz
      AND check_name=v_child_intent.body#>>'{m0_authority,check_name}'
      AND exact_head_sha=
        (v_child_intent.body#>>'{m0_authority,exact_head_sha}')::char(40)
      AND repository_id=v_child_intent.repository_id
      AND policy_digest=v_child_intent.policy_digest
      AND revoked_at IS NULL;
  SELECT * INTO v_parent_observation FROM factory.m0_authority_observations
    WHERE observed_at=(v_parent_intent.body#>>'{m0_authority,observed_at}')::timestamptz
      AND check_name=v_parent_intent.body#>>'{m0_authority,check_name}'
      AND exact_head_sha=
        (v_parent_intent.body#>>'{m0_authority,exact_head_sha}')::char(40)
      AND repository_id=v_parent_intent.repository_id
      AND policy_digest=v_parent_intent.policy_digest
      AND revoked_at IS NULL;
  IF v_child_task.task_id IS NULL OR v_child_intent.intent_id IS NULL
    OR v_parent_task.task_id IS NULL OR v_parent_intent.intent_id IS NULL
    OR v_child_task.intake_actor_kind IS DISTINCT FROM 'repair_broker'
    OR v_child_task.intake_actor_id IS DISTINCT FROM
      'semantic-repair-child-broker'
    OR v_child_observation.observation_id IS NULL
    OR v_parent_observation.observation_id IS NULL
    OR v_child_task.accepted_at<v_child.created_at
    OR v_child_task.repository_id IS DISTINCT FROM v_parent_task.repository_id
    OR v_child_intent.repository_id IS DISTINCT FROM v_parent_intent.repository_id
    OR v_child_task.source_type IS DISTINCT FROM 'api'
    OR v_child_intent.source_type IS DISTINCT FROM 'api'
    OR v_child_task.source_id IS DISTINCT FROM trim(v_child.child_proposal_digest)
    OR v_child_intent.source_id IS DISTINCT FROM trim(v_child.child_proposal_digest)
    OR v_child_intent.source_digest IS DISTINCT FROM v_child.child_proposal_digest
    OR trim(v_child_intent.exact_base_sha) IS DISTINCT FROM
      v_child.body->>'exact_base_sha'
    OR trim(v_child_intent.architecture_digest) IS DISTINCT FROM
      v_child.body->>'architecture_digest'
    OR v_child_intent.spec_digest IS DISTINCT FROM v_parent_intent.spec_digest
    OR v_child_intent.governance_digest IS DISTINCT FROM
      v_parent_intent.governance_digest
    OR v_child_intent.policy_digest IS DISTINCT FROM v_parent_intent.policy_digest
    OR v_child_intent.body->>'route_id' IS DISTINCT FROM
      v_parent_intent.body->>'route_id'
    OR v_child_intent.body->>'change_id' IS DISTINCT FROM
      v_parent_intent.body->>'change_id'
    OR v_child_intent.body->'acceptance_ids' IS DISTINCT FROM
      v_parent_intent.body->'acceptance_ids'
    OR (v_child_intent.body->'architecture')-'exact_head_sha' IS DISTINCT FROM
      (v_parent_intent.body->'architecture')-'exact_head_sha'
    OR (v_child_intent.body->'governance')-'exact_head_sha' IS DISTINCT FROM
      (v_parent_intent.body->'governance')-'exact_head_sha'
    OR v_child_intent.body#>>'{architecture,exact_head_sha}' IS DISTINCT FROM
      v_child.body->>'parent_exact_head_sha'
    OR v_child_intent.body#>>'{governance,exact_head_sha}' IS DISTINCT FROM
      v_child.body->>'parent_exact_head_sha'
    OR v_child_intent.body#>>'{m0_authority,exact_head_sha}' IS DISTINCT FROM
      v_child.body->>'parent_exact_head_sha'
    OR NOT EXISTS (
      SELECT 1 FROM factory.semantic_subjects parent_subject
      WHERE parent_subject.subject_digest=v_child.subject_digest
        AND trim(parent_subject.exact_head_sha)=
          v_child.body->>'parent_exact_head_sha'
    )
    OR v_child_intent.body#>>'{m0_authority,check_name}' IS DISTINCT FROM
      v_parent_intent.body#>>'{m0_authority,check_name}'
    OR v_child_observation.issuer IS DISTINCT FROM v_parent_observation.issuer
    OR v_child_task.accepted_at-v_child_observation.observed_at
      NOT BETWEEN interval '0 seconds' AND interval '300 seconds'
    OR v_parent_task.accepted_at-v_parent_observation.observed_at
      NOT BETWEEN interval '0 seconds' AND interval '300 seconds'
    OR v_child_task.deadline_at>v_parent_task.deadline_at
    OR v_child_task.deadline_at>(v_child.body->>'deadline_at')::timestamptz
    OR (v_child_intent.body#>>'{limits,max_cost_usd_micros}')::bigint>
      (v_parent_intent.body#>>'{limits,max_cost_usd_micros}')::bigint
    OR (v_child_intent.body#>>'{limits,max_token_units}')::bigint>
      (v_parent_intent.body#>>'{limits,max_token_units}')::bigint
    OR (v_child_intent.body#>>'{limits,max_output_bytes}')::bigint>
      (v_parent_intent.body#>>'{limits,max_output_bytes}')::bigint
    OR (v_child_intent.body#>>'{limits,max_events}')::bigint>
      (v_parent_intent.body#>>'{limits,max_events}')::bigint
    OR (v_child_intent.body#>>'{limits,wall_seconds}')::bigint>
      (v_parent_intent.body#>>'{limits,wall_seconds}')::bigint
    OR (v_child_intent.body#>>'{limits,infrastructure_retries}')::integer>
      (v_parent_intent.body#>>'{limits,infrastructure_retries}')::integer
    OR (v_child_intent.body#>>'{limits,semantic_repairs}')::integer>
      (v_parent_intent.body#>>'{limits,semantic_repairs}')::integer
    OR (v_child_intent.body#>>'{limits,max_cost_usd_micros}')::bigint>
      (v_child.body->>'max_cost_usd_micros')::bigint
    OR (v_child_intent.body#>>'{limits,max_token_units}')::bigint>
      (v_child.body->>'max_token_units')::bigint
    OR (v_child_intent.body#>>'{limits,max_output_bytes}')::bigint>
      (v_child.body->>'max_output_bytes')::bigint
    OR (v_child_intent.body#>>'{limits,max_events}')::bigint>
      (v_child.body->>'max_events')::bigint
    OR (v_child_intent.body#>>'{limits,infrastructure_retries}')::integer>
      (v_child.body->>'infrastructure_retries_remaining')::integer
    OR (v_child_intent.body#>>'{limits,semantic_repairs}')::integer>
      (v_child.body->>'budget_remaining_units')::integer
  THEN RETURN NULL; END IF;

  INSERT INTO factory.semantic_child_task_bindings(
    binding_digest,child_proposal_digest,child_task_id,child_intent_digest,body
  ) VALUES (
    p_binding_digest,v_child.child_proposal_digest,v_child_task.task_id,
    v_child_intent.intent_digest,v_binding
  );
  RETURN v_binding;
EXCEPTION WHEN unique_violation OR check_violation OR foreign_key_violation
  OR invalid_text_representation OR numeric_value_out_of_range OR data_exception THEN
  RETURN NULL;
END;
$$;

CREATE FUNCTION factory.semantic_plan_repair(
  p_idempotency_key char(64),p_request_digest char(64),
  p_request_canonical text,p_task_id uuid
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE
  v_request jsonb;
  v_input jsonb;
  v_subject factory.semantic_subjects%ROWTYPE;
  v_verdict factory.semantic_verdicts%ROWTYPE;
  v_result factory.workspace_results%ROWTYPE;
  v_packet factory.execution_packets%ROWTYPE;
  v_manifest factory.execution_manifests%ROWTYPE;
  v_current_task factory.tasks%ROWTYPE;
  v_current_intent factory.accepted_intents%ROWTYPE;
  v_prior factory.semantic_command_results%ROWTYPE;
  v_previous factory.semantic_child_proposals%ROWTYPE;
  v_handoff factory.semantic_child_task_bindings%ROWTYPE;
  v_existing_directive factory.semantic_directives%ROWTYPE;
  v_existing_child factory.semantic_child_proposals%ROWTYPE;
  v_reason text;
  v_cycle integer;
  v_lineage_count integer := 0;
  v_budget integer;
  v_remaining_cost bigint;
  v_remaining_tokens bigint;
  v_remaining_output bigint;
  v_remaining_events bigint;
  v_remaining_infrastructure_retries integer;
  v_baseline_risk text;
  v_deadline text;
  v_finding_list text;
  v_previous_json text;
  v_directive_canonical text;
  v_directive jsonb;
  v_directive_digest char(64);
  v_child_canonical text;
  v_child jsonb;
  v_child_digest char(64);
  v_escalation_canonical text;
  v_escalation jsonb;
  v_escalation_digest char(64);
  v_response jsonb;
BEGIN
  IF current_setting('transaction_isolation') IS DISTINCT FROM 'read committed'
    OR p_idempotency_key IS NULL OR p_idempotency_key !~ '^[0-9a-f]{64}$'
    OR p_request_digest IS NULL OR p_request_digest !~ '^[0-9a-f]{64}$'
    OR p_request_canonical IS NULL OR octet_length(p_request_canonical)>262144
    OR p_task_id IS NULL
  THEN RETURN NULL; END IF;

  v_request=p_request_canonical::jsonb;
  v_input=v_request->'repair_request';
  IF trim(factory.execution_contract_hash(NULL,p_request_canonical))
      IS DISTINCT FROM trim(p_request_digest)
    OR jsonb_typeof(v_request) IS DISTINCT FROM 'object'
    OR (SELECT count(*) FROM jsonb_object_keys(v_request))<>4
    OR v_request->>'contract' IS DISTINCT FROM
      'adaptive-factory.semantic-repair-command/v1'
    OR v_request->>'idempotency_key' IS DISTINCT FROM trim(p_idempotency_key)
    OR v_request->>'task_id' IS DISTINCT FROM p_task_id::text
    OR jsonb_typeof(v_input) IS DISTINCT FROM 'object'
    OR (SELECT count(*) FROM jsonb_object_keys(v_input))<>15
    OR NOT (v_input ?& ARRAY[
      'schema_version','subject_digest','verdict_digest','requested_cycle',
      'previous_child_proposal_digest','writer_id','context_digest',
      'expected_workspace_result_digest','expected_fence','expected_head_sha',
      'expected_base_sha','expected_architecture_digest','expected_authority_digest',
      'expected_diff_digest','expected_risk_level'
    ])
    OR v_input->>'schema_version' IS DISTINCT FROM '1'
    OR jsonb_typeof(v_input->'requested_cycle') IS DISTINCT FROM 'number'
    OR v_input->>'requested_cycle' !~ '^(0|[1-9][0-9]{0,6})$'
    OR (v_input->>'requested_cycle')::integer>1000000
    OR jsonb_typeof(v_input->'expected_fence') IS DISTINCT FROM 'number'
    OR v_input->>'expected_fence' !~ '^[1-9][0-9]{0,18}$'
    OR v_input->>'subject_digest' !~ '^[0-9a-f]{64}$'
    OR v_input->>'verdict_digest' !~ '^[0-9a-f]{64}$'
    OR v_input->>'context_digest' !~ '^[0-9a-f]{64}$'
    OR v_input->>'expected_workspace_result_digest' !~ '^[0-9a-f]{64}$'
    OR v_input->>'expected_head_sha' !~ '^[0-9a-f]{40}$'
    OR v_input->>'expected_base_sha' !~ '^[0-9a-f]{40}$'
    OR v_input->>'expected_architecture_digest' !~ '^[0-9a-f]{64}$'
    OR v_input->>'expected_authority_digest' !~ '^[0-9a-f]{64}$'
    OR v_input->>'expected_diff_digest' !~ '^[0-9a-f]{64}$'
    OR COALESCE(octet_length(v_input->>'writer_id'),0) NOT BETWEEN 1 AND 128
    OR v_input->>'writer_id' !~ '^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$'
    OR v_input->>'expected_risk_level' NOT IN ('low','medium','high','critical')
    OR jsonb_typeof(v_input->'previous_child_proposal_digest')
      NOT IN ('null','string')
    OR (
      jsonb_typeof(v_input->'previous_child_proposal_digest')='string'
      AND v_input->>'previous_child_proposal_digest' !~ '^[0-9a-f]{64}$'
    )
  THEN RETURN NULL; END IF;

  v_cycle=(v_input->>'requested_cycle')::integer;
  IF (v_cycle=1 AND v_input->>'previous_child_proposal_digest' IS NOT NULL)
    OR (v_cycle>=2 AND v_input->>'previous_child_proposal_digest' IS NULL)
  THEN RETURN NULL; END IF;

  SELECT * INTO v_prior FROM factory.semantic_command_results
    WHERE operation='plan_repair' AND idempotency_key=p_idempotency_key;
  IF FOUND THEN
    RETURN CASE WHEN v_prior.request_digest=p_request_digest
      THEN v_prior.response_body ELSE NULL END;
  END IF;

  SELECT * INTO v_subject FROM factory.semantic_subjects
    WHERE task_id=p_task_id
      AND subject_digest=(v_input->>'subject_digest')::char(64)
    FOR UPDATE;
  IF NOT FOUND THEN RETURN NULL; END IF;
  SELECT * INTO v_verdict FROM factory.semantic_verdicts
    WHERE subject_digest=v_subject.subject_digest
      AND verdict_digest=(v_input->>'verdict_digest')::char(64);
  IF NOT FOUND OR v_verdict.body IS DISTINCT FROM
      factory.semantic_expected_verdict(v_subject.subject_digest)
  THEN RETURN NULL; END IF;

  SELECT * INTO v_result FROM factory.workspace_results
    WHERE workspace_result_digest=v_subject.workspace_result_digest;
  SELECT * INTO v_packet FROM factory.execution_packets
    WHERE packet_digest=v_subject.task_packet_digest AND run_id=v_subject.run_id;
  SELECT * INTO v_manifest FROM factory.execution_manifests
    WHERE manifest_digest=v_subject.run_manifest_digest AND run_id=v_subject.run_id;
  SELECT * INTO v_current_task FROM factory.tasks
    WHERE task_id=v_subject.task_id;
  SELECT * INTO v_current_intent FROM factory.accepted_intents
    WHERE intent_id=v_current_task.intent_id;
  IF v_result.workspace_result_digest IS NULL OR v_packet.packet_digest IS NULL
    OR v_manifest.manifest_digest IS NULL OR v_current_task.task_id IS NULL
    OR v_current_intent.intent_id IS NULL
  THEN RETURN NULL; END IF;

  IF v_cycle BETWEEN 2 AND 3 THEN
    SELECT * INTO v_previous FROM factory.semantic_child_proposals
      WHERE child_proposal_digest=
        (v_input->>'previous_child_proposal_digest')::char(64);
    IF NOT FOUND OR v_previous.cycle<>v_cycle-1
      OR v_previous.body->>'proposal_state' IS DISTINCT FROM 'pending_handoff'
      OR v_previous.body->>'writer_id' IS DISTINCT FROM v_subject.owner_id
      OR v_previous.body->>'exact_base_sha' IS DISTINCT FROM
        v_subject.subject_body->>'exact_base_sha'
      OR v_previous.body->>'architecture_digest' IS DISTINCT FROM
        v_subject.subject_body->>'architecture_digest'
      OR NOT EXISTS (
        SELECT 1
        FROM factory.semantic_subjects previous_subject
        JOIN factory.execution_packets previous_packet
          ON previous_packet.packet_digest=previous_subject.task_packet_digest
            AND previous_packet.run_id=previous_subject.run_id
        WHERE previous_subject.subject_digest=v_previous.subject_digest
          AND (previous_packet.body->'authority')-'exact_head_sha'
            IS NOT DISTINCT FROM
              (v_packet.body->'authority')-'exact_head_sha'
      )
      OR (
        v_previous.subject_digest<>v_subject.subject_digest
        AND v_previous.body->>'context_digest' IS DISTINCT FROM
          v_subject.subject_body->>'original_writer_context_digest'
      )
    THEN RETURN NULL; END IF;
    IF v_previous.subject_digest<>v_subject.subject_digest THEN
      SELECT * INTO v_handoff FROM factory.semantic_child_task_bindings
        WHERE child_proposal_digest=v_previous.child_proposal_digest
          AND child_task_id=v_subject.task_id
          AND child_intent_digest=v_current_intent.intent_digest;
      IF NOT FOUND
        OR v_handoff.body->>'child_proposal_digest' IS DISTINCT FROM
          trim(v_previous.child_proposal_digest)
        OR v_handoff.body->>'child_task_id' IS DISTINCT FROM v_subject.task_id::text
        OR v_handoff.body->>'child_intent_digest' IS DISTINCT FROM
          trim(v_current_intent.intent_digest)
        OR v_current_task.repository_id IS DISTINCT FROM v_subject.repository_id
        OR v_current_intent.repository_id IS DISTINCT FROM v_subject.repository_id
        OR v_current_task.source_type IS DISTINCT FROM 'api'
        OR v_current_intent.source_type IS DISTINCT FROM 'api'
        OR v_current_task.source_id IS DISTINCT FROM trim(v_previous.child_proposal_digest)
        OR v_current_intent.source_id IS DISTINCT FROM trim(v_previous.child_proposal_digest)
        OR v_current_intent.source_digest IS DISTINCT FROM
          v_previous.child_proposal_digest
        OR trim(v_current_intent.exact_base_sha) IS DISTINCT FROM
          v_previous.body->>'exact_base_sha'
        OR trim(v_current_intent.architecture_digest) IS DISTINCT FROM
          v_previous.body->>'architecture_digest'
        OR trim(v_subject.input_head_sha) IS DISTINCT FROM
          v_previous.body->>'parent_exact_head_sha'
        OR v_packet.body#>>'{authority,exact_head_sha}' IS DISTINCT FROM
          v_previous.body->>'parent_exact_head_sha'
        OR v_current_intent.body#>>'{architecture,exact_head_sha}' IS DISTINCT FROM
          v_previous.body->>'parent_exact_head_sha'
        OR v_current_intent.body#>>'{governance,exact_head_sha}' IS DISTINCT FROM
          v_previous.body->>'parent_exact_head_sha'
        OR v_current_intent.body#>>'{m0_authority,exact_head_sha}' IS DISTINCT FROM
          v_previous.body->>'parent_exact_head_sha'
        OR v_current_task.accepted_at<v_previous.created_at
      THEN RETURN NULL; END IF;
    END IF;
    WITH RECURSIVE lineage AS (
      SELECT child_proposal_digest,cycle,body,previous_child_proposal_digest
      FROM factory.semantic_child_proposals
      WHERE child_proposal_digest=
        (v_input->>'previous_child_proposal_digest')::char(64)
      UNION ALL
      SELECT prior.child_proposal_digest,prior.cycle,prior.body,
        prior.previous_child_proposal_digest
      FROM factory.semantic_child_proposals prior
      JOIN lineage child
        ON prior.child_proposal_digest=child.previous_child_proposal_digest
    )
    SELECT count(*) INTO v_lineage_count FROM lineage;
    IF v_lineage_count<>v_cycle-1 OR EXISTS (
      WITH RECURSIVE lineage AS (
        SELECT cycle,subject_digest,body,previous_child_proposal_digest
        FROM factory.semantic_child_proposals
        WHERE child_proposal_digest=
          (v_input->>'previous_child_proposal_digest')::char(64)
        UNION ALL
        SELECT prior.cycle,prior.subject_digest,prior.body,
          prior.previous_child_proposal_digest
        FROM factory.semantic_child_proposals prior JOIN lineage child
          ON prior.child_proposal_digest=child.previous_child_proposal_digest
      )
      SELECT 1 FROM lineage
      JOIN factory.semantic_subjects lineage_subject
        ON lineage_subject.subject_digest=lineage.subject_digest
      WHERE body->>'baseline_risk_level' IS DISTINCT FROM
        v_previous.body->>'baseline_risk_level'
        OR body->>'baseline_risk_level' NOT IN ('low','medium','high','critical')
        OR body->>'parent_exact_head_sha' IS DISTINCT FROM
          trim(lineage_subject.exact_head_sha)
        OR body->>'authority_digest' IS DISTINCT FROM
          lineage_subject.subject_body->>'authority_digest'
    ) THEN RETURN NULL; END IF;
    v_baseline_risk=v_previous.body->>'baseline_risk_level';
    v_budget=LEAST(
      (v_packet.body#>>'{limits,semantic_repairs}')::integer,
      (v_previous.body->>'budget_remaining_units')::integer
    )-1;
    v_deadline=CASE
      WHEN (v_manifest.body->>'deadline')::timestamptz<=
        (v_previous.body->>'deadline_at')::timestamptz
      THEN v_manifest.body->>'deadline'
      ELSE v_previous.body->>'deadline_at'
    END;
  ELSE
    v_lineage_count=0;
    v_baseline_risk=v_subject.subject_body->>'risk_level';
    v_budget=(v_packet.body#>>'{limits,semantic_repairs}')::integer;
    v_deadline=v_manifest.body->>'deadline';
  END IF;
  IF v_baseline_risk NOT IN ('low','medium','high','critical') THEN RETURN NULL; END IF;
  v_remaining_cost=GREATEST(
    v_current_task.cost_limit_micros-v_current_task.cost_observed_micros,0
  );
  v_remaining_tokens=GREATEST(
    v_current_task.token_limit-v_current_task.tokens_observed,0
  );
  SELECT GREATEST(
      v_current_task.output_limit_bytes-COALESCE(sum(output_bytes),0),0
    ) INTO v_remaining_output
    FROM factory.usage_observations WHERE task_id=v_current_task.task_id;
  SELECT GREATEST(
      v_current_task.event_limit-count(*) FILTER (WHERE NOT mandatory_cleanup),0
    ) INTO v_remaining_events
    FROM factory.task_events WHERE task_id=v_current_task.task_id;
  SELECT GREATEST(
      (v_packet.body#>>'{limits,infrastructure_retries}')::integer-
      count(*) FILTER (WHERE failure_class IN (
        'database_unavailable','worker_lost','provider_transport_unavailable',
        'temporary_resource_exhaustion'
      )),0
    ) INTO v_remaining_infrastructure_retries
    FROM factory.attempts WHERE task_id=v_current_task.task_id;
  SELECT '[' || COALESCE(string_agg(to_jsonb(value)::text,',' ORDER BY value),'') || ']'
    INTO v_finding_list
    FROM jsonb_array_elements_text(v_verdict.body->'finding_identity_digests') item(value);

  IF v_input->>'writer_id' IS DISTINCT FROM v_subject.owner_id THEN
    v_reason='original_writer_mismatch';
  ELSIF v_cycle NOT BETWEEN 1 AND 3 THEN
    v_reason='repair_cycle_out_of_bounds';
  ELSIF v_previous.child_proposal_digest IS NOT NULL AND (
    v_previous.subject_digest=v_subject.subject_digest
    OR v_previous.body->>'parent_workspace_result_digest'=
      trim(v_subject.workspace_result_digest)
  ) THEN
    v_reason='workspace_result_changed';
  ELSIF v_previous.child_proposal_digest IS NOT NULL
    AND v_previous.body->>'parent_exact_head_sha'=trim(v_subject.exact_head_sha)
  THEN
    v_reason='head_changed';
  ELSIF EXISTS (
    WITH RECURSIVE lineage AS (
      SELECT body,previous_child_proposal_digest
      FROM factory.semantic_child_proposals
      WHERE child_proposal_digest=
        (v_input->>'previous_child_proposal_digest')::char(64)
      UNION ALL
      SELECT prior.body,prior.previous_child_proposal_digest
      FROM factory.semantic_child_proposals prior JOIN lineage child
        ON prior.child_proposal_digest=child.previous_child_proposal_digest
    )
    SELECT 1 FROM lineage,
      jsonb_array_elements_text(lineage.body->'finding_identity_digests') prior(identity)
    JOIN jsonb_array_elements_text(v_verdict.body->'finding_identity_digests') current(identity)
      ON current.identity=prior.identity
  ) THEN
    v_reason='finding_recurrence';
  ELSIF v_input->>'expected_risk_level' IS DISTINCT FROM
      v_subject.subject_body->>'risk_level'
    OR (CASE v_subject.subject_body->>'risk_level'
        WHEN 'low' THEN 0 WHEN 'medium' THEN 1 WHEN 'high' THEN 2 ELSE 3 END
      > (CASE v_baseline_risk
        WHEN 'low' THEN 0 WHEN 'medium' THEN 1 WHEN 'high' THEN 2 ELSE 3 END)) THEN
    v_reason='risk_increased';
  ELSIF (v_subject.subject_body->>'diff_lines')::integer>
      (v_subject.subject_body->>'diff_limit')::integer THEN
    v_reason='diff_limit_exceeded';
  ELSIF v_input->>'expected_diff_digest' IS DISTINCT FROM
      v_subject.subject_body->>'diff_digest' THEN
    v_reason='diff_changed';
  ELSIF v_input->>'expected_architecture_digest' IS DISTINCT FROM
      v_subject.subject_body->>'architecture_digest' THEN
    v_reason='architecture_changed';
  ELSIF v_input->>'expected_authority_digest' IS DISTINCT FROM
      v_subject.subject_body->>'authority_digest' THEN
    v_reason='authority_changed';
  ELSIF v_input->>'expected_base_sha' IS DISTINCT FROM trim(v_subject.exact_base_sha)
  THEN
    v_reason='base_changed';
  ELSIF v_input->>'expected_workspace_result_digest' IS DISTINCT FROM
      trim(v_subject.workspace_result_digest) THEN
    v_reason='workspace_result_changed';
  ELSIF (v_input->>'expected_fence')::bigint<>v_subject.fence THEN
    v_reason='stale_fence';
  ELSIF v_input->>'expected_head_sha' IS DISTINCT FROM trim(v_subject.exact_head_sha)
  THEN
    v_reason='head_changed';
  ELSIF v_result.terminal_stage<>'completed' OR v_result.m4_status<>'ready_for_human'
    OR v_result.failure_class IS NOT NULL OR v_result.failure_reason IS NOT NULL
    OR v_packet.body->>'role'<>'writer'
  THEN
    v_reason='unsupported_result_disposition';
  ELSIF v_budget<=0 OR v_remaining_cost<=0 OR v_remaining_tokens<=0
    OR v_remaining_output<=0 OR v_remaining_events<=0 THEN
    v_reason='budget_exhausted';
  ELSIF v_deadline IS NULL OR v_deadline::timestamptz<=clock_timestamp() THEN
    v_reason='deadline_exhausted';
  ELSIF v_input->>'context_digest' IS NOT DISTINCT FROM
      v_subject.subject_body->>'original_writer_context_digest'
    OR EXISTS (
      WITH RECURSIVE lineage AS (
        SELECT body,previous_child_proposal_digest
        FROM factory.semantic_child_proposals
        WHERE child_proposal_digest=
          (v_input->>'previous_child_proposal_digest')::char(64)
        UNION ALL
        SELECT prior.body,prior.previous_child_proposal_digest
        FROM factory.semantic_child_proposals prior JOIN lineage child
          ON prior.child_proposal_digest=child.previous_child_proposal_digest
      )
      SELECT 1 FROM lineage
      WHERE body->>'context_digest'=v_input->>'context_digest'
    )
  THEN
    v_reason='context_not_fresh';
  ELSIF v_verdict.body->>'decision'<>'repair' THEN
    v_reason='verdict_not_repair';
  END IF;

  SELECT * INTO v_prior FROM factory.semantic_command_results
    WHERE operation='plan_repair' AND idempotency_key=p_idempotency_key;
  IF FOUND THEN
    RETURN CASE WHEN v_prior.request_digest=p_request_digest
      THEN v_prior.response_body ELSE NULL END;
  END IF;

  IF v_reason IS NOT NULL THEN
    v_escalation_canonical='{"reason":' || to_jsonb(v_reason)::text ||
      ',"request_digest":' || to_jsonb(trim(p_request_digest))::text ||
      ',"requested_cycle":' || v_cycle::text ||
      ',"schema_version":1' ||
      ',"subject_digest":' || to_jsonb(trim(v_subject.subject_digest))::text ||
      ',"verdict_digest":' || to_jsonb(trim(v_verdict.verdict_digest))::text || '}';
    v_escalation=v_escalation_canonical::jsonb;
    v_escalation_digest=factory.execution_contract_hash(NULL,v_escalation_canonical);
    INSERT INTO factory.semantic_escalations(
      escalation_digest,subject_digest,verdict_digest,requested_cycle,reason,
      request_digest,body
    ) VALUES (
      v_escalation_digest,v_subject.subject_digest,v_verdict.verdict_digest,
      v_cycle,v_reason,p_request_digest,v_escalation
    ) ON CONFLICT (escalation_digest) DO NOTHING;
    v_response=jsonb_build_object(
      'decision','needs_human','reason',v_reason,
      'subject_digest',trim(v_subject.subject_digest),
      'verdict_digest',trim(v_verdict.verdict_digest),'cycle',v_cycle,
      'directive_digest',NULL,'directive',NULL,
      'child_proposal_digest',NULL,'child_proposal',NULL,
      'escalation_digest',trim(v_escalation_digest),'escalation',v_escalation
    );
    INSERT INTO factory.semantic_command_results(
      operation,idempotency_key,request_digest,resource_digest,response_body
    ) VALUES (
      'plan_repair',p_idempotency_key,p_request_digest,v_escalation_digest,v_response
    );
    RETURN v_response;
  END IF;

  v_directive_canonical='{"context_digest":' ||
    to_jsonb(v_input->>'context_digest')::text ||
    ',"cycle":' || v_cycle::text ||
    ',"exact_head_sha":' || to_jsonb(trim(v_subject.exact_head_sha))::text ||
    ',"finding_identity_digests":' || v_finding_list ||
    ',"schema_version":1' ||
    ',"subject_digest":' || to_jsonb(trim(v_subject.subject_digest))::text ||
    ',"verdict_digest":' || to_jsonb(trim(v_verdict.verdict_digest))::text ||
    ',"writer_id":' || to_jsonb(v_subject.owner_id)::text || '}';
  v_directive=v_directive_canonical::jsonb;
  v_directive_digest=factory.execution_contract_hash(NULL,v_directive_canonical);
  v_previous_json=COALESCE(
    to_jsonb(v_input->>'previous_child_proposal_digest')::text,'null'
  );
  v_child_canonical='{"architecture_digest":' ||
    to_jsonb(v_subject.subject_body->>'architecture_digest')::text ||
    ',"authority_digest":' || to_jsonb(v_subject.subject_body->>'authority_digest')::text ||
    ',"baseline_risk_level":' || to_jsonb(v_baseline_risk)::text ||
    ',"budget_remaining_units":' || v_budget::text ||
    ',"context_digest":' || to_jsonb(v_input->>'context_digest')::text ||
    ',"cycle":' || v_cycle::text ||
    ',"deadline_at":' || to_jsonb(v_deadline)::text ||
    ',"diff_digest":' || to_jsonb(v_subject.subject_body->>'diff_digest')::text ||
    ',"directive_digest":' || to_jsonb(trim(v_directive_digest))::text ||
    ',"exact_base_sha":' || to_jsonb(trim(v_subject.exact_base_sha))::text ||
    ',"finding_identity_digests":' || v_finding_list ||
    ',"infrastructure_retries_remaining":' ||
      v_remaining_infrastructure_retries::text ||
    ',"max_cost_usd_micros":' || v_remaining_cost::text ||
    ',"max_events":' || v_remaining_events::text ||
    ',"max_output_bytes":' || v_remaining_output::text ||
    ',"max_token_units":' || v_remaining_tokens::text ||
    ',"parent_exact_head_sha":' || to_jsonb(trim(v_subject.exact_head_sha))::text ||
    ',"parent_fence":' || v_subject.fence::text ||
    ',"parent_run_id":' || to_jsonb(v_subject.run_id::text)::text ||
    ',"parent_run_manifest_digest":' || to_jsonb(trim(v_subject.run_manifest_digest))::text ||
    ',"parent_task_id":' || to_jsonb(v_subject.task_id::text)::text ||
    ',"parent_task_packet_digest":' || to_jsonb(trim(v_subject.task_packet_digest))::text ||
    ',"parent_workspace_result_digest":' || to_jsonb(trim(v_subject.workspace_result_digest))::text ||
    ',"previous_child_proposal_digest":' || v_previous_json ||
    ',"proposal_state":"pending_handoff"' ||
    ',"requires_new_semantic_subject":true' ||
    ',"requires_new_workspace_result":true' ||
    ',"schema_version":1' ||
    ',"subject_digest":' || to_jsonb(trim(v_subject.subject_digest))::text ||
    ',"verdict_digest":' || to_jsonb(trim(v_verdict.verdict_digest))::text ||
    ',"writer_id":' || to_jsonb(v_subject.owner_id)::text || '}';
  v_child=v_child_canonical::jsonb;
  v_child_digest=factory.execution_contract_hash(NULL,v_child_canonical);

  SELECT * INTO v_existing_directive FROM factory.semantic_directives
    WHERE directive_digest=v_directive_digest
      OR verdict_digest=v_verdict.verdict_digest;
  IF FOUND AND (
    v_existing_directive.directive_digest<>v_directive_digest
    OR v_existing_directive.subject_digest<>v_subject.subject_digest
    OR v_existing_directive.body IS DISTINCT FROM v_directive
  ) THEN RETURN NULL; END IF;
  IF NOT FOUND THEN
    INSERT INTO factory.semantic_directives(
      directive_digest,subject_digest,verdict_digest,request_digest,body
    ) VALUES (
      v_directive_digest,v_subject.subject_digest,v_verdict.verdict_digest,
      p_request_digest,v_directive
    );
  END IF;

  SELECT * INTO v_existing_child FROM factory.semantic_child_proposals
    WHERE child_proposal_digest=v_child_digest
      OR (subject_digest=v_subject.subject_digest AND cycle=v_cycle);
  IF FOUND AND (
    v_existing_child.child_proposal_digest<>v_child_digest
    OR v_existing_child.directive_digest<>v_directive_digest
    OR v_existing_child.body IS DISTINCT FROM v_child
  ) THEN RETURN NULL; END IF;
  IF NOT FOUND THEN
    INSERT INTO factory.semantic_child_proposals(
      child_proposal_digest,subject_digest,directive_digest,parent_task_id,
      parent_run_id,parent_fence,cycle,previous_child_proposal_digest,
      proposal_state,request_digest,body
    ) VALUES (
      v_child_digest,v_subject.subject_digest,v_directive_digest,v_subject.task_id,
      v_subject.run_id,v_subject.fence,v_cycle,
      (v_input->>'previous_child_proposal_digest')::char(64),
      'pending_handoff',p_request_digest,v_child
    );
  END IF;

  v_response=jsonb_build_object(
    'decision','repair','reason','repair_allowed',
    'subject_digest',trim(v_subject.subject_digest),
    'verdict_digest',trim(v_verdict.verdict_digest),'cycle',v_cycle,
    'directive_digest',trim(v_directive_digest),'directive',v_directive,
    'child_proposal_digest',trim(v_child_digest),'child_proposal',v_child,
    'escalation_digest',NULL,'escalation',NULL
  );
  INSERT INTO factory.semantic_command_results(
    operation,idempotency_key,request_digest,resource_digest,response_body
  ) VALUES (
    'plan_repair',p_idempotency_key,p_request_digest,v_child_digest,v_response
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
  factory.semantic_child_task_bindings,factory.semantic_escalations,
  factory.semantic_recovery_records,
  factory.semantic_metric_events FROM PUBLIC;
REVOKE ALL ON TABLE factory.semantic_command_results,factory.semantic_subjects,
  factory.semantic_assignments,factory.semantic_findings,factory.semantic_coverage,
  factory.semantic_verdicts,factory.semantic_directives,factory.semantic_child_proposals,
  factory.semantic_child_task_bindings,factory.semantic_escalations,
  factory.semantic_recovery_records,
  factory.semantic_metric_events
  FROM factory_runtime,factory_artifact_attestor,factory_semantic_coordinator,
    factory_semantic_validator,factory_semantic_adjudicator;
REVOKE INSERT, UPDATE, DELETE ON TABLE factory.semantic_command_results,
  factory.semantic_subjects,factory.semantic_assignments,factory.semantic_findings,
  factory.semantic_coverage,factory.semantic_verdicts,factory.semantic_directives,
  factory.semantic_child_proposals,factory.semantic_child_task_bindings,
  factory.semantic_escalations,
  factory.semantic_recovery_records,
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
REVOKE ALL ON FUNCTION factory.semantic_plan_repair(char,char,text,uuid) FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.semantic_bind_repair_child(char,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.semantic_repair_intake_status(text,text,text,char,char,text,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.semantic_task_claimable(uuid,uuid,text,text,text,text) FROM PUBLIC;
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
GRANT EXECUTE ON FUNCTION factory.semantic_plan_repair(char,char,text,uuid)
  TO factory_semantic_coordinator;
GRANT EXECUTE ON FUNCTION factory.semantic_bind_repair_child(char,text)
  TO factory_semantic_coordinator;
GRANT EXECUTE ON FUNCTION factory.semantic_repair_intake_status(text,text,text,char,char,text,text)
  TO factory_runtime;
GRANT EXECUTE ON FUNCTION factory.semantic_task_claimable(uuid,uuid,text,text,text,text)
  TO factory_runtime;
