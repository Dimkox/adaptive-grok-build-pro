# architect — M0.3 bind-main: docs/tests encoding, bootstrap supersede, trust domain, actor-mismatch proof

Route `54313e326a39`. Change `20260824-user-query-давай-далее-user-query-54313e`.  
Read-only design. No product edits. No `.env`/PEM. No merge of PR #5. No human approval private keys. No Administration grant to GitHub App `4694114`.

**Sources:** this package `brief.md` + `evidence/branch-protection-payload.json`; `docs/superpowers/specs/2026-08-24-m0-live-trust-authority.md`; `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md`; `engineering/runbooks/trust-ci-activation-report.md`; `trust-ci/src/adaptive_trust_ci/github.py`; `trust-ci/src/adaptive_trust_ci/cli.py`; `trust-ci/tests/test_ops.py`; `trust-ci/tests/test_webhooks_github.py`; `trust-ci/tests/test_m0_invariants.py`; `trust-ci/holdout.example/validate.py`; `AGENTS.md`; sibling `analysis-docs_researcher.md` / `analysis-repo_explorer.md`. GitHub REST: protected-branch `checks[].app_id`; Checks API write is App-only.

---

## Verdict

Encode the live gate as **two facts that must appear together**, never as a name-only check:

| Fact | Value |
| --- | --- |
| Required check context | `adaptive-trust-ci/verified@6737355947c2` |
| Bound GitHub App ID | `4694114` (`slug` `adaptive-trust-ci`) |

GitHub’s required-status-check object is `{"context": "<epoch name>", "app_id": <int>}`. Omitting `app_id` lets GitHub auto-select “the app that last posted this name, or any app”. Passing `-1` explicitly allows any app. A name-only rule would treat a same-text Check Run from GitHub Actions, another App, or a legacy commit status as satisfying protection. That is the failure mode M0.3 exists to close.

**Split the slice:**

1. **Operator (outside the PR trust domain):** temporary human admin token → `adaptive-trust-ci branch-protect` with the frozen payload; disable leftover Actions catalog workflow `340420982`; run the no-merge actor-mismatch and push-reject probes; fill the activation-report live cells from GET responses.
2. **Write owner (git):** characterization tests first, then supersede current-state sentences. Do not implement a new configurator. Do not change `branch_protection_payload()` unless a test proves it would emit `contexts` or omit/`-1` `app_id` (it already rejects non-positive `app_id` and omits `contexts`).

Do **not** merge PR #5 in this slice. Do **not** mint or use human Ed25519 approval keys. Do **not** PATCH Check Run `97527445754` (or any `adaptive-trust-ci/verified@*`) to `success`. Protecting `main` while PR #5 is `action_required` is intended: merge stays blocked until a later human-owned success path.

---

## 1. How docs should encode the binding

### 1.1 Living current-state (must name both facts)

`AGENTS.md` already has the **standing contract** and must stay epoch-generic:

> Branch protection binds that exact check name to the configured GitHub App ID.

Do **not** hardcode `@6737355947c2` or `4694114` into `AGENTS.md`. A later policy/holdout retitle changes the suffix; the contract is “current epoch + configured App ID”, not a frozen SHA12 forever.

Pin the **live** pair only in operator-safe current-state surfaces:

| File | After M0.3 |
| --- | --- |
| `README.md` current-state (today L11) | Replace “The App-owned check is not live in this release; merge of PR #2 is a bootstrap exception”. State: merge gate on `main` is Check Run `adaptive-trust-ci/verified@6737355947c2` **bound to GitHub App ID `4694114`**. Keep “No GitHub Actions” as a **forbid-Actions** sentence, not as merge authority. Keep L9: local `grok_verify` is preflight. Product identity stays **2.0.12**; Trust CI service identity stays **2.1.0**. This is not a release. |
| `engineering/runbooks/trust-ci-activation-report.md` | Fill the four live cells from GET, no secrets: `` `main` protected `` = `true`; `Protection app_id` = `4694114`; leftover workflow `340420982` = `disabled` (catalog id + name `trusted-ci`); `Bootstrap-exception language superseded` = dated pointer to the new `decisions.md` entry. Keep required check name `adaptive-trust-ci/verified@6737355947c2`. Rewrite the lead sentence that currently says “`main` is still unprotected.” |
| New `decisions.md` entry **at the top** (≤3 sentences) | M0.3 bound `main` to `adaptive-trust-ci/verified@6737355947c2` + App ID `4694114`. Named bootstrap exceptions (M1 start, PR #2, PR #4) are **revoked because a live App-owned check exists** — never because a check was forged. Do not grant Administration to the App. |
| Plan `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md` | Check the M0.3 boxes that this slice actually does: branch-protect, actor-mismatch/push-reject **probes**, disable `340420982`, supersede language, fill report. **Leave unchecked** “Mark PR ready; merge only through the live App-owned check”. Brief forbids merging #5. Keep the M0.2 historical line `**Do not protect \`main\`** in M0.2` as history (tests already match that string). |
| Spec freeze table | Keep the 404/`state=active` rows **labeled design-freeze**. Do not rewrite freeze history as if `main` was already protected. Live facts belong in the activation report. |
| `DARK_FACTORY_ROADMAP.md` M0 work items | Check “Apply branch protection…”, “Verify … binds the exact policy-epoch check and the GitHub App ID”, “Remove or supersede the bootstrap-exception language…”. Direct-push/force-push/delete/merge-without-check are proven by the operator probes in §4, not by merging #5. |
| `QUICKSTART.md` / `trust-ci/README.md` / `engineering/runbooks/trust-ci-rollout.md` | Keep “webhook, then prove, then branch-protect” as **order**. After M0.3 they are no longer “do not protect yet”. Add one sentence: protection on this repo is App-bound (`app_id` required; never `contexts`-only; never `app_id: -1`). |

### 1.2 What “supersede” means

**Supersede = add a later dated ruling + fix living current-state. Do not silently delete or rewrite historical entries.**

`CHANGELOG.md` 2.0.12 (“rebase-merge of draft PR #2 is a bootstrap exception because the App-owned check is not live yet”) is a **ship record for that release**. Leave it. If a reader would confuse it with *now*, the new `decisions.md` entry and README current-state are the correction.

Do not rewrite `decisions.md` 2026-08-23 / 2026-08-24 M0.2 paragraphs in place. They correctly describe those slices. After M0.3 they are history; the new top entry is the standing order.

`mistakes.md` has nothing to supersede.

`trust-ci/runtime/trust-store.json` actor `claw-m01-bootstrap` is a **trust-store actor name**, not the merge bootstrap exception. Do not touch the trust store.

### 1.3 Sentences that must not be claimed

- GitHub Actions is or was the merge gate. (“No GitHub Actions” forbids Actions as CI; leftover catalog `340420982` is residue to disable, not a required check.)
- Local receipts, `grok_approve.py` grants, GitGuardian, or this change package are merge authority.
- Offline attestation / human Ed25519 requeue / source-mutation / policy-holdout retitle are done. They stay **not done** (user-closed M0.2). They are also **not** required to bind `main`, and they are **not** merge authority.
- The GitHub App has repository Administration.
- Product version bumped; this is not a release.

---

## 2. How tests should encode the binding

Plan TDD: characterization tests **before** docs land; keep them green after. **Do not assert “main is unprotected”.**

Split tests into **in-tree (no network, no secrets)** vs **operator evidence (change package, not unittest)**. Unittests must not call `api.github.com`, read `TRUST_CI_GITHUB_ADMIN_TOKEN`, or open PEM.

### 2.1 Keep (already correct)

| Test | Why it stays |
| --- | --- |
| `trust-ci/tests/test_webhooks_github.py::test_branch_protection_binds_epoch_check_to_app_id` | Payload is `{context, app_id}`, **no** `contexts`, `strict`/`enforce_admins` true, no force-push/delete. |
| `…::test_branch_protection_update_uses_encoded_branch_epoch_and_app_id` | PUT path + body carry epoch + `app_id`. |
| `trust-ci/tests/test_ops.py::test_branch_protection_is_app_bound_and_actions_independent` | Dummy `app_id=12345`; payload string has no `actions`. |
| `holdout.example/validate.py` | Literal `'checks': [{'context': status_context, 'app_id': app_id}]` in `github.py`. |
| `test_m0_invariants.py` no `.github/workflows`, API has no `GitHubClient`/`GitHubAppAuth`, no PEM markers, Funnel URL, no ChatGPT webhook host | Unchanged by bind-main. |
| `test_m0_2_webhook_stage_closed_on_github_delivery` asserting `**Do not protect \`main\`**` | That string is **M0.2 history** in the plan. Keep it. Do not turn it into “main is unprotected now”. |

Generic constructor tests should **keep** dummy ids (`12345`, `@abc123def456`). They prove the function, not the live epoch.

### 2.2 Add (characterization; fail until docs/report match)

Put live-epoch assertions in `trust-ci/tests/test_m0_invariants.py` (already the M0 docs/report reader). Optional extra in `tests/test_structure.py` only if README current-state is the chosen pin; that file is a Trust CI **governance** glob (see §3).

**A. Payload fixture equality (no GitHub).**

Load this package’s `evidence/branch-protection-payload.json` **or** a copy under `trust-ci/tests/` if the write owner wants a product-tree fixture. Assert:

```python
branch_protection_payload(
    "adaptive-trust-ci/verified@6737355947c2",
    app_id=4694114,
) == fixture
```

Also assert:

- `required_status_checks.checks == [{"context": "adaptive-trust-ci/verified@6737355947c2", "app_id": 4694114}]`
- `"contexts" not in required_status_checks`
- `app_id` is `int` `4694114`, not `-1`, not omitted
- `enforce_admins is True`; `allow_force_pushes is False`; `allow_deletions is False`; `strict is True`

Constructor already raises on `app_id <= 0` and bool. Add an explicit test that `-1` is rejected (GitHub’s “any app” sentinel). If today’s `app_id <= 0` check already covers `-1`, assert the exception message; do not special-case `-1` in production unless a test requires it.

**B. Docs/report pins (no GitHub).** After docs land:

- Activation report: `` `main` protected `` cell is `true`; `Protection app_id` cell is `4694114`; leftover workflow cell contains `disabled` and `340420982`; bootstrap-exception cell is not `UNKNOWN`.
- README current-state contains both `adaptive-trust-ci/verified@6737355947c2` and `4694114`, and does **not** contain “The App-owned check is not live in this release” / “merge of PR #2 is a bootstrap exception”.
- `decisions.md` contains a 2026-08-24 M0.3 entry with `6737355947c2`, `4694114`, and a revoke/supersede verb. Historical 2026-08-23 headings **remain** (no silent delete).
- Plan M0.3 does **not** require the merge-PR-#5 box to be checked.
- No test asserts “main is unprotected” or `GET .../protection` 404 as a **current** fact. Freeze-table 404 may remain in the spec file as labeled freeze.

**C. Forbidden in tests.**

- No live `gh api` / `GitHubClient` against production.
- No reading `trust-ci/runtime/*.pem`, `env/*.env`, `.env`.
- No creating Check Runs.
- No asserting attestation verified, human approval present, or PR #5 merged.
- Do not add `.github/workflows/**`.

### 2.3 Operator evidence (not unittest, stored redacted in this change package)

After live PUT/GET:

- Redacted `GET /repos/Dimkox/adaptive-grok-build-pro/branches/main/protection` (no tokens). Must show `checks[0].context` and `checks[0].app_id == 4694114`.
- Workflow `340420982` GET: `state=disabled` (or deleted).
- Transcripts of the §4 probes (`pr merge` 405/422, `git push` to `main` rejected, user-token Check Run POST 403).

Change-package JSON is workflow evidence. It is **not** merge authority. Product tests should keep passing from git docs/report/fixture even if this directory is later ignored.

---

## 3. Bootstrap-exception language that must be superseded

Plan names **M1 start, PR #2, PR #4**. Spec names `decisions.md` / README.

| Location | Current standing sentence | Action |
| --- | --- | --- |
| `README.md` L11 | “The App-owned check is not live in this release; merge of PR #2 is a bootstrap exception (see decisions.md).” | **Replace** with live pair + App-bound `main`. This is the cold-reader current-state. |
| `decisions.md` 2026-08-23 — M0 live Trust Authority bootstrap exception for M1 start | “Revoke the exception when a live App-owned check exists on an exact PR SHA.” | **Keep as history.** New top entry records the revoke (live Check Runs `97524725228` / `97527445754` on PR #5 SHAs). |
| `decisions.md` 2026-08-23 — Bootstrap merge of PR #2 | “`main` is unprotected, so rebase-merge of PR #2 is the named bootstrap exception” | **Keep as history.** New entry revokes it. |
| PR #4 bootstrap | Not in root `decisions.md`; lives in `engineering/changes/20260824-user-query-да-user-query-37bf04/` | Name PR #4 in the **new** root entry so the plan item is satisfied without editing frozen packages. |
| `decisions.md` 2026-08-24 — Close M0.2 | “Do not protect `main` until M0.3.” | **Keep.** It is the M0.2 gate, now satisfied by doing M0.3 — not a standing forever-unprotected order. |
| `decisions.md` 2026-08-24 — Host-socket overlay | “`main` protection remain out of scope.” | **Keep** as that slice’s scope. Webhook later closed; protection is this slice. |
| `engineering/runbooks/trust-ci-activation-report.md` L5, cells `main` protected / bootstrap superseded | `false` / `UNKNOWN` | **Fill** after live GET. |
| Plan M0.1 checked line “`main` still unprotected”; M0.3 checkboxes | Stale / open | Check M0.3 items except merge-#5. Do not rewrite M0.1/M0.2 checked history into a lie about *when* protection happened. |
| `CHANGELOG.md` 2.0.12 | bootstrap exception for that ship | **Leave.** Historical. |
| `DARK_FACTORY_ROADMAP.md` L206 / L614 | M1–M3 may proceed after live proof **or** a named bootstrap exception | After supersede, live proof exists; exception is no longer the standing license. Do not delete the sentence; the M0 checklist item L247 is what gets checked. |
| `AGENTS.md` | already App-bound, PR-only | **No supersede.** Align other docs to this, not the reverse. |

“No GitHub Actions” sentences are **not** bootstrap-exception language. Keep them.

---

## 4. What must stay outside the PR trust domain

`AGENTS.md` already lists the boundary. M0.3 docs/tests **describe** it; they **must not mutate** it.

**Trusted / outside the pull-request tree (do not edit from this PR, do not treat git copies as live):**

| Asset | Why |
| --- | --- |
| Deployed `policy.json` (digest `6737355947c21eb561073cb506ebc5698afd170088a34f8eaace50007c57d1a5`) | Epoch name is computed from this file on the host. Retitle is a later approved slice. |
| Deployed holdout bundle + digest `b78d17006e270cec373aa130d7b0d11de357ffa236297b41075234e6ad7d5db8` | External to checkout; worker fails closed on mismatch. |
| Deployed images (`name@sha256:` in the activation report) | Host-pinned; git examples stay placeholders/example. |
| PostgreSQL volume `adaptive-trust-ci_trust-ci-postgres` and durable jobs | Job `external_id` is the Check Run correlation; restore-into-live is forbidden. |
| CI Ed25519 signing key (worker-only) | Attestation; agent must not read. |
| GitHub App RSA private key (worker-only) | Check Run publisher; filename gitignored; **not opened**. |
| Human public-key trust store (API-only) | Approval verify; actor `claw-m01-bootstrap` is not merge authority. |
| Human approval **private** keys | Never on `claw`, never in the agent workspace, never minted here. |
| Webhook HMAC secret (API-only) | Funnel path already live; do not rotate in this slice. |
| GitHub App installation + reduced token scopes | `checks:write`, `contents:read`, `pull_requests:read`. **No Administration.** |
| Temporary `TRUST_CI_GITHUB_ADMIN_TOKEN` | Human, short-lived, only for `branch-protect` / workflow disable. Not the App. |
| Live GitHub branch-protection object | A PR cannot PUT protection. Git records the intended payload; GitHub holds the authority. |
| Host overlay (docker.sock on worker/runner-loader) | Untracked operational exception; do not “fix” into tracked compose in this slice. |

**Untrusted (may change in the PR; never merge authority):** `AGENTS.md`, README, decisions, tests, prompts, hooks, `.grok-stack/runtime`, local receipts, delegated grants, this change package, GitGuardian, leftover Actions catalog entries, agent output, the repository copy of `trust-ci/` source.

**Governance glob consequence (deployed policy example, which the live policy is expected to match):** edits to `decisions.md`, `tests/test_structure.py`, and `trust-ci/**` (including `trust-ci/tests/test_m0_invariants.py`) enqueue `needs_approval`. README, CHANGELOG, `engineering/runbooks/trust-ci-activation-report.md`, and `docs/superpowers/**` are **not** in that example governance list. This slice still **must not** mint human keys to clear `action_required`. A `needs_approval` Check Run on PR #5 after docs land is expected and is **not** a license to PATCH the check green.

Do not “fix” `needs_approval` by editing deployed policy or holdout. That is outside the PR trust domain and would retitle the epoch (`@6737355947c2` must stay).

---

## 5. Prove a same-named check from a different actor cannot satisfy protection

### 5.1 GitHub semantics (the actual control)

From GitHub REST (protected branches, `checks[]`):

- `app_id` = the GitHub App that **must** provide the check.
- **Omit** `app_id` → GitHub picks the app that recently posted that name, or any app.
- **`app_id: -1`** → any app may set the status.
- Legacy `contexts` is closing-down and must not appear in our PUT body.

From GitHub Checks API:

- **Only GitHub Apps** can create Check Runs. OAuth apps and authenticated users can **view** them, not create them. Users who want a status use the **commit statuses** API, a different object type.

Therefore a user PAT **cannot** produce a Check Run named `adaptive-trust-ci/verified@6737355947c2`. A same-text **commit status** can be posted, but with `app_id: 4694114` GitHub must **not** treat it as the required check. GitHub Actions would be another App (`github-actions`); leftover workflow `340420982` is that class of actor and is disabled rather than used as a probe.

### 5.2 Proof ladder — no merge, no human private keys, no forged success

Run **after** `GET .../branches/main/protection` shows `app_id == 4694114`. If `app_id` is missing, `0`, or `-1`, **stop**. Do not post a same-named status (that would satisfy a name-only rule). Do not merge. Do not grant Administration to the App to “retry”.

Use draft **PR #5** as the victim SHA (`56f5462e78c7ebc0ab7e69fbffd5c1371ff7af78` or whatever HEAD is then). The existing App-owned Check Run is `conclusion=action_required`. That is enough. Completing it would need worker attestation and possibly human Ed25519; this slice forbids both.

| Step | Command class | Pass | Fail / stop |
| --- | --- | --- | --- |
| 0 | `GET .../branches/main/protection` | `checks[0].context` exact epoch; `checks[0].app_id == 4694114`; no usable `contexts` list; `enforce_admins` true; force-push/delete false; `strict` true | Name-only or wrong app → do not continue probes that post same-named statuses |
| 1 Binding observation | Store redacted JSON in this package | Live GitHub stored the pair | — |
| 2 User cannot mint a Check Run | `POST /repos/.../check-runs` with a **user** token, `name=adaptive-trust-ci/verified@6737355947c2`, `head_sha=<PR#5>` | **403** (Checks write is App-only) | 201 would mean a non-App actor created the object — abort and investigate; do not leave it `success` |
| 3 Optional legacy-status ignore | Only after step 0 passes: `POST /repos/.../statuses/<sha>` user token, `context` = exact epoch, `state=success` | 201 **and** PR `mergeable_state` still blocked / required check not green | If the PR becomes mergeable, **protection is name-only** — revert protection or fix `app_id` before anything else; do not merge |
| 4 Inventory | `GET .../commits/<sha>/check-runs?check_name=adaptive-trust-ci/verified@6737355947c2` | Every Check Run with that name has `app.id == 4694114` | Foreign `app.id` with that name: document it; it must not satisfy mergeability |
| 5 Merge-without-success | `gh pr merge 5 --rebase` **without** `--admin` | HTTP **405/422**, required check not satisfied | A merge would violate the brief; do not retry with admin bypass |
| 6 Direct push / force-push / delete | `git push origin HEAD:main`; `git push --force origin <anything>:main`; `git push origin :main` | All **rejected** | Any accept → protection not applied / admins not enforced |
| 7 Disable Actions actor | Workflow `340420982` `state=disabled` (or 404 if deleted) | Catalog leftover cannot emit a same-named Actions check | Do **not** re-enable it to “prove” Actions cannot satisfy — that would add an Actions actor |

**Forbidden during the proof:**

- `gh pr merge 5` succeeding, `--admin`, or deleting the branch.
- `PATCH` of Check Run `97527445754` / `97524725228` / any `@6737355947c2` run to `success` or `neutral`.
- Creating a **second GitHub App** to post the same name.
- Re-enabling or adding `.github/workflows/`.
- `adaptive-trust-ci approval-create` or any human private key.
- Reading App RSA / CI signing key to “finish” the job.
- Treating GitGuardian, local receipts, or a user commit status as the required check.

Step 2 (user POST Check Run → 403) plus step 0 (GET `app_id=4694114`) is **sufficient** actor-mismatch proof without posting a same-named object. Step 3 is optional extra: it shows GitHub ignores legacy statuses **only after** binding is confirmed. It is a negative probe, not merge authority. Prefer a user-token status over a forged Check Run; never set an App-looking Check Run `success` from a non-worker credential.

### 5.3 Why this does not need merge or human keys

The required check on PR #5 is already **not success** (`action_required` / `needs_approval`). Branch protection with `strict` + exact context + `app_id` therefore **blocks merge** without anyone completing the job. Completing the job is a later slice (human Ed25519, runner mutation, attestation). Binding `main` only requires GitHub to **refuse** non-App same-text and to **refuse** merge/push without the App-owned success. Both are observable as HTTP errors.

---

## 6. Sequence for the write owner and operator

1. Characterization tests (§2.2) — expected red until docs/report match. Do not assert unprotected `main`.
2. Operator, exact grants, temporary **human** admin token (not the App): PUT protection from `evidence/branch-protection-payload.json` / `adaptive-trust-ci branch-protect --branch main` with `--context adaptive-trust-ci/verified@6737355947c2` and App ID `4694114`. Disable workflow `340420982`.
3. §5 probes. Store redacted GET + 403/422 transcripts in this package `evidence/`.
4. Docs supersede (§1–§3). Fill activation report from GET, not from memory.
5. Tests green locally: `python3 -m unittest trust-ci.tests.test_m0_invariants` (and payload tests) then `python3 scripts/grok_verify.py --mode pr` if product files changed.
6. **Stop.** Do not `gh pr ready` / merge #5. Check Run may remain `action_required` if governance files changed. That is correct.

Rollback (operator): remove or relax protection only with a new human admin token and an explicit later grant. Git rollback is revert of the docs/tests commit; it does **not** un-protect `main`. Do not leave `main` unprotected as a “fix” for `needs_approval`.

---

## 7. Non-goals / forbidden in this design

- Merge, tag, GitHub Release, VERSION bump.
- Policy/holdout/image retitle (would change `@6737355947c2`).
- Granting Administration to App `4694114`.
- Forging `adaptive-trust-ci/verified@*`.
- GitHub Actions, Dependabot CI, `.github/workflows/`.
- M1 re-implementation; M2–M9; `factory/`; root `pyproject.toml`.
- Publishing Trust CI on host 8080.
- Using Funnel/socat/compose as this architect’s job (already live; do not churn).

---

## 8. Risks

| Risk | Mitigation |
| --- | --- |
| Protecting `main` while PR #5 cannot go green (`needs_approval`, no human key) | Intended. Brief: do not merge #5. Docs PR waits. Do not forge success. |
| Name-only protection accidentally applied | Constructor + fixture tests; GET must show `app_id` 4694114 before any same-named status probe. |
| Tests pin live epoch in `AGENTS.md` | Do not. Pin in README current-state + activation report + payload fixture. |
| Silent delete of 2026-08-23 decisions | Forbidden. New dated entry only. |
| README claims protected `main` before GET is true | Operator PUT/GET **before** or in the same turn as the README sentence. Tests that read the report cell `true` must not land while the cell is still `false`. |
| `test_m0_2_*` vs M0.3 | Keep M0.2 “Do not protect in M0.2” string; never assert current unprotected. |

**Success metric for this design:** git current-state and characterization tests name `adaptive-trust-ci/verified@6737355947c2` **and** App ID `4694114` together; bootstrap exceptions are revoked by a new decision, not erased; live GET shows the same pair; user Check Run POST is 403; `gh pr merge 5` fails; `main` push/delete fail; workflow `340420982` disabled; no merge, no human private key, no App Administration.
