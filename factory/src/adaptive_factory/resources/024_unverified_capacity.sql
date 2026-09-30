-- F07: independent of paid-work leases. Terminal ACK/timeout never releases capacity.
-- Existing installations above the bounded backfill limit fail atomically for an
-- operator-planned bounded backfill; no records are silently skipped or deleted.
LOCK TABLE factory.execution_packets, factory.workspace_results,
  factory.semantic_verdicts IN SHARE ROW EXCLUSIVE MODE;
DO $$ BEGIN
  IF (SELECT count(*) FROM factory.execution_packets)>10000 THEN
    RAISE EXCEPTION 'unverified_backfill_requires_bounded_operator_plan';
  END IF;
END $$;

CREATE TABLE factory.unverified_limits (
  repository_id text NOT NULL CHECK (octet_length(repository_id) BETWEEN 1 AND 128),
  profile_digest char(64) NOT NULL CHECK (profile_digest ~ '^[0-9a-f]{64}$'),
  max_unverified_inflight integer NOT NULL DEFAULT 32 CHECK (max_unverified_inflight BETWEEN 1 AND 64),
  PRIMARY KEY (repository_id,profile_digest)
);
CREATE TABLE factory.unverified_slots (
  run_id uuid PRIMARY KEY REFERENCES factory.runs(run_id) ON DELETE RESTRICT,
  repository_id text NOT NULL,
  profile_digest char(64) NOT NULL,
  packet_digest char(64) NOT NULL,
  candidate_sha char(40),
  generated_at timestamptz,
  reserved_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  CHECK ((candidate_sha IS NULL)=(generated_at IS NULL)),
  CHECK (candidate_sha IS NULL OR candidate_sha ~ '^[0-9a-f]{40}$')
);
CREATE INDEX unverified_slots_scope ON factory.unverified_slots(repository_id,profile_digest,run_id);
CREATE TABLE factory.unverified_resolutions (
  run_id uuid PRIMARY KEY REFERENCES factory.unverified_slots(run_id) ON DELETE RESTRICT,
  disposition text NOT NULL CHECK (disposition IN ('verified','quarantined','expired')),
  evidence_digest char(64) NOT NULL CHECK (evidence_digest ~ '^[0-9a-f]{64}$'),
  resolved_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TRIGGER unverified_resolutions_immutable BEFORE UPDATE OR DELETE
  ON factory.unverified_resolutions FOR EACH ROW EXECUTE FUNCTION factory.semantic_reject_mutation();

CREATE FUNCTION factory.unverified_admit() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE v_profile char(64); v_limit integer;
BEGIN
  IF NEW.body->>'role'<>'writer' THEN RETURN NEW; END IF;
  v_profile=factory.execution_contract_hash('adaptive-factory.provider-profile/v1',NEW.body->'provider');
  PERFORM pg_advisory_xact_lock(hashtextextended('unverified:' || (NEW.body->>'repository_id') || ':' || v_profile,0));
  -- BEFORE INSERT runs even for the canonical function's ON CONFLICT replay.
  IF EXISTS(SELECT 1 FROM factory.unverified_slots WHERE run_id=NEW.run_id
      AND packet_digest=NEW.packet_digest AND profile_digest=v_profile
      AND repository_id=NEW.body->>'repository_id') THEN RETURN NEW; END IF;
  SELECT max_unverified_inflight INTO v_limit FROM factory.unverified_limits
    WHERE repository_id=NEW.body->>'repository_id' AND profile_digest=v_profile;
  v_limit=COALESCE(v_limit,32);
  IF (SELECT count(*) FROM factory.unverified_slots s
      WHERE s.repository_id=NEW.body->>'repository_id' AND s.profile_digest=v_profile
      AND NOT EXISTS (SELECT 1 FROM factory.unverified_resolutions r WHERE r.run_id=s.run_id))>=v_limit THEN
    RAISE EXCEPTION 'unverified_capacity_exhausted' USING ERRCODE='P0001';
  END IF;
  INSERT INTO factory.unverified_slots(run_id,repository_id,profile_digest,packet_digest)
    VALUES(NEW.run_id,NEW.body->>'repository_id',v_profile,NEW.packet_digest);
  RETURN NEW;
END $$;
CREATE TRIGGER unverified_admission BEFORE INSERT ON factory.execution_packets
  FOR EACH ROW EXECUTE FUNCTION factory.unverified_admit();

CREATE FUNCTION factory.unverified_generated() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
BEGIN
  UPDATE factory.unverified_slots SET candidate_sha=NEW.exact_head_sha,generated_at=NEW.created_at
    WHERE run_id=NEW.run_id AND candidate_sha IS NULL;
  RETURN NEW;
END $$;
CREATE TRIGGER unverified_generated AFTER INSERT ON factory.workspace_results
  FOR EACH ROW EXECUTE FUNCTION factory.unverified_generated();

CREATE FUNCTION factory.unverified_verified() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
BEGIN
  IF NEW.body->>'decision'='pass' THEN
    INSERT INTO factory.unverified_resolutions(run_id,disposition,evidence_digest)
      SELECT s.run_id,'verified',NEW.verdict_digest FROM factory.unverified_slots s
      JOIN factory.semantic_subjects subject ON subject.run_id=s.run_id
      WHERE subject.subject_digest=NEW.subject_digest AND subject.exact_head_sha=s.candidate_sha
      ON CONFLICT(run_id) DO NOTHING;
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER unverified_verified AFTER INSERT ON factory.semantic_verdicts
  FOR EACH ROW EXECUTE FUNCTION factory.unverified_verified();

-- Owner-only recovery: an immutable receipt names confirmed stop/quarantine or
-- confirmed stop/expiry. Runtime and workers cannot create/rewrite these receipts.
CREATE FUNCTION factory.unverified_resolve(p_run uuid,p_disposition text,p_evidence char(64)) RETURNS boolean
LANGUAGE plpgsql SET search_path=pg_catalog,factory AS $$
BEGIN
  IF p_disposition NOT IN ('quarantined','expired') OR p_evidence !~ '^[0-9a-f]{64}$' THEN
    RETURN false;
  END IF;
  PERFORM 1 FROM factory.unverified_slots WHERE run_id=p_run;
  IF NOT FOUND THEN RETURN false; END IF;
  IF EXISTS(SELECT 1 FROM factory.unverified_resolutions WHERE run_id=p_run) THEN
    RETURN EXISTS(SELECT 1 FROM factory.unverified_resolutions WHERE run_id=p_run
      AND disposition=p_disposition AND evidence_digest=p_evidence);
  END IF;
  INSERT INTO factory.unverified_resolutions(run_id,disposition,evidence_digest)
    VALUES(p_run,p_disposition,p_evidence);
  RETURN true;
END $$;

INSERT INTO factory.unverified_slots(run_id,repository_id,profile_digest,packet_digest,candidate_sha,generated_at,reserved_at)
  SELECT p.run_id,p.body->>'repository_id',
    factory.execution_contract_hash('adaptive-factory.provider-profile/v1',p.body->'provider'),
    p.packet_digest,w.exact_head_sha,w.created_at,p.created_at
  FROM factory.execution_packets p LEFT JOIN factory.workspace_results w ON w.run_id=p.run_id
  WHERE p.body->>'role'='writer';
INSERT INTO factory.unverified_resolutions(run_id,disposition,evidence_digest)
  SELECT s.run_id,'verified',v.verdict_digest FROM factory.unverified_slots s
  JOIN factory.semantic_subjects subject ON subject.run_id=s.run_id AND subject.exact_head_sha=s.candidate_sha
  JOIN factory.semantic_verdicts v ON v.subject_digest=subject.subject_digest
  WHERE v.body->>'decision'='pass';

REVOKE ALL ON factory.unverified_limits, factory.unverified_slots, factory.unverified_resolutions FROM PUBLIC;
GRANT SELECT ON factory.unverified_limits, factory.unverified_slots, factory.unverified_resolutions TO factory_runtime;
REVOKE ALL ON FUNCTION factory.unverified_admit(),factory.unverified_generated(),factory.unverified_verified(),
  factory.unverified_resolve(uuid,text,char) FROM PUBLIC;
