# Analysis — task_analyst

Change: `20260906-continue-published-2-0-15-to-next-final-stage-su-8e7fea`  
Route: `8e7fea3efac6` · intent=`feature` · risk=`low` · complexity=`standard` · domains=`generic`  
Write owner: `general_implementer`  
Analysis wave: `repo_explorer` / `task_analyst` / `architect` / `docs_researcher`  
Reviews after implementation: `code_reviewer` + `test_reviewer`  
Evidence kinds: `verification`, `code_review`, `test_review`  
Human gates on this route: **none**  
Skills loaded: `/adaptive-delivery`, `feature-workflow` (analysis only)

Narrow question: convert “continue to final stage” into a bounded outcome and testable acceptance criteria for **this** route. What is in scope vs out of scope? What is the smallest coherent vertical the `general_implementer` should ship? What remains blocked for a human? Explicit non-goals.

Read-only except this evidence report. No application-code edits. No `.env`. No push / tag / merge / deploy from this agent.

---

## Ruling (one screen)

User ask: *«так, читай все правила изменения и подхватывай проект до финальной стадии»*.

“Final stage” for **this** route is **not** M9 production, live pilot, merge, tag, or a new GitHub Release. Those are either already published, already on `main` as repository product, or separately blocked.

For this route, “final stage” means: **leave the stale 2.0.12 checkout, start a new PR-only successor from published `origin/main` (`fd51dcf`), and extract the first unique remaining product work — PR #12 lazy Trust CI CLI imports — adapted to the current CLI.** Stop at an open successor PR plus local verification/review receipts. Do not merge it.

| Layer | Meaning |
| --- | --- |
| Published identity | `v2.0.15` already exists on merge `fd51dcf`. Do not retag, rebuild ZIP, or bump `VERSION`. |
| Current checkout | `fix/path-aware-shell-policy-circuit-breaker` @ `7c61e3b` is **2.0.12**. Implementing here ships the wrong tree. |
| Docs PR #28 | OPEN, `MERGEABLE`/`clean`, App check SUCCESS. Human merge only. **Do not use it as the product base.** |
| First unique successor | Adapt PR #12 command-local imports + isolation tests + operator docs to current `cli.py`. |
| Later unique work | PR #13 security-sensitive profiles and PR #15 investor demo stay **out of this slice**. |
| Last mile | Adaptive-delivery §7: print-only. No merge, deploy, tag, or production write. |

Route `human_gates: []` means the implementer may proceed after this bounded design. It does **not** authorize merge, human approval keys, or deployed-policy changes.

---

## Verified facts (do not invent against GitHub)

Checked 2026-09-06 against GitHub `Dimkox/adaptive-grok-build-pro` and local git. Recovered facts hold.

| Item | Verified value |
| --- | --- |
| Published release | [v2.0.15](https://github.com/Dimkox/adaptive-grok-build-pro/releases/tag/v2.0.15) on `fd51dcfed6b33f4a8707c0db602328146df17cc9` |
| ZIP SHA-256 | `1f0f64557fd258df7e533f674bb4e7c55d4a1a51454d48bcfecfa5487d08e9d7` |
| `origin/main` | `fd51dcf` — `feat(pilot): bounded Codex issue-to-draft-PR capability (2.0.15 candidate) (#27)` |
| `origin/main` `VERSION` | `2.0.15` |
| PR #27 | **MERGED** at `2026-09-05T20:14:37Z` by `Dimkox`. Head was `9fcc9d9`. |
| PR #28 | **OPEN**, `mergeable_state=clean`, head `ef7c8fa` on `docs/v2.0.15-published-handoff` |
| PR #28 checks | `adaptive-trust-ci/verified@06ecf1c875bc` SUCCESS (`101385984851`); GitGuardian SUCCESS (`101385980981`) |
| PR #12 | **OPEN**, `dirty` vs current `main`, head `0f7f508` on `fix/human-approval-cli`, base still `1c06299` |
| PR #13 | **OPEN**, `dirty`, head `f2fd8a7` — repository-scoped Trust CI profiles |
| PR #15 | **OPEN**, `dirty`, head `165d5dd` — investor-ready MVP / demo |
| Unique-work inventory | `engineering/runbooks/20260905-open-pr-reconciliation.md` on PR #28 / `origin/docs/v2.0.15-published-handoff` (absent from this checkout) |
| Local HEAD | `7c61e3b` on `fix/path-aware-shell-policy-circuit-breaker` (behind its origin by 2) |
| Local `VERSION` | `2.0.12` |
| Local dirt | modified `decisions.md`, `trust-ci/compose.yaml`; this change package is **untracked** on the stale tree |
| Current `cli.py` on `origin/main` | Eager top-level imports of `api`, `backup`, `github`, `github_app`, `holdout`, `migrations`, `models`, `policy`, `settings`, `signing`, `store`, `worker` |
| `trust-ci/tests/test_cli.py` on `origin/main` | **does not exist** |
| CLI command set | `origin/main` and PR #12 share the same 17 subcommands; unique delta is import placement + tests + operator README |
| Runtime `active-route.json` | Currently overwritten to later route `c08804e69b66` / different task. **This package’s `route.json` (`8e7fea3efac6`) is authority for this change.** |
| Deadline | `2026-09-08 00:00 UTC+3` does not waive Trust CI or signed approvals (`decisions.md` 2026-08-31) |
| Pilot | Pre-pilot. No real model turn. Landing profile stale (`6990103` vs observed `80d6215`). |
| M0–M9 repo product | Already on `main` via earlier merges / v2.0.13–2.0.15. Operational M8/M9 activation is **not** in this slice. |

PR #28 body confirms: docs-only handoff; product/architecture/contracts/Trust CI/factory/pilot and ZIP bytes unchanged; extract #12 first; #13 needs its own security-sensitive scope; do not close old PRs until successors exist.

---

## What “final stage” is not

The user asked to take the project to the final stage. The change rules already bound that:

1. **M0–M9 repository product is already on `main`.** Repeating M4–M9 source work is not the next unique step.
2. **Operational M8 cohort/activation and M9 production are not this slice.** They need evidence cohorts, signed approvals, and deployed-policy authority this route does not have.
3. **Live pilot is still blocked** on a stale landing-profile refresh. This route cannot spend a model attempt.
4. **PR #28 is already at the merge gate.** Agents must not merge it.
5. **Deadline pressure is not a waiver.** Compressing scope is the allowed response; fabricating merge/deploy/pilot success is forbidden.

Therefore the only coherent “continue” for a generic/feature/low/standard route with `write_agent=general_implementer` is the **first unique remaining product successor**.

---

## Outcome

A human operator can run `approval-create --help`, `approval-submit --help`, and `approval-submit` from a reviewed `origin/main`-based checkout **without importing FastAPI, uvicorn, worker, PostgreSQL, migrations, backup, GitHub App, or other server-only modules**. `approval-create` may import only models/policy/signing. Envelope schema, `/approvals`, policy, trust store, API, SQL, and deployed Trust CI remain unchanged.

The successor is an **open pull request** against `main`, locally verified, independently reviewed. Merge, close of old PRs, deploy, tag, and live pilot remain human actions.

Observable user result: the published 2.0.15 product tree gains the missing operator-path isolation that PR #12 already proved on an obsolete base, without mixing docs-sync (#28), policy catalogs (#13), investor demo (#15), or M8/M9/pilot work.

---

## Smallest coherent vertical (implementer recipe)

Exactly this, in order:

1. **Leave the stale checkout.** Do not edit product files on `fix/path-aware-shell-policy-circuit-breaker` @ `7c61e3b`. Do not commit local dirty `decisions.md` / `trust-ci/compose.yaml` / untracked 2026-08-* packages as this successor.
2. **New branch from `origin/main`**, exact SHA `fd51dcfed6b33f4a8707c0db602328146df17cc9`. Prefer a clean worktree. Recreate or copy **this** change package onto that branch; do not base product work on PR #28.
3. **Do not use PR #28 as the base.** It is docs-only, already check-green, and independently human-mergeable. Stacking CLI work on it would mix concerns, invalidate `ef7c8fa`’s exact-SHA check, and block the successor on a merge agents cannot perform. Read the runbook from `origin/docs/v2.0.15-published-handoff`; do not absorb that docs tree.
4. **Do not merge, rebase, or cherry-pick PR #12 wholesale.** It is `dirty` against current `main` (base `1c06299`). Re-apply the *behavior*: command-local imports, isolation tests, operator docs, adapted to current `cli.py`.
5. **Failing characterization first** (adaptive-delivery §4 / feature-workflow): prove that current `origin/main` `cli.py` eagerly imports server modules before a human subcommand is selected.
6. **Implement only** `trust-ci/src/adaptive_trust_ci/cli.py` import relocation, `trust-ci/tests/test_cli.py` (new on main), and the current `trust-ci/README.md` human-approval operator section. Touch `decisions.md` only with a short “adapted #12 onto 2.0.15 main” fact if the next subtask needs it.
7. **`python3 scripts/grok_verify.py --mode pr`** on the successor tree.
8. **Independent `code_reviewer` + `test_reviewer`** on the same final tree; fingerprint-bound receipts.
9. **Open a new PR to `main`.** Link PR #12 as the preserved source. Do not close #12/#13/#15, do not merge, do not deploy.

PR #12’s command-local import map is the intended design (already matches current 17 subcommands). Copy the pattern, not the obsolete ancestry.

---

## In scope

- New isolated branch from `origin/main` (`fd51dcf`).
- Relocate product imports in `trust-ci/src/adaptive_trust_ci/cli.py` into the selected command branch (PR #12 pattern).
- Keep `approval-submit` stdlib-only (`argparse` / `json` / `os` / `sys` / `urllib` / `pathlib` only).
- Keep `approval-create` limited to `models` / `policy` / `signing`.
- Keep `--help` for the root parser, `approval-create`, and `approval-submit` free of server and `cryptography` imports.
- Add `trust-ci/tests/test_cli.py` adapted from PR #12:
  - fresh-process blocked-import tests for human commands;
  - per-command import-slice + safe-effect smoke for the 17 non-human branches (fake modules; no live DB, no live API, no Docker, no GitHub).
- Adapt the `trust-ci/README.md` human-approval operator setup so it matches **current** envelope fields (`pr_number`, `approval_id`, `schema_version`, `reason`) and the isolated CLI invocation (`PYTHONPATH=… python -m adaptive_trust_ci.cli`). Verify against current `models`/`cli` on `origin/main`, do not blindly overwrite later README sections.
- Local `grok_verify --mode pr`, then route reviews and receipts.
- Open one successor PR targeting `main`. Record the link to PR #12 in the PR body / change package.
- Rollback note: revert the successor commit / close the successor PR. No data migration.

---

## Out of scope / explicit non-goals

- Implementing on the current 2.0.12 path-aware checkout.
- Using PR #28 (`docs/v2.0.15-published-handoff`) as the product base, or mixing its docs-sync into the CLI PR.
- Merging PR #28, PR #12, or the successor PR.
- Closing PRs #12 / #13 / #15 (human, after a linked successor or explicit product decision).
- Wholesale cherry-pick / merge of `0f7f508` onto current main.
- PR #13: `PolicyCatalog`, repository-scoped immutable commands/holdouts, policy-digest binding in API/worker, deployed-policy epoch, holdout-root pairing.
- PR #15: investor dashboard / `demo.py` / `grok_demo.py` / `.grok-stack/demo/`.
- VERSION bump, ZIP rebuild, tag, GitHub Release, or README “current-state” rewrite that belongs to PR #28.
- Operational M8 cohort/activation, M9 production qualification, factory migrations.
- Live pilot: landing-profile refresh, model turn, target-repository write, hosted publication.
- Deployed Trust CI policy, holdout, images, PostgreSQL state, GitHub App key, human trust store, branch protection.
- Reading or writing `.env`, `trust-ci/runtime/*.pem`, human private keys, or creating/submitting a real human approval envelope.
- Submitting tests to a live Trust CI URL; tests stay loopback/tempfile.
- GitHub Actions, force-push, merge to `main`, deploy, production mutation.
- Expanding into `api.py` / `policy.py` / `worker.py` / `settings.py` / SQL / signing verification behavior / `/approvals` contract.
- Second write agent. Security/data/release reviews are **not** selected by this route; do not fake them. If the implementer leaves the CLI-isolation boundary, stop and re-route rather than silently widening.

---

## Frozen boundaries (must not change)

From PR #12 and current AGENTS.md; still valid on `fd51dcf`:

- `/approvals` HTTP contract
- Approval/attestation envelope schema and signing verification semantics
- Policy document / digest algorithm / trust store
- API, store, models (except CLI import of existing symbols)
- SQL and migrations
- Branch protection
- Deployed service state
- Human private keys and the server-mounted public trust store
- Published `v2.0.15` tag, ZIP, and sidecar bytes

---

## Testable acceptance criteria

Close **this** change only when all of these are true on the **same** successor tree, branched from `fd51dcf`, not from `7c61e3b` or PR #28.

### A. Base and delivery hygiene

- [ ] AC-A1: Given the implementer starts work, when `git rev-parse --abbrev-ref HEAD` and `git merge-base --is-ancestor fd51dcfed6b33f4a8707c0db602328146df17cc9 HEAD` are checked, then the successor branch contains `fd51dcf` as ancestor and is **not** `fix/path-aware-shell-policy-circuit-breaker`.
- [ ] AC-A2: Given the successor diff vs `origin/main`, when files are listed, then product edits are limited to `trust-ci/src/adaptive_trust_ci/cli.py`, `trust-ci/tests/test_cli.py`, `trust-ci/README.md`, this change package / evidence, and at most a short `decisions.md`/`mistakes.md` fact. No `compose.yaml`, no `policy.py`/`api.py`/`worker.py`, no `VERSION`, no `packages/`/`dist/` ZIP, no `.github/workflows/`.
- [ ] AC-A3: Given PR #28 remains OPEN and MERGEABLE, when this successor is published, then it is a **new** PR to `main` and PR #28 is neither merged nor used as `base`.
- [ ] AC-A4: Given AGENTS.md last-mile rules, when this route closes, then no merge, tag, deploy, live API write, or human-key use has occurred.

### B. Isolation behavior

- [ ] AC-B1: Given a fresh Python process with `adaptive_trust_ci.api`, `backup`, `github`, `github_app`, `holdout`, `migrations`, `settings`, `store`, `worker`, `fastapi`, `psycopg`, `uvicorn`, and `cryptography` blocked, when `python -m adaptive_trust_ci.cli --help` (and `approval-create --help`, `approval-submit --help`) runs, then exit code is 0.
- [ ] AC-B2: Given the same blocked set **without** `cryptography` blocked, when `approval-create` runs with an **ephemeral tempfile key** generated in-test (never a human path, never `trust-ci/runtime/`, never `.env`), then it writes a new envelope file mode `0600` and does not import server modules.
- [ ] AC-B3: Given `approval-submit` with server **and** `cryptography` blocked, when it POSTs fixture bytes to a loopback HTTP server, then it posts exact bytes to `/approvals` with `Content-Type: application/json` and `User-Agent: adaptive-trust-ci-human/2.1.0`, exit 0.
- [ ] AC-B4: Given module import of `adaptive_trust_ci.cli`, when no command has been selected, then `sys.modules` does not contain `adaptive_trust_ci.api` / `.worker` / `.store` / `.migrations` / `.backup` / `.github` / `.github_app` / `fastapi` / `uvicorn` / `psycopg`.
- [ ] AC-B5: Given each of the 17 non-human commands (`api`, `worker`, `migrate`, `migration-status`, `policy-digest`, `holdout-digest`, `doctor`, `keygen`, `trust-store-validate`, `approval-verify`, `attestation-verify`, `branch-protect`, `backup-create`, `backup-verify`, `backup-prune`, `restore-drill`, `kill-switch`), when executed with fake modules, then only that command’s import slice is loaded and a safe mocked effect is reached (no live PostgreSQL, Docker, GitHub, or backup files outside tempfile).
- [ ] AC-B6: Given `approval-create` on current `origin/main` payload fields, when an ephemeral envelope is verified with in-test `TrustStore`/`Policy`, then `scope` and `policy_digest` match; schema fields are unchanged from current models.
- [ ] AC-B7: Given tests, when they finish, then no human key path was read, no key was written under `~/.config` or `trust-ci/runtime`, and `keygen` smoke did not persist `unused-private.pem` / `unused-public.pem`.

### C. Documentation

- [ ] AC-C1: Given `trust-ci/README.md` human-approval section, when compared to current CLI/models, then the bind list uses current field names (`pr_number` not `pull_request`; includes `schema_version`, `approval_id`, `reason`) and the operator example runs via `PYTHONPATH=… python -m adaptive_trust_ci.cli` from a reviewed checkout with venv/keys/policy **outside** the checkout.
- [ ] AC-C2: Given the operator docs, when a reader follows them, then they are told: one envelope per scope, no silent checkout update between review and signing, no automatic retry of ambiguous submit timeouts, HTTP 400/403/404/409/503 meanings, and rollback is “use previous reviewed CLI, do not weaken policy/trust-store/branch protection”.

### D. Verification and review (this route)

- [ ] AC-D1: Given the final successor tree, when `python3 scripts/grok_verify.py --mode pr` runs, then it PASSes.
- [ ] AC-D2: Given that PASS, when `code_reviewer` and `test_reviewer` inspect the actual diff, then both reports are stored under this change package and `grok_review.py` receipts bind the **same** tree fingerprint.
- [ ] AC-D3: Given `required_evidence` is `verification` + `code_review` + `test_review`, when `python3 scripts/grok_status.py` runs after receipts, then evidence gaps for this route are empty. Local receipts are not merge authority.

### E. Explicit non-claims (must remain true)

- [ ] AC-E1: `VERSION` is still `2.0.15`. No new tag or GitHub Release.
- [ ] AC-E2: Published ZIP/sidecar digests for `v2.0.15` are unchanged.
- [ ] AC-E3: PRs #12, #13, #15, #28 are not merged or closed by this route.
- [ ] AC-E4: No landing-profile refresh, model turn, M8 activation, or M9 production claim is made.

---

## Failure and edge cases

- Current checkout implementation → ships 2.0.12 path-aware tree. **Hard fail.** Leave it.
- Basing on PR #28 → mixes docs-sync with CLI isolation; stale-checks #28. **Hard fail.**
- Cherry-picking `0f7f508` onto `fd51dcf` without adapting tests/docs → dirty conflicts / obsolete packaging assumptions. Adapt, do not merge the old PR.
- Isolation tests that import `cli` after the test process already imported `api`/`store` → false pass. Human-command tests must use a **fresh subprocess** with `sitecustomize` import guards (PR #12 pattern).
- `approval-create` test that reads `~/.config/adaptive-trust-ci/*.pem` or `trust-ci/runtime/*.pem` → forbidden. Ephemeral tempfile keys only.
- Fake-module tests that actually call `Signer.generate()` for `keygen` without intercepting `write_keypair` → may write keys. PR #12 intercepts this; keep that.
- Expanding into `policy.py`/`api.py` to “finish Trust CI” → that is PR #13, security-sensitive, needs a different route and a deployed-policy epoch. Stop.
- Treating `human_gates: []` as merge permission → forbidden. Merge stays human + App check + signed scopes.
- Deadline-driven skip of Trust CI / reviews → forbidden. Report the blocker instead.

---

## What remains blocked for a human

These are **not** this route’s job. Do not stall the CLI successor on them, and do not perform them.

| Blocked action | Why |
| --- | --- |
| Merge PR #28 | Human-owned. Already MERGEABLE with App check SUCCESS. |
| Merge the CLI successor PR | Requires App-owned `adaptive-trust-ci/verified@<policy-sha12>` on the **new** head SHA plus any required signed scopes. |
| Close PRs #12 / #13 / #15 | Only after a linked successor exists or an explicit product decision. |
| Human-signed Trust CI approvals | Ed25519 envelopes from a human machine; agents must not create or read the private key. |
| Refresh stale landing profile (`6990103` → preserve observed `80d6215` analytics/archive) | Required before any live model attempt. |
| First live pilot model turn | Still pre-pilot; default-unavailable. |
| Operational M8 cohort / M9 production | Not in this slice; deadline does not waive gates. |
| Deployed-policy epoch / rollout for PR #13 | Repository source cannot grant activation. |
| Tag / GitHub Release / deploy / production writes | Need exact delegated local grant **and** remaining external gates. Never implied by “continue to final stage”. |

---

## Constraints

- **Backward compatibility:** CLI flags, subcommand names, envelope JSON, and `/approvals` stay identical. Only *when* modules load changes.
- **Data/privacy:** Tests must not read credentials, customer data, or human keys. Disposable keys stay in tempfile and are deleted.
- **Performance:** No requirement. Import isolation should make human commands *faster* to start, not slower.
- **Operational:** No service restart, no image rebuild, no policy digest change. Rollback is revert of the successor PR.
- **Security:** This route selected **no** `security_reviewer`. Stay inside CLI isolation so that remains honest. Crossing into policy/API/worker is a stop condition, not a drive-by edit.
- **Observability:** No new metrics. Operator docs must keep “HTTP acceptance is not merge authority”.

---

## Recommended implementer tasks (once analysis wave finishes)

1. New worktree/branch from `origin/main` (`fd51dcf`).
2. Characterization test: blocked-import `--help` fails on current eager `cli.py`.
3. Move imports to command branches (PR #12 map).
4. Port isolation tests; keep 17-command smoke with fakes.
5. Update only the human-approval operator section of `trust-ci/README.md` to current fields.
6. `python3 scripts/grok_verify.py --mode pr`.
7. Independent code + test reviews; bind receipts.
8. Open successor PR to `main`; link #12; stop.

Do **not** wait for PR #28 merge. Do **not** implement #13 or #15 in the same PR. Do **not** declare the program “final” after this slice; declare only that the first unique remaining product successor is locally complete and waiting on external Trust CI + human merge.

---

## Residual risks

- Runtime `active-route.json` was overwritten by a later session (`c08804e69b66`). Implementer must follow **this** package `route.json` (`8e7fea3efac6`) and `allowed_agents`.
- This change package currently exists only as untracked files on the stale 2.0.12 working tree. It must be recreated on the `origin/main` branch; committing it from `7c61e3b` would attach the wrong parent.
- PR #12 README also rewrote envelope field names that `origin/main` README still lists incorrectly (`pull_request`). Confirm against current `ApprovalPayload` on `fd51dcf` before copying prose.
- `test_approval_create_…` in PR #12 generates an ephemeral key. That is allowed **only** as a disposable test key in tempfile, not as a human approval key. The runbook line “Do not read or create any human approval key while testing” forbids human/runtime keys, not in-test `Signer.generate()` under tempfile.
- Deadline `2026-09-08 00:00 UTC+3` is close. The allowed compression is **this** small successor, not skipping gates to claim M8/M9/pilot.

---

## Decision record for the next agent

**Base:** `origin/main` `fd51dcfed6b33f4a8707c0db602328146df17cc9`.  
**Not base:** current checkout `7c61e3b`; PR #28 `ef7c8fa`.  
**Ship:** PR #12 lazy CLI imports, adapted.  
**Do not ship:** #13, #15, M8/M9 ops, live pilot, merge, deploy, tag.  
**Done when:** successor PR is open, `grok_verify --mode pr` PASS, code_review + test_review receipts bound to that tree.  
**Not done when:** those human/external gates are still open — and they should be.
