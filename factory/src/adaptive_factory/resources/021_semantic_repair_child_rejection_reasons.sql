-- Forward-only redefinition of factory.semantic_bind_repair_child(char,text).
--
-- Shipped resources are immutable: PostgresMigrator.plan_migrations() compares the
-- recorded (version,name,sha256) of every already-applied prefix row against the
-- packaged file, so editing 018 would fail every existing database with
-- "migration drift at version 18". Applied resources are never re-run, so the fix
-- is a new resource that replaces the function in place with CREATE OR REPLACE.
--
-- Each guard path previously did a bare RETURN NULL. The coordinator role cannot see
-- why a bind was refused, and store.bind_repair_child fed the SQL NULL into
-- RepairChildTaskBindingV1.from_dict, which raised the generic
-- "invalid_object: repair_child_task_binding" -- a valid contract-shaped binding that
-- was refused for a deadline or precondition reason was reported as a malformed
-- payload. Guards now return a single-key rejection envelope:
--
--   {"repair_child_rejection":"<one allowlisted reason>"}
--
-- The envelope can never be confused with a binding: the binding branch of this
-- function already requires exactly four keys (schema_version,
-- child_proposal_digest, child_task_id, child_intent_digest) and adaptive_factory
-- validates the rejection key against a closed allowlist before any payload parse, so
-- an unknown reason cannot reach the caller and invalid_object stays reserved for
-- genuinely malformed payloads.
--
-- Guard conditions are preserved verbatim from 018; the large precondition block is
-- partitioned into four contiguous named groups so a deadline or limit refusal is
-- distinguishable. Accept/reject truth is unchanged: OR over the same conditions,
-- re-grouped, is TRUE under exactly the same rows.
-- No table, index, row or privilege is dropped or rewritten by this resource.
CREATE OR REPLACE FUNCTION factory.semantic_bind_repair_child(
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
  THEN RETURN jsonb_build_object('repair_child_rejection','command_input_invalid'); END IF;
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
  THEN RETURN jsonb_build_object('repair_child_rejection','binding_payload_invalid'); END IF;

  SELECT * INTO v_child FROM factory.semantic_child_proposals
    WHERE child_proposal_digest=
      (v_binding->>'child_proposal_digest')::char(64) FOR UPDATE;
  IF NOT FOUND OR v_child.body->>'proposal_state' IS DISTINCT FROM 'pending_handoff'
  THEN RETURN jsonb_build_object('repair_child_rejection','proposal_not_pending'); END IF;

  SELECT * INTO v_parent_task FROM factory.tasks
    WHERE task_id=v_child.parent_task_id;
  IF NOT FOUND THEN RETURN jsonb_build_object('repair_child_rejection','parent_task_missing'); END IF;
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
  THEN RETURN jsonb_build_object('repair_child_rejection','child_task_unavailable'); END IF;

  SELECT * INTO v_existing FROM factory.semantic_child_task_bindings
    WHERE child_proposal_digest=v_child.child_proposal_digest;
  IF FOUND THEN
    RETURN CASE WHEN v_existing.binding_digest=p_binding_digest
      AND v_existing.child_task_id=v_child_task.task_id
      AND v_existing.child_intent_digest=
        (v_binding->>'child_intent_digest')::char(64)
      AND v_existing.body IS NOT DISTINCT FROM v_binding
      THEN v_existing.body ELSE jsonb_build_object('repair_child_rejection','binding_conflict') END;
  END IF;
  IF EXISTS (
    SELECT 1 FROM factory.semantic_child_task_bindings
    WHERE child_task_id=v_child_task.task_id
      OR child_intent_digest=(v_binding->>'child_intent_digest')::char(64)
  ) THEN RETURN jsonb_build_object('repair_child_rejection','child_already_bound'); END IF;

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
  THEN RETURN jsonb_build_object('repair_child_rejection','lineage_mismatch'); END IF;
  IF v_child_task.accepted_at-v_child_observation.observed_at
      NOT BETWEEN interval '0 seconds' AND interval '300 seconds'
    OR v_parent_task.accepted_at-v_parent_observation.observed_at
      NOT BETWEEN interval '0 seconds' AND interval '300 seconds'
  THEN RETURN jsonb_build_object('repair_child_rejection','authority_not_fresh'); END IF;
  IF v_child_task.deadline_at>v_parent_task.deadline_at
    OR v_child_task.deadline_at>(v_child.body->>'deadline_at')::timestamptz
  THEN RETURN jsonb_build_object('repair_child_rejection','deadline_exceeded'); END IF;
  IF (v_child_intent.body#>>'{limits,max_cost_usd_micros}')::bigint>
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
  THEN RETURN jsonb_build_object('repair_child_rejection','child_limits_exceeded'); END IF;

  INSERT INTO factory.semantic_child_task_bindings(
    binding_digest,child_proposal_digest,child_task_id,child_intent_digest,body
  ) VALUES (
    p_binding_digest,v_child.child_proposal_digest,v_child_task.task_id,
    v_child_intent.intent_digest,v_binding
  );
  RETURN v_binding;
EXCEPTION WHEN unique_violation OR check_violation OR foreign_key_violation
  OR invalid_text_representation OR numeric_value_out_of_range OR data_exception THEN
  RETURN jsonb_build_object('repair_child_rejection','store_write_rejected');
END;
$$;

REVOKE ALL ON FUNCTION factory.semantic_bind_repair_child(char,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION factory.semantic_bind_repair_child(char,text)
  TO factory_semantic_coordinator;
