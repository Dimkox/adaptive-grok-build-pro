# M2-A final code review

## Verdict: BLOCKED

Reviewed the exact range from adoption base `25bfbe59ea188d9687b20a9caad19e7db3d031f8` (tree `b6bb74f00fba7fd194ac1da01a00cca7aea89bf5`) to head `b995fae3f1c519355bd5b966c4f43249c559cb1e` (tree `1c829a4bee1180d5619509e1131162f946a283bd`) against the frozen M2-A design, implementation plan, typed change specification, packaged diff, and relevant surrounding source/tests.

The exact-state/base/bootstrap/receipt flow, fitness coverage, risk monotonicity, installer ownership, contract separation, and documentation scope are otherwise coherent, but two Important bounded-input defects violate AC-001/AC-003 and INV-001. The route cannot receive a passing code-review receipt at this head.

## Critical findings

None.

## Important findings

### I1 — Authority and contract reads silently follow symlinks when `O_NOFOLLOW` is unavailable

The shared authority reader substitutes `0` for an unavailable `os.O_NOFOLLOW` while traversing ancestors and opening the final file (`.grok-stack/adaptive_grok/architecture.py:152-176`). `_inspect_repository_path()` makes the same fallback for declared repository and contract paths (`architecture.py:495-526`). This is not fail-closed behavior: it removes the only flag that prevents descriptor-relative opens from following symlinks. The shared reader is used for both architecture authority/schema/contract bytes and the adoption marker (`architecture.py:439-474,559-580`; `.grok-stack/adaptive_grok/receipts.py:44-56`).

The frozen design requires symlinks and non-regular authority paths to fail closed (`docs/superpowers/specs/2026-08-26-m2-executable-architecture-design.md:48-55`), the plan requires safe reads (`docs/superpowers/plans/2026-08-26-m2a-executable-architecture.md:43-49`), and AC-001/INV-001 require safe, bounded untrusted inputs (`engineering/changes/20260826-m2-executable-architecture-015603/change-spec.yaml:3-7,74-79`). The implementation already recognizes this requirement in the drift and worktree readers, which explicitly reject an unavailable `O_NOFOLLOW` instead of replacing it with zero (`architecture.py:659-669`; `.grok-stack/adaptive_grok/architecture_diff.py:328-338`).

This review reproduced the bypass without changing product files: in a temporary repository, replace `architecture/system.yaml` with a symlink to a valid JSON document outside the repository, patch `os.O_NOFOLLOW` to `0` to model an unavailable flag, and call `load_architecture()`. The loader accepted the external target and returned `ARCH-ADAPTIVE-GROK-M2`. The existing symlink regression only exercises a host where `O_NOFOLLOW` exists and therefore does not cover this fallback (`tests/test_architecture_model.py:480-497`). This is also a compatibility problem for the documented Windows installation/adoption flow because descriptor-relative/no-follow primitives are platform-dependent (`QUICKSTART.md:8-24`).

Repair by making no-follow capability explicit: either implement a proven platform-specific reparse-safe contained reader or raise a structured `ArchitectureError` before any authority/marker/contract/path read when the required primitives are unavailable. Never substitute zero for `O_NOFOLLOW`. Add focused tests that simulate missing no-follow support for the model, marker, schema/contract inventory, and repository-path inspection.

### I2 — Diagram verification performs unbounded, symlink-following reads

`compare_generated()` reads each existing projection with `Path.read_bytes()` and applies no byte limit, no descriptor-relative containment check, no `O_NOFOLLOW`, and no concurrent-identity validation (`.grok-stack/adaptive_grok/architecture_diagrams.py:118-130`). Both `diagram --check` and the architecture verification gate call this function (`scripts/grok_architecture.py:143-159`; `.grok-stack/adaptive_grok/verification.py:86-91`). A repository-controlled oversized or special projection can therefore force an unbounded allocation before the command can report drift; a symlink can make the standalone CLI compare bytes outside the repository.

That contradicts AC-003's bounded deterministic CLI/projection requirement (`change-spec.yaml:13-17`) and the frozen CLI contract that explicit paths remain contained and machine output is bounded (`docs/superpowers/specs/2026-08-26-m2-executable-architecture-design.md:157-159`). The model bounds make the expected rendered bytes finite, so there is no need to accept an arbitrarily large actual file. The existing CLI regression covers an ordinary valid file and a small stale file only (`tests/test_architecture_fitness.py:1055-1085`).

Repair with a contained descriptor-relative, no-follow regular-file read that rejects unavailable platform primitives, caps the actual file before allocation (a fixed generated-artifact cap or expected-length-plus-one is sufficient), and detects concurrent replacement. Add CLI and verification regressions for oversized, symlinked, non-regular, and swapped generated projections; each must fail in bounded time with structured evidence.

## Minor findings

### M1 — The durable release note reports a stale package state

`engineering/changes/20260826-m2-executable-architecture-015603/release.md:17` says the current package remains `implementing`, while the exact reviewed state is `reviewing` after a recorded `implementing -> verifying -> reviewing` transition (`engineering/changes/20260826-m2-executable-architecture-015603/state.json:29-44`). The rest of the document correctly keeps `ready`, PR, deployment, and M2-B open, so this is explanatory-document staleness rather than an authority or runtime defect. Rewrite the sentence as a Task-5 historical statement or point readers to `state.json` for current workflow state.

## Confirmed compliant areas

- The strict system/rules documents and marker parse as canonical JSON; all schema-declared objects are closed with `additionalProperties: false`, and the current model validates with no drift.
- Exact commit fitness from `25bfbe59...` to `b995fae...` reports all 12 mandatory categories, `fitness_status=pass`, `baseline_introduced=true`, and monotonic `red -> red` risk with explicit architecture/contract/data/security scopes.
- Receipt construction and verification use the same exact-object base selector, separately bind the historical route base, preserve the frozen product adoption base, and carry the explicit verified consumer-bootstrap decision without weakening direct CLI diff behavior.
- Installer source, schemas, CLI, and non-authoritative templates are managed while marker/model/rules are excluded even under `--force`; the three focused installer regressions passed independently.
- README preserves exactly 120 K16 edges and labels the graph decorative-only; M2-B independent enforcement, external deployment, PR/check/merge eligibility, and external writes remain explicitly open.
- The exact adoption-base-to-head range contains no `trust-ci/**`, GitHub Actions, root dependency marker, service, database, migration, queue, provider, or external-state mutation.

## Verification evidence

- Exact head/tree and base/tree matched the final review brief; `git diff --check 25bfbe59..b995fae` passed.
- `python3 scripts/grok_spec.py validate --change-id 20260826-m2-executable-architecture-015603 --gate --json`: `ok=true`, 7/7 criteria mapped.
- Architecture `validate`, `drift`, and `diagram --check`: passed; five committed projection digests matched.
- Exact architecture fitness at the reviewed base/head: passed with all 12 categories and `red -> red` risk.
- Six focused installer/K16/docs/CLI regressions passed in 4.652 seconds.
- The no-follow capability probe independently reproduced I1 in a temporary repository. I2 is directly established by the unbounded `Path.read_bytes()` implementation; no destructive large-file probe was needed.
- Broad implementation and coordinator verification evidence was inspected but not rerun during this final read-only code review.

This report is local review evidence only. It does not create merge authority and does not substitute for the App-owned policy-epoch Check Run on an exact pull-request SHA.
