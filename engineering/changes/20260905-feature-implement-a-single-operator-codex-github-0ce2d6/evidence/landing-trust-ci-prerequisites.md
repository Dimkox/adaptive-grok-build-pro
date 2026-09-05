# Landing Trust CI prerequisites — read-only audit

## Binding and executive ruling

This audit is bound to route `0ce2d62a018e`, tracked source HEAD
`6f3b6ed2853b7a6f78804888cffca578d4dc9448`, tree
`913f646649f878e97959d7ba2489a57de2379a1d`, and GitHub observation time
`2026-09-05T15:16Z`. The target repository was observed at default branch
`main`, exact commit `699010380f4f90a0193a9c22090c35e6aded7d2c`. Only tracked
Trust CI source/examples, operator-safe repository documentation, and read-only
GitHub API responses were inspected. No environment file, key, credential,
deployed policy/holdout, database/runtime state, webhook delivery body, model
call, test suite, or external write was accessed or performed.

**Ruling:** there is no evidence-backed, operator-settings-only path that can
make the exact old context `adaptive-trust-ci/verified@06ecf1c875bc` both run
for and be required on `Dimkox/ai-dark-factory-landing` today.

1. The target is private and `main` is unprotected. GitHub's protection and
   ruleset GET endpoints both return `403` with `Upgrade to GitHub Pro or make
   this repository public to enable this feature.` A plan/visibility decision is
   therefore a hard prerequisite to making any check mandatory, though not to
   publishing an App-owned Check Run.
2. Current tracked Trust CI is a single global repository policy. Its template
   allowlists only `Dimkox/adaptive-grok-build-pro`, and its mandatory commands
   and external holdout are specific to that repository
   (`trust-ci/config/policy.example.json:3-59`). The landing has its own
   stdlib unittest suite but no `scripts/grok_verify.py`, `.grok-stack`, or
   `trust-ci/` tree, so merely appending its name to the current global allowlist
   would not produce a meaningful passing gate.
3. More fundamentally, the normalized `allowed_repositories`, commands,
   sandbox, holdout digest, and approval rules are inputs to the policy SHA-256,
   and the first 12 hex characters are appended to the check name
   (`trust-ci/src/adaptive_trust_ci/policy.py:227-270`). Adding the landing or
   changing its checks therefore cannot retain `06ecf1c875bc` under this policy
   form.

The old exact name is valid for the landing only if an operator, using the
deployed trust domain, can positively prove that the already-deployed full
policy digest
`06ecf1c875bc12fa696956998983e04b102f28571a586bc3bb7a2fff5083fdb2`
already authorizes this exact repository and supplies compatible independent
checks. That cannot be established from tracked source or GitHub, and deployed
runtime inspection was expressly out of scope. Until proved, fail closed: do
not configure landing `main` to require `@06ecf1c875bc`, because an unproducible
required context would lock delivery.

The safe expected outcome is a **repository-specific landing policy epoch**,
`adaptive-trust-ci/verified@<landing-policy-sha12>`, still owned by GitHub App
ID `4694114`. The existing `@06ecf1c875bc` remains the authority for
`Dimkox/adaptive-grok-build-pro`; it is not a portable brand name.

## What is observable now

| Item | Read-only observation | Consequence |
| --- | --- | --- |
| Target identity | Repository ID `1357006647`, owner type `User`, visibility `PRIVATE`, default branch `main`; current viewer has `ADMIN`. | The operator can install the App and manage protection once the product tier permits it. |
| Current target state | `main` is at `699010380f4f90a0193a9c22090c35e6aded7d2c`, reports `protected=false`, has no PRs, and its current head has zero Check Runs. | There is no target-repository proof yet that Trust CI intake or App publication works. Absence of runs is not proof that the App is absent because no PR event exists. |
| Plan/visibility barrier | Both branch-protection and ruleset reads return the explicit Pro-or-public `403`. | This private repository under its current entitlement cannot enforce the required check. GitHub documents protected branches for public Free repositories and private repositories on Pro/Team/Enterprise. |
| App public identity | `Adaptive Trust CI`, slug `adaptive-trust-ci`, App ID `4694114`, owner `Dimkox`; permissions are `checks:write`, `contents:read`, `metadata:read`, `pull_requests:write`; subscribed events include `pull_request`. | The registered App has the capabilities needed to receive PR events and create checks. The worker further reduces its installation token to `checks:write`, `contents:read`, `pull_requests:read` (`trust-ci/src/adaptive_trust_ci/github_app.py:75-91`). |
| App ownership precedent | Historical exact-head check `101099224099` on the source repository is a successful `adaptive-trust-ci/verified@06ecf1c875bc` Check Run owned by App `4694114`. | The App identity and old epoch are real, but that proof is repository- and SHA-specific and cannot transfer to the landing. |
| Installation selection | `GET /repos/Dimkox/ai-dark-factory-landing/installation` returned `401` because the current credential is not an App JWT; the user-installations endpoint likewise was unavailable to this token class. | Installation on the landing is **UNKNOWN**, not absent. An authorized human/App-side observation is required. No key should be exposed to an agent. |
| Landing verification surface | The exact target tree contains a stdlib suite under `tests/`; its README specifies `python -m unittest discover -s tests -v`. It has no GitHub Actions workflow. | A landing profile can use one bounded local unittest command, but still needs a separate external holdout to remain independent. |

GitHub's current documentation confirms the relevant platform constraints:

- [protected-branch availability and App-selected required-check source](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches);
- [the seven-day successful-check prerequisite](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks);
- [selecting repositories for an App installation](https://docs.github.com/en/apps/using-github-apps/reviewing-and-modifying-installed-github-apps);
- [Checks API writes require a GitHub App with Checks write permission](https://docs.github.com/en/rest/checks/runs);
- [installation tokens cannot exceed the installation's repository selection or permissions](https://docs.github.com/en/rest/apps/apps#create-an-installation-access-token-for-an-app).

## Exact minimum to make the gate run

### 1. Supply a repository-specific trusted policy, not a widened global one

Current shipped source exposes one `Policy`, one global command list, one
holdout, and an exact allowlist (`trust-ci/src/adaptive_trust_ci/policy.py:164-285`);
the API rejects any repository outside it (`trust-ci/src/adaptive_trust_ci/api.py:75-102`).
Repository-scoped profile support is explicitly recorded as absent from `main`
(`START_HERE.md:14`). Therefore the smallest invariant-preserving prerequisite
is a clean, reviewed successor to the stale repository-profile work, followed by
deployment into the independent Trust CI domain. Do not weaken the source
repository's four mandatory commands or replace its holdout with a lowest-common-
denominator landing check.

The landing profile must bind at least:

- exact repository `Dimkox/ai-dark-factory-landing`;
- the existing pinned no-network runner image and empty allowed environment;
- bounded command argv
  `python3 -m unittest discover -s tests -v` for the exact checkout;
- a landing-specific external holdout directory and measured digest, mounted
  read-only outside the checkout, with an independent static-site validator;
- explicit approval globs/scopes appropriate to this repository; and
- existing exact-SHA checkout, source-mutation rejection, signed attestation,
  durable retry, and output-redaction behavior unchanged.

The external holdout should minimally reject GitHub Actions, unexpected
executable content or remote first-load dependencies, and—while this pilot is
narrow—changes outside its permitted `index.html`/`content.css` surface. It
must validate from the base/head diff and static files, not trust tests supplied
by the PR. Any profile, holdout, runner image, or approval-rule byte change
creates a new profile digest and invalidates old jobs/approvals by design.

### 2. Grant the existing App access to the target repository

From the human-owned GitHub App installation settings, verify whether App
`4694114` already has `ai-dark-factory-landing` selected. If the existing
personal-account installation uses selected repositories, add exactly this
repository. Because both repositories are owned by `Dimkox`, this should use
the existing account installation; verify rather than assume its historical
installation ID. The current worker accepts one fixed installation ID
(`trust-ci/src/adaptive_trust_ci/worker.py:34-45`), so a genuinely different
installation would require a separate worker/configuration or reviewed
repository-to-installation resolution before activation.

Confirm, without exposing any token or key, that a reduced installation token
can read the exact target commit and create/update a Check Run. The public App's
broader `pull_requests:write` grant is not a blocker because the worker requests
read-only pull-request scope, but reducing the registered App permission at a
later maintenance window is sensible hardening and not required for this
pilot.

### 3. Prove intake and one exact-head success before protection

Ensure the App's existing HTTPS webhook is active for `pull_request` events on
the newly selected repository and uses the API's existing HMAC secret. Then a
human—or an agent with separate exact grants for branch push and PR creation—must
open a disposable PR against landing `main`. This audit did not do so.

For that exact PR head, require all of the following before proceeding:

1. the webhook is accepted for the exact repository and creates one durable job;
2. the worker checks out the exact base/head through the selected installation;
3. the landing external holdout and the configured unittest command pass in the
   no-network immutable runner without tracked-source mutation;
4. a signed attestation binds repository, PR, base SHA, head SHA, landing policy
   digest, commands, holdout and required approval scopes; and
5. GitHub shows one successful
   `adaptive-trust-ci/verified@<landing-policy-sha12>` owned by App `4694114` on
   that exact head.

GitHub states that a required status check must have completed successfully in
that repository during the preceding seven days. This proof therefore precedes
branch protection; it is not optional ceremony.

## Exact minimum to make the gate required

### 4. Resolve the GitHub product-tier barrier by one explicit human choice

Choose exactly one:

- **Confidentiality-preserving default:** upgrade the `Dimkox` account to
  GitHub Pro and keep the repository private.
- **No-plan-cost alternative:** make the repository public, but only after a
  human confirms every tracked file and history may be disclosed. Publication
  cannot make already copied history private again, so it is not an automatic
  technical fallback.

App installation and Check Run publication can be proven before this decision.
Enforcement cannot.

### 5. Bind `main` to the observed landing epoch and App ID

After the successful check is visible, a human administrator uses a temporary
administration credential (or equivalent GitHub UI) to apply the existing
fail-closed protection shape to `main`:

- pull request required;
- strict up-to-date required status check;
- `checks=[{"context":"adaptive-trust-ci/verified@<landing-policy-sha12>",
  "app_id":4694114}]`, not the text-only legacy `contexts` form;
- administrators enforced, conversations resolved, linear history required;
- force push and deletion disabled.

That payload is the tracked implementation in
`trust-ci/src/adaptive_trust_ci/github.py:55-88`. The admin operation must use a
temporary human administration token; the long-lived App must not gain repository
administration (`engineering/runbooks/trust-ci-rollout.md:67-87`). Read back the
rule and perform the documented negative spoof/direct-push checks before calling
the gate enforced.

If, exceptionally, the deployed trust owner proves that the existing exact
`06ecf1c875bc...` policy already contains a compatible landing profile, substitute
the literal `adaptive-trust-ci/verified@06ecf1c875bc` in this step—but only after
an App-`4694114` success with that exact name has appeared in this repository in
the last seven days. GitHub currently shows no such run.

## Human-signed approval boundary

Trust CI approval and GitHub administration are separate authorities:

- A clean successor implementing repository profiles changes `trust-ci/**` and
  therefore matches the tracked `governance` approval rule
  (`trust-ci/config/policy.example.json:61-82`). Its exact PR SHA requires a
  human-signed `governance` envelope before the existing Trust CI can conclude
  success. Added Docker/compose/systemd material could additionally match
  `production`.
- The expected pilot landing diff, limited to `index.html` and `content.css`,
  matches none of the current example's governance/database/production globs.
  If the deployed landing profile retains that outcome, it needs no human-signed
  Trust CI scope. Only the deployed policy is authoritative; if the Check Run
  says `action_required`, the named missing scope must be signed.
- A signed approval binds exact repository, PR, base SHA, head SHA, policy
  digest and scope and expires; any SHA/base/policy/holdout change requires a
  fresh one (`trust-ci/src/adaptive_trust_ci/api.py:111-149`,
  `trust-ci/README.md:194-236`). The private approval key remains solely on the
  human workstation; an agent must never request, read, generate or submit it.
- Installing the App, choosing Pro/public, deploying policy/holdout, and editing
  branch protection are human/operator external changes. They require repository
  ownership and explicit operational authorization, but they are not made valid
  by a Trust CI approval envelope or a local `grok_approve.py` receipt.

## Finite stop condition and rollback

Onboarding is complete only when a read-only evidence capture shows all of:

1. target `main` remains the intended base and an exact disposable PR head is
   named;
2. the target repository is selected in App `4694114`'s installation;
3. the deployed landing policy/holdout full digests and resulting check name are
   recorded without secret material;
4. one exact-head App-owned check succeeds with an offline-verified attestation;
5. `main` protection reads back strict, enforced for admins, with the exact
   context plus `app_id=4694114`; and
6. a same-name result from another actor, a stale SHA, a direct push, force push,
   and deletion do not satisfy or bypass the rule.

Stop as blocked—without installing protection—on unknown App selection, policy
ambiguity, a missing/failed check, absent attestation, a stale epoch, or the
current private-plan `403`.

Before protection, rollback is simply to leave `main` unprotected, remove the
target from the App's selected repositories if desired, and retain the failed
job evidence. After protection, follow the existing emergency runbook: enable
the Trust CI kill switch, preserve PostgreSQL/attestations, and use a human admin
credential to remove only the exact required epoch while service/policy is
repaired; prove a restored/new epoch on a disposable PR before reapplying the
rule (`engineering/runbooks/trust-ci-rollout.md:106-137`). A policy or holdout
rollback is itself a new epoch. If public visibility was chosen, returning the
repository to private does not retract prior disclosure or copies; this is why
Pro is the default when confidentiality matters.
