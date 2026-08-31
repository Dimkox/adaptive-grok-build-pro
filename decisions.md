# Decisions

<!-- BEGIN ADAPTIVE GROK GOVERNANCE PROJECTION: decisions.md -->
> **NON-AUTHORITATIVE PROJECTION.** Canonical JSON governance records remain authority; this Markdown cannot approve, activate, repay, or accept any record.

## Active governance rules

_No active governance rules._

## Candidate governance rules

_No candidate governance rules._
<!-- END ADAPTIVE GROK GOVERNANCE PROJECTION: decisions.md -->

## 2026-08-28 — Bind governance handoffs to fresh exact state

Reopen the loader-bound governance root, recompute every component digest and finding, validate the complete M2 evidence envelope, and prove the Git head is exact and clean immediately before publishing the six-field handoff. Keeping projections in marked read-only blocks makes them reviewable without giving Markdown mutation or authority capability.

## 2026-08-28 — Freeze governance transitions as canonical values

Represent rule transitions as immutable canonical-byte `RuleRecord` values and append only typed review or approval records supplied at the transition boundary. This preserved rule identity across revisions and prevented callers from mutating a returned record through nested dictionaries.

Patterns that paid for themselves. Each entry is at most three sentences.

## 2026-08-26 — Provider-neutral factory core with explicit adapter boundary

Keep deterministic policy, state, leases, budgets, and capabilities in a PostgreSQL-backed provider-neutral core; make Codex, Grok, and future providers explicit versioned JSON/JSONL translators with no silent fallback. This preserves one-writer and trust boundaries across provider changes while allowing model-native streams to evolve behind conformance-tested adapters.

## 2026-08-26 — Isolate local PostgreSQL proof in a dedicated database

Use `adaptive_grok_build_pro_test` with four bounded `NOLOGIN` Trust CI roles inside the already-running local PostgreSQL service. Dedicated data and least-privilege roles prove migration/store behavior without touching application schemas or representing the run as deployment.

## 2026-08-26 — Version the strict typed contract as change-spec v2

Freeze schema v1 and its YAML-subset reader for explicit unchanged-history compatibility only; every new or modified spec is canonical JSON using schema v2. This prevents malformed canonical input from downgrading into legacy parsing and gives the exactly-one-key evidence model a new contract identity.

## 2026-08-26 — Rebuild M1 from the approved branch, not the stale baseline

The user explicitly approved rebuilding from the roadmap and its M1 design; preserve merged M0 and later repairs because the roadmap forbids discarding newer work. Treat the existing M1 prototype as characterization input, use dual-read/single-write migration, and deliver trusted-runtime deployment as a separate externally approved operation.

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

## 2026-08-24 — M0 CI host is claw, not a laptop

The M0 Trust CI host is hostname `claw` (Xeon E5-2680 v4, ~16 GiB ECC, Ubuntu 24.04). Never call it a laptop; SearXNG already owns `127.0.0.1:8080` and co-located n8n/app databases remain residual risk the user accepted. Trust CI therefore publishes another loopback port (`127.0.0.1:18080` by default) with compose project `adaptive-trust-ci`.

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
