#!/usr/bin/env python3
"""Synthetic M7 durability proof on the exact bound disposable PostgreSQL only."""
from datetime import timedelta
import json
import os
import subprocess
import sys

from adaptive_factory import store
from adaptive_factory.shadow_lookup import M7LookupRequestV1, M7OutcomeObservationV1, M7BundleRegistrationV1
from factory.tests import test_shadow_lookup_postgres as fixtures
from factory.tests import test_postgres_integration as producer
from factory.tests.postgres_restart_probe import _restart_database
from factory.tests.test_shadow_evaluation import outcome_payload
from factory.tests.test_shadow_lookup import measurements


def child(payload):
    fixtures.assert_disposable()
    assert os.getpid() != payload["parent_pid"], "lookup must reopen in a new process"
    request = M7LookupRequestV1.from_dict(payload["request"])
    reader = store.PostgresM7LookupStore(payload["urls"]["reader"])
    result = reader.lookup(request)
    assert result.registration.bundle.digest == request.bundle_digest
    assert result.outcome.digest == payload["full_digest"]
    assert result.coverage["measurements"] == "complete"
    assert result.acceptance == "accepted" and result.signed_check == "invalid"
    assert result.currentness == "unavailable" and "epoch_expired" in result.unavailable_reasons
    assert result.m8_qualification == "not_evaluated" and result.authority_effect == "none"
    registry = store.PostgresM7RegistryStore(payload["urls"]["registry"],
        source_id="synthetic-registry", repository_id=request.repository_id)
    registration = M7BundleRegistrationV1.from_dict(payload["registration"])
    assert registry.register_bundle(registration, idempotency_key="register-restart") == registration
    observer = store.PostgresM7OutcomeObserverStore(payload["urls"]["outcome"],
        source_id="synthetic-human_outcome", repository_id=request.repository_id)
    partial = M7OutcomeObservationV1.from_dict(payload["partial"])
    assert observer.record_outcome(partial) == partial
    assert reader.lookup(request).outcome.digest == payload["full_digest"]
    import psycopg
    with psycopg.connect(fixtures.DATABASE_URL) as connection:
        for name, expected in payload["cardinalities"].items():
            assert name in fixtures.TABLES
            assert connection.execute("SELECT count(*) FROM factory." + name).fetchone()[0] == expected
    print("PASS: M7 new-process lookup, exact replay, stable record digests/cardinality, revoked/expired evidence")


def main():
    if sys.argv[1:] == ["--child"]:
        child(json.loads(sys.stdin.read(4194305)))
        return
    fixtures.assert_disposable()
    fixtures.M7LookupPostgresTests.setUpClass()
    fixture = fixtures.M7LookupPostgresTests("test_completed_bundle_registration_replays_after_active_lease_clears")
    try:
        fixture.setUp()
        registration, request = fixture.register_completed("restart")
        partial, check, _github, epoch = fixture.all_green(request)
        full = fixture.outcome(request,
            provenance=fixture.provenance("human_outcome", 2, partial.digest),
            outcome={**outcome_payload("synthetic-outcome-1"), "bundle_digest": request.bundle_digest},
            measurements=measurements(cost_usd_micros=100, latency_ms=100, repair_count=0,
                rollback_count=0, regression_count=0, intervention_count=0, intervention_coverage="complete",
                intervention_source_refs=["synthetic:session"],
                session_started_at=(fixture.now - timedelta(seconds=1)).isoformat(), session_ended_at=fixture.now.isoformat()))
        fixture.observer.record_outcome(full)
        fixture.context_store("signed_ci").record_check(fixture.check(request, result="revoked",
            provenance=fixture.provenance("signed_ci", 2, check.digest)))
        fixture.context_store("deployed_epoch").record_context(fixture.epoch(request,
            provenance={**fixture.provenance("deployed_epoch", 2, epoch.digest),
                        "valid_until": (fixture.now + timedelta(microseconds=1)).isoformat()}))
        import psycopg
        with psycopg.connect(fixtures.DATABASE_URL) as connection:
            cardinalities = {name: connection.execute("SELECT count(*) FROM factory." + name).fetchone()[0]
                             for name in fixtures.TABLES}
        owner, _, _ = _restart_database(os.environ["FACTORY_TEST_POSTGRES_CONTAINER"],
            os.environ["FACTORY_TEST_POSTGRES_CONTAINER_ID"], os.environ["FACTORY_TEST_POSTGRES_NONCE"],
            fixtures.DATABASE_URL, fixtures.DATABASE_URL, fixtures.DATABASE_URL)
        from psycopg.conninfo import conninfo_to_dict, make_conninfo
        port = int(conninfo_to_dict(owner)["port"])
        urls = {kind: make_conninfo(**{**conninfo_to_dict(value), "port": port}) for kind, value in fixture.urls.items()}
        fixtures.DATABASE_URL = owner
        producer.DATABASE_URL = owner
        environment = {**os.environ, "FACTORY_TEST_DATABASE_URL": owner}
        payload = {"parent_pid": os.getpid(), "request": request.to_dict(), "registration": registration.to_dict(),
                   "partial": partial.to_dict(), "full_digest": full.digest, "cardinalities": cardinalities, "urls": urls}
        subprocess.run([sys.executable, "-m", "factory.tests.m7_postgres_restart_probe", "--child"],
            input=json.dumps(payload), text=True, env=environment, check=True, timeout=30)
        fixtures.DATABASE_URL = owner
        producer.DATABASE_URL = owner
    finally:
        fixtures.M7LookupPostgresTests.tearDownClass()


if __name__ == "__main__":
    main()
