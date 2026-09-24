# Repository exploration — issues #35, #36, #39, #48, #73, #121, #122, #167

## Scope and disposition

This is a read-only source inspection from the route's current checkout. The issues split into four implementation seams:

| Issue | Source seam | Bounded repository fix | Main risk / external boundary |
|---:|---|---|---|
| #35 | shell verification command construction and/or shell-script lint checks | Add a reusable per-file `bash -n` loop plus regression tests; reject multi-path `bash -n` forms in gate scripts | Must avoid treating prose/examples as executable checks |
| #36 | command recorder / verifier result capture | Fix status capture to `cmd >log 2>&1 || code=$?`, preserve signal/launch failures, add regression tests | Changes verifier semantics; writer must own all callers |
| #39 | JS lint scope configuration (no active ESLint config was found in the inspected tree) | Add explicit generated/worktree ignores and changed-file/deep-mode scope contract only if the relevant lint consumer is present | Current repository is predominantly Python; issue may be historical/external and needs source confirmation before implementation |
| #48 | shell environment verifier patterns | No matching product verifier/guard kit was found in the current tree; likely external/user-level kit. Record as external unless a linked source is intentionally imported | Do not invent a core patch for absent code |
| #73 | committed evidence naming and GitGuardian false-positive convention | Rename sensitive-looking digest keys in committed evidence (e.g. `authorization_tree_fingerprint` → `grant_binding_digest`) and update schema/tests/docs; alternatively document a safe allow-list convention | Existing historical evidence must remain immutable; only current writable records can change |
| #121 | runtime observation dossier / provider activation probe persistence | Current `factory/` persistence has durable landing jobs, but the cited activation dossier is historical. Choose downgrade-to-attested wording or add a bounded durable probe record and tests | Adding a DB write is a behavior/data change requiring schema and rollback reasoning; source-only minimum is wording/record contract |
| #122 | `trust-ci/config/policy.example.json` versus deployed policy explanation | Clarify example is illustrative and identify deployed policy epoch/runbook source; add tests that prevent claims of deployed enforcement | Cannot modify/defer deployed Trust CI policy from repository |
| #167 | route-local verification selection for static SEO side projects | The new AGENTS contract already states focused landing tests first, while full `grok_verify --mode pr` remains required for mixed/runtime diffs. Add/adjust adaptive-delivery route implementation and regression tests if current router ignores this contract | App-owned Trust CI remains mandatory for PR merge; this only narrows local preflight |

## Exact inspected seams

- `tests/test_seo_landing_side_project.py` contains the focused static landing contract (`SeoLandingSkillTests` and `SeoLandingShowcaseContractTests`). It is the natural focused suite for #167. `AGENTS.md:178-181` already states the static-only scope split; the missing implementation seam is the route/verification dispatcher, not the landing contract itself.
- `tests/test_deploy.py` and `scripts/grok_verify.py` are the central root verification/deploy seams. The repository's shell scripts under `trust-ci/scripts/` use `set -euo pipefail`; `trust-ci/scripts/smoke.sh` contains `grep -q` pipelines, so any #36/#48 shell recorder changes must account for `pipefail` and SIGPIPE behavior.
- `trust-ci/config/policy.example.json` contains the broad `approval_rules[governance].globs` list cited by #122. `trust-ci/README.md` explicitly labels the file as an example/non-deployed policy around the policy explanation; this is the correct documentation anchor for a clarifying patch.
- `factory/tests/test_semantic_persistence.py` and `factory/tests/test_landing_*` show existing durable semantic/landing persistence tests. A #121 durable probe implementation would need to bind `job_id`, profile digest, status, usage, and event provenance to the same integrity checks rather than putting probe numbers only in JSON prose.
- Historical #121 evidence is under `engineering/changes/20260916-record-the-qwen-omni-intl-executor-activation-as-9d1695/evidence/` per the issue body. It must be treated as historical input; do not rewrite it as if a new probe occurred.
- No active ESLint `package.json`, ESLint config, or JS lint runner was found in the top-level product tree during this inspection. #39 therefore needs an owner-side source check before writing a fix. The repository has JS assets in `side-projects/seo-landing-showcase`, but its tests use static resource checks and a browser runner, not ESLint.
- No implementation of the user-level `~/.bashrc`/installed CLI guard described by #48 exists in this checkout. The issue body links an external gist; this repository cannot safely close it without importing that product scope.

## Recommended implementation/test slices

1. **Verifier shell/status slice (#35/#36):** locate the actual command-building and recording functions in the selected writer branch; add tests that run two temporary shell files (one valid, one invalid), assert every file is parsed, and assert a failing/failed-to-start command retains its nonzero exit code and nonempty log evidence. Add a static guard against multi-path `bash -n` and `if ! ...; code=$?` in executable gate scripts.
2. **Evidence/policy docs slice (#73/#122):** update only current evidence schemas/fixtures and the operator-facing explanation. Add tests asserting digest-bearing keys use neutral names and that `policy.example.json` is marked illustrative, with the deployed epoch/runbook reference remaining explicit. Do not alter Trust CI deployment state.
3. **Runtime records slice (#121):** prefer the issue's option 2 for a bounded source-only batch: mark provider probe leaves `attested_not_rederivable`, separate them from the durable pilot job, and add a schema/test invariant forbidding the two event IDs/usage values from being conflated. Durable probe persistence is a separate data-change task.
4. **Static route slice (#167):** test that a diff confined to `side-projects/seo-landings/**` plus focused tests selects the focused suite, and that adding runtime/contract/Trust CI files falls back to full `grok_verify`. Preserve full external merge authority.
5. **#39/#48:** leave explicitly unimplemented in this route unless the writer identifies the actual source/config being fixed. The issue text alone does not justify a fictional patch.

## Priority and closure evidence

The bounded source-only candidates are #35/#36, #73/#122, #121 (wording/contract option), and #167. #39 and #48 are currently source-absent; their issues should remain open or be closed only with a documented external-project disposition. #121 cannot claim re-derivability without a durable probe record or an explicit downgraded claim. Any issue closure must wait for a merged successor PR and fresh exact-head App-owned Trust CI; this report is analysis evidence only.
