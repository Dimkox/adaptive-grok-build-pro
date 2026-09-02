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
    (current_stage='prepared' AND p_stage IN ('running','failed','needs_human','cancelled')) OR
    (current_stage='running' AND p_stage IN ('collecting','failed','needs_human','cancelled')) OR
    (current_stage='collecting' AND p_stage IN ('completed','failed','needs_human','cancelled'))
  ) THEN RETURN false; END IF;

  SELECT COALESCE(max(stage_sequence),0)+1 INTO next_sequence
    FROM factory.execution_stage_events WHERE manifest_digest=manifest;
  UPDATE factory.execution_manifests SET stage=p_stage,updated_at=clock_timestamp(),
    terminal_at=CASE WHEN p_stage IN ('completed','failed','needs_human','cancelled')
      THEN clock_timestamp() ELSE NULL END
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
  existing_kind text;
  existing_body jsonb;
BEGIN
  IF octet_length(p_body::text)>65536 THEN RETURN false; END IF;
  PERFORM 1 FROM factory.tasks t
    JOIN factory.runs r ON r.run_id=t.current_run_id AND r.task_id=t.task_id
    JOIN factory.capacity_allocations a ON a.run_id=r.run_id AND a.task_id=t.task_id
    JOIN factory.execution_manifests m ON m.run_id=r.run_id AND m.packet_digest=p_packet_digest
    WHERE t.task_id=p_task_id AND r.run_id=p_run_id AND r.owner_id=p_owner
      AND r.fence=p_fence AND r.packet_digest=p_legacy_packet_digest
      AND t.current_fence=p_fence AND r.released_at IS NULL AND a.released_at IS NULL
      AND m.terminal_at IS NULL AND r.lease_expires_at>clock_timestamp()
    FOR UPDATE OF t,r,m;
  IF NOT FOUND THEN RETURN false; END IF;
  SELECT proposal_kind,body INTO existing_kind,existing_body
    FROM factory.execution_proposals
    WHERE run_id=p_run_id AND (producer_sequence=p_sequence OR idempotency_key=p_idempotency_key)
    FOR UPDATE;
  IF FOUND THEN
    RETURN existing_kind=p_kind AND existing_body=p_body;
  END IF;
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

REVOKE ALL ON factory.execution_packets,factory.execution_manifests,
  factory.execution_stage_events,factory.execution_proposals FROM PUBLIC,factory_runtime;
REVOKE ALL ON FUNCTION factory.execution_start(uuid,uuid,text,bigint,char,char,char,text,text,jsonb,jsonb)
  FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.execution_advance(uuid,uuid,text,bigint,char,char,text)
  FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.execution_propose(uuid,uuid,text,bigint,char,char,bigint,char,text,jsonb)
  FROM PUBLIC;
REVOKE ALL ON FUNCTION factory.execution_proposal_context(uuid,uuid,text,bigint,char,char)
  FROM PUBLIC;
GRANT EXECUTE ON FUNCTION factory.execution_start(uuid,uuid,text,bigint,char,char,char,text,text,jsonb,jsonb)
  TO factory_runtime;
GRANT EXECUTE ON FUNCTION factory.execution_advance(uuid,uuid,text,bigint,char,char,text)
  TO factory_runtime;
GRANT EXECUTE ON FUNCTION factory.execution_propose(uuid,uuid,text,bigint,char,char,bigint,char,text,jsonb)
  TO factory_runtime;
GRANT EXECUTE ON FUNCTION factory.execution_proposal_context(uuid,uuid,text,bigint,char,char)
  TO factory_runtime;
