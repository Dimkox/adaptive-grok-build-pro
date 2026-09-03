# Implementation report — local candidate

## Result

The local candidate implements the bounded GET-only External Observer, closed config/evidence/status contracts, typed historical M0-M9 claims, exact configured PR/check/App validation, bounded tag/compare proof, coherent opening/closing rereads, independent truth axes, deterministic JSON/text, persisted fail-closed ignored runtime state, CLI, installer inventory, runbook, and K17 complete README graph.

This report deliberately contains no final implementation SHA or external-delivery claim. Parent verification and independent route reviews remain pending; anonymous GitHub quota can legitimately produce `UNAVAILABLE`/`STALE`, and attestation remains `ATTESTATION_UNOBSERVABLE`.

## TDD evidence

- RED: `python3 -m unittest tests.test_external_observer -v` exited 1 because `adaptive_grok.external_observer` did not exist.
- GREEN: see the final exact targeted command in `implementation-ledger.md`.
- Tests use injected fake transports only; no live GitHub request, credential, push, PR mutation, merge, release, deployment, Factory or Trust CI mutation occurred.
