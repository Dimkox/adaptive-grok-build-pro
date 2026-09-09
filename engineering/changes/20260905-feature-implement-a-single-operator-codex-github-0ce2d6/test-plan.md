# Test plan — finite pilot evidence

## Focused implementation checks

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Issue/model data cannot widen trusted profile or grant | `pilot/tests/test_coordinator.py`, `test_authority.py` |
| P0 | One Codex start, sandbox denial, private exact clone and trusted seal | `test_codex_executor.py`, `test_workspace.py` |
| P0 | Restart never duplicates Codex/push/PR; ambiguous effects observe only | `test_recovery.py`, `test_github.py`, `test_live.py` |
| P0 | Tests and semantics bind unchanged exact candidate | `test_validation.py` |
| P0 | App-server accepts one exact confined turn and rejects requests, wrong IDs, failures, EOF and timeout | `test_app_server_codex.py` |
| P0 | Current-control grants, exact GitHub argv and distinct branch/proposal authority fail closed | `test_runtime_authority.py`, `test_live_github.py`, `test_github.py` |
| P0 | Merge/close/deploy and fake Trust CI/human outcomes are impossible | `test_coordinator.py`, `test_github.py` |
| P1 | Closed contracts, canonical digests, schema and store replay | `test_contracts.py`, `test_store.py` |
| P1 | CLI default-off, direct composition dispatch, private recovery and one deterministic phased E2E | `test_cli.py`, `test_workspace.py`, `test_live.py` |

Run only affected focused tests during implementation. The configured target command is exactly one `python -m unittest discover -s tests -v` invocation inside the sealed landing candidate; semantic checks then run against the unchanged tree.

## Final boundary

Commit final source/docs/state as parent `R`, build matching ZIP+sidecar bytes from two private exact-`R` clones, and import only that pair as artifact child `A`. Run one detached `python3 scripts/grok_verify.py --mode pr` on exact `A`; only after PASS dispatch the route-selected code, test and security reviewers in parallel and record receipts against unchanged `A`. Keep reports in ignored runtime evidence so review Markdown does not trigger another package/verifier/review cycle. Only a repaired core source failure invalidates affected evidence.

The live pilot is one separately authorized observation/invocation/publication attempt, not part of repeated local tests. It stops on the first terminal result.
