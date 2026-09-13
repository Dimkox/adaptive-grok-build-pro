# Code review — 4e71afa (post-landing hardening #60/#61/#63)

**PASS** — no byte-level, security or API defect: all three sealed epochs return exactly the
pre-change tuples, the guard is an identity function that can only raise, import ordering is sound.
Fix in this same PR: restore the duplicate-detection this commit dropped (§4, one line) and keep one
independently written forbidden set in tests (§3). Neither alters sealed bytes.

## 1. Epoch behavior preserved (verified, not just read)
Loaded the `eb9df64` blob of `landing_artifact.py` beside the new module: all three epochs equal, same
order, same type (20/19/22); unknown epoch still raises `LandingArtifactError('source_identity')`;
`_approved_deploy_members(t) is t` → True, so no reorder/dedup/normalize/copy is possible. `seal()`
never calls the resolver — it uses the raw `DEPLOY_MEMBERS` constant for `contents`,
`member_records`, `member_count` and `member_names` — so the guard cannot reach sealed output.

## 2. Error contract and placement — acceptable
`prohibited_deploy_member:<names>` is the only colon-delimited message here (others are bare tokens,
`source_identity`, `{name}_inventory`), but nothing keys off message text: no `str(exc) ==` or
`args[0] ==` in `factory/src`/`factory/tests`, and handlers catch by type and re-wrap with fixed
literals (`store_record`, `artifact_integrity`), so a variable message cannot leak into sealed,
attested or HTTP code fields. Self-check at line 120 sits after `class LandingArtifactError` (117),
so the forward reference resolves; module imports clean. The single `DEPLOY_MEMBERS` self-check
transitively covers epochs 1–2 because `_PRIOR_DEPLOY_MEMBERS` is its subset. Accepted side effect:
a prohibited name now crashes import of every consumer rather than one operation — intended
fail-closed.

## 3. #61 — two of three tests are tautological (fix)
`PROHIBITED_MEMBERS = PROHIBITED_DEPLOY_MEMBERS` turned the pre-existing assertion at
`test_landing_artifact.py:82` from an independent oracle into production-vs-production: it can never
fail, because the import self-check raises first.
`test_every_epoch_inventory_is_disjoint_from_production_prohibited_set` is the same tautology (all
inputs derive from one constant in one file). Only
`test_epoch_resolution_fails_closed_on_a_prohibited_member` has real power (injects a poisoned
`DEPLOY_MEMBERS`; fails if the wrapper is removed), but the patch does not reach
`_PRIOR_DEPLOY_MEMBERS`, so epochs 1–2 are untested. Restore a literal forbidden set asserted `==`
against production and cover epochs 1–2. Also: the guard gates retention only
(`landing_artifact_retention.py:223` → store `:705`), so a poisoned `DEPLOY_MEMBERS` would still be
packaged and rejected later — have `seal()` select members through the resolver.

## 4. #60 — partly tautological, one lost guarantee (fix)
`contract_inventory` (`architecture.py:639-648`) builds records by iterating
`snapshot.system["contracts"]` — the same list both set assertions compare against. So id-set
equality is true by construction (catches only a non-string id via `str()`) and path-set equality
only catches path *rewriting*. Catches: truncation to ≤40 (floor); missing/malformed declared
contract file (loader raises → test errors); leftover undeclared contract file
(`validate_repository_drift`, line 1319). Cannot catch a 1-for-1 retire+add whose file is deleted —
but the old `len==41` could not either, so no regression. **Regressed by this commit:** sets collapse
duplicates, so a repeated entry in `architecture/system.yaml` now passes (old failed at 42 records)
while corrupting `contract_inventory_digest`. Restore with
`self.assertEqual(len(records), len(declared_ids))`. Live inventory is 41 records / 41 unique ids /
41 unique paths — zero slack over the floor today.

## 5. #63 — real child executes, but the substantive half skips
`extract_pdf_text` does not short-circuit the parser check parent-side, so `pdf_parser_unavailable`
proves the shipped worker body ran (rlimits, import attempt, strict JSON). But `pypdf` is absent here
(`PackageNotFoundError`, no `.venv`), so 4 of 7 tests — all of `PdfWorkerWithPinnedParser` — skip;
nothing fails if the pin stops resolving, so this coverage is silently absent from the default gate.
Run the file under `uv run` in verification or assert `_pypdf_pinned()` in the gated env. Nits:
`CURRENT_EPOCH_SHA` (line 18) is dead; the `..._before_any_spawn` names do not assert no-spawn.

**Verification** (read-only; scratch in /tmp; only this report written): `test_landing_artifact` 9 OK
(both new guard tests ran); `test_landing_pdf_worker` 7 OK / 4 skipped;
`tests.test_architecture_model` 67 OK; `ruff check` on the four changed files clean.
