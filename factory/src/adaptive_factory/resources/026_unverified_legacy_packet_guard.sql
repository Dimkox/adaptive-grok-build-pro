-- Forward repair: preserve migration024 bytes and historical minimal packets.
CREATE OR REPLACE FUNCTION factory.unverified_admit() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
DECLARE v_profile char(64); v_limit integer;
BEGIN
  IF (NEW.body->>'role') IS DISTINCT FROM 'writer' THEN RETURN NEW; END IF;
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
