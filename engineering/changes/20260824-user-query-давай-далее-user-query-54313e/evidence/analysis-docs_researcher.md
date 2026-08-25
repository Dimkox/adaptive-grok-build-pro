# docs_researcher — sentences to supersede for M0.3 bind-main

Route `54313e326a39`. Change `20260824-user-query-давай-далее-user-query-54313e`. Read-only recovery. No APIs invented. `engineering/adr/` is empty (no ADR files). Stubs `engineering/decisions.md` and `engineering/mistakes.md` only say “Canonical log is /decisions.md” / `/mistakes.md`.

**M0.3 intent (this package `brief.md`):** protect `main` with check `adaptive-trust-ci/verified@6737355947c2` and App ID `4694114`; disable leftover Actions workflow `340420982`; supersede bootstrap-exception / “main unprotected” language. Do not merge PR #5. Do not mint human keys. Do not grant Administration to the App.

**Not merge-gate language:** “Never use GitHub Actions” / “No GitHub Actions” in `AGENTS.md`, `README.md`, `trust-ci/README.md`, CHANGELOG “Still no GitHub Actions”, and `decisions.md` 2026-08-16. Those forbid Actions as CI; they do **not** claim Actions is the merge gate. **No current product sentence says GitHub Actions is the merge gate.** Closest historical confuse-with-merge-gate: CHANGELOG 2.0.6 and `decisions.md` “only quality gate” = **local `grok_verify`**, not Actions.

---

## 1. `README.md` (must update for M0.3 current-state)

```
- Independent CI candidate: [`trust-ci/`](trust-ci/) — … **No GitHub Actions.**
- Trust CI service identity is **2.1.0** (`trust-ci/pyproject.toml`); it is not product `2.0.12`. The App-owned check is not live in this release; merge of PR #2 is a bootstrap exception (see decisions.md).
```

(lines 10–11). Supersede the second sentence: App-owned check **is** live (Check Run name `adaptive-trust-ci/verified@6737355947c2`, App `4694114`); PR #2 bootstrap exception is **revoked** once `main` is protected. Keep “No GitHub Actions” (absence of GHA, not merge authority).

Line 9 already says local verify is preflight, not merge authority — keep.

---

## 2. `decisions.md`

**Keep as historical but mark superseded (plan item: M1 start, PR #2, PR #4):**

```
## 2026-08-24 — Close M0.2 after live GitHub webhook; residual human/runner/policy
… Do not protect `main` until M0.3.
```

(lines 5–7). After M0.3, this sentence is false if left as standing order.

```
## 2026-08-24 — Host-socket overlay produced the first App-owned Check Run
… public webhook registration and `main` protection remain out of scope.
```

(lines 33–35). Public webhook is now Funnel live; M0.3 **is** in scope.

```
## 2026-08-23 — M0 live Trust Authority bootstrap exception for M1 start
User approved unattended execution. M0 exit criteria are not met on this host.
M1 may proceed. Exception does not create adaptive-trust-ci/verified, protect main, or authorize merge. Revoke the exception when a live App-owned check exists on an exact PR SHA.
```

(lines 45–48). Plan names this as “M1 start”. Revoke: live App-owned check exists on PR #5 SHAs (`97524725228` / `97527445754`).

```
## 2026-08-23 — Bootstrap merge of PR #2 without a live App-owned check
The user ordered commit, push, merge, and release while the Trust CI GitHub App check does not exist yet. `main` is unprotected, so rebase-merge of PR #2 is the named bootstrap exception; do not forge `adaptive-trust-ci/verified@*` or protect `main` in this slice.
```

(lines 54–56). This is the primary bootstrap-exception paragraph. Do not delete history; add a later entry that M0.3 **revokes** it because a live check exists — never by forging one.

```
## 2026-08-16 — Never GitHub Actions
Local `make verify` / `python3 scripts/grok_verify.py --mode pr` is the only quality gate. …
```

(lines 114–116). **Quality** gate vs **merge** gate. After M0.3, merge gate is App-owned Check + branch protection; local verify stays preflight. Do not rewrite as “Actions is the gate.”

**PR #4** is not in root `decisions.md`. It lives in closed change package `engineering/changes/20260824-user-query-да-user-query-37bf04/evidence/analysis-architect.md`: “rebase-merge … onto unprotected `main`. … Do not protect `main`.” Plan still lists “Supersede bootstrap-exception language (M1 start, PR #2, PR #4)”.

---

## 3. `mistakes.md`

No sentences about unprotected `main`, bootstrap-exception, “Do not protect main”, or GitHub Actions as merge gate. Nothing to supersede.

---

## 4. `engineering/runbooks/trust-ci-activation-report.md`

Lead (line 5):

```
… M0.2 webhook stage is closed; … `main` is still unprotected.
```

Table:

```
| `main` protected | false |
| Protection `app_id` | UNKNOWN |
| Leftover Actions workflow 340420982 | UNKNOWN (must be disabled by M0.3) |
| Bootstrap-exception language superseded | UNKNOWN |
```

(lines 30–32, 35). M0.3 must fill: `main` protected true; `app_id` `4694114`; leftover workflow disabled; bootstrap-exception language superseded.

---

## 5. `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md`

Line 3: `No GitHub Actions.` (keep: forbid GHA.)

Line 5: `Do not assert “main is unprotected” (that would fight M0.3).` (test invariant; keep.)

Line 28 (M0.1, **checked**, stale fact):

```
- [x] Public GitHub webhook still absent; `main` still unprotected
```

Line 41 (M0.2, **checked** as a “do not” of that slice):

```
- [x] **Do not protect `main`** in M0.2 (M0.3 remains **not done**)
```

### M0.3 checklist — all still unchecked (lines 47–52)

```
- [ ] Temporary human admin token: `adaptive-trust-ci branch-protect` with epoch name **and** App ID
- [ ] Prove same text from another actor fails; direct push / force-push / delete / merge-without-check fail
- [ ] Disable leftover Actions workflow `340420982`
- [ ] Supersede bootstrap-exception language (M1 start, PR #2, PR #4)
- [ ] Fill activation report with IDs and digests; no secrets
- [ ] Mark PR ready; merge only through the live App-owned check
```

**Note:** this package `brief.md` says **Do not merge PR #5**. The last box (“Mark PR ready; merge…”) is **not** this slice’s merge of #5; do not tick it by merging #5. Fill protection + disable workflow + supersede language + report fields without merging #5.

### Other still-unchecked M0.2 residual (not merge authority; not this bind-main slice)

```
- [ ] Offline attestation verify — **not done** (`needs_approval`; no human private key on claw)
- [ ] `trust-ci/**` → `needs_approval` → human Ed25519 requeue … — **not done**
- [ ] Source-mutation fail-closed — **not done** (runner-loader exited; no live runner)
```

Policy/holdout retitle also **not done** (called out on the SHA-change checked line).

---

## 6. `docs/superpowers/specs/2026-08-24-m0-live-trust-authority.md` (related contract)

Freeze table (historical, keep labeled freeze):

```
| `GET .../branches/main/protection` | HTTP 404 `Branch not protected` |
| GitHub Actions registry | leftover workflow `trusted-ci` **id 340420982**, path `.github/workflows/trusted-ci.yml`, **state=active**, 0 runs on `main` |
```

Rollout step 4 (binding):

```
4. **Then** protect `main` with the exact epoch name **and** App ID. Disable leftover Actions workflow `340420982`. Supersede bootstrap-exception language because a live check exists — never by forging one.
Protecting `main` before the live check can lock the repository.
```

Exit extras:

```
Also: leftover Actions workflow `340420982` disabled or deleted; bootstrap-exception language in `decisions.md` / README superseded.
```

Forbidden: `Protecting `main` before the live App-owned check` — live check already exists; this forbids **early** protect, not M0.3.

Stale in spec body: “M0.2 is still incomplete (no public HTTPS webhook)” (line 38) vs plan/report “M0.2 webhook stage closed.”

---

## 7. `trust-ci/README.md`

No “main unprotected” / bootstrap-exception / “Do not protect main”.

```
It does **not** use GitHub Actions.
```

(line 3)

```
The first production contour does not auto-merge, auto-deploy or mutate production. Merge remains human-owned. … GitHub Actions are not installed or required.
```

(line 288). Keep. Merge gate is App-owned Check, not Actions; human still owns merge click.

---

## 8. `AGENTS.md`

```
- The authoritative merge gate is the GitHub App-owned policy-epoch Check Run `adaptive-trust-ci/verified@<policy-sha12>` for the exact pull-request head SHA. Branch protection binds that exact check name to the configured GitHub App ID.
- Never use GitHub Actions for this repository. …
```

(lines 11–12). Already the **target** wording. Does **not** say main is unprotected or that Actions is the gate. Align README/decisions/CHANGELOG with this, not the reverse.

Prohibited: `Adding `.github/workflows/` or any GitHub Actions dependency.` (line 158). Keep.

---

## 9. Related product docs (no ADR files)

**`CHANGELOG.md` 2.0.12 (line 8):**

```
- PR-only delivery; rebase-merge of draft PR #2 is a bootstrap exception because the App-owned check is not live yet
```

Supersede in a later CHANGELOG/current-state if README identity stays 2.0.12, or note in decisions that this changelog line is historical for the 2.0.12 ship.

**`CHANGELOG.md` 2.0.6 (line 64):**

```
- No GitHub Actions / Dependabot; local `python3 scripts/grok_verify.py --mode pr` is the only gate. `--with-ci` is forbidden.
```

Historical quality-gate wording. Not Actions-as-merge-gate.

**`DARK_FACTORY_ROADMAP.md`:**

```
Milestones M1, M2, and M3 may be developed in parallel only after M0 has a live proof or an explicitly documented bootstrap exception approved by the user.
```

(line 206)

```
- [ ] Apply branch protection only after the live check has succeeded.
- [ ] Verify that branch protection binds the exact policy-epoch check and the GitHub App ID.
- [ ] Verify that direct push, force push, branch deletion, and merge without the required check fail.
- [ ] Remove or supersede the bootstrap-exception language once live authority is established.
```

(lines 244–247)

```
- [ ] Refuse dispatch when M0 Trust CI authority is unavailable unless the user records a named bootstrap exception.
```

(line 614)

**`engineering/runbooks/trust-ci-rollout.md` line 5:**

```
… bind branch protection to its GitHub App ID, and only then protect `main`. GitHub Actions remain absent.
```

Instructional order, not “main stays unprotected forever.”

**`GROK_BUILD_HANDOFF.md`:** PR #2 draft until App-owned check; “GitHub Actions-based implementation … superseded”; “Do not add GitHub Actions”. Handoff branch `feat/trust-ci-control-plane` is historical (PR #2 merged via bootstrap).

---

## 10. What **not** to claim

- Do not say GitHub Actions is or was the merge gate in current AGENTS/README.
- Leftover catalog workflow `340420982` (`trusted-ci.yml`, freeze: **state=active**, 0 runs on `main`) is residue to **disable**, not a required check.
- Residual M0.2 human/attestation/mutation/retitle stay **not done**; they are not required to bind `main` per user-closed M0.2 (`decisions.md` 2026-08-24) but they are **not** merge authority either.
- `main` protected | false and Bootstrap-exception | UNKNOWN are **current report facts** until M0.3 writes succeed.

---

## Sources used

`README.md`, `decisions.md`, `mistakes.md`, `AGENTS.md`, `CHANGELOG.md`, `DARK_FACTORY_ROADMAP.md`, `GROK_BUILD_HANDOFF.md`, `trust-ci/README.md`, `engineering/runbooks/trust-ci-activation-report.md`, `engineering/runbooks/trust-ci-rollout.md`, `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md`, `docs/superpowers/specs/2026-08-24-m0-live-trust-authority.md`, this change `brief.md`. No `.env`/PEM. No ADR files present.
