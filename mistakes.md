# Mistakes

Root causes, not symptoms. Record only mistakes that caused a real problem.

## 2026-08-30 — Checked idempotency before inserting the authority row

**Symptom:** Two concurrent identical acceptance requests produced one success and one replay error instead of returning the committed winner to the retry.
**Root cause:** A pre-read followed by a unique insert is not atomic across transactions; the idempotency key needs a transactional reservation whose losing insert waits for and re-reads the committed winner.

## 2026-08-30 — Trusted a caller timestamp for promotion consumption

**Symptom:** An expired promotion could be consumed by supplying a historical in-window time.
**Root cause:** The database function authorized and persisted the caller-provided time instead of deriving both decisions from the database clock.

## 2026-08-30 — Granted a deployer role without bootstrapping it

**Symptom:** The migration silently skipped deployer permissions and no isolated deployer database identity existed.
**Root cause:** Role activation was treated as optional in migration 004 even though the bootstrap contract did not create the role; bootstrap must guarantee the identity before an unconditional grant.

## 2026-08-30 — Checked migration preservation after test cleanup

**Symptom:** The populated-003 upgrade test reported that migration 004 lost the seeded job.
**Root cause:** The assertion ran after per-test `TRUNCATE`, so it measured harness cleanup rather than migration behavior; preservation must be captured immediately after the upgrade.

## 2026-08-30 — Ordered append-only events by caller time and UUID

**Symptom:** Accepted and consumed events with the same caller timestamp were returned in reverse business order.
**Root cause:** Caller timestamps plus random UUIDs are not a total append order; durable audit ordering requires a database-owned monotonic sequence.

## 2026-08-30 — Cached startup policy authorized a stale promotion epoch

**Symptom:** A running API accepted a newly submitted promotion after the mounted policy had rotated away from the envelope epoch.
**Root cause:** Promotion authorization reused the startup `Policy` object and the database received only the envelope epoch, so neither boundary established the independently current policy at acceptance time.

## 2026-08-24 — Misread «приложуха» as a public website

**Symptom:** Agents treated «приложуха» as a public website instead of GitHub App `https://github.com/apps/adaptive-trust-ci`.
**Root cause:** Overloaded Russian «приложение» means both a GitHub App and a public website, so the two were collapsed into one live target. Operator truth is `https://github.com/apps/adaptive-trust-ci`.

## 2026-08-24 — Treated a ChatGPT hostname as the live webhook URL

**Symptom:** Operator packages and `decisions.md` pointed GitHub App webhook and Apache TLS at `https://trust-ci.ii-tonya.ru/webhooks/github`.
**Root cause:** A ChatGPT-invented hostname was copied as operator truth. That hostname is a ChatGPT invention, not the GitHub App and not Trust CI on claw; do not configure, probe, or complete TLS for it.

## 2026-08-23 — First protected write invalidated the rest of the grant

**Symptom:** README.md, trust-ci/README.md and decisions.md were denied after tests/toolchain landed, then the session shut down mid-docs pass.
**Root cause:** A fingerprint-bound protected-path grant is consumed by the first successful mutation of the working tree. Remaining listed resources are not a multi-file session; they need a fresh grant or one parallel batch against the then-current fingerprint.

## 2026-08-16 — Hid the prompt files under engineering/

**Symptom:** A user listing the repo root next to `AGENTS.md` still could not see `decisions.md` or `mistakes.md`.
**Root cause:** We rewrote the original prompt filenames to `engineering/decisions.md` / `engineering/mistakes.md` on purpose so agents would not create root files, which hid the files the prompt named.

## 2026-08-16 — Self-learning bullets never wired into AGENTS.md

**Symptom:** Agents had `engineering/decisions.md` and `engineering/mistakes.md` but no standing `AGENTS.md` order to write them.
**Root cause:** Authorship omission when `AGENTS.md` was first written as the Engineering Contract (`ca63b2d`); the log files were added later (`097f5c9`) without wiring the trigger. Not a later delete.

## 2026-08-14 — Treated a matcher bug as an environment block

**Symptom:** PreToolUse denied ordinary `ls`/`cat`/`git` and leftover routes had no write owner, so hooks were moved to `.grok/hooks.disabled/`.
**Root cause:** The deny reason was read as “hooks are too strict to work under,” not as “`PRODUCTION_COMMANDS` matches path text and rematch is keyed off `is_development_prompt`.” Disabling the execution machinery hid both bugs and left the stack unable to classify or police itself until the canonical `.grok/hooks/` tree was restored after the fix.

## 2026-08-14 — Bound verification to an intermediate tree

**Symptom:** First `grok_verify --mode pr` could not be the completion receipt; reports and `state.json` still had to be written.
**Root cause:** Verification was used as a mid-implementation checkpoint. The receipt fingerprint is the whole dirty tree, so any later change-package or review-report write invalidates it. Evidence must be recorded only after the last file that will remain in that tree.

## 2026-08-30 — Treated filesystem policy checks as transaction authority

**Symptom:** A deterministic policy rotation at Store entry could still accept the stale signed epoch after the API's final mounted-file check.
**Root cause:** Re-reading a file and passing an API-selected epoch did not serialize with policy activation. The authority decision must lock and compare a database-owned active-policy row inside the same transaction that reserves idempotency and creates the promotion.

## 2026-08-30 — Refreshed activation time on an idempotent policy retry

**Symptom:** Re-activating the already-active epoch changed `activated_at`, falsely representing a replay as a new activation.
**Root cause:** The initial upsert updated the row unconditionally. Same-epoch activation must return the stored timestamp without updating the row; only an epoch transition records a new database timestamp.

## 2026-08-30 — Echoed the caller's operation ID for every consume conflict

**Symptom:** The first consume boundary attached the newly supplied operation ID to a generic already-consumed error, which could misidentify it as the durable winning operation.
**Root cause:** Promotion and operation uniqueness conflicts were collapsed before checking the committed pair. The database and MemoryStore now distinguish only an exact stored pair; generic conflicts expose no operation identity and cannot authorize another effect.

## 2026-08-30 — Applied a Store method at an ambiguous class boundary

**Symptom:** An intermediate patch placed the MemoryStore reconciliation method inside `PostgresStore.enqueue`, interrupting that method until the immediate compile inspection caught it.
**Root cause:** The patch anchor matched a repeated method boundary without enough class-specific context. Subsequent Store edits used an exact surrounding implementation block and an immediate definition/compile check.

## 2026-08-30 — Bound a CLI output stream at function definition time

**Symptom:** A focused CLI test passed but its success response escaped `redirect_stdout` into the test runner output.
**Root cause:** The helper defaulted `stream=sys.stdout`, capturing the original stream at import time; resolving `sys.stdout` inside the call preserves redirection and test isolation.

## 2026-08-30 — Let runtime settings widen digest-bound promotion policy

**Symptom:** A server running with a 3,600-second runtime TTL accepted a 30-minute envelope even though the active policy epoch limited promotions to 900 seconds.
**Root cause:** Acceptance compared the database only to the policy digest, then authorized environment and lifetime from independent settings without proving those settings were a subset of the digest-bound promotion controls.

## 2026-08-30 — Used pathname checks instead of descriptor-bound sensitive reads

**Symptom:** Promotion creation accepted a symlink to a group/world-readable private key, and envelope readers had a pathname replacement window.
**Root cause:** `is_file()` and later pathname reads followed links and did not bind metadata, bounds and parsing to one descriptor; sensitive inputs now use no-follow, close-on-exec, nonblocking regular-file descriptors and private-key owner/mode checks.

## 2026-08-30 — Added a plaintext localhost exception to an HTTPS-only CLI

**Symptom:** The submit command could send a signed envelope and idempotency key to `http://localhost`, while urllib could inherit an environment proxy.
**Root cause:** A test convenience became a public transport option and the opener did not install an explicit empty proxy handler; the operator CLI now accepts HTTPS only, disables environment proxies and refuses redirects.

## 2026-08-30 — Preserved a second legacy PR signature in the production ceremony

**Symptom:** The design called two envelopes in one session a single human gate, contradicting the required invariant of exactly one signature only at production deploy.
**Root cause:** The deployed legacy-policy bootstrap constraint was treated as permanent workflow semantics instead of an external automated-policy cutover prerequisite; development must block on cutover rather than request a PR signature.

## 2026-08-30 — Contract verification treated JSON-form YAML as raw YAML text

**Symptom:** A valid OpenAPI 3.1 JSON object stored at the contract's `.yaml` path failed `contract-structure` because its top-level keys were quoted.
**Root cause:** The verifier inferred structure from `openapi:`/`paths:` substrings instead of parsing JSON when the YAML document was valid JSON; JSON-form documents now use top-level object keys while ordinary YAML retains the conservative heuristic.

## 2026-08-30 — Recovery backup discarded runtime grants

**Symptom:** A real disposable restore preserved promotion data but runtime-role queries failed with insufficient privilege. **Root cause:** both dump and restore used `--no-acl`, silently deleting the constrained grants that make the restored authority operable; recovery now retains ACLs and tests worker, API and deployer access after restore.

## 2026-08-30 — A lint cleanup matched the wrong repeated fetch

**Symptom:** the real PostgreSQL suite failed only the duplicate enqueue path because its fallback result was fetched but not assigned. **Root cause:** a small patch intended to remove an unused terminal-event local matched an earlier repeated `cursor.fetchone()` block; the exact enqueue context was restored and the database regression retained.

## 2026-08-30 — Modeled retries and policy cutover outside runtime state

**Symptom:** transient merge failures could burn 20 attempts in one hot loop, while a passing set-only cutover drill could not prove the production GitHub adapter preserved protection. **Root cause:** retry eligibility and transition sequencing lived only in control flow/test models instead of durable PostgreSQL state and the production transport boundary; both are now exercised through the actual stores, worker loop and GitHub client.

## 2026-08-30 — Bound host-only recovery checks into the untrusted runner

**Symptom:** local verification passed using an ignored virtualenv and Docker daemon, while the authoritative read-only/no-network runner could execute neither. **Root cause:** one verification command conflated repository-safe exact-SHA checks with trusted-host PostgreSQL orchestration; capability-tagged evidence now separates them and a clean-runner drill fails if `.venv` or Docker leaks back in.
## 2026-08-30 — Fresh clusters hid a role-upgrade gap

The root cause was treating the PostgreSQL init directory as an upgrade mechanism
although it runs only for empty data directories. Upgrade tests must begin with
the old cluster-role set as well as the old schema.
