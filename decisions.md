# Decisions

<!-- BEGIN ADAPTIVE GROK GOVERNANCE PROJECTION: decisions.md -->
> **NON-AUTHORITATIVE PROJECTION.** Canonical JSON governance records remain authority; this Markdown cannot approve, activate, repay, or accept any record.

## Active governance rules

_No active governance rules._

## Candidate governance rules

_No candidate governance rules._
<!-- END ADAPTIVE GROK GOVERNANCE PROJECTION: decisions.md -->

## 2026-09-09 — Port the separable capability instead of rebasing a superseded branch

`mvp/investor-ready` carried 275 changed files against `main`, but only 35 were unique: the loopback demo UI, its OpenAPI contract, its tests and its change package. The other 240 were M1-M9 work that `main` already received through the squash-merged PR #22, which is why the merge produced add/add collisions on `architecture*.py`, `VERSION` and `START_HERE.md`. Porting the 35 unique files plus the two small backward-compatible core additions they need onto a fresh branch preserved the work and passed the exact gate, while rebasing 152 commits would have re-litigated already-delivered milestones.
## 2026-09-09 — Reproduce the runner capability instead of trusting a bare local gate

Running `grok_verify --mode pr` without `GROK_VERIFY_CAPABILITY=repository-sandbox` fails `factory-postgres-exit` on any host that lacks `uv` or nested containers, which the runner skips by design. Setting the runner-equivalent capability makes the local result comparable to the exact-SHA check and keeps environment gaps from being read as product failures.
## 2026-08-28 — Bind governance handoffs to fresh exact state

Reopen the loader-bound governance root, recompute every component digest and finding, validate the complete M2 evidence envelope, and prove the Git head is exact and clean immediately before publishing the six-field handoff. Keeping projections in marked read-only blocks makes them reviewable without giving Markdown mutation or authority capability.

## 2026-08-28 — Freeze governance transitions as canonical values

Represent rule transitions as immutable canonical-byte `RuleRecord` values and append only typed review or approval records supplied at the transition boundary. This preserved rule identity across revisions and prevented callers from mutating a returned record through nested dictionaries.

Patterns that paid for themselves. Each entry is at most three sentences.

## 2026-09-23 — Preserve the no-owner disposition for #186/#36

The exact-tree and reachable-history audit found no repository-owned shell recorder, while current Python/Trust CI paths already preserve nonzero exit codes. Keeping the change evidence-only avoids inventing a helper or regression target; #36 remains blocked until an authoritative external owner link and reproduction are supplied.

## 2026-09-05 — Calibrate only the accepted pilot vertical

Raise only `FIT-BOUNDED-PILOT-CHANGE` to 400,000 bytes, 10,000 lines, and AST complexity 1,100, leaving global, Factory, and Trust-CI limits unchanged. This preserves a narrow ceiling with at most 15% headroom over the accepted pilot implementation while making the exact route fitness gate reflect its actual bounded scope.

## 2026-08-26 — Provider-neutral factory core with explicit adapter boundary

Keep deterministic policy, state, leases, budgets, and capabilities in a PostgreSQL-backed provider-neutral core; make Codex, Grok, and future providers explicit versioned JSON/JSONL translators with no silent fallback. This preserves one-writer and trust boundaries across provider changes while allowing model-native streams to evolve behind conformance-tested adapters.

## 2026-08-26 — Isolate local PostgreSQL proof in a dedicated database

Use `adaptive_grok_build_pro_test` with four bounded `NOLOGIN` Trust CI roles inside the already-running local PostgreSQL service. Dedicated data and least-privilege roles prove migration/store behavior without touching application schemas or representing the run as deployment.

## 2026-08-26 — Version the strict typed contract as change-spec v2

Freeze schema v1 and its YAML-subset reader for explicit unchanged-history compatibility only; every new or modified spec is canonical JSON using schema v2. This prevents malformed canonical input from downgrading into legacy parsing and gives the exactly-one-key evidence model a new contract identity.

## 2026-08-26 — Rebuild M1 from the approved branch, not the stale baseline

The user explicitly approved rebuilding from the roadmap and its M1 design; preserve merged M0 and later repairs because the roadmap forbids discarding newer work. Treat the existing M1 prototype as characterization input, use dual-read/single-write migration, and deliver trusted-runtime deployment as a separate externally approved operation.

## 2026-09-01 — Converge branch work through one delivery ledger

Many isolated branches and worktrees may preserve implementation evidence, but they converge through one consolidated delivery route before completion. That route updates the five-axis `PROJECT_STATE.json` implementation/review/stack-merge/main-delivery/gate ledger so branch presence is never mistaken for delivery.

## 2026-08-24 — M0.3 bind main; revoke bootstrap exceptions

Live App-owned check `adaptive-trust-ci/verified@6737355947c2` is bound to GitHub App ID `4694114` on protected `main`. Revoke the 2026-08-23 M1-start / PR #2 / PR #4 bootstrap exceptions because that live App-owned check exists (never by forging one). PR #5 stays unmerged while Check Run `97529209576` is `action_required`.

## 2026-08-24 — Close M0.2 after live GitHub webhook; residual human/runner/policy

User ordered M0.2 closed once Funnel + App `pull_request` + App-owned Check Run `action_required` were live (`9d56734`/`97524725228`, later `56f5462`/`97527445754`). Human Ed25519, offline attestation, source-mutation, and policy/holdout retitle stay **not done**; they are not merge authority. Do not protect `main` until M0.3.

## 2026-08-24 — GitHub App pull_request webhook is live

GitHub POSTed `pull_request`/`synchronize` to `https://claw.taild9f611.ts.net/webhooks/github` (HTTP 200) for PR #5 SHA `9d56734`; Check Run `97524725228` App `adaptive-trust-ci` `external_id=0e147461-6de8-415f-b712-d06b2034c735` `conclusion=action_required`. Do not add a repository webhook.

## 2026-08-24 — «Приложуха» is GitHub App adaptive-trust-ci

Operator «приложуха» is GitHub App `adaptive-trust-ci` at `https://github.com/apps/adaptive-trust-ci`. Webhook configuration lives on that App registration, not on a public website and not as a substitute repository webhook. Do not treat a public website as the app; live intake is Funnel `https://claw.taild9f611.ts.net/webhooks/github` plus loopback HMAC characterization.

## 2026-08-24 — ChatGPT-invented public webhook hostname is void

User voided a ChatGPT-invented public webhook hostname: do not configure GitHub App or repository webhook to it, do not probe it, and do not complete certbot for it. Host Apache HTTP leftovers from that slice stay untouched. Leave `TRUST_CI_PUBLIC_BASE_URL` on loopback until a named public HTTPS path actually reaches FastAPI HMAC.

## 2026-08-24 — Apache HTTP leftover exists; public A is not this NAT host

Host Apache plus an HTTP ACME vhost were installed because 80/443 were free (n8n Caddy is 3001/5678). Certbot HTTP-01 cannot run while public A `157.22.187.237` is not this NAT host (`192.168.0.229`, egress `45.85.105.28`). That leftover is not a live Trust CI edge; leave `TRUST_CI_PUBLIC_BASE_URL` on loopback.

## 2026-08-24 — Live named volume is backup source and restart subject only

The M0.2 claw drill restored only into a throwaway tmpfs Postgres (`trust_ci_restore`, hostname not `postgres`) on `adaptive-trust-ci_trust-ci`. Volume `adaptive-trust-ci_trust-ci-postgres` was the dump source and `compose restart postgres` subject, never a restore TARGET. Live project was not `down` or `down -v`.

## 2026-08-24 — Unify git for live M0 facts; continue host-local M0.2

User «своди все воедино и продолжай» unifies already-proven M0 live facts into git on milestone/m0-live-trust-authority and continues host-local M0.2 (kill-switch, attestation 404). It does not name git-push-branch; SHA-change invalidation waits for an explicit push of draft PR #5. Policy/holdout retitle and human Ed25519 requeue remain blocked by the trust boundary.

## 2026-08-24 — Host-socket overlay produced the first App-owned Check Run

Nested rootless DinD cannot start on this Engine, so `claw` used an untracked overlay mounting the host docker socket on `worker` and `runner-loader` only, plus `host.docker.internal:1080` via a host socat to glider. A loopback HMAC POST for draft PR #5 published Check Run `adaptive-trust-ci/verified@6737355947c2` (id `97390635614`, App `4694114`, `external_id` = job id) with `conclusion=action_required`; public webhook registration and `main` protection remain out of scope.

## 2026-08-24 — M0.1-complete worker IDs without PEM; webhook still blocked

User-supplied GitHub App ID `4694114` and installation ID `156003193` were patched in-place into gitignored worker env without reading PEM or minting JWT. Compose-up of `docker-engine`/`runner-loader`/`worker` was issued; DinD stayed unhealthy (`rootlesskit` `operation not permitted`), so the worker never reached running. GitHub webhook registration stays blocked until a public HTTPS URL exists.

## 2026-08-24 — M0.1 claw listener trust-store public key, worker deferred

Bootstrap generated one Ed25519 pair only to insert the public key into untracked `runtime/trust-store.json`, then unlinked the private file so no approval private key remains on `claw`. Worker stays off until GitHub App ID and installation ID exist without reading PEM or minting JWT. The live listener is loopback HTTP on `127.0.0.1:18080` (`postgres` + `migrate` + `api` only).

## 2026-08-23 — M0 live Trust Authority bootstrap exception for M1 start

User approved unattended execution. M0 exit criteria are not met on this host.
M1 may proceed. Exception does not create adaptive-trust-ci/verified, protect main, or authorize merge. Revoke the exception when a live App-owned check exists on an exact PR SHA.

## 2026-08-23 — New release after an existing tag is 2.0.12

`v2.0.11` already peels to `c54fd01`. A new ship therefore bumps VERSION, rebuilds the zip, and tags `v2.0.12`. Do not retag `v2.0.11`.

## 2026-08-23 — Bootstrap merge of PR #2 without a live App-owned check

The user ordered commit, push, merge, and release while the Trust CI GitHub App check does not exist yet. `main` is unprotected, so rebase-merge of PR #2 is the named bootstrap exception; do not forge `adaptive-trust-ci/verified@*` or protect `main` in this slice.

## 2026-08-23 — README stack graph is K16 including Trust CI

Trust CI API, worker, PostgreSQL, runner, holdout and GitHub App are now listed core nodes, so the first mermaid is one K16 clique of 120 undirected `---` edges generated from `itertools.combinations`. A missing pair is a stale map; Trust CI is no longer outside the graph. Prompts and local receipts remain not merge authority.

## 2026-08-23 — Draft pull requests must still enqueue Trust CI jobs

Handoff keeps PR #2 draft until the App-owned check exists, so ignoring `draft=true` webhooks makes that check unreachable. Enqueue opened/synchronize/reopened draft events; keep closed-draft cancellation.

## 2026-08-23 — PostgreSQL restart drills need a named volume

`compose restart` stops the container and discards tmpfs. A named test volume plus `down --volumes` in the trap proves catalog recovery without leaving data behind.

## 2026-08-17 — Skip no-op checks; always push main and release

A dirty change-package tree is not a product change. Do not spend an analysis/review wave on status or leftover paperwork. When product files do change and verify is green, push `origin main` and publish the GitHub Release.

## 2026-08-17 — New release after an existing tag is 2.0.11

`v2.0.10` already peels to `975ccb2`. A new push/release therefore bumps VERSION, rebuilds the zip, and tags `v2.0.11`. Do not retag `v2.0.10`.

## 2026-08-16 — New release after an existing tag is 2.0.10

`v2.0.9` already peels to `f72c0fc`. A new «релиз сделай» therefore bumps VERSION, rebuilds the zip, and tags `v2.0.10`. Do not retag `v2.0.9`.

## 2026-08-16 — New release after an existing tag is 2.0.9

`v2.0.8` already peels to `0284241`. A new «релиз сделай» therefore bumps VERSION, rebuilds the zip, and tags `v2.0.9`. Do not retag `v2.0.8`.

## 2026-08-16 — Green verify means a new release

If `grok_verify --mode pr` and required reviews pass, publish: refresh README, rebuild the zip, tag, push, `gh release create`. Do not sit on an untagged VERSION when the user has standing release consent.

## 2026-08-16 — Publish unpublished 2.0.8, do not invent 2.0.9

`VERSION` is already 2.0.8 and no `v2.0.8` tag exists, so the new GitHub Release is 2.0.8 of the current tree. Rebuild the zip after notes, then tag that commit. Do not retag 2.0.7.

## 2026-08-16 — Split one large task; share memory

One giant prompt produces a stale README and half-finished last miles. Split into concrete subtasks that write facts into `AGENTS.md` / `decisions.md` / `mistakes.md` so the next slice can start without the chat. That is how the self-learning files stay the product map instead of session debris.

## 2026-08-16 — README is the push-time product map

A cold reader (human or LLM) only gets current context if `README.md` is refreshed to the tree being shipped. Before every `git push` or `grok_deploy`, rewrite current state and keep the mermaid a complete pairwise-linked graph. Structure tests fail if that AGENTS.md rule or the complete graph disappears.

## 2026-08-16 — README stack graph is K10 with every pair written out

The caption already promised every core piece is linked to every other. Once `AGENTS.md` / `decisions.md` / `mistakes.md` became core, a K7 mermaid was a lie. Enumerate all 45 `---` pairs so a structure test can fail on a missing link instead of trusting mermaid shorthand.

## 2026-08-16 — Move the live logs; stub the old path

`git mv` (not copy) keeps one source of truth and blame. A two-line stub at the old `engineering/` path stops a stale writer from starting a second log. Root `decisions.md` / `mistakes.md` are what the original prompt named and what a root listing shows.

## 2026-08-16 — Pin tests after bump, pack after VERSION

Hardcoded version asserts go red first so a skipped identity file cannot hide. Pack only after `VERSION` is `2.0.8` so the zip name and in-zip `VERSION` cannot still say `2.0.7`. The 2.0.8 ship used that sequence and the in-zip `VERSION` matched.

## 2026-08-16 — Never GitHub Actions

Local `make verify` / `python3 scripts/grok_verify.py --mode pr` is the only quality gate. Do not add `.github/workflows/`, Dependabot, `--with-ci` copies, or another CI SaaS. `install_into --with-ci` is `SystemExit` / forbidden.

## 2026-08-16 — Ruff lives in ruff.toml, not pyproject.toml

`grok_verify` runs Ruff/Bandit without a packaging marker. Config is root `ruff.toml` (and `bandit.yaml`). Do not add `pyproject.toml` / `requirements.txt` / `setup.py` — those flip `detect_repo` and, with pytest on PATH, skip `python-unittest`.

## 2026-08-15 — Ten is a read-only ceiling

Launch every listed analysis agent in one wave. Ten is `max_parallel_analysis`, not a staffing target and not ten writers. `routing.json` names floors; domain specialists join only on match; `docs_researcher` is on every non-micro wave.

## 2026-08-15 — Root hook shims fail-open after pull

Grok `project/adaptive` may still run `python3 pre_tool_use.py` from the project root. Missing that file is python exit 2 and a full tool lockout. Keep thin root dispatchers into `.grok/hooks/` and `||` allow fallbacks. Never put `_lib.py` at the repo root.

## 2026-08-15 — Commercial product, free, MIT

Treat Adaptive Grok Build Pro as a commercial-grade product that is free of charge and MIT-licensed. No EULA, no paid tier. Do not read «коммерческий продукт» as a production deploy: `_risk` matches `прод` as a word, not as a substring of `продукт`.

## 2026-08-15 — MIT public, not a paid SKU

The repo is MIT, free, and public. Commercial means product bar, not billing. `grok_deploy.py` is public release tooling.

## 2026-08-15 — SubagentStop must emit empty JSON

Grok re-fires SubagentStop when the hook returns `additionalContext`, eight times per agent. Emit `{}` and record the stop only while the id is still in `active`. Do not resume a finished reviewer to recover a truncated report — that is a second loop.

## 2026-08-15 — Unwrap one `-c` layer; reuse follow-ups only if open and same session

`bash -lc 'git push'` is one argv prefix miss, not a reason to write a shell parser: strip a matching quoted `-c`/`-lc` payload and run the existing invocation matcher on the inner chunks. Follow-up tokens stay a prompt-shape test (`should_reuse_active_route`); the hook uses `can_reuse_active_route` so `делай` does not revive a ready route or a leftover from another session.

## 2026-08-14 — Match production side-effects as argv prefixes

Split Bash on `&&` / `||` / `;` / `|` / newlines, strip comments, `NAME=value`, and wrappers, then compare leading tokens to `git push`, `gh pr merge`, `docker push`, `npm publish`, `gh release create`. Bare-word `\brelease\b` / `\bpublish\b` / `\bprod(?:uction)?\b` on the whole string locked `ls`/`cat` of change-package paths and `scripts/grok_approve.py production`. Invocation prefixes unstuck ordinary tools while the real commands stayed gated.

## 2026-08-14 — Rematch every non-follow-up; skip child briefs

Reuse the active route only when `FOLLOW_UP_RE` matches the whole prompt, or the UserPromptSubmit payload is a child (`agent_id` / `You are …`). `is_development_prompt` is the inverse of “has intent keywords”, so leftover high-risk routes stuck on `repair yourself` and architect briefs overwrote the parent `route_id`. Follow-up-only reuse plus child-skip let a repair prompt get a write owner and let reviews run without replacing the route.

## 2026-08-14 — Run unittest from verify without a packaging marker

`verification._python` used `pyproject.toml` / `requirements.txt` / `setup.py` as the only trigger, so this repo’s `tests/` never ran under `grok_verify`. Detect `tests/test*.py` and run `python -m unittest discover -s tests`. Do not add a packaging marker just to light the check — that flips `detect_repo` and, when pytest is present, skips unittest.

## 2026-08-14 — Bind receipts after the last change-package write

`tree_fingerprint` hashes every non-runtime changed file, including `engineering/changes/**/state.json`. Transition the durable package to `ready` first, then run `grok_verify` and `grok_review`. Recording evidence before that last write guarantees stale receipts and a second verification loop.

## 2026-08-29 — Bind repository profiles by effective digest

Exact repository plus effective content digest works because the existing job, store, approval, and attestation fields already preserve immutable identity, avoiding a migration. Catalog mode therefore selects isolated commands and holdouts while legacy schema-v1 parsing remains unchanged.

## 2026-08-24 — M0 CI host is claw, not a laptop

The M0 Trust CI host is hostname `claw` (Xeon E5-2680 v4, ~16 GiB ECC, Ubuntu 24.04). Never call it a laptop; SearXNG already owns `127.0.0.1:8080` and co-located n8n/app databases remain residual risk the user accepted. Trust CI therefore publishes another loopback port (`127.0.0.1:18080` by default) with compose project `adaptive-trust-ci`.

## 2026-08-28 — Multi-role CLIs import after command dispatch

A shared CLI that serves human and server roles must keep module scope stdlib-only and load each dependency slice inside the selected command. Fresh-process import guards proved this keeps private-key and envelope submission paths independent of API, worker and PostgreSQL packages.

## 2026-08-26 — Qualify aggregate criterion identity by spec path

Acceptance-criterion IDs are local to one change spec, so multi-spec attestation coverage uses `engineering/changes/<change>/change-spec.yaml#AC-NNN` while single-spec coverage keeps the historical bare ID. This preserves deterministic, unambiguous aggregation without inventing a repository-global criterion namespace.

## 2026-08-26 — Git path identity is NUL-delimited data

Trusted changed-file and mutation discovery consumes byte-oriented `git ... -z` output, decodes each path as strict UTF-8, and preserves Unicode, whitespace, and backslash characters exactly. Display-oriented line output and slash rewriting are never approval or provenance inputs.

## 2026-08-26 — Architecture adoption is explicit target state

Use a strict, target-owned `architecture/adoption.json` marker as the adoption switch; diagrams, model drafts, and receipts are evidence rather than durable adoption authority. Marker/model absence preserves legacy `not_configured` only when current/route-base trees contain no authority and bounded history contains no canonical adoption marker; incomplete shallow history fails closed because it cannot prove legacy absence.

## 2026-08-26 — Install architecture tools, never target authority

The installer manages architecture modules, CLI, strict schemas, and non-authoritative examples, while an explicit denylist protects `architecture/adoption.json`, `architecture/system.yaml`, and `architecture/rules.yaml` even if a future managed list includes them accidentally. Repository owners adapt and validate the examples, then create the canonical marker manually as the final adoption step.

## 2026-08-27 — Projection rendering is read-only

Return deterministic Mermaid artifacts on stdout and keep checked-in projection updates in the normal reviewed source-edit path; removing the in-place writer eliminated unnecessary repository mutation capability. Queue applicability uses one bounded package-aware provenance result for both fitness and risk so uncertainty fails closed without turning unrelated method names into queue signals.

## 2026-08-27 — Preserve provenance identity and installer mutation ownership

Queue provenance retains tuple/list positions and dictionary keys so only the changed operation's dependency can trigger fitness/risk; ambiguous selection over queue and non-queue values is explicitly unsupported. Installer-created directories remain transaction-owned until complete-path identity is reproved, allowing relocation failure to remove only operation-created entries and restore exact file mode under umask.

## 2026-08-27 — Replace patch accumulation with semantic joins and single-publication install

After repeated adjacent review failures, model queue provenance with bounded monotone abstract values and control-flow joins instead of syntax-specific overwrites. Make installation read-only for existing repositories and publish only a fully prepared new target with one atomic rename, eliminating the impossible promise that a failed rollback can always restore already-mutated external bytes.

## 2026-08-27 — Charge alias components before copying or merging

Represent may-alias state as one member set per component plus a name-to-component map, union smaller components into larger ones, and charge create, merge, fork, and mutation work before performing it. This removes duplicated per-name closure state and makes the configured value ceiling bound alias analysis as well as abstract values.

## 2026-08-27 — Created names are not cleanup ownership proof

Bind cleanup identity from the descriptor returned by the original create/open sequence and compare the current no-follow name before removal. If the directory-create gap or descriptor identity failure leaves ownership unresolved, preserve the entry and emit an exact manual-cleanup diagnostic instead of adopting a later same-name occupant.

## 2026-08-28 — Derived data artifacts are first-class fitness inputs

Treat packaged migration mirrors as applicability and inventory roots, not as checks reached only through a primary-path change. Secret-bearing data classifications require an explicitly authenticated `secret_flow`, while source ownership and allowed-data edges describe the credentialed process that actually performs the read or write.

## 2026-08-28 — Bound migration work before crossing expensive stages

Charge conservative schema, derived-root, matching, inventory, semantic-plan, and blob-read work before each stage, and consume SQL statements lazily. This makes every exhausted budget a typed unsupported result without first performing the work the budget is meant to bound.

## 2026-08-28 — Canonical migrations seed phased history

Treat the immutable `001_schema`, `002_operational_indexes`, and `003_database_roles` names as exact logical versions in history while reserving expand/migrate/contract semantics for new phased artifacts. This preserves the repository's established convention while making version 004 contiguous and rejecting phased reuse of versions 001–003.
Legacy versus phased identity is tracked independently of the free-form group text, so a phased group cannot evade the reservation by copying a canonical stem.

## 2026-08-28 — Authenticate authority outside agent-authored records

Treat `actor_kind`, approver names, timestamps, and authority observations inside task/governance JSON as untrusted claims until an independently verifiable receipt binds the exact subject, digest, scope, action, resource, and expiry. This keeps model/provider output proposal-only and prevents evidence-shaped data from minting governance, control-plane, or delivery authority.

## 2026-08-28 — Preserve nullable contracts with typed schema unions

When a closed schema requires a value or `null`, support the standard JSON Schema type array and test both the allowed null and a rejected non-member type. This preserves fail-closed typing instead of weakening the field to an unconstrained value.

## 2026-08-28 — Normalize only declared governance sets

Sort registry records by stable identity and sort only fields whose governance contract defines set semantics; preserve every other array in source order. This makes equivalent registries digest-identical without silently erasing meaning from ordered schema or future record fields.

## 2026-08-28 — Derive handoff inputs at the trust boundary

Recompute the complete M2 architecture evidence from the clean exact Git base/head with conservative trusted risk, then compare every canonical field to the supplied envelope. A caller file is transport only; its self-hash and aggregate architecture digest do not grant authority.

## 2026-08-28 — Separate worktree governance receipts from committed handoffs

Use a distinct `adaptive-grok.governance-receipt-evidence/v1` digest domain for local receipts and bind it to the worktree fingerprint, applicable Git commits, M2 architecture digest, and all effective M3 state. This prevents a local preflight digest from being mistaken for the clean exact-SHA `GovernanceHandoffV1` consumed by later milestones.

## 2026-08-28 — Bind stacked verification to the immediate reviewed predecessor

Set each stacked milestone route's base commit and clean fingerprint to its exact reviewed predecessor, not the program's inception commit. This keeps code budgets, contract deltas, architecture evidence, and rollback scope local to the milestone while preserving the unchanged route identity and approved scope.

## 2026-08-28 — Evaluate exact handoff inputs against immutable Git objects

Bind every authority and consumed evidence byte to the requested exact-head Git blob before emitting a governance handoff. Clean-worktree sampling remains a diagnostic because a nested rename or content swap can be restored between samples.

## 2026-08-29 — Scope build trust and metadata to the operation

Read-only CI helpers pass the exact canonical repository as command-scoped Git trust while continuing to ignore host configuration. Archive metadata is rendered in memory, leaving explicit generation as the only operation allowed to write the source manifest.
The final measured compatibility diff is 10,739 lines, so the repository-owned architecture ceiling moves narrowly from 10,000 to 10,820 instead of weakening the security or streaming implementation.

## 2026-08-29 — Bind package bytes at the repository descriptor boundary

Exclude symlinks/non-regular entries and open every source component root-relative with `O_NOFOLLOW`, then require the same identity and digest during manifest hashing and ZIP streaming. Create the random sibling with `O_EXCL|O_NOFOLLOW`, retain its fd and digest authority through publication, accept success only after the output name matches that inode, and resolve POSIX-only capabilities lazily so explicit legacy manifest helpers remain portable. Bind all output operations to one effective-UID-owned private parent fd beneath trusted/non-renamable ancestors, no-follow-bind and `fchmod` every newly created parent to exact `0700`, and publish the sidecar from its own exclusive verified fd so pre-existing names are never opened or followed.

## 2026-08-31 — Classify only proven zombie-only post-KILL groups as cleaned up

Retain TERM/KILL/reap, reserve a bounded tail of KILL grace for one read-only procfs scan, and preserve the original command error only if every observed matching PGID member is positively `Z`. Live or incomplete procfs evidence remains fail-closed, avoiding both container zombie error masking and cleanup weakening.

## 2026-08-31 — Keep frozen-adoption receipt tests scoped to their binding contract

The receipt regression proves selected base, route-base, fingerprint, and evidence consistency; it must not assert a global fitness pass for every later stacked worktree. Architecture fitness continues to run independently against the active route base and retains the mixed-change policy.

## 2026-08-31 — Test bounded procfs classification without the host procfs

Mocking `scandir`, stat-file open/read, and monotonic time directly exercises parser and fail-closed branches deterministically while the existing runner regression continues to prove real descendant cleanup. This separates host-dependent process behavior from the security decision over procfs evidence.

## 2026-08-31 — Restack M3 on the exact accepted M2 predecessor

Consume accepted M2 `022411b05924618cfde0cb97b8c8aff4955e6013` through a true two-parent merge and regenerate architecture, governance, and receipt evidence for the resulting exact M3 head. This preserves both reviewed lineages while preventing historical exact-state artifacts from being reused as current authority.

## 2026-09-01 — Keep factory control and merge trust as separate authority domains

Model the factory as a nested local package with its own PostgreSQL schema/roles/migrations and Unix-socket API, and give it no edge or dependency on Trust CI, GitHub, providers, deployment, or production. This made installer, architecture, privilege and API tests able to prove the separation directly.

## 2026-09-01 — Make the deployed boundary executable, not descriptive

Pre-bind the owned mode-`0660` Unix socket, force every store connection through `SET ROLE factory_runtime`, and require persisted verifier/operator M0 records before intake. Exercising those boundaries through the mandatory disposable restart suite exposed failures that metadata and adapter-only tests could not.

## 2026-09-01 — Couple terminal projection changes to resource ownership

Lock capacity in one order and close the live run, allocation and counters before clearing a task's current lease pointer. This makes cancel, supersede, release and orphan reconciliation idempotent views of the same resource invariant.

## 2026-09-01 — Serialize immutable command and intake identities without mutable-row authority

Use transaction advisory locks derived from validated command or intake identity keys, then persist exact command results before returning. This closes concurrent replay races while allowing `factory_runtime` to lose UPDATE authority over immutable intake identity rows.

## 2026-09-01 — Make capacity mutation capability-shaped

Encode 20/10/1 identities and ceilings as schema constraints, revoke raw runtime counter DML, and expose only allocation-bound security-definer functions with a fixed safe search path. This keeps scheduler lifecycle atomic while making arbitrary counter insert/reset impossible to the effective runtime role.

## 2026-09-01 — Bind lease validity to a live capacity allocation

Treat an unreleased canonical allocation as part of the worker fence and deny runtime direct allocation updates. This keeps heartbeat, release and accounting fail-closed if privileged out-of-band drift hides an allocation, without implicitly repairing counters.

## 2026-09-01 — Lock trusted authority inside intake without granting row mutation

Use fixed-search-path security-definer predicates that take a row lock on the exact repository/policy/action subject, and invoke them after intake identity serialization in the insertion transaction. This prevents revocation TOCTOU while retaining an EXECUTE-only runtime boundary.

## 2026-09-01 — Keep SEO landing generation isolated and repository-scoped

Embedding the Codex skill under `.agents/skills/` and its showcase under `side-projects/` makes the capability available on demand without changing Trust CI runtime behavior. The showcase remains `noindex, nofollow` until a real production origin is supplied and verified.

## 2026-09-02 — Integrate legacy evidence at the stricter contract boundary

When a current-main merge introduces legacy evidence into a stricter accepted stack, migrate only the affected artifacts to the current canonical contract and model real local test capabilities explicitly. Pure URL parsing is not network access, while loopback browser execution is a declared `local_only` edge; this preserved validator strength without granting general egress.

## 2026-09-02 — Bind PR preflight to route and target ranges

Derive the exact route ancestor and the local PR target merge base from Git metadata, then use their changed-file union for hygiene, secret, contract, and SQL gates. This keeps a stale route base from hiding PR-only changes without fetching or treating repository prose as merge authority.

## 2026-09-02 — Exclude exact verifier environments from architecture inventory

Skip untracked directory components named `.venv`, but enumerate force-added index entries beneath them and inspect those exact paths through root-relative no-follow descriptors. This prevents verifier tooling from poisoning later runs without letting the cache-shaped name hide tracked repository source or symlinks.

## 2026-09-02 — Terminalize conditionally across claim races

Cancel and supersede may terminalize directly only while `current_run_id IS NULL`; a failed conditional transition re-reads the committed run, acquires capacity locks before the task row, releases the run exactly once, and retries. This preserves the canonical capacity-to-task order while preventing a winning claim from being erased with live capacity.

## 2026-09-03 — Scope Git ownership trust to the canonical package root

Pass one command-local `safe.directory=<canonical-root>` entry only to repository Git reads while retaining the scrubbed config environment. This supports read-only runner mounts owned by another UID without trusting a wildcard, persisting configuration, or broadening non-repository commands.

## 2026-09-03 — Preserve unresolved accounting as an explicit quarantine

Cancel, supersession and deadline cleanup retain live reservation evidence and set `accounting_blocked` because absence of provider work cannot be proven. Mandatory event/audit metadata records the bounded quarantine decision, and readiness fails closed on equivalent unmarked terminal history.

## 2026-09-03 — Use one cursor-stable deadline reconciliation candidate

An orphan run releases capacity and terminalizes its already-expired queued/retry task in the same candidate savepoint. This prevents a newly eligible row with the same task UUID from falling behind the returned keyset cursor while keeping candidate kinds mutually exclusive.

## 2026-09-03 — Keep the unaccepted repair schema-neutral on PostgreSQL 17

No M4 candidate was accepted or authorized for persistent rollout, so the repair supports fresh PostgreSQL 17 schema `013` and does not invent an upgrade population or migration. Older candidate databases remain killed comparison evidence and are replaced fresh, while PostgreSQL 17 `transaction_timeout` plus decreasing statement timeouts enforces the whole reconciliation deadline. Leaving later migration numbers unused also avoids a compatibility collision with provisional M5 `014` through `017`.

## 2026-09-03 — Separate intent, work and command identities

Keep `intent_digest` over the complete normalized intake as the immutable stored/M5 packet identity, but deduplicate on a namespaced semantic work digest that excludes only transport `request_id` and the entire M0 proof. Bind each request ID separately to its full request digest and exact result in `command_results`, so refreshed equivalent authority deduplicates while changed reuse conflicts.

## 2026-09-03 — Keep history cursors public but order by durable keys

Expose a task-bound run UUID cursor while resolving it to the run's immutable fence, and use event sequence directly for event pages. Selecting and validating a `limit+1` window before slicing preserves stable pagination and makes malformed lookahead evidence fail closed without changing schema or `LeaseGrant` v1.

## 2026-09-03 — Centralize task transitions without changing lock ownership

Apply every task-state update through one operation-scoped, lock-neutral policy primitive after the caller acquires its required locks. This preserves capacity-before-task ordering in cleanup paths and makes any policy or evidence failure roll back the full mutation transaction.

## 2026-09-03 — Make one checked document the API contract

Disable runtime OpenAPI generation and describe all 17 operations with closed inline schemas, stable operation IDs, normalized errors and required response correlation in the checked contract. Keeping operation IDs optional for legacy architecture inputs while validating uniqueness and compatibility when present preserves existing Trust CI contracts without weakening the factory-specific gate.

## 2026-09-03 — Normalize unexpected local API failures at the outer boundary

Return one closed, redacted 500 envelope and establish correlation inside the outer exception handler because unexpected failures can bypass user middleware. Declare that response for every checked operation and never reflect exception text.

## 2026-09-03 — Derive release member modes from the Git tree

Use exact Git `100644`/`100755` modes only for release ZIP attributes while retaining the full opened-file identity for no-follow and replacement checks. This makes exact-tree archives byte-stable across checkouts without weakening secure source or publication binding.

## 2026-09-03 — Layer finite budgets instead of rewriting the M2 bound

Restore the original six-prefix M2 budget unchanged and enforce separate finite error budgets over the governed aggregate, all factory files, source, contracts and tests. Independent overlaps preserve the historical M2 rationale while bounding the measured frozen M4 representation without minification, stacked-route partitioning or an exemption.

## 2026-09-03 — Anchor the remaining milestones to accepted predecessors

Define T0 only when an exact M4 SHA earns separately authorized PR delivery, external exact-SHA gates and protected acceptance, then sequence M5-M9 from accepted predecessors rather than missed calendar promises. This keeps M8 cohort duration and M9 signed-artifact/environment/recovery entry conditions truthful; 2026-09-08 remains superseded history, never a waiver.

## 2026-09-03 — Keep final evidence outside the package fingerprint

Build the artifact-only final HEAD first, then store exact-head review reports under the locally ignored `engineering/changes/<active>/evidence/final-runtime-<sha>/` so the active change package retains them without changing Git package inventory or the final tree fingerprint. Runtime receipts bind that unchanged fingerprint; this workflow evidence is not merge authority.

## 2026-09-04 — Make historical and published provenance clone-independent

Preserve the frozen M2 architecture inputs as manifest-bound text fixtures and exercise Git base selection in synthetic repositories. Bind the already-published 2.0.13 ZIP to `PROJECT_STATE.json` and its immutable release tag instead of requiring parity with later documentation-only HEADs.

## 2026-09-04 — Dogfood landing generation without overwriting prior evidence

Preserve the tracked showcase and the read-only private target, generating candidates only from its exact SHA/tree in independent disposable workspaces where root `index.html` and `content.css` are the complete write allowlist. Fixed command-provider ports with a sealed fixture keep the local flow executable, while unavailable defaults and a disabled publisher keep provider and production claims fail-closed until external authority exists.

## 2026-09-04 — Amend finite budgets for mandatory safety repairs

Raise only the measured factory-total AST ceiling to 1,450, factory-source AST ceiling to 1,010, and factory-test byte ceiling to 510,000 after required review repairs measured 1,404 total AST units, 1,005 source AST units, and 503,232 test bytes. Keeping test AST and every other ceiling unchanged makes the safety work explicit without moving files or deleting checks to game fitness.

## 2026-09-04 — Bind publication to the protected merge tree

Compare the protected merge tree with the checked artifact-child tree, then rebuild from the exact merged commit before pushing the tag and publishing the release. This proved the squash changed commit identity while preserving the reviewed bytes and kept the published archive bound to its immutable tag target.

## 2026-09-05 — Separate stale-PR cleanup from product source

Close stale conflicting PR #21 only after verifying that PR #22 and PR #24 delivered its superseding product history, and bind the cleanup to its own exact external-write grant. Keeping that historical mutation outside the product change avoided package restacking and reverification while restoring protected main and immutable releases as source of truth.

## 2026-09-05 — Persist exact effect intent before the sole publication attempt

Derive each GitHub resource from the canonical request digest, require one literal current grant, and commit both request and grant-use facts before entering the injected transport. A reopened prepared or in-flight effect performs observation only, which made hard-crash reconciliation deterministic without granting a second write.

## 2026-09-05 — Use the official app-server as an opaque subscription-auth boundary

Start one ephemeral Codex app-server thread/turn through the host ChatGPT capability without reading or copying auth-store bytes, while clearing MCP/web/shell-env inheritance. The initial workspace-write profile did not prove read isolation; the review correction below is required before claiming credentials are inaccessible to model commands.

## 2026-09-05 — Bind command confinement to the effective pinned profile

Use the same closed `pilot_confined` configuration and pinned executable for the no-model sentinel proof and actual Codex invocation, with outside reads, filesystem/abstract Unix sockets and temporary roots denied. The installed `0.153.4` binary passed the synthetic proof; this establishes local command isolation, not a successful model turn or live delivery.

## 2026-09-05 — Preserve single ownership after the agent thread ceiling

After both permitted attempts to resume the selected implementer hit the global agent-thread ceiling, the user explicitly authorized primary `/root` to take over as the sole write owner. Existing code, test and security reviewers remain independent and read-only; no second implementer or extra review wave is created.

## 2026-09-05 — Carry unchanged evidence without concealing the failed command

Preserve the original full-verifier failure and successful targeted PostgreSQL retry, then bind unchanged component evidence by Git identity while freshly checking the repaired pilot, verifier selection and package. This follows the user's explicit affected-tests-only instruction without representing a targeted continuation as a second full-suite PASS.

## 2026-09-06 — Factory live landing assembly is injected, not default-on

compose_landing_live automatically normalize→render→evaluate→seals the 20-member L5 artifact only when a caller injects an enabled binding and executor. The shipped server stays unavailable, live_url stays null, and observed landing SHA 80d6215 fails closed until a reviewed renderer/inventory refresh.

## 2026-09-06 — Root decisions.md and mistakes.md may be appended in every worktree

The user explicitly allowed additive writes to `decisions.md` and `mistakes.md` in every project tree, including the repository root. This is append-only self-learning, not a grant to rewrite history, merge, or edit other protected paths.

## 2026-09-06 — Live Grok and Qwen landing executors stay outside the no-httpx landing core

httpx is already a factory dependency, but FIT-FACTORY-LANDING-DOGFOOD-BOUNDARY forbids it in landing_runtime.py. Grok/Qwen chat-completions adapters therefore live in landing_live_executors.py, remain default-off, and take injected keys plus an optional MockTransport.

## 2026-09-06 — Live landing HTTP sits in its own factory node

NODE-FACTORY-LANDING-DOGFOOD stays network: none. Grok/Qwen httpx adapters live in NODE-FACTORY-LANDING-LIVE-EXECUTORS with a declared HTTPS edge to NODE-FACTORY-LANDING-MODEL-PROVIDER inside TD-FACTORY-CONTROL, so fitness can own the new file without giving the dogfood core live network or a Trust-CI/external-platform crossing.
## 2026-09-07 — Keep shipped factory server off httpx; compose live landing from env in operator injection

NODE-FACTORY-LOCAL-API is network: none and owns server.py. Live Grok/Qwen stay in landing_live_executors via compose_env_landing, which returns None when FACTORY_LANDING_PROVIDER is unset. Local composition injects that helper or an offline fixture executor so landing assembly is a factory byproduct without importing httpx into the API module.


## 2026-09-10 — Reconstruct historical delivery from actual refs

Compare a consumer repository’s selected delivery ref with every observed PR head before classifying open work as undelivered; default branches can retain an obsolete baseline. This resolved stale-open history without inventing additional task acceptances, and keeps project evidence distinct from profile-qualified M8 records.

## 2026-09-10 — Keep historical denominators and profile metadata explicit

Separate PR pagination completeness from task-inventory completeness, and report observed records alongside nullable full-history totals. This preserves existing work without turning missing acceptance/session evidence into zeros; complete profile metadata remains bucketed accounting with no M8 authority.

- 2026-09-11 test tooling bootstrap: extracting only runner image pins and its existing operations assertion preserves FIT-TRUST-CI-SEPARATION while making the parallel-runner prerequisite reviewable. Source preparation and independent image deployment remain separate facts.

- 2026-09-11 price-table identity: use SHA-256 over the complete closed, compact sorted-key UTF-8 JSON table and floor each token bucket before summing. This keeps price identity reproducible and prevents fractional remainders from one billing category changing another category's price.

- 2026-09-11 explicit usage protocol split: preserve the exact V1 usage payload and model V2 as a separate protocol/versioned proposal with a table-bound derived total. This prevents an expanded payload from silently changing legacy billing semantics while carrying all V2 facts into idempotency.

- 2026-09-11 parser version propagation: validate accepted JSONL events using their supported protocol version and preserve that version in the canonical event. This keeps the adapter-facing entrypoint aligned with the V1/V2 contract split rather than testing V2 only through constructed values.

## 2026-09-13 — Reconstruct delivery slices against genuine predecessors

The import-only prerequisite can be extracted onto actual main while later slices introduce their modules, schemas and test dependencies together. Keep architecture fitness on each new route's genuine predecessor and retain the separate cumulative main inventory; neither refs nor budgets need to change.

## 2026-09-13 — Keep final review evidence beside an immutable source checkout

A dedicated same-repository evidence worktree can hold the exact change-package reports while source commits stay unchanged. Recording fresh independent reviews by absolute report path preserves the original verification fingerprint and avoids rerunning the product suite for paperwork; the evidence checkout's commit is never represented as a tested source identity.

- 2026-09-13: Direct FactorySettings with real temporary SQLite isolates runtime ownership tests from the later dedicated-host slice. Data analysis additionally found an initialization-interruption cleanup gap; reproducing and narrowly fixing it before delivery gives independently reviewable ownership behavior without changing the schema.

- 2026-09-13: Writer ownership is tested with a second real SQLite opener after injected startup failures, rather than by inspecting private descriptor flags. Four reproduced interruption/close-failure paths required only three cleanup hunks, retaining schema and durable reader bytes.

- 2026-09-13: Complete the helper-only host_config in E together with its dedicated host tests, keeping D independently runnable. Runtime templates stay deferred until their publication/backup entrypoints exist in G.

- 2026-09-13: After an independent predecessor repair, recreate the remaining unsubmitted publication slice on the actual corrected predecessor and verify its unchanged product projection. Preserving the old route/failure and starting from a clean real base avoids attributing an inherited server change to publication or inventing comparison authority.


## Preserved L5 reconstruction history

These dated notes retain earlier decisions and mistakes. Temporary deferrals and old active-package references describe past phases; current G scope/evidence takes precedence.

## 2026-09-12 — Use II-Tonya and Pump as the L5 evidence basis

The user selected these two existing projects and delegated deployment/provider choices, so preserve their saved task/PR/acceptance records and read actual DB telemetry instead of manufacturing new proof or using project counts as accepted-task counts. Use local Claw for the new isolated runtime and the native immutable-release/systemd pattern from II-Tonya. Keep private cost/session records outside the public checkout; cumulative tokens without currency or cache/output breakdown are not measured dollar costs.

## 2026-09-12 — Continue L5 from main with verification explicitly deferred

Use isolated `feat/l5-production-completion` from `a730ee9` because the original checkout contains older shell-policy work while the merged L5 runtime lives on main. The user's «прверки пока не проводим» defers tests, builds, verification and reviews; implementation evidence must remain unverified, and no live operation or release is implied. Complete durable server composition and truthful bounded HTTP provider handling before attempting operational activation.

## 2026-09-12 — Separate HTTP provenance from the native Codex profile

HTTP calls must bind the actual provider/model/endpoint and record observed time and reported usage; the existing Codex executable profile and fixed 25 ms / 1-token counters cannot describe that transport. Reuse strict draft reconstruction and the existing SQLite runtime while preserving native Codex and fixture compatibility. Saved implementation and hosting/source/media follow-ups live in `engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/`; tests and new test authoring remain deferred.

## 2026-09-13 — Resume the host audit from its actual test baseline

The interrupted L5 work already contained SSE tests at `3324504`; a fresh pinned-dependency baseline reproduced nine executor failures and found no dedicated host tests. Continuing with a bounded host regression slice preserves that evidence and avoids treating inherited failures as newly introduced defects.

## 2026-09-13 — Separate URI parsing from transport in boundary findings

L5's new modules share a provider-egress architecture node but miss the landing file-boundary list; `urllib.parse.quote` only escapes SQLite file URIs. Inspecting both ownership and import semantics identifies the classification gap without falsely reporting pure parsing as network activity.

## 2026-09-13 — Exercise host ownership with real offline resources

Private temporary sibling roots and synthetic actor injection allow real FastAPI, SQLite persistence, writer exclusion and lifespan tests without a provider or PostgreSQL. The control directory must exist even with live mode disabled, while the source checkout may remain absent.

## 2026-09-13 — Compare parallel runners only with matching prerequisites

Archived PR33 sandbox failures include missing pytest and an unreadable worktree Git index, so they do not establish a CPU-capacity cause. This host exposes all 28 CPUs to explicitly configured test children despite the shell's inherited 22-CPU affinity; retain real dependency and source bindings when using that parallelism.

## 2026-09-13 — Keep host cleanup attempts independent

Red/green host tests reproduced skipped runtime/socket cleanup when an earlier close raised. Nested `finally` blocks preserved the existing socket identity guard and made every cleanup stage run, while retaining idempotent SQLite shutdown and exception chaining.

## 2026-09-13 — Declare socket tests under their existing API owner

The new host test inherited the broad factory-control owner and failed the network fitness rule for Unix sockets. Assigning its exact path to the existing local API node, alongside the server test, made the declaration accurate without adding network permissions, nodes, edges or exemptions.

### 2026-09-13 — Qwen credentials and region are separate inputs

A minimal synthetic request distinguished a region mismatch from an unusable key: the same authorized DashScope key was rejected by Beijing and accepted by Singapore. Declare Singapore as a separate closed profile and pass an explicit private credential file through the existing live-only composition seam; this preserves earlier profile identities and makes the actual local connection reproducible.

### 2026-09-13 — Own child cleanup before configuring I/O

Register child termination, reaping and pipe closure immediately after Popen, before constructing the selector. ExitStack keeps later cleanup callbacks running when selector setup or closure fails; bounded real-child regression tests verified that no process or open pipe survives these failure paths.

## 2026-09-13 — Preserve producer versions before extending schema checks

An unsupported compatibility result can conceal a real producer break: compare the changed value domain in its declared direction before changing the checker. The HTTP success value widened provider-evidence v1, so a separately versioned v2 with dual-version retained readers preserves truthful provenance and original v1 identities.

## 2026-09-13 — Resolve imports from their actual source root

Static boundary checks must resolve relative imports in namespace packages as well as regular packages. Negative tests with module-less imports and an ancestor initializer reproduced an escape from the intended source root; explicit canonical src-root resolution closed those cases without changing unrelated import scanners or widening network access.

## 2026-09-13 — Keep immutable source separate from completed evidence

Freezing each actual predecessor before verification lets independent reports and receipts bind unchanged source while the matching evidence checkout records results. Genuine predecessor re-extraction resolved inherited-route provenance without altering a base or weakening architecture budgets.

## 2026-09-13 — Check known recovery cost before creating roots

Restore knows the complete validated payload size, so preflight its second copy against remaining accounted I/O before creating destination roots. A reduced-cap fixture proves early refusal and the exact successful two-pass boundary without increasing limits or allocating large files.

## 2026-09-14 — Canonicalize only within original validation bounds

For PR #82, checking section shape before iteration and leaving over-limit item lists for strict rejection preserves controlled errors while using the exact contract JSON sort key handles multilingual and escaped strings. Red/green decoder, HTTP/Codex and SQLite service regressions demonstrated stable canonical output and retained failure evidence without changing contracts or caller catches.

## 2026-09-14 — Generate structurally valid fixtures for parser limits

Using the pinned PdfWriter to serialize actual 100/101-page documents let the real bounded PDF child reach the intended count guard. This isolated a pre-existing test defect and restored meaningful limit coverage without changing runtime parsing or resource bounds.

## 2026-09-13 — Absent Trust CI check run on a fresh head means queued, not lost

The self-hosted runner processes policy-epoch verifications serially (~18–20 min per PR head); the stacked L5 heads A–G each verified only after the predecessor's job completed. A missing `adaptive-trust-ci/verified@…` run was confirmed queue state via the live `TRUST_CI_PR_NUMBER` job, so no head re-push or dispatch retry was attempted. Never churn a PR head to "wake" a check — a new commit invalidates the exact-SHA attestation chain.

## 2026-09-13 — Land append-coupled stacked slices as one tree-identical union with a fresh gate

Squash-merging the bottom slice of a stacked chain destroys the commit identities the upper PRs need (shared append files then guarantee three-way conflicts), so the remaining six L5 slices landed as a single commit whose tree equals the attested top head `e6a813e`: `merge-tree` proved conflict-freedom and final-tree identity before push, the union got its own exact-SHA Trust CI success, and post-merge `tree(main)==tree(top head)` was re-verified. Per-slice attestations stay recorded in the ledger as historical content evidence. Rule adopted: for stacks that append to shared documents, landing is all-or-nothing — a merge-commit chain (GitHub rejected `--merge` as disallowed even though the settings API reported it enabled, so a second read of live behavior, not just config, is required) or one union with a fresh gate; never a partial squash cascade.

## 2026-09-13 — Real-delivery registry seeded as runtime data at the doctrine path

No product-side registry exists on `main`, so operator-supplied factory-delivered project outcomes land in the canonical gitignored runtime file `.grok-stack/runtime/m8-real-delivery/real-delivery-registry.json` (first record: `aleksandr-alhoff/seo-landing`, ChatGPT/Codex ids + factory audit route `c9179d70b949`). Why this shape: decisions.md 2026-09-06 fixed the doctrine that the registry is runtime data and not a product contract; inventing an unreviewed schema in the product tree would create a governance surface the M8 branch line never merged.

## 2026-09-14 — Check installed L5 state separately from shipped defaults

Read-only host inspection found `adaptive-l5.service` active/running and ready on installed commit `969c4f65f54ef9230f3f94587e228098d1c2ecb9`, with `live_enabled=true` and `selected_profile=qwen-intl`; default-off source documentation does not establish the installed state or successful task delivery. PR #82 merged as `5f6f6ce1ecb0cef8e1b3910b037af983c5fb8f8a` after App-owned check `103833535728` passed on `6bd86207ca9955a8ad91224224cf665e16a282da`, and both trees equal `f138beda12d1cf21f24cb26bb95166ffa9b120d7`. A clean upgrade source is staged at `/home/pall/grok-projects/adaptive-l5-pr82-stage-5f6f6ce`; runtime deployment and the synthetic provider probe still require exact operational delegation, with the prepared plan in the l5fix tree's `.grok-stack/runtime/pr82-runtime-upgrade/plan.md`.

## 2026-09-14 — Put offline test scaffolding in a non-`test_*` module beside the tests

`factory/tests/landing_host_fixture.py` now carries only the offline half (private roots, 0600 config, synthetic actors, `write_config`, `reopen_store`) while `test_landing_host.py` subclasses it and keeps the web-stack half (`build_app`, `TestClient`). Why this shape worked: the dependency-free backup/restore boundary suite became collectable on a host with no fastapi/uvicorn/psycopg (executed coverage of `landing_backup.py` 12%→84%), the host suite needed zero body edits, and a filename outside `test_*` keeps `unittest discover` away while `factory/tests/__init__.py` already bootstraps `sys.path`, so no packaging, coverage or fitness rule had to change. The narrowness is now asserted by a guard test that itself needs no heavy dependency, so the coupling cannot return silently.

## 2026-09-14 — Borrow the installed release's venv as the deps-complete interpreter, framed as corroboration

This host's system `python3` cannot collect the FastAPI-bound suites, so instead of installing packages globally I ran the tests with `/opt/adaptive-l5/releases/<sha>/venv/bin/python` plus `PYTHONPATH=.:factory/src:delivery/src` — read-only as an interpreter, nothing installed — which made the previously unexecutable half run and proved the fixture extraction neutral (36 host tests OK on base and on the change; whole factory suite 712→713, `OK`, identical skip set). Why it is stated as corroboration rather than as the record: the venv matches the `factory/uv.lock` pins for the five web/db names but not for all 21 entries (`anyio` differs), it is host state a clean checkout cannot reproduce, and it is deps-complete but not DB-complete. Reproducible percentages therefore stay in the dependency-incomplete environment, and `find <release> -newermt …` empty is the check that the borrowing left installed state untouched.

## 2026-09-14 — Close PR82 with installed service and authenticated artifact evidence

Under the user's production-and-YOLO delegation, deployed merged commit `5f6f6ce1ecb0cef8e1b3910b037af983c5fb8f8a` to Claw, backed up state, preserved the previous unit/config, and verified `adaptive-l5.service` active/running and enabled at boot with matching dependency inventory. The Qwen normalizer passed and the authenticated Unix request `pr82-smoke-5f6f6ce1ecb0` reached `artifact_ready` with digest `85b3360aaa28c38448c8d31770a5307df809aa7ce4829e81f1ac7b4ddddc76ed`; systemd supplied credentials opaquely, and no public site was published. Evidence lives in the l5fix tree's `.grok-stack/runtime/pr82-runtime-upgrade/result.json` and `result.md`; this supersedes the earlier pending-runtime-delegation note and worked by checking the installed service and actual job result separately from source/release claims.


## 2026-09-14 — Preserve the current public landing instead of publishing a runtime smoke artifact

The user selected the working The Real AI Dark Factory landing; read-only HTTPS checks of `/`, `/ru/`, `/roadmap.html`, `/robots.txt` and `/sitemap.xml` all returned 200 and matched landing main `6226aa0b86e1fe08c63724cc3761b3f788146b91` byte-for-byte. Preserve that deployment on the separate LiteSpeed host: L5's pinned `fde60e0` is an older deterministic source and its gardening-club artifact is synthetic acceptance evidence. The user identified conversation `01a06856-3aba-7e81-bdb5-311d58a4f491` as the source of truth, but it was not found in available local/imported history; current publication evidence is in the l5fix runtime's `pr82-runtime-upgrade/public-site-check.json`.

## 2026-09-15 — Trace provider failures with sanitized response counters

A separate synthetic diagnostic isolated the Grok connection failure to executor_usage: xAI reported reasoning tokens outside completion_tokens but inside total_tokens. Capturing only response structure and factual counters proved the API key/model worked without exposing credentials or preserving model reasoning, and lets the repair use a deterministic offline regression.

## 2026-09-15 — Keep provider-specific usage identity local to Grok

Select Grok adapter and decoder identity in both profile facts and emitted evidence so the isolated reasoning-accounting repair does not invalidate Qwen bindings. Reconcile separate reasoning from explicit counts, retain valid inclusive legacy accounting, and cap normalized generated output as post-consumption acceptance validation.


## 2026-09-15 — Separate source, release, installed runtime and accepted outcomes

A dated state table bound to source SHAs, immutable release hashes and authenticated service results removes contradictory bootstrap instructions without rewriting artifacts. Keeping live-enabled instances separate from default-off source preserves the real deployment evidence while leaving external pilot, M8/M9 and cost/intervention acceptance unproven.


## 2026-09-15 — State the external CI choice as a trust-boundary decision

The repository chooses policy and holdout validation outside the PR-controlled tree, exact-SHA execution and an App-owned required check. Documenting those architectural reasons keeps the no-Actions rule independent of repository licensing or CI pricing.


## 2026-09-15 — Keep README architecture references tied to the reviewed model

Removing the complete decorative graph and its duplicate tests leaves the real model, rules, generated views and adoption checks as the architecture references. Moving packaging internals into the existing package guide keeps the README concise while preserving operator details and immutable release evidence.

## 2026-09-15 — Separate credential presence from provider access

A bounded selected-key parser confirmed all five requested API variables without printing their values, then read-only metadata probes exposed HTTP403 on all three new providers before paid inference. OpenAI explicitly reported a regional restriction; keeping that fact separate from adapter implementation prevents claiming a configured key is a working integration.

## 2026-09-15 — Test the installed supervisor's failure behavior

Both installed landing units use `RuntimeDirectoryPreserve=no`, so stopping a provider can remove its socket parent directory as well as the socket. Comparing the caller's path checks with real unit metadata exposed a configuration rejection that ordinary missing-socket fixtures would miss; stopped-provider coverage must include the missing runtime directory while retaining ancestor safety checks.

## 2026-09-15 — Classify complete provider error outcomes

A received HTTP error status is insufficient when its body is truncated or times out before classification. Preserving that uncertainty prevents fallback from treating an incomplete policy/error response as a confirmed availability failure; dedicated red-to-green coverage exercises this boundary.

## 2026-08-30 — Compile framework artifacts through one advisory boundary

Normalize explicitly manifested Spec Kit, BMAD, and Superpowers files through a descriptor-bound anti-corruption layer into stable source, task-graph, and convergence contracts. Keeping imported documents candidate-only and requiring native route/receipt/fingerprint checks prevents a second planning framework from becoming a second authority system.

## 2026-08-30 — Serialize workflow artifact publication around atomic exchange

Use a persistent descriptor-safe runtime lock per target so cooperating writers serialize, then publish missing targets with no-clobber link or existing targets with atomic exchange after pre-validating digest and identity. A post-exchange identity mismatch rolls back before reading displaced content and preserves any second competitor under a bounded recovery name; unsupported platforms fail closed instead of claiming universal filesystem CAS.

## 2026-08-30 — Separate tracked source claims from effective receipt state

Persist only bounded source-status hints in the task graph and derive effective pending/verified state from current canonical receipts during runtime validation. This removes the fingerprint/receipt rewrite cycle while keeping disagreement between tracked source claims blocking and auditable.

## 2026-08-31 — Bind the M0–M9 program to 2026-09-15 00:00 UTC+3

Compress the critical path through continuous execution, minimum exit-criterion scope, and read-only preparation of successor milestones, with feature freeze at 2026-09-14 20:00. The deadline never overrides exact-SHA Trust CI, signed approvals, security, migration, evidence-cohort, or recovery gates; threatened delivery is reported immediately instead of fabricating completion.

## 2026-08-31 — Supersede the M0–M9 deadline with 2026-09-08 00:00 UTC+3

The 2026-09-15 decision remains historical but is superseded by the management deadline of 2026-09-08 00:00 UTC+3; compress through continuous handoffs, read-only successor preparation, one frozen documentation-only M8 candidate class with at least 30 human-accepted tasks, and non-production M9 validation. The deadline does not waive exact-SHA Trust CI, signed approvals, sequential integration, PostgreSQL/security/review, evidence-cohort, or recovery gates; promote M8 or claim M9 only when evidence passes, otherwise report the exact blocker.

## 2026-09-10 — Include three consumer cases in autonomy assessment

Use Puls Pump Selector (stand acceptance), Google Ads Automation main (Ads/Postgres/n8n integration) and ii-Tonya (native deployment and Claw verification) as existing real project evidence alongside the factory controller. This worked because cross-repository inspection corrected the false first-real-case gap and exposed evidence that controller handoff files do not aggregate. Reconstruct qualifying accepted tasks and operator-intervention metrics from existing history before proposing new cohort work; do not infer an M8 count or activation from project count, PR count, or product runtime automation alone.

## 2026-09-15 Grok alongside primary Qwen

A separate adaptive-l5-grok.service with its own socket and durable roots allowed Grok 4.6 to be added without restarting or reconfiguring primary Qwen. Binding installation to merged PR88 commit61a05da, verifying its tree and installed module hashes against tested4e94f7a, then requiring an authenticated artifact_ready result before enabling startup established the whole live path. Both services are active/enabled and Qwen retains PID698333 and its original configuration hash.

## 2026-09-15 — Pin third-party workflow formats as config, named tests, and a dated observation

`source_version` in the workflow adapters stays free-form because a version gate would turn the advisory anti-corruption layer into an authority and break historical fixtures; currency is instead the `workflow_sources` block in `.grok-stack/config/toolchain.json` plus `tests/test_workflow_sources.py`, which proves each pinned release (superpowers 6.3.0, BMAD 6.12.0, spec-kit 1.0.7) has a committed unmodified-shape parser test and a fresh dated observation. ADR-0001 records the full contract, including the rule that no upstream tree is ever vendored into the product.

## 2026-09-15 — Amend content-addressed specs instead of rewriting them

The 2026-08-30 design/plan/tasks documents are SHA-256-addressed by the d41aa6 workflow manifest, so upstream-format corrections ship as a linked amendment under `docs/superpowers/specs/` rather than edits to frozen sources. Same rule covers the version claim: real-version fixtures and named unmodified-shape tests prove currency; parser version gates stay rejected (ADR-0001).

## 2026-09-15 — Derive receipt-kind sets from the router's emitted kinds

Porting the epic's closed RECEIPT_KINDS byte-identically would have failed every bitrix/data route because router.py emits two domain review kinds the 2026-08-30 snapshot predated; the canonical set is now pinned to the router's seven emitted kinds and asserted by a parity test. Closed sets copied across the epic boundary must be re-diffed against the live emitter at port time, not trusted from the snapshot.

## 2026-09-09 — Remove a misclassified import instead of declaring a false edge

`FIT-DECLARED-NETWORK-ONLY` flagged `trust-ci/src/adaptive_trust_ci/settings.py` as an undeclared `tcp` client for the worker, because the fitness scanner treats any `socket` import as a network-client family. The module used `socket` for exactly one call, `socket.gethostname()`, to build a worker id. Replacing it with `platform.node()` removed a dependency the module never needed and kept the architecture model truthful; declaring a `tcp` edge would have recorded a connection that does not exist.

## 2026-09-16 — Hash oversized tracked binaries from a bounded stream

The architecture diff now profiles any object above `MAX_ANALYZED_FILE_BYTES` by streaming 64 KiB chunks into a SHA-256 (with the streamed length required to equal the `ls-tree`/`fstat` size and the dev/ino/size/mtime tuple re-checked afterwards), rather than buffering it or excluding it. It worked: the tracked 10,940,676-byte v2.0.17 ZIP yields exactly the buffered `sha256` in both commit and worktree modes, memory stays flat, and the pre-existing limit tests still pass because oversized text and explicit `read_diff_files` requests keep refusing.

## 2026-09-16 — Keep the fitness comparator closed; guard the frozen contract by shape, not membership

The gate proved the comparator cannot represent object-valued enum members, which freezes
`landing-backend-capability.v1.schema.json` against new profiles. Instead of widening `.grok-stack/adaptive_grok/architecture.py`
inside a product PR (one historical edit only; the reviewed escape admits unchanged documents; a trust-tooling
semantics change smuggled into feature work defeats its purpose), the PR files issue #104 with the two real
options (reviewed comparator extension vs v2 coexistence), reverts the enum edit, and pins the strongest
surviving invariant: declared entries byte-equal to table facts, and every undeclared profile forced to a
declared sibling's exact key set and per-key JSON types.

## 2026-09-17 — Re-derive an issue's root cause from the code before scoping the fix

Issue #109 asked for the platform gating that `_run_capped` supposedly had and `_stream_git_blob` lacked;
the module never had any `os.name` dispatch, so implementing the request literally would have added a
branch while leaving the real defect (untyped setup path, child stop only for named exceptions, unguarded
close order) in place. The wave fixes what the code actually does and publishes the correction of the false
sentence on the issue before merging, because the issue trail must match the shipped code.

### 2026-09-19 — Per-service acceptance and full snapshot rollback

Keep each upgraded service's acceptance and recovery independent: Grok's real artifact allowed its upgrade to remain while Qwen's rejected draft triggered containment and full snapshot restoration. Holding both old writer locks and preserving v2 roots before restoring v1 protected the failed attempt and recovered the prior artifact without another provider call. This prevented a partial rollout from becoming either a false two-service success or an unnecessary rollback of the working service.

### 2026-09-19 — One-off operator script evidence
Store retired and explicitly delegated one-off operator command bodies as exact-byte archives with an original-path/hash index and an explicit external execution boundary. This keeps repository evidence inert without granting fictitious TCP rights to the evidence node; separate actual-body reviews and hash-checked grants still govern execution.

### 2026-09-19 — Retain rejected-draft diagnostics in the existing reason field

Static consumer analysis found reason_code already persisted and sealed with no value enum, while observation v1 has a closed field set. Reusing reason_code avoids a schema migration and preserves old receipts; only fixed allowlisted codes may cross the model-output boundary. Retaining adapter/profile identity is appropriate for this observability correction because provider wire behavior, accepted drafts, prompt/model and decoder policy stay unchanged; the deployed source SHA identifies the correction.

### 2026-09-19 — Independently preserve wire hashes and historical receipts in regression tests

Hash the exact mocked HTTP envelope independently and freeze a historical receipt before editing the normalizer. These fixtures caught both the lost upstream digest and generic rejection reason, while preventing current serializers from silently regenerating the expected historical evidence.

### 2026-09-20 — Treat an unpassable success criterion as in-scope, and say so

When the mandatory PostgreSQL tier turned out to be deterministically red for a reason unrelated to #155 (fixture authority clock vs the product's 300 s window), the winning move was to fix it inside this branch and record it as a named *bounded scope ruling* in `brief.md`, not to ship an criterion that no host could satisfy. The alternative — filing it and stopping — would have delivered evidence that cannot be produced; a blocker discovered while producing mandatory proof is in scope by definition.

### 2026-09-20 — Prove every review fix with a mutation before taking receipts

For each finding fixed in the delivered tree (false `malformed payload` diagnosis, `_guard_lines` blindness, missing `authority_not_fresh` assertion), the fix was accepted only after reproducing the defect it claims to prevent in a scratch copy and watching the new test turn red — inverted `CASE`, deleted guard-group boundary, clause removed from `018` and `021` together: baseline green, all three caught. A review fix that has not flipped a control is a claim about code, not evidence, and the delta costs minutes while the reviewer is still warm.

### 2026-09-21 — Classify store refusals before parsing bindings

Recognize a legacy SQL NULL before calling the binding contract parser, so the caller receives a store refusal without a fabricated shape-error cause. A red/green regression now inspects the exception cause, context and formatted traceback while preserving the real cause for malformed documents. This closes the diagnostic boundary that message-only assertions missed.

## 2026-09-21 — Refresh the target before repeating a pilot

Reading the live target and the closed attempt before spending another provider invocation exposed a 26-commit baseline drift and a version task that no longer fits the site. A separate AST inventory probe identified a current two-file browser-audit gap, so the next pilot now has a concrete issue draft and reproducible failure. Keep that successor separate from #155 and from the historical profile; a draft or local proof does not establish maintainer acceptance.


## 2026-09-21 — Derive route scores and diagnostics from the same bounded token matches

Use Unicode word boundaries for short domain terms and retain substring matching for longer stems, then derive scores and persisted keyword evidence from that same match set. The exact #155 regression removes `ui` from `distinguish` without demoting genuine UI/API/SQL/D7/1C specialists or Bitrix repository guarantees. Keeping the evidence field optional and validating its bounded shape preserves historical route loading and makes future routing mistakes diagnosable.


### 2026-09-21 — Keep the change-spec receipt enum aligned with runtime registries

For issue #162, compare the schema enum exactly against both runtime receipt sets and validate each kind in a complete spec; this exposed the two missing domain reviews before the additive repair and guards against future drift. Keep draft scaffold timing and receipt authority unchanged because neither caused the vocabulary mismatch.

### 2026-09-21 — Align shipped Trust CI source validators without changing deployed trust

Independent review found that the runner and example holdout still had the old five-kind allowlists. A source-only validator patch and tests proved the repair, but `FIT-TRUST-CI-SEPARATION` requires it in a separately routed successor based on the delivered schema fix; the #162 branch must remain schema-only. Deployed worker and holdout rollout still requires separate authority.


## 2026-09-21 — #153 / #161 consumer installation documentation

Audit generated consumer documentation in the materialized tree, rather than only the source repository: this exposed nine missing link targets. Rendering documents from descriptor-validated template bytes kept payload identity deterministic.

## 2026-09-21 — Consumer rendering inputs and outputs

Ship rendering inputs as explicit .md.tmpl artifacts with their output destination declared, and verify installed-source reuse. This keeps the reusable input contract intact while distinguishing it from navigable Markdown documents.


## 2026-09-21 — #168 untracked agent scratch fingerprints

Combine index ownership with changed-path provenance before ignoring agent scratch. A staged deletion disappears from the index, so diff provenance is necessary to keep a recreated path and both rename endpoints bound to evidence.

## 2026-09-21 — Preserve literal filesystem paths in evidence
Treat NUL-delimited Git paths as filesystem bytes and preserve their literal separators through filtering, hashing and JSON serialization. This binds POSIX backslash lookalikes and non-UTF-8 names without widening the untracked scratch exemption; 19 focused regressions pass.


## 2026-09-21 — #147 / #148 schema resolution and bounded diagnostics

Bound diagnostic presentation only after the complete base and head traversals. Testing raw expansion as well as final findings prevents existing final deduplication from hiding an unbounded intermediate result or an incorrect omitted count.

## 2026-09-21 — Preserve conservative closure while fixing comparator fallback
Keep the registered-ID fallback local to the comparator when raw path grammar refuses a spelling. The shared helper still exposes that refusal to dependency analysis, preserving both concrete and declared-ID edges; focused regression controls pass.


## 2026-09-21 — Observe migration contention through the actual advisory lock

The issue166 regression seeds the real populated packaged prefix, observes the migrator waiting on its advisory-lock holder, then separately checks release-success and server-timeout recovery. This worked on PostgreSQL17 and verifies preserved ledger, rows, function identity and privileges without assuming that an executing function call blocks CREATE OR REPLACE.

## 2026-09-21: Integrate exact reviewed files on the delivered base
The six reviewed candidates use a predecessor whose complete tree is identical to merged main, and their19 product paths are disjoint. Preserving exact blobs and separate issue evidence gives a concrete combined tree for fresh verification while shared handoff records are reconciled once.

- When a short security keyword needs a word boundary, retain its legitimate expanded forms through an explicit finite alias set and check the entire resulting risk/reviewer/gate contract in an otherwise empty repository. This repaired the auth/роль compatibility regression while keeping unrelated author/authority and embedded lookalikes outside security routing.

### 2026-09-21 — Preserve complete candidate entrypoints and historical evidence

Comparing every candidate path against the source manifest exposed the missing Stop adapter before integration, while exact blob checks preserved the existing repair rather than inventing new behavior. Retain failed runs, revised reviews and candidate handoffs as historical evidence, then qualify the actual merged-base composition with fresh checks; this keeps provenance separate from current authority.

- Preserve both historical and current populated migration-prefix tests when a new function replacement lands. Exact reversal of the refusal-only SQL edits, together with post-transaction classification and both upgrade proofs, let all five independent reviewers confirm unchanged guard, privilege and persistence behavior.

### 2026-09-21 — Retake stale local-control PRs through path-scoped diffs

Applying only the selected source, test and documentation diffs onto delivered main isolated three real textual conflicts without carrying historical approvals or receipts. Keep main's checkpoint and status behavior during conflict resolution, and qualify the new composition independently instead of promoting old App successes to current authority.

## 2026-09-23 — Migrate current grant bindings without rewriting evidence

When a detector heuristic is caused by a current serialized grant envelope, rename only the current producer field and keep a fail-closed legacy reader. This preserved immutable evidence bytes while allowing existing runtime grants to expire normally without an in-place migration.

### 2026-09-22 — Mark checked-in policy examples and provider probes as non-authoritative

The checked-in Trust CI policy example now declares its illustrative-only authority explicitly, while the README names the deployed server-mounted policy epoch and exact App-owned Check Run as the merge authority. Runtime documentation and structure tests separately bind provider probes as operator-attested, non-re-derivable observations so local source evidence cannot be mistaken for deployed trust or durable job evidence.

### 2026-09-22 — Bind the release as a two-stage R/A chain

Keep release-sync source identity on the merged R tree and build the ZIP from that sealed parent, while the artifact-only A child owns repository custody, tag and publication. This separates reproducible bytes from the commit that carries them and prevents a later documentation change from silently changing release identity.

### 2026-09-22 — Require Git status provenance for focused landing eligibility

Focused verification now consumes a status-preserving Git inventory and rejects deleted, renamed, copied, malformed, or ambiguous records before selecting a landing contract. This keeps the optimization fail-closed while leaving the full PR path unchanged.

## 2026-09-24 — Freeze the exact base before expensive gates

When a predecessor merges, first restack the continuation branch and bind its route/evidence to the new protected-main SHA. Only then run one final full verifier, record receipts, push, and enqueue Trust CI; this prevents expensive checks from becoming stale because of a later base change.

### 2026-09-24 — Make cited identifiers pasteable and mechanically checkable

Receipts now echo one canonical `RECEIPT kind=… fingerprint=… path=…` line, and `scripts/grok_citations.py` flags any 8-64 hex token that exists in no machine-state receipt, contract digest, package sidecar or Git object. The corpus deliberately excludes report prose so a fabricated hex cannot become authoritative by repetition. Why: issue #206 and #117 are the same failure — a plausible identifier cited as proof inside an otherwise-true report — and existence of an enumerable id is a mechanical question that should never be a judgment call.

### 2026-09-24 — Drop `extended-citation` and bind the echo to the run instead of the tree

A citation longer than every real identifier it prefixes is not a faithful truncation of anything, so no acceptance rule covers it; keeping the branch reopened the exact issue #206 shape for 197 of 547 corpus identifiers, and the deleted-branch mutation passed the whole suite. The receipt echo now answers only "what did this invocation record", bounded by the CLI's own run start, because the tree fingerprint cannot distinguish "recorded now" from "never recorded" on the governance-fail branch where the tree is unchanged.
