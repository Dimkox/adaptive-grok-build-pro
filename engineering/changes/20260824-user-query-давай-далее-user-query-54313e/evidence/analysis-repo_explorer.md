# repo_explorer — M0.3 bind-main (route `54313e326a39`)

Read-only map. No product edits, no secrets, no merge, no Funnel/socat.

**Change:** `20260824-user-query-давай-далее-user-query-54313e`  
**Question:** files that document or implement GitHub branch protection for `main`, required check `adaptive-trust-ci/verified@6737355947c2`, App ID `4694114`, leftover Actions workflow `trusted-ci` id `340420982`, bootstrap-exception language, and activation-report cells for M0.3.

## Verdict

M0.3 is **not applied** in git. Protection is implemented as a CLI + payload generator (`adaptive-trust-ci branch-protect`); live GitHub state is recorded as **unprotected**. After protecting `main` and disabling workflow `340420982`, the **current-state cells and bootstrap-exception sentences** below become stale. Historical decision entries stay as history; they need a **superseding** 2026-08-24 M0.3 note, not silent deletion.

Exact check name and App ID already appear in the activation report and this change package’s payload. They should **not** be rewritten unless policy digest changes.

## 1. Implementation (configurator — wording does not go stale from protecting `main`)

| Path | Role |
| --- | --- |
| `trust-ci/src/adaptive_trust_ci/github.py` | `branch_protection_payload()` builds `required_status_checks.checks[].context` + `app_id`; `GitHubClient.configure_branch_protection` PUTs it. |
| `trust-ci/src/adaptive_trust_ci/cli.py` | Subcommand `branch-protect` (`--repository`, `--branch` default `main`, `--context`, `--policy`, `--app-id`). Requires `TRUST_CI_GITHUB_ADMIN_TOKEN`. |
| `trust-ci/tests/test_ops.py` | `test_branch_protection_is_app_bound_and_actions_independent` |
| `trust-ci/tests/test_webhooks_github.py` | `test_branch_protection_binds_epoch_check_to_app_id`, `test_branch_protection_update_uses_encoded_branch_epoch_and_app_id` |
| `engineering/changes/20260824-user-query-давай-далее-user-query-54313e/evidence/branch-protection-payload.json` | Frozen PUT body: context `adaptive-trust-ci/verified@6737355947c2`, `app_id` **4694114**, `enforce_admins` true, `allow_force_pushes`/`allow_deletions` false. |

Payload snippet (current file):

```json
"checks": [{ "context": "adaptive-trust-ci/verified@6737355947c2", "app_id": 4694114 }]
```

No `.github/workflows/` in the tree. Leftover `trusted-ci` exists only in the **GitHub Actions catalog** (id `340420982`).

## 2. Operator contract / M0.3 procedure

| Path | Current wording that goes stale after protect + disable |
| --- | --- |
| `engineering/runbooks/trust-ci-activation-report.md` | **Primary M0.3 cells.** |
| `engineering/runbooks/trust-ci-rollout.md` | Sequence: prove check, **then** `adaptive-trust-ci branch-protect` with admin token. |
| `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md` | M0.3 checklist still open; M0.2 “Do not protect `main`”. |
| `docs/superpowers/specs/2026-08-24-m0-live-trust-authority.md` | Live-gap freeze: `GET .../branches/main/protection` **404**; leftover workflow **state=active**; exit extras. |
| `DARK_FACTORY_ROADMAP.md` | Unchecked “Apply branch protection…”, “Remove or supersede bootstrap-exception…”. |
| `QUICKSTART.md` | “Webhook, then prove, then branch-protect”. |
| `trust-ci/README.md` | Same order; CLI example. |
| `docs/superpowers/specs/2026-08-23-trust-ci-control-plane-design.md` | Generic configurator contract (`adaptive-trust-ci/verified` without epoch suffix in older wording). |

## 3. Activation-report cells (exact current values)

File: `engineering/runbooks/trust-ci-activation-report.md`

Prose (line 5) that becomes stale:

> `main` is still unprotected.

Table cells that M0.3 must fill:

| Field | Current value | After successful M0.3 |
| --- | --- | --- |
| Required check name | `` `adaptive-trust-ci/verified@6737355947c2` `` | **Keep** (epoch unchanged) |
| App ID | `4694114` | **Keep** |
| `main` protected | `false` | `true` |
| Protection `app_id` | `UNKNOWN` | `4694114` |
| Leftover Actions workflow 340420982 | `UNKNOWN (must be disabled by M0.3)` | disabled/deleted (catalog id `340420982`, name `trusted-ci`) |
| Bootstrap-exception language superseded | `UNKNOWN` | `true` / dated pointer to new `decisions.md` entry |

Identity already filled (not M0.3 unknowns): slug `adaptive-trust-ci`, Installation `156003193`, policy digest `6737355947c21eb561073cb506ebc5698afd170088a34f8eaace50007c57d1a5`, PR **5**, head SHA `56f5462e78c7ebc0ab7e69fbffd5c1371ff7af78`, Check Run `97527445754`.

## 4. Bootstrap-exception language (supersede, do not silently delete)

| Path | Current wording |
| --- | --- |
| `README.md` L11 | “The App-owned check is not live in this release; merge of PR #2 is a bootstrap exception (see decisions.md).” |
| `CHANGELOG.md` 2.0.12 | “rebase-merge of draft PR #2 is a bootstrap exception because the App-owned check is not live yet” |
| `decisions.md` **2026-08-23 — M0 live Trust Authority bootstrap exception for M1 start** | “Exception does not create adaptive-trust-ci/verified, protect main, or authorize merge. Revoke the exception when a live App-owned check exists on an exact PR SHA.” |
| `decisions.md` **2026-08-23 — Bootstrap merge of PR #2** | “`main` is unprotected, so rebase-merge of PR #2 is the named bootstrap exception; do not forge `adaptive-trust-ci/verified@*` or protect `main` in this slice.” |
| `decisions.md` **2026-08-24 — Close M0.2** | “Do not protect `main` until M0.3.” — **this sentence is the live gate**; after M0.3, add a new entry; do not rewrite M0.2 history as if protection already happened then. |
| `decisions.md` **2026-08-24 — Host-socket overlay** | “public webhook registration and `main` protection remain out of scope.” — historical for that slice; webhook later closed; protection still out of that slice. |
| `DARK_FACTORY_ROADMAP.md` L247 | “Remove or supersede the bootstrap-exception language once live authority is established.” (unchecked) |
| Spec exit extras | “bootstrap-exception language in `decisions.md` / README superseded.” |
| Plan M0.3 | “Supersede bootstrap-exception language (M1 start, PR #2, PR #4)” |

`AGENTS.md` describes **how** merge trust works (`adaptive-trust-ci/verified@<policy-sha12>`, App-owned check). It does **not** claim `main` is unprotected; it stays valid after M0.3.

## 5. Check name + App ID (stable identifiers, already correct)

| Path | Note |
| --- | --- |
| Activation report | Required check + App ID 4694114 |
| `engineering/changes/20260824-user-query-давай-далее-user-query-54313e/brief.md` | “check `adaptive-trust-ci/verified@6737355947c2` bound to App ID `4694114`” |
| This package `evidence/branch-protection-payload.json` | Same pair |
| Plan M0.2 check-run row | App `4694114`, epoch `@6737355947c2` |
| Spec live-gap | leftover `trusted-ci` **id 340420982**, path `.github/workflows/trusted-ci.yml`, **state=active** |

## 6. Leftover Actions workflow `trusted-ci` / 340420982

| Path | Current wording |
| --- | --- |
| Spec live-gap | leftover workflow `trusted-ci` **id 340420982**, path `.github/workflows/trusted-ci.yml`, **state=active**, 0 runs on `main` |
| Plan M0.3 | “Disable leftover Actions workflow `340420982`” (unchecked) |
| Activation report | `UNKNOWN (must be disabled by M0.3)` |
| Tree | **no** `.github/workflows/trusted-ci.yml` (file absent; catalog leftover only) |

After disable, catalog state is the thing that changes; git still must **not** revive `.github/workflows/`.

## 7. Change-package brief (this slice)

`engineering/changes/20260824-user-query-давай-далее-user-query-54313e/brief.md`:

> Disable leftover Actions workflow 340420982. Apply `branch-protect` payload for `main`: check `adaptive-trust-ci/verified@6737355947c2` bound to App ID `4694114`. Do not merge PR #5. Do not mint human approval keys. Do not grant Administration to the GitHub App.

`requirements.md` / `architecture.md` in this package are still empty templates.

## 8. What must not be treated as merge authority after protect

Local receipts, `grok_approve.py` grants, GitGuardian, leftover Actions `340420982`, same check **text** from a non-App actor. Branch protection must keep `app_id: 4694114` on context `adaptive-trust-ci/verified@6737355947c2`.

## 9. Impact surface for the write owner (docs only, after live GitHub ops)

1. Fill activation-report cells: `main` protected, Protection `app_id`, leftover workflow, bootstrap-exception superseded.  
2. New `decisions.md` entry: exception **revoked because live App-owned check exists**, not because a check was forged.  
3. README current-state L11: drop “check is not live / PR #2 bootstrap exception” once that is no longer true of the product tree.  
4. Check off plan M0.3 and roadmap branch-protection items.  
5. Do **not** merge PR #5 in this slice (brief). Do **not** grant Administration to App `4694114`.

## Out of scope / not implementation of protection

Historical change-package evidence under other `engineering/changes/20260824-*` directories **describes** unprotected `main` and workflow 340420982; they are frozen reviews, not the operator live report. `trust-ci/runtime/trust-store.json` actor `claw-m01-bootstrap` is a **trust-store actor name**, not the merge bootstrap exception.
