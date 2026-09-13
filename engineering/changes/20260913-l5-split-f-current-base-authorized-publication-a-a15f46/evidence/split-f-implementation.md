# F sole-writer handoff

Selected writer data_implementer; route5bc0f4cdffc5; worktree /home/pall/grok-projects/adaptive-grok-build-pro-l5-split-f; genuine predecessor E356c7f991ee6835506255e823c06124068fc4e0e. Frozen source f31406e970d67f7cd59694da5de88915adb0fa68 was read only. Product/test writes are complete and frozen for parent-owned commit, full verification and the five selected independent reviews.

## Exact extraction

Eleven product/test/config paths are bound to SHA256, Git blob and executable mode in split-f-source-sha256.json. Six files match the frozen reference byte-for-byte: filesystem adapter, publication request/bundle contracts, request v1 JSON schema, Factory CLI, repository governance wrapper, and Factory tests bootstrap. The remaining five are staged architecture model/rule/inventory, the explicitly strengthened Factory publication tests, and the bounded publication-store validation correction detailed below.

The three production publication components and both halves of the authorization bridge are now available together. The Factory CLI requires a callable authority before apply reads configuration/state. The wrapper supplies exact remote/repository/route/change/current HEAD/fingerprint/action/resource/unique-grant/expiry validation. Actual authorization follows loading the persisted request and observation/artifact validation, and precedes the inflight transition and filesystem effect. Observation-only bookkeeping remains allowed without a grant; no stronger zero-local-state-access claim is made.

Architecture adds only landing_publication_cli to the offline source owner/rule/inventory, and request v1 schema to NODE-STAGED-DELIVERY-SOURCE. Production inventory is21 modules. No backup module, future script, factory console entrypoint or boundary/budget relaxation was introduced. All previous C/D/E product bytes remain identical to E, including the independent reader/runtime lifecycle tests, D's repaired SQLite writer cleanup, v1/v2 schemas and E host files. The manifest audit compares every pre-existing product-root file, not just named protected examples.

## Reproduced schema gap and disclosed correction

The frozen PublicationStore accepted matching column names while omitting required request-ID uniqueness or primary-key semantics, using incorrect types/nullability/defaults/STRICT/rowid flags or extra triggers/views/indexes. Thirteen temporary schema variants are now checked in writer and readonly modes. The initial twelve variants produced22 failing subcases on frozen code; the pre-existing extra-table check already rejected its two subcases. Supported-schema reopen/idempotency and wrong-application/version cases also ran as positive/negative controls.

The initial repair reused SQLite inventory's LIKE sqlite_% pattern. An additional targeted trigger named sqliteXpublication exposed that underscore is a LIKE wildcard: two readonly/writer subcases still accepted an unexpected trigger. Those cases were recorded RED, then inventory filtering changed to GLOB sqlite_* so underscore is literal. This is within the same explicit schema-object validation requirement.

The production change is limited to delivery/src/adaptive_delivery/landing_publication.py: _COLUMNS and _validate_schema replace name-only checking. Validation checks the exact supported regular STRICT table and rowid flag; ordered typed columns, nullability, defaults, primary-key position and hidden-column absence; no foreign keys or unexpected non-internal schema objects; and exactly the expected unique BINARY ascending primary/request-ID indexes without partial predicates. Index names from the database are bound as pragma_index_xinfo parameters, never interpolated into SQL.

The schema creation SQL, application ID0x4C355055, user version1 and all coordinator/prepare/transition/reconciliation methods remain byte/AST-identical to frozen. Supported existing databases are not migrated. Unsupported lookalikes fail with publication_state_schema. Exact production deviation patch: split-f-publication-frozen-deviation.patch. Preserve this change through G and in final comparison with f31406e.

## Additional independent behavior evidence

The extended existing test_landing_publication_cli.py preserves all eleven frozen test bodies, adding only the readonly no-lock assertion and six focused regression methods in the existing/new schema test classes. It exercises:

- Expected schema initialization/reopen, idempotent same request, conflict on reused request ID with changed baseline, and wrong application/version rejection without identity mutation.
- All thirteen altered-schema cases in writable and readonly modes, including constraints, flags, indexes, triggers, views, extra table and the internal-prefix lookalike.
- Actual stage and activation effects followed by injected KeyboardInterrupt, retained inflight state, real store close/reopen, and fresh coordinator apply that observes success while stage/activate/authority callbacks forbid replay.
- Real temporary publication activation and restore to an empty baseline, requiring exact restore action authority and an activated predecessor; stage lineage and stale activation fail closed.
- Two separately sealed artifacts, activation of the second over the first, rejection of the wrong previous lineage, then an authorized restore of the actual prior release while the second immutable release remains present.

These tests operate only within owned temporary fixture directories with synthetic grant callbacks. They do not issue actual grants, read an approval or credential file, contact an origin/provider, or mutate deployed state. Successful local operations still report http_origin_verified=false.

## Verification

- Extraction-first RED: expected missing delivery landing_filesystem module against E before source extraction; split-f-extraction-red.out (one collection error).
- Frozen schema RED:22 failing subcases,3 parent methods passed and10 subcases passed; split-f-schema-red.out. This was a failed run; the unittest parent pass count does not erase subtest failures.
- Initial schema repair GREEN:3 tests+32 subtests, split-f-schema-green.out. The later internal-prefix mutation then reproduced two failing subcases, split-f-schema-prefix-red.out, before its GLOB fix.
- Final Factory publication suite: **17 tests+68 subtests passed in7.94s**, split-f-factory-focused-final28.out. Earlier bounded runs are retained rather than relabeled.
- Full existing Delivery suite separately: **88 tests+116 subtests passed in10.00s**, split-f-delivery-full-final28.out. This suite completed before only the final schema-prefix predicate/test change, which was then covered by the complete Factory publication rerun. An initial Delivery command omitted factory/src from PYTHONPATH and produced five collection errors; split-f-delivery-full28.out preserves that non-evidence attempt. No test/package files were changed to work around it.
- Root architecture/model/mandatory inventory suite: **172 tests+616 subtests passed in68.27s**, split-f-architecture-green28.out. Architecture files remained unchanged afterward.
- Actual genuine-base final fitness: **PASS**, split-f-fitness-final.json. Code budgets, separation, forbidden edges, module/import/secret/tenant/workspace checks all pass; unrelated migration/contract/network checks remain not_applicable.
- Ruff on all8 changed Python files passes, split-f-ruff-final.out. Architecture diagrams --check passes without generating changes, split-f-diagrams.json. git diff --check passes.

Focused suite environment: PYTHONPATH=.:factory/src:delivery/src:.grok-stack, PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 and PYTHONDONTWRITEBYTECODE=1. The Factory file, Delivery directory and root architecture files were collected in separate processes to preserve their test-package boundaries. Each used:

```
taskset -c 0-27 /tmp/agbp-venv/bin/python -m pytest -c /dev/null -p xdist.plugin -p no:cacheprovider --rootdir=. --import-mode=prepend -q -n28 --dist=loadfile --max-worker-restart=0 <selected paths>
/tmp/agbp-venv/bin/python scripts/grok_architecture.py fitness --base 356c7f991ee6835506255e823c06124068fc4e0e --worktree --pre-risk red --json
```

Full mandatory verifier and independent reviews remain parent-owned pending work. No full-route, coverage-percentage or external Trust CI success is claimed here.

## Recovery and handoff

Rollback to E requires stopping the publication writer while preserving intent SQLite/WAL and immutable releases. Removing F code does not restore current; restore remains a separately prepared exact authorized operation. Preserve ambiguous intents and partial releases for observation rather than retrying filesystem effects. G must retain owned_lock/private_root, .intent-writer.lock, application identity and the new schema validator; publication snapshots do not include or restore the published target tree.

Suggested shared-memory fact for decisions.md (root-owned): Publication schema validation must cover constraints and object inventory, since matching names do not preserve idempotency. Temporary weakened schemas and a committed-effect restart test established fail-closed readers and observation-only recovery without altering schema version or replaying effects.

Suggested mistakes.md fact (root-owned): Reusing LIKE sqlite_% accidentally treated underscore as a wildcard and ignored sqliteXpublication; a negative trigger fixture exposed it and GLOB restored the literal prefix. A separate Delivery test command omitted its existing Factory dependency path and failed collection; use all existing source roots even when collecting one test package. The first ownership edit guessed NODE-STAGED-DELIVERY rather than inspecting NODE-STAGED-DELIVERY-SOURCE, so the missing schema-owner entry was corrected before fitness and the final manifest.
