# docs_researcher — M0 git vs live vs plan (route 85a17ed2e935)

Read-only. Sources: git-tracked docs/ADRs/runbooks/CLI help strings. No `.env`, no PEM.

Compared:

- **HEAD** `1fc942065a124ce75659bd082519d8ebc37774e8` — message: `ops: record Trust CI App 4694114 / install 156003193; DinD blocked`
- **Dirty working tree** — `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md`, `engineering/runbooks/trust-ci-activation-report.md`, `decisions.md` already describe overlay worker + Check Run `97390635614` on PR #5
- **Branch history** — `9f84dfd` froze spec/plan/invariants; later `d38e43d`, `60eaa48`, `1fc9420`

Live facts already recorded in WT (not invented here): worker via untracked host-socket overlay on `claw`; Check Run `97390635614` App `4694114` on SHA `1fc9420`; `conclusion=action_required`; public webhook absent; `main` unprotected.

---

## 1. Git-tracked docs stale vs live (claw)

| Path | HEAD / committed claim | Live / WT fact | Verdict |
| --- | --- | --- | --- |
| `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md` **HEAD** | M0.1: DinD unhealthy; worker not running | Worker running via overlay | **HEAD stale**; WT plan already patched for M0.1 |
| Same plan **M0.0 checkboxes** (HEAD and WT) | Spec/plan/activation-report/invariants/verify/draft PR all `[ ]` | Those artifacts exist on branch from `9f84dfd`; PR #5 exists | **Docs drift (false negatives)** — see §4 |
| Same plan **M0.2** HEAD | Check Run / webhook / attestation all unchecked, no PR ids | Partial Check Run via **local HMAC**, not GitHub-registered webhook | HEAD omits partial proof; WT notes partial |
| `docs/superpowers/specs/2026-08-24-m0-live-trust-authority.md` | “Live gap”: no Trust CI containers; `M0 is source-complete and live-absent` | API+postgres+worker live on `127.0.0.1:18080`; first Check Run exists | **Spec freeze snapshot is historical**, not current claw |
| `engineering/runbooks/trust-ci-activation-report.md` HEAD | Template `UNKNOWN` | WT fills host, App/install IDs, policy digest, PR #5, Check Run id, image digests; attestation/kill/backup/`main` still `UNKNOWN` | WT is closer; HEAD is empty template |
| `README.md` current-state | “The App-owned check is not live in this release; merge of PR #2 is a bootstrap exception” | App-owned Check Run exists on **this branch’s** SHA but `main` still unprotected; check is `needs_approval`, not merge-success | **Partially stale for claw**; still true that **product `main` / 2.0.12** has no live gate. Cold reader of the **milestone branch** will think nothing ran. |
| `decisions.md` HEAD | “M0.1-complete worker IDs… DinD stayed unhealthy… worker never reached running” | Newer WT entry: overlay produced Check Run `97390635614` | HEAD decisions contradict later WT; both bootstrap-exception entries (2026-08-23 M1 start, PR #2) **not superseded** (M0.3) |
| `trust-ci/README.md` | Generic deploy: `docker compose up -d postgres migrate api worker`; isolated worker; HTTPS webhook then protect | Tracked compose still documents DinD; claw uses **untracked overlay**; no public HTTPS | README is the **intended** topology, not claw’s overlay. Do not rewrite as if overlay were the product contract. |
| `engineering/runbooks/trust-ci-rollout.md` | Rollout assumes HTTPS webhook then disposable PR then protect | Proof used loopback HMAC; webhook still missing | Procedure names are correct; **M0.2 is not complete** |

Do **not** treat overlay as documented API. Tracked compose + `trust-ci/README.md` still name isolated DinD / `docker-engine` + `runner-loader`.

---

## 2. Offline attestation verify (no secrets)

Documented **operator** wording:

- `engineering/runbooks/trust-ci-rollout.md`: “Fetch `/attestations/<job_id>` and verify it offline with the CI public key.”
- `trust-ci/README.md` Verification section does **not** name the CLI; it says publish the public key for offline verification.
- Activation report field: `Attestation verified offline | UNKNOWN` (WT). Job id recorded: `1b63d10b-90c1-498a-97b8-7b5e0ea76aec`.

**Exact CLI** (contract in `trust-ci/src/adaptive_trust_ci/cli.py`, also named in older change-package notes):

```bash
adaptive-trust-ci attestation-verify \
  --attestation <path-to-envelope.json> \
  --public-key <path-to-ci-public.pem>
```

Public key only. Do not pass worker private key, App PEM, or webhook secret.

M0.2 checkbox “Offline attestation verify” remains **unchecked** in the plan (HEAD and WT) — that is **not** a false negative; report still `UNKNOWN`.

---

## 3. Kill-switch and backup/restore drills (command names)

**Kill switch** (`trust-ci/README.md`, `engineering/runbooks/trust-ci-rollout.md`, `QUICKSTART.md`):

```bash
adaptive-trust-ci kill-switch on
adaptive-trust-ci kill-switch status
adaptive-trust-ci kill-switch off
```

Default file documented as `/run/adaptive-trust-ci/STOP`. Activation report: `Kill switch drill | UNKNOWN`.

**Backup / restore** — two documented layers (do not invent flags):

1. Runbook `engineering/runbooks/trust-ci-rollout.md` Database backup:

   ```bash
   docker compose exec -T postgres \
     pg_dump --format=custom --no-owner --file=/tmp/trust-ci.dump "$POSTGRES_DB"
   docker compose cp postgres:/tmp/trust-ci.dump ./runtime/trust-ci.dump
   ```

   Restore drill is described in prose (“Perform a restore drill…”) plus rollback sequence: kill-switch → retain PG/attestations → human admin temporarily remove exact required check → repair → prove check → re-protect. `main` is still unprotected, so the protection-removal step is **not** applicable yet.

2. Product CLI (`QUICKSTART.md` + `cli.py`):

   ```bash
   adaptive-trust-ci backup-create
   adaptive-trust-ci backup-verify
   adaptive-trust-ci backup-prune
   adaptive-trust-ci restore-drill --confirm-disposable
   ```

   CLI **required** args (from `cli.py`, not fully shown in QUICKSTART): `backup-create --database-label`; `backup-verify --dump --manifest`; `restore-drill --dump --manifest --confirm-disposable`. QUICKSTART omits those flags — **docs gap**, not a new API.

Activation report: `Backup/restore/restart drill | UNKNOWN`. Plan M0.2 kill/backup boxes still empty — **true open work**.

---

## 4. M0.0 unchecked boxes are false negatives

On `milestone/m0-live-trust-authority` commit `9f84dfd` (`docs: freeze M0 live Trust Authority spec, plan, and invariants`):

- Spec `docs/superpowers/specs/2026-08-24-m0-live-trust-authority.md` **exists**
- Plan (this file) **exists**
- `engineering/runbooks/trust-ci-activation-report.md` **exists**
- Invariant tests and `test_m0_invariants` were part of that freeze
- Draft PR #5 exists (activation report / WT plan)

Yet M0.0 still lists those items as `[ ]` in **both HEAD and dirty plan**. That is checklist lag after the freeze commit, not missing files.

The M0.0 **STOP** (“no compose.yaml up…”) is historically true for the freeze slice and **false as a current operator instruction** — compose already ran on claw.

---

## 5. What «своди все воедино» should update so a cold reader of the branch matches claw

Update **tracked narrative**, not Trust CI policy/images:

1. **Check off M0.0** in `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md` for artifacts already on the branch; keep STOP as a historical note, not current law.
2. **Commit the WT M0.1/M0.2 plan + activation report + overlay decision** so origin matches claw (HEAD still says DinD blocked).
3. **Annotate the spec “Live gap” table** as probed-at-freeze; add a “live now” pointer to the activation report so the spec does not claim `live-absent` as present tense.
4. **`README.md` current-state**: distinguish product `main` 2.0.12 (bootstrap exception, no protection) vs **this milestone branch** (App-owned Check Run observed, webhook/HTTPS/`main` still open). Do not claim M0 exit criteria.
5. **`decisions.md`**: keep 2026-08-23 bootstrap exceptions until M0.3; do not delete them. The later overlay/Check Run entries must land so they are not only WT. M0.3 still owns “supersede bootstrap-exception language”.
6. **Do not** rewrite `trust-ci/README.md` compose as host-socket overlay; document overlay as **untracked host exception** in plan/activation report only.
7. **Continue M0.2** (not M0.3): public HTTPS webhook; `attestation-verify` with published CI **public** key; SHA/policy/holdout retitle; `trust-ci/**` approval requeue; source-mutation; kill-switch + backup/restore drills. Fill remaining `UNKNOWN` in activation report. **Do not protect `main`.**

Unchanged truth for a cold reader: leftover Actions workflow `340420982`; no GitHub-registered webhook; check `needs_approval`; attestation/kill/backup drills unproven; M0.3 not started.
