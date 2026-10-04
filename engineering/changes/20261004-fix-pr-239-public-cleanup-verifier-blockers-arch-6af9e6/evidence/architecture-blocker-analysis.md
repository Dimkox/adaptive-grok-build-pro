# Architecture blocker analysis

Independent architect analysis, not verification completion or merge authority.

At HEAD `7da46ca2d4ab2e30e7e2a2a19ee4cf53915095b6`, exact changed-source AST inspection found one syntax error among 20 nondeleted Python files. Public-path redaction broke the executable literal in the historical `split-c-source-audit.py`. The writer restored the portable `ruff` executable, retained the historical-only notice, and added a parse/command regression. Existing policy did not need changing.

After that repair, the bounded architecture check at HEAD `691ae2dfa39e4fe554c68fdbba4a698d12252077` reported one remaining category: `background_job`, status `unsupported`, reason `queue_provenance_unresolved`, path `tests/test_change_receipts.py`. Drift and generated diagrams had already passed separately; those older checks are historical component evidence only.

The architect isolated the changed-source queue provenance traversal without rerunning complete fitness. Exact base `97a7581238022356b2de8d193a9bd8363fc92dc3` and head `691ae2dfa39e4fe554c68fdbba4a698d12252077` both reached the existing import cycle `change -> package_status -> receipts -> state -> agent_lifecycle -> policy -> _policy_legacy -> human_gates -> state`. The repeated active module closes a cycle at depth eight; it does not expand to a ninth module. `_local_queue_resolution` nevertheless checked the depth limit before recognizing that cycle.

An in-memory diagnostic that only reordered the existing cycle/depth checks produced no adapter names, queue signals or uncertainty for either exact receipt-test source. It did not edit the candidate or supply approval. The selected repair keeps the depth, module, AST and work budgets unchanged, keeps queue-bearing cycles unsupported, and tests genuine ninth-module rejection. Removing the receipt test or weakening architecture policy was rejected.

During earlier diagnostic retries, the held Git registration directory changed and correctly invalidated the binding. The diagnostic printed the differing metadata before raising; it never suppressed the error. Read-only coordination now uses `GIT_OPTIONAL_LOCKS=0`, with no concurrent Git mutation during verification. This scheduling fix does not change the binding guard.
