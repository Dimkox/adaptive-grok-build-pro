-- M5 execution-plane schema follows M4 migration 013.
CREATE TABLE factory.execution_packets (
  packet_digest char(64) PRIMARY KEY CHECK (packet_digest ~ '^[0-9a-f]{64}$'),
  task_id uuid NOT NULL,
  run_id uuid NOT NULL,
  legacy_packet_digest char(64) NOT NULL CHECK (legacy_packet_digest ~ '^[0-9a-f]{64}$'),
  provider_id text NOT NULL CHECK (octet_length(provider_id) BETWEEN 1 AND 128),
  body jsonb NOT NULL CHECK (octet_length(body::text) <= 1048576),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  UNIQUE (run_id),
  UNIQUE (packet_digest, run_id),
  FOREIGN KEY (run_id, task_id) REFERENCES factory.runs(run_id, task_id) ON DELETE RESTRICT
);

CREATE TABLE factory.execution_manifests (
  manifest_digest char(64) PRIMARY KEY CHECK (manifest_digest ~ '^[0-9a-f]{64}$'),
  task_id uuid NOT NULL,
  run_id uuid NOT NULL UNIQUE,
  packet_digest char(64) NOT NULL,
  workspace_handle text NOT NULL CHECK (workspace_handle ~ '^workspace:[0-9a-f]{64}$'),
  stage text NOT NULL CHECK (stage IN ('prepared','running','collecting','completed','failed','needs_human','cancelled','orphaned')),
  body jsonb NOT NULL CHECK (octet_length(body::text) <= 65536),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  terminal_at timestamptz,
  FOREIGN KEY (packet_digest, run_id) REFERENCES factory.execution_packets(packet_digest, run_id) ON DELETE RESTRICT,
  FOREIGN KEY (run_id, task_id) REFERENCES factory.runs(run_id, task_id) ON DELETE RESTRICT,
  CHECK ((terminal_at IS NULL) = (stage NOT IN ('completed','failed','needs_human','cancelled','orphaned')))
);
CREATE INDEX execution_manifests_recovery ON factory.execution_manifests(updated_at,run_id)
  WHERE terminal_at IS NULL;

CREATE TABLE factory.execution_stage_events (
  stage_event_id bigserial PRIMARY KEY,
  manifest_digest char(64) NOT NULL REFERENCES factory.execution_manifests(manifest_digest) ON DELETE RESTRICT,
  stage_sequence bigint NOT NULL CHECK (stage_sequence > 0),
  stage text NOT NULL CHECK (stage IN ('prepared','running','collecting','completed','failed','needs_human','cancelled','orphaned')),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  UNIQUE (manifest_digest,stage_sequence)
);

CREATE TABLE factory.execution_proposals (
  proposal_id uuid PRIMARY KEY,
  task_id uuid NOT NULL,
  run_id uuid NOT NULL,
  packet_digest char(64) NOT NULL,
  producer_sequence bigint NOT NULL CHECK (producer_sequence > 0),
  idempotency_key char(64) NOT NULL CHECK (idempotency_key ~ '^[0-9a-f]{64}$'),
  proposal_kind text NOT NULL CHECK (proposal_kind IN ('note','artifact','usage','terminal')),
  body jsonb NOT NULL CHECK (octet_length(body::text) <= 65536),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  UNIQUE (run_id,producer_sequence),
  UNIQUE (run_id,idempotency_key),
  FOREIGN KEY (packet_digest,run_id) REFERENCES factory.execution_packets(packet_digest,run_id) ON DELETE RESTRICT,
  FOREIGN KEY (run_id,task_id) REFERENCES factory.runs(run_id,task_id) ON DELETE RESTRICT
);
CREATE UNIQUE INDEX execution_proposals_one_terminal
  ON factory.execution_proposals(run_id) WHERE proposal_kind='terminal';

CREATE TABLE factory.workspace_results (
  workspace_result_digest char(64) PRIMARY KEY CHECK (workspace_result_digest ~ '^[0-9a-f]{64}$'),
  task_id uuid NOT NULL,
  run_id uuid NOT NULL UNIQUE,
  task_packet_digest char(64) NOT NULL,
  run_manifest_digest char(64) NOT NULL UNIQUE,
  exact_head_sha char(40) NOT NULL CHECK (exact_head_sha ~ '^[0-9a-f]{40}$'),
  workspace_snapshot_digest char(64) NOT NULL UNIQUE CHECK (workspace_snapshot_digest ~ '^[0-9a-f]{64}$'),
  terminal_stage text NOT NULL CHECK (terminal_stage IN ('completed','failed','needs_human')),
  terminal_proposal_digest char(64) NOT NULL,
  artifact_manifest_digest char(64) NOT NULL CHECK (artifact_manifest_digest ~ '^[0-9a-f]{64}$'),
  note_manifest_digest char(64) NOT NULL CHECK (note_manifest_digest ~ '^[0-9a-f]{64}$'),
  usage_evidence_digest char(64) NOT NULL CHECK (usage_evidence_digest ~ '^[0-9a-f]{64}$'),
  diagnostics_digest char(64) NOT NULL CHECK (diagnostics_digest ~ '^[0-9a-f]{64}$'),
  workspace_snapshot jsonb NOT NULL CHECK (octet_length(workspace_snapshot::text) <= 65536),
  body jsonb NOT NULL CHECK (octet_length(body::text) <= 65536),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  FOREIGN KEY (task_packet_digest,run_id) REFERENCES factory.execution_packets(packet_digest,run_id) ON DELETE RESTRICT,
  FOREIGN KEY (run_manifest_digest) REFERENCES factory.execution_manifests(manifest_digest) ON DELETE RESTRICT,
  FOREIGN KEY (run_id,terminal_proposal_digest) REFERENCES factory.execution_proposals(run_id,idempotency_key) ON DELETE RESTRICT,
  FOREIGN KEY (run_id,task_id) REFERENCES factory.runs(run_id,task_id) ON DELETE RESTRICT
);

CREATE FUNCTION factory.execution_start(
  p_task_id uuid,
  p_run_id uuid,
  p_owner text,
  p_fence bigint,
  p_legacy_packet_digest char(64),
  p_packet_digest char(64),
  p_manifest_digest char(64),
  p_workspace_handle text,
  p_provider_id text,
  p_packet jsonb,
  p_manifest jsonb
) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
BEGIN
  IF octet_length(p_packet::text)>1048576 OR octet_length(p_manifest::text)>65536 THEN
    RETURN false;
  END IF;
  PERFORM 1 FROM factory.tasks t
    JOIN factory.runs r ON r.run_id=t.current_run_id AND r.task_id=t.task_id
    JOIN factory.capacity_allocations a ON a.run_id=r.run_id AND a.task_id=t.task_id
    WHERE t.task_id=p_task_id AND r.run_id=p_run_id AND r.owner_id=p_owner
      AND r.fence=p_fence AND r.packet_digest=p_legacy_packet_digest
      AND t.packet_digest=p_legacy_packet_digest AND t.current_fence=p_fence
      AND t.state='leased' AND r.state='leased' AND r.released_at IS NULL
      AND a.released_at IS NULL AND r.lease_expires_at>clock_timestamp()
      AND t.deadline_at>clock_timestamp()
    FOR UPDATE OF t,r;
  IF NOT FOUND THEN RETURN false; END IF;

  INSERT INTO factory.execution_packets(
    packet_digest,task_id,run_id,legacy_packet_digest,provider_id,body
  ) VALUES (
    p_packet_digest,p_task_id,p_run_id,p_legacy_packet_digest,p_provider_id,p_packet
  );
  INSERT INTO factory.execution_manifests(
    manifest_digest,task_id,run_id,packet_digest,workspace_handle,stage,body
  ) VALUES (
    p_manifest_digest,p_task_id,p_run_id,p_packet_digest,p_workspace_handle,'prepared',p_manifest
  );
  INSERT INTO factory.execution_stage_events(manifest_digest,stage_sequence,stage)
    VALUES (p_manifest_digest,1,'prepared');
  RETURN true;
EXCEPTION WHEN unique_violation OR check_violation OR foreign_key_violation THEN
  RETURN false;
END;
$$;

CREATE FUNCTION factory.execution_advance(
  p_task_id uuid,
  p_run_id uuid,
  p_owner text,
  p_fence bigint,
  p_legacy_packet_digest char(64),
  p_packet_digest char(64),
  p_stage text
) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE
  current_stage text;
  manifest char(64);
  next_sequence bigint;
BEGIN
  PERFORM 1 FROM factory.tasks t
    JOIN factory.runs r ON r.run_id=t.current_run_id AND r.task_id=t.task_id
    JOIN factory.capacity_allocations a ON a.run_id=r.run_id AND a.task_id=t.task_id
    WHERE t.task_id=p_task_id AND r.run_id=p_run_id AND r.owner_id=p_owner
      AND r.fence=p_fence AND r.packet_digest=p_legacy_packet_digest
      AND t.packet_digest=p_legacy_packet_digest AND t.current_fence=p_fence
      AND t.state='leased' AND r.state='leased' AND r.released_at IS NULL
      AND a.released_at IS NULL AND r.lease_expires_at>clock_timestamp()
      AND t.deadline_at>clock_timestamp()
    FOR UPDATE OF t,r;
  IF NOT FOUND THEN RETURN false; END IF;

  SELECT m.stage,m.manifest_digest INTO current_stage,manifest
    FROM factory.execution_manifests m
    WHERE m.task_id=p_task_id AND m.run_id=p_run_id AND m.packet_digest=p_packet_digest
      AND m.terminal_at IS NULL
    FOR UPDATE;
  IF NOT FOUND THEN RETURN false; END IF;
  IF NOT (
    (current_stage='prepared' AND p_stage='running') OR
    (current_stage='running' AND p_stage='collecting')
  ) THEN RETURN false; END IF;

  SELECT COALESCE(max(stage_sequence),0)+1 INTO next_sequence
    FROM factory.execution_stage_events WHERE manifest_digest=manifest;
  UPDATE factory.execution_manifests SET stage=p_stage,updated_at=clock_timestamp(),
    terminal_at=NULL
    WHERE manifest_digest=manifest;
  INSERT INTO factory.execution_stage_events(manifest_digest,stage_sequence,stage)
    VALUES (manifest,next_sequence,p_stage);
  RETURN true;
END;
$$;

CREATE FUNCTION factory.execution_propose(
  p_task_id uuid,
  p_run_id uuid,
  p_owner text,
  p_fence bigint,
  p_legacy_packet_digest char(64),
  p_packet_digest char(64),
  p_sequence bigint,
  p_idempotency_key char(64),
  p_kind text,
  p_body jsonb
) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE
  collision_count bigint;
  exact_replay boolean;
  previous_sequence bigint;
  authoritative_max_events bigint;
  packet_max_events text;
  durable_role text;
  packet_role text;
BEGIN
  IF p_body IS NULL OR octet_length(p_body::text)>65536
    OR p_sequence IS NULL OR p_sequence<=0
    OR p_idempotency_key IS NULL OR trim(p_idempotency_key)!~'^[0-9a-f]{64}$'
    OR p_kind IS NULL OR p_kind NOT IN ('note','artifact','usage','terminal')
  THEN RETURN false; END IF;
  SELECT t.event_limit,p.body#>>'{limits,max_events}',r.role,p.body->>'role'
    INTO authoritative_max_events,packet_max_events,durable_role,packet_role
    FROM factory.tasks t
    JOIN factory.runs r ON r.run_id=t.current_run_id AND r.task_id=t.task_id
    JOIN factory.capacity_allocations a ON a.run_id=r.run_id AND a.task_id=t.task_id
      AND a.repository_id=t.repository_id AND a.role=r.role
    JOIN factory.execution_packets p ON p.run_id=r.run_id AND p.task_id=t.task_id
      AND p.packet_digest=p_packet_digest AND p.legacy_packet_digest=p_legacy_packet_digest
    JOIN factory.execution_manifests m ON m.run_id=r.run_id AND m.task_id=t.task_id
      AND m.packet_digest=p.packet_digest
    WHERE t.task_id=p_task_id AND r.run_id=p_run_id AND r.owner_id=p_owner
      AND r.fence=p_fence AND r.packet_digest=p_legacy_packet_digest
      AND t.packet_digest=p_legacy_packet_digest AND t.current_fence=p_fence
      AND t.state='leased' AND r.state='leased'
      AND r.released_at IS NULL AND a.released_at IS NULL
      AND m.terminal_at IS NULL AND r.lease_expires_at>clock_timestamp()
      AND t.deadline_at>clock_timestamp()
    FOR UPDATE OF t,r,m;
  IF NOT FOUND
    OR packet_max_events IS DISTINCT FROM authoritative_max_events::text
    OR packet_role IS DISTINCT FROM durable_role
    OR (p_kind='artifact' AND durable_role<>'writer')
    OR (p_kind='note' AND p_body->>'author_role' IS DISTINCT FROM durable_role)
  THEN
    RETURN false;
  END IF;

  SELECT count(*),COALESCE(bool_and(
      producer_sequence=p_sequence
      AND trim(idempotency_key)=trim(p_idempotency_key)
      AND proposal_kind=p_kind
      AND body=p_body
    ),false)
    INTO collision_count,exact_replay
    FROM factory.execution_proposals
    WHERE run_id=p_run_id
      AND (producer_sequence=p_sequence OR idempotency_key=p_idempotency_key);
  IF collision_count>0 THEN
    RETURN collision_count=1 AND exact_replay;
  END IF;

  IF p_sequence>authoritative_max_events THEN RETURN false; END IF;
  IF EXISTS (
    SELECT 1 FROM factory.execution_proposals
    WHERE run_id=p_run_id AND proposal_kind='terminal'
  ) THEN RETURN false; END IF;
  SELECT producer_sequence INTO previous_sequence
    FROM factory.execution_proposals
    WHERE run_id=p_run_id
    ORDER BY producer_sequence DESC
    LIMIT 1;
  previous_sequence=COALESCE(previous_sequence,0);
  IF p_sequence<>previous_sequence+1 THEN RETURN false; END IF;

  INSERT INTO factory.execution_proposals(
    proposal_id,task_id,run_id,packet_digest,producer_sequence,idempotency_key,proposal_kind,body
  ) VALUES (
    gen_random_uuid(),p_task_id,p_run_id,p_packet_digest,p_sequence,p_idempotency_key,p_kind,p_body
  );
  RETURN true;
EXCEPTION WHEN unique_violation OR check_violation OR foreign_key_violation THEN
  RETURN false;
END;
$$;

CREATE FUNCTION factory.execution_proposal_context(
  p_task_id uuid,
  p_run_id uuid,
  p_owner text,
  p_fence bigint,
  p_legacy_packet_digest char(64),
  p_packet_digest char(64)
) RETURNS jsonb
LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
  SELECT p.body FROM factory.tasks t
  JOIN factory.runs r ON r.run_id=t.current_run_id AND r.task_id=t.task_id
  JOIN factory.capacity_allocations a ON a.run_id=r.run_id AND a.task_id=t.task_id
  JOIN factory.execution_packets p ON p.run_id=r.run_id AND p.task_id=t.task_id
  JOIN factory.execution_manifests m ON m.run_id=p.run_id AND m.packet_digest=p.packet_digest
  WHERE t.task_id=p_task_id AND r.run_id=p_run_id AND r.owner_id=p_owner
    AND r.fence=p_fence AND r.packet_digest=p_legacy_packet_digest
    AND t.packet_digest=p_legacy_packet_digest AND t.current_fence=p_fence
    AND p.packet_digest=p_packet_digest AND t.state='leased' AND r.state='leased'
    AND r.released_at IS NULL AND a.released_at IS NULL AND m.terminal_at IS NULL
    AND r.lease_expires_at>clock_timestamp() AND t.deadline_at>clock_timestamp()
$$;

CREATE FUNCTION factory.execution_result_for_run(p_task_id uuid,p_run_id uuid) RETURNS jsonb
LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
  SELECT jsonb_build_object(
    'result',w.body,
    'snapshot',w.workspace_snapshot,
    'packet',p.body,
    'manifest',m.body
  )
  FROM factory.workspace_results w
  JOIN factory.execution_packets p ON p.run_id=w.run_id AND p.packet_digest=w.task_packet_digest
  JOIN factory.execution_manifests m ON m.run_id=w.run_id AND m.manifest_digest=w.run_manifest_digest
  WHERE w.task_id=p_task_id AND w.run_id=p_run_id
$$;

CREATE FUNCTION factory.execution_result_by_digest(
  p_task_id uuid,p_workspace_result_digest char(64)
) RETURNS jsonb
LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
  SELECT jsonb_build_object(
    'result',w.body,
    'snapshot',w.workspace_snapshot,
    'packet',p.body,
    'manifest',m.body
  )
  FROM factory.workspace_results w
  JOIN factory.execution_packets p ON p.run_id=w.run_id AND p.packet_digest=w.task_packet_digest
  JOIN factory.execution_manifests m ON m.run_id=w.run_id AND m.manifest_digest=w.run_manifest_digest
  WHERE w.task_id=p_task_id AND w.workspace_result_digest=p_workspace_result_digest
$$;

CREATE FUNCTION factory.execution_finalize_context(
  p_task_id uuid,
  p_run_id uuid,
  p_owner text,
  p_fence bigint,
  p_legacy_packet_digest char(64),
  p_packet_digest char(64)
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE
  result jsonb;
BEGIN
  PERFORM 1 FROM factory.tasks t
    JOIN factory.runs r ON r.run_id=t.current_run_id AND r.task_id=t.task_id
    JOIN factory.capacity_allocations a ON a.run_id=r.run_id AND a.task_id=t.task_id
    JOIN factory.execution_packets p ON p.run_id=r.run_id AND p.task_id=t.task_id
    JOIN factory.execution_manifests m ON m.run_id=p.run_id AND m.packet_digest=p.packet_digest
    WHERE t.task_id=p_task_id AND r.run_id=p_run_id AND r.owner_id=p_owner
      AND r.fence=p_fence AND r.packet_digest=p_legacy_packet_digest
      AND t.packet_digest=p_legacy_packet_digest AND t.current_fence=p_fence
      AND p.packet_digest=p_packet_digest AND t.state='leased' AND r.state='leased'
      AND r.released_at IS NULL AND a.released_at IS NULL AND m.terminal_at IS NULL
      AND r.lease_expires_at>clock_timestamp() AND t.deadline_at>clock_timestamp()
    FOR UPDATE OF t,r,m;
  IF NOT FOUND THEN RETURN NULL; END IF;
  IF (SELECT count(*) FROM factory.execution_proposals WHERE run_id=p_run_id)>1000 THEN
    RETURN NULL;
  END IF;
  SELECT jsonb_build_object(
    'repository_id',t.repository_id,
    'workspace_handle',m.workspace_handle,
    'input_head_sha',p.body#>>'{authority,exact_head_sha}',
    'run_manifest_digest',m.manifest_digest,
    'terminal_stage',CASE terminal.body->>'terminal_type'
      WHEN 'run.completed' THEN 'completed'
      WHEN 'run.failed' THEN 'failed'
      WHEN 'run.needs_human' THEN 'needs_human'
      ELSE NULL END,
    'terminal_proposal_digest',trim(terminal.idempotency_key),
    'artifact_digests',COALESCE((SELECT jsonb_agg(trim(x.idempotency_key) ORDER BY trim(x.idempotency_key)) FROM factory.execution_proposals x WHERE x.run_id=p_run_id AND x.proposal_kind='artifact'),'[]'::jsonb),
    'note_digests',COALESCE((SELECT jsonb_agg(trim(x.idempotency_key) ORDER BY trim(x.idempotency_key)) FROM factory.execution_proposals x WHERE x.run_id=p_run_id AND x.proposal_kind='note'),'[]'::jsonb),
    'usage_digests',COALESCE((SELECT jsonb_agg(trim(x.idempotency_key) ORDER BY trim(x.idempotency_key)) FROM factory.execution_proposals x WHERE x.run_id=p_run_id AND x.proposal_kind='usage'),'[]'::jsonb),
    'diagnostic_digests','[]'::jsonb
  ) INTO result
  FROM factory.tasks t
  JOIN factory.execution_packets p ON p.task_id=t.task_id AND p.run_id=p_run_id AND p.packet_digest=p_packet_digest
  JOIN factory.execution_manifests m ON m.run_id=p.run_id AND m.packet_digest=p.packet_digest
  JOIN factory.execution_proposals terminal ON terminal.run_id=p.run_id AND terminal.proposal_kind='terminal'
  WHERE t.task_id=p_task_id;
  IF result->>'terminal_stage' IS NULL THEN RETURN NULL; END IF;
  RETURN result;
END;
$$;

CREATE FUNCTION factory.execution_finalize_commit(
  p_task_id uuid,
  p_run_id uuid,
  p_owner text,
  p_fence bigint,
  p_legacy_packet_digest char(64),
  p_packet_digest char(64),
  p_workspace_result_digest char(64),
  p_snapshot jsonb,
  p_result jsonb
) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE
  current_stage text;
  v_manifest_digest char(64);
  manifest_workspace text;
  repository text;
  input_head text;
  terminal_type text;
  terminal_digest char(64);
  target_stage text;
  next_sequence bigint;
BEGIN
  IF octet_length(p_snapshot::text)>65536 OR octet_length(p_result::text)>65536 THEN RETURN false; END IF;
  SELECT m.stage,m.manifest_digest,m.workspace_handle,t.repository_id,
    p.body#>>'{authority,exact_head_sha}',terminal.body->>'terminal_type',terminal.idempotency_key
    INTO current_stage,v_manifest_digest,manifest_workspace,repository,input_head,terminal_type,terminal_digest
  FROM factory.tasks t
  JOIN factory.runs r ON r.run_id=t.current_run_id AND r.task_id=t.task_id
  JOIN factory.capacity_allocations a ON a.run_id=r.run_id AND a.task_id=t.task_id
  JOIN factory.execution_packets p ON p.run_id=r.run_id AND p.task_id=t.task_id
  JOIN factory.execution_manifests m ON m.run_id=p.run_id AND m.packet_digest=p.packet_digest
  JOIN factory.execution_proposals terminal ON terminal.run_id=p.run_id AND terminal.proposal_kind='terminal'
  WHERE t.task_id=p_task_id AND r.run_id=p_run_id AND r.owner_id=p_owner
    AND r.fence=p_fence AND r.packet_digest=p_legacy_packet_digest
    AND t.packet_digest=p_legacy_packet_digest AND t.current_fence=p_fence
    AND p.packet_digest=p_packet_digest AND t.state='leased' AND r.state='leased'
    AND r.released_at IS NULL AND a.released_at IS NULL AND m.terminal_at IS NULL
    AND r.lease_expires_at>clock_timestamp() AND t.deadline_at>clock_timestamp()
  FOR UPDATE OF t,r,m,terminal;
  IF NOT FOUND THEN RETURN false; END IF;
  target_stage=CASE terminal_type
    WHEN 'run.completed' THEN 'completed'
    WHEN 'run.failed' THEN 'failed'
    WHEN 'run.needs_human' THEN 'needs_human'
    ELSE NULL END;
  IF target_stage IS NULL OR (target_stage='completed' AND current_stage<>'collecting') THEN RETURN false; END IF;
  IF target_stage='completed' AND NOT EXISTS (
    SELECT 1 FROM factory.usage_observations u WHERE u.task_id=p_task_id AND u.run_id=p_run_id
  ) THEN RETURN false; END IF;
  IF target_stage='completed' AND EXISTS (
    SELECT 1 FROM factory.budget_reservations b WHERE b.task_id=p_task_id AND b.released_at IS NULL
  ) THEN RETURN false; END IF;
  IF p_snapshot->>'source'<>'trusted_git_broker'
    OR p_snapshot->>'repository_id'<>repository
    OR p_snapshot->>'workspace_handle'<>manifest_workspace
    OR p_snapshot->>'input_head_sha'<>input_head
    OR p_result->>'task_id'<>p_task_id::text
    OR p_result->>'run_id'<>p_run_id::text
    OR p_result->>'task_packet_digest'<>trim(p_packet_digest)
    OR p_result->>'run_manifest_digest'<>trim(v_manifest_digest)
    OR p_result->>'exact_head_sha'<>p_snapshot->>'result_head_sha'
    OR p_result->>'workspace_snapshot_digest'<>p_snapshot->>'workspace_snapshot_digest'
    OR p_result->>'workspace_result_digest'<>trim(p_workspace_result_digest)
    OR p_result->>'terminal_stage'<>target_stage
    OR p_result->>'terminal_proposal_digest'<>trim(terminal_digest)
  THEN RETURN false; END IF;
  INSERT INTO factory.workspace_results(
    workspace_result_digest,task_id,run_id,task_packet_digest,run_manifest_digest,exact_head_sha,
    workspace_snapshot_digest,terminal_stage,terminal_proposal_digest,artifact_manifest_digest,
    note_manifest_digest,usage_evidence_digest,diagnostics_digest,workspace_snapshot,body
  ) VALUES (
    p_workspace_result_digest,p_task_id,p_run_id,p_packet_digest,v_manifest_digest,
    p_result->>'exact_head_sha',p_result->>'workspace_snapshot_digest',target_stage,terminal_digest,
    p_result->>'artifact_manifest_digest',p_result->>'note_manifest_digest',
    p_result->>'usage_evidence_digest',p_result->>'diagnostics_digest',p_snapshot,p_result
  );
  SELECT COALESCE(max(stage_sequence),0)+1 INTO next_sequence
    FROM factory.execution_stage_events WHERE execution_stage_events.manifest_digest=v_manifest_digest;
  UPDATE factory.execution_manifests SET stage=target_stage,updated_at=clock_timestamp(),terminal_at=clock_timestamp()
    WHERE execution_manifests.manifest_digest=v_manifest_digest;
  INSERT INTO factory.execution_stage_events(manifest_digest,stage_sequence,stage)
    VALUES (v_manifest_digest,next_sequence,target_stage);
  RETURN true;
EXCEPTION WHEN unique_violation OR check_violation OR foreign_key_violation THEN
  RETURN false;
END;
$$;

REVOKE ALL ON factory.execution_packets,factory.execution_manifests,
  factory.execution_stage_events,factory.execution_proposals,factory.workspace_results FROM PUBLIC,factory_runtime;
REVOKE ALL ON FUNCTION factory.execution_start(uuid,uuid,text,bigint,char,char,char,text,text,jsonb,jsonb)
  FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.execution_advance(uuid,uuid,text,bigint,char,char,text)
  FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.execution_propose(uuid,uuid,text,bigint,char,char,bigint,char,text,jsonb)
  FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.execution_proposal_context(uuid,uuid,text,bigint,char,char)
  FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.execution_result_for_run(uuid,uuid) FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.execution_result_by_digest(uuid,char) FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.execution_finalize_context(uuid,uuid,text,bigint,char,char) FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.execution_finalize_commit(uuid,uuid,text,bigint,char,char,char,jsonb,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION factory.execution_start(uuid,uuid,text,bigint,char,char,char,text,text,jsonb,jsonb)
  TO factory_runtime;
GRANT EXECUTE ON FUNCTION factory.execution_advance(uuid,uuid,text,bigint,char,char,text)
  TO factory_runtime;
GRANT EXECUTE ON FUNCTION factory.execution_propose(uuid,uuid,text,bigint,char,char,bigint,char,text,jsonb)
  TO factory_runtime;
GRANT EXECUTE ON FUNCTION factory.execution_proposal_context(uuid,uuid,text,bigint,char,char)
  TO factory_runtime;
GRANT EXECUTE ON FUNCTION factory.execution_result_for_run(uuid,uuid) TO factory_runtime;
GRANT EXECUTE ON FUNCTION factory.execution_result_by_digest(uuid,char) TO factory_runtime;
GRANT EXECUTE ON FUNCTION factory.execution_finalize_context(uuid,uuid,text,bigint,char,char) TO factory_runtime;
GRANT EXECUTE ON FUNCTION factory.execution_finalize_commit(uuid,uuid,text,bigint,char,char,char,jsonb,jsonb) TO factory_runtime;
