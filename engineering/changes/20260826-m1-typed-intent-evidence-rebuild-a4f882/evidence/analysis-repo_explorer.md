# Repository exploration — M1 rebuild

## Baseline

- Worktree: `/home/pall/grok-projects/adaptive-grok-build-pro-m1`; HEAD remains `0a4dd0a` (`docs: plan M1 typed intent and evidence`), with route base `069fe82`.
- Active route is `a4f88266a848`, high risk/security, write owner `general_implementer`, and required reviews `code_reviewer`, `test_reviewer`, `security_reviewer`, and `release_reviewer`.
- The worktree has unrelated modified `decisions.md`/`mistakes.md`; no application implementation changes are present. The active package contains the standard Markdown files plus a placeholder `change-spec.yaml`; its current `risk.tier`, `objective.statement`, and `rollback.strategy` are still template placeholders.
- The six-task source of truth is `docs/superpowers/plans/2026-08-26-m1-typed-intent-evidence.md`, constrained by `docs/superpowers/specs/2026-08-26-m1-typed-intent-evidence-design.md`.

## Existing implementation and exact interfaces

Task 1's nominal files already exist in the baseline, as a prior partial prototype:

- `schemas/change-spec.schema.json`: Draft-2020-12 metadata, strict object boundaries, `$defs` for `OBJ`, `AC`, `INV`, `FORBID`, and a generic `{kind, ref}` evidence object. It lacks `SIG-*` and production-signal modeling; evidence kinds are `test`, `receipt`, `review`, `holdout`, and `command`.
- `.grok-stack/adaptive_grok/spec.py`: custom stdlib YAML-subset parser/dumper (`parse_yaml_subset`, `dump_yaml_subset`), `$defs`/schema recursion (`validate_schema`), `load_spec`, `generate_spec`, `summarize_spec`, `map_evidence`, and `canonical_digest`.
- Current `validate_spec(spec, schema=None, *, schema_only=False)` returns a result dict or raises `SpecError`; it is not the planned path-based `validate_spec(root, path, *, gate, route, changed) -> list[str]`. Current completeness rejects every `UNKNOWN`, including generated drafts, and has no route-aware docs-only exemption, production-signal resolution, or coverage object.
- `scripts/grok_spec.py` currently exposes `validate`, `generate`, `summarize`, and `map`; it does not expose the planned `summary`, `coverage`, `--gate`, or deterministic `--json` contract. The CLI loads the schema through `spec.py`'s repository-root-relative `SCHEMA_PATH`.
- `tests/test_change_spec.py` has 14 passing prototype tests. They assert the old API/model and will need additive or carefully compatibility-preserving updates for the six-task contract.

Existing downstream surfaces that M1 must extend:

- `.grok-stack/adaptive_grok/change.py:start_change()` copies `.grok-stack/templates/change/` and substitutes legacy placeholders (`CHANGE_ID`, `TITLE`, `TASK`, `CREATED_AT`, `RISK`, `COMPLEXITY`, `DOMAINS`). It does not substitute typed `OBJECTIVE_STATEMENT`, `RISK_TIER`, or `ROLLBACK_STRATEGY` and does not map route risk (`low/medium/high`) to typed tiers (`green/yellow/red`).
- `.grok-stack/templates/change/change-spec.yaml` is legacy YAML with placeholders and empty collections. `brief.md`, `requirements.md`, and `architecture.md` have no typed-authority notice.
- `.grok-stack/adaptive_grok/receipts.py:write_receipt(root, kind, status, report=None, details=None)` stores route/tree identity but no `criterion_ids`, `spec_digest`, or `spec_fingerprint`; `validate_evidence()` only checks receipt status and current tree fingerprint.
- `.grok-stack/adaptive_grok/verification.py:verify()` runs local checks and writes a generic verification receipt. It has no spec check/report section, coverage binding, draft-vs-gate mode, or missing-spec exemption logic.
- `trust-ci/holdout.example/validate.py` is the only holdout validator; `trust-ci/holdout.example/change_spec_validate.py` is absent. `trust-ci/src/adaptive_trust_ci/models.py:AttestationPayload` has no spec metadata fields, and `trust-ci/src/adaptive_trust_ci/runner.py:JobRunner.process()` signs command results/changed files/approval scopes but does not calculate typed-spec metadata.

The active package's own spec is not yet valid: it uses placeholders, has no criteria/evidence, and has no approval scopes. Task 6 must replace it with a complete yellow-risk, gate-valid spec and evidence mappings.

## Compatibility constraints

- New specs must be canonical JSON text in `.yaml`; do not add PyYAML, jsonschema, a root dependency manifest, or a new root package marker. Historical unchanged specs must not be mass-migrated.
- Preserve the old helper behavior where existing tests/callers depend on it, or provide a compatibility adapter while introducing the planned path-based interface. Existing callers include `scripts/grok_spec.py` and `tests/test_change_spec.py`.
- Schema and executable validator must support exactly the checked-in keyword subset and reject unknown schema keywords. Errors must be path-qualified and fail closed for malformed/untrusted input.
- Gate semantics differ from draft semantics: only objective metric/target may be `UNKNOWN` in drafts; standard/high-risk gates require known metric/target, at least one criterion, evidence on every criterion, resolvable production signals, and red-risk forbidden outcomes plus approval scopes.
- Trust CI cannot import PR-controlled `.grok-stack` code. Its holdout and attestation extraction must use stdlib/data-only parsing and deterministic sorted paths/digests.
- M1 changes touch control-plane-adjacent paths (`.grok-stack`, `scripts`, `trust-ci/holdout.example`, `trust-ci/src`), so the active high-risk route's security/release reviews and exact external Trust CI gate remain required.

## Installer and package impact

- `scripts/install_into.py` copies only `MANAGED_DIRS = ('.grok', '.agents', '.grok-stack')`, listed `scripts/*`/root hook/config files, and creates engineering directories. It does **not** copy root `schemas/` or `engineering/changes` contents. A consumer installed from the stack therefore receives `spec.py`/`grok_spec.py` but not `schemas/change-spec.schema.json`; the repository-root-relative schema lookup will fail unless M1 explicitly fixes distribution or makes schema resolution self-contained.
- `tests/_support.py:project_copy()` also copies `.grok`, `.agents`, `.grok-stack`, and a few root configs but not `schemas/`; current CLI tests patch `ROOT`/`find_root` while `spec.py` still resolves its schema from the source checkout, so they do not exercise an installed consumer's schema availability.
- `.grok-stack/adaptive_grok/manifest.py` and `scripts/package_stack.py` include root `schemas/change-spec.schema.json` in archives because they package nearly all non-excluded root files. This helps full product archives but does not repair `install_into.py`'s target copy behavior.
- `tests/test_installer.py` and `tests/test_manifest_package.py` cover managed-copy conflict behavior, no GitHub Actions, deterministic archives, and exclusions, but have no assertion for schema installation or `grok_spec.py` operation in a target without the source checkout.

## Task-by-task file delta

1. Task 1: revise `schemas/change-spec.schema.json`, `.grok-stack/adaptive_grok/spec.py`, and `tests/test_change_spec.py`; add strict IDs/evidence/signals, draft/gate validation, coverage, digest, and fingerprint while preserving compatibility.
2. Task 2: modify `change.py`, typed template, and three Markdown templates; add route risk/domain/objective generation and authority notices. Generation must remain lossless and leave only metric/target as `UNKNOWN`.
3. Task 3: modify `scripts/grok_spec.py`, `receipts.py`, `verification.py`, the focused spec tests, and receipt/verification tests. Add CLI JSON contracts, criterion-bound receipts, spec-aware staleness, and verification report `spec` data.
4. Task 4: add `trust-ci/holdout.example/change_spec_validate.py`, wire it into `validate.py`, and extend Trust CI holdout tests. It must not import `adaptive_grok.spec`.
5. Task 5: modify `trust-ci/src/adaptive_trust_ci/models.py`, `runner.py`, and runner/signing tests. Add optional backward-compatible `spec_digest` and normalized criterion coverage, computed from changed spec bytes/data only.
6. Task 6: complete the active M1 package, validate its spec, run both test trees/compileall/repository verification, then update roadmap evidence only after green evidence. Do not implement M2+ architecture/governance/factory work.

## Baseline verification evidence

The focused baseline command `python3 -m unittest tests.test_change_spec tests.test_change_receipts tests.test_installer tests.test_manifest_package -v` passed all 47 tests. These are prototype/current-behavior tests; they do not prove the planned M1 interfaces or external holdout/attestation behavior.
