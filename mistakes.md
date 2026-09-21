# Mistakes

<!-- BEGIN ADAPTIVE GROK GOVERNANCE PROJECTION: mistakes.md -->
> **NON-AUTHORITATIVE PROJECTION.** Canonical JSON governance records remain authority; this Markdown cannot approve, activate, repay, or accept any record.

## Open governance debt

_No open governance debt._

## Overdue governance debt

_No overdue governance debt._
<!-- END ADAPTIVE GROK GOVERNANCE PROJECTION: mistakes.md -->

Root causes, not symptoms. Record only mistakes that caused a real problem.

## 2026-09-09 — Rewrote a whole architecture model to add three entries

**Symptom:** Declaring one demo node, contract and edge produced a 1889-line diff in `architecture/system.yaml` instead of the 57 lines actually added.
**Root cause:** The writer re-serialized the model with sorted collections, but the committed model stores `contracts`, `edges` and `nodes` in insertion order, so every element moved.
**Durable rule:** When editing a canonical JSON model, append in place and re-serialize with the file's existing key and element order; verify the diff size matches the intended change before running any gate.

## 2026-09-09 — Read a stale local branch as the current product

**Symptom:** A worktree checkout reported VERSION 2.0.12 while the published release was 2.0.15, and the local `main` ref sat four releases behind at v2.0.11.
**Root cause:** Every worktree tracked a feature branch and no worktree tracked `main`, so `git fetch` updated only remote refs while every readable checkout stayed on old work.
**Durable rule:** Keep one worktree pinned to fast-forwarded `main` as the state-reading entry point and treat any feature-branch checkout as work in progress, never as product identity.
## 2026-09-09 — Shipped a legacy-schema change spec into the exact PR gate

**Symptom:** PR #30 head `a41cd28` failed `repository-verification` on `change-spec` alone; compileall, external holdout, ruff, bandit, architecture, governance and every unittest step passed.
**Root cause:** The change package was authored against compatibility-only `schema_version: 1`, which the decoder accepts for historical reads but refuses as current gate evidence, and no exact `grok_verify --mode pr` run was made before the branch was published.
**Durable rule:** Author every new change spec against the current `schemas/change-spec.schema.json` version and run the exact PR gate with the runner-equivalent `GROK_VERIFY_CAPABILITY` before publishing a branch.
## 2026-09-05 — Mistook architecture validity for route fitness

**Symptom:** Architecture validate, repository drift, and diagram checks passed, but exact route fitness rejected a local pilot import as external and treated `pilot/tests/**` as production source.
**Root cause:** The model assigned the nested test subtree to the pilot production owner without declaring the top-level `pilot` package root, and preflight stopped before running route fitness against the exact base/head pair.
**Durable rule:** Give package roots production ownership and more-specific nested test roots verifier ownership, and run the exact route-fitness command before declaring architecture evidence green.

## 2026-09-05 — Treated targeted implementation tests as the exact PR gate

**Symptom:** The exact PR verifier found unowned `pilot/tests/**`, secret-scan fixture false positives, and root unittest failures after the targeted pilot tests had passed.
**Root cause:** The implementation preflight omitted the exact PR gate, so architecture ownership/adoption fixtures and credential-shaped test/documentation strings were not checked against the repository-wide architecture and secret-scan contracts before the source freeze.
**Durable rule:** Preflight changed architecture ownership and scanner fixtures with their focused repository-wide gate methods, then run the exact PR verifier once on the frozen product tree.

## 2026-08-31 — Ran the restack verifier with its inherited divergent route base

**Symptom:** The first full verifier passed tests and coverage but failed architecture and governance because it compared the merge against unrelated `1c06299894279a88b881defa3f19b004fa742223`.
**Root cause:** The active route was created from a different worktree lineage and its base was not corrected to exact accepted M2 before verification; stacked verification must bind the immediate accepted predecessor before the first full run.

## 2026-08-31 — Invoked the scoped Trust-CI test without its package root

**Symptom:** The first focused workspace test command failed during import with `ModuleNotFoundError: adaptive_trust_ci`.
**Root cause:** The repository-root unittest invocation omitted the service's `trust-ci/src` import root; scoped service tests must run with their package path configured or from the service environment.

## 2026-08-28 — Froze a contract shell instead of the complete schema

**Symptom:** Governance fitness accepted handoff schemas whose five digest/SHA fields were booleans and whose `$defs` or draft identity had been removed.
**Root cause:** `_handoff_shape_matches()` compared selected root names and only the version field, treating a familiar outer shape as equivalent to the complete frozen v1 contract.
**Durable rule:** Frozen contracts must be bound to a trusted canonical semantic digest or compared exhaustively; unknown and additive schema mutations fail closed.

## 2026-08-28 — Let a direct evidence mapping bypass strict JSON parsing

**Symptom:** A direct caller could put `NaN` into an architecture evidence mapping and receive a raw serialization `ValueError` instead of a typed governance rejection.
**Root cause:** File-backed evidence passed the bounded strict JSON parser, but the in-process builder reached digest serialization without applying the same canonical-JSON failure boundary.
**Durable rule:** Every authority input path, including direct typed APIs, must convert canonicalization failures into the same fail-closed domain error before digest or status evaluation.

## 2026-08-28 — Treated evidence-shaped claims as live governance evidence

**Symptom:** Task 3 review showed that a direct rule with `../outside` could transition to reviewed and active rules with missing or mutated evidence could become effective.
**Root cause:** `RuleRecord.from_dict()` erased repository provenance, while transition and effectiveness treated a non-empty path plus lowercase hex as equivalent to descriptor-relative containment and an exact live content hash.
**Durable rule:** Authority-bearing lifecycle values must carry a non-caller-constructible, digest-bound repository identity and reverify evidence through the pinned no-follow boundary at every promotion or effect decision.

## 2026-08-28 — Stored governance authority on a caller-visible object

**Symptom:** The first live-evidence repair could be bypassed by calling `_with_document()` on a loaded candidate and pairing the rebound active record with a replaced snapshot.
**Root cause:** An underscore method, private dataclass, and object-identity sentinel were treated as a capability boundary even though ordinary in-process callers could read and invoke all three.
**Durable rule:** Keep authorization provenance outside caller-held values in closure-owned identity state; copied or reconstructed values receive no authority, and public effects consult only that state.

## 2026-08-29 — Opened derived checksum metadata at its authority name

**Symptom:** A pre-existing sidecar hardlink overwrote an external sentinel, while a FIFO blocked package completion after the archive was already published.
**Root cause:** Sidecar publication used `O_TRUNC` directly on the final pathname instead of constructing and validating a separate exclusive inode before atomic replacement.

## 2026-08-29 — Validated only the output-parent leaf

**Symptom:** Common umask `0002` created `dist/` as `0775` and self-rejected it, while an unrelated writer on a non-sticky ancestor could relocate an otherwise private parent outside the requested path.
**Root cause:** Parent creation inherited ambient permissions and the threat boundary ignored ancestor ownership/sticky rename authority.

## 2026-08-29 — Treated a pathname check as publication authority

**Symptom:** A swap after the final successful temporary-name validation could publish an unrelated inode and checksum its bytes, while later post-replace validation still implied an unattainable portable zero-transient guarantee in a mutable shared directory.
**Root cause:** Validation and pathname replacement were separate operations, success was not conditioned on the published name matching the still-held archive descriptor, and the output-parent trust boundary was not explicit or descriptor-bound.

## 2026-08-29 — Evaluated packaging-only POSIX capabilities at shared-module import

**Symptom:** Manifest consumers could raise raw `AttributeError` on platforms without `O_DIRECTORY`, `O_NOFOLLOW`, or `O_CLOEXEC`, before doctor or explicit legacy helpers could run.
**Root cause:** Security capability discovery was placed in module initialization instead of the secure descriptor operation that requires it.

## 2026-08-29 — Discarded exclusive temporary-file authority before publication

**Symptom:** A same-directory pathname swap redirected ZIP writes into an external sentinel, and atomic replacement published archives as `0600` instead of normal or preserved permissions.
**Root cause:** The secure `mkstemp` fd was closed and its lexical name was reopened, while the replacement design treated atomicity as sufficient without preserving inode authority or filesystem mode compatibility.

## 2026-08-29 — Treated lexical package paths as stable file authority

**Symptom:** A benign-looking source symlink archived external sentinel bytes, a replacement could make manifest and ZIP content disagree, and final checksum calculation buffered the complete archive.
**Root cause:** Enumeration, hashing, metadata, and streaming used separate path-following opens without descriptor identity/digest binding, while bounded-memory reasoning stopped before the output checksum.

## 2026-08-29 — Assumed isolated tests could trust and mutate the checkout

**Symptom:** The pinned non-root runner produced five architecture Git ownership failures, a receipt clone child-process ownership failure, and a package failure while writing `MANIFEST.sha256` under `/workspace:ro`.
**Root cause:** Local same-owner/writable-checkout behavior was treated as part of the test contract, so architecture isolation discarded the runner's exact trust, the clone's child lacked process-scoped trust, and packaging used an explicit source-writing API for derived archive metadata.

## 2026-08-26 — Parallelized a bytecode-mutating holdout command with its digest test

**Symptom:** Exact holdout validation ran without `PYTHONDONTWRITEBYTECODE=1` beside the Trust suite, created ignored `holdout.example/__pycache__`, and raced the measured-bundle assertion into one failure out of 200; the cache was moved recoverably to `/tmp/adaptive-grok-holdout-pycache-20260826-final`.
**Root cause:** The shared measured bundle was assumed read-only even though direct Python execution could write bytecode, so two commands with conflicting filesystem effects were parallelized.
**Durable rule:** Run them sequentially with bytecode disabled or validate an isolated bundle copy; the sequential rerun passed 200/200 and exact holdout validation passed with only two files and digest `e2de03333ac37e6478433ad37486f6ee904ae8ba8054c86481c04eb7d56fcd64`.

## 2026-08-26 — Ran PostgreSQL migrations before bootstrapping referenced roles

**Symptom:** The first focused PostgreSQL invocation failed during setup, before its ten test methods ran, because migration 003 referenced absent `trust_ci_*` roles.
**Root cause:** The dedicated database and DSN were prepared before the four roles that the role-grant migration assumes already exist.

## 2026-08-26 — Split temporary workspace initialization across cleanup boundaries

**Symptom:** Failed `GitWorkspace` construction leaked a checkout on its first `chmod`, or a trusted config directory on config `chmod` and XDG creation failures.
**Root cause:** Resource allocation began before the constructor's exception guard, and its rollback tracked only the checkout rather than every independently allocated path.

## 2026-08-26 — Expanded an abbreviated commit identity by hand

**Symptom:** The first final exact-SHA holdout invocation failed closed at `git cat-file -e` before validation.
**Root cause:** I manually invented the suffix of the new short commit ID instead of obtaining the authoritative full identity with `git rev-parse HEAD`.

## 2026-08-26 — Combined mutually exclusive autonomous Codex flags

**Symptom:** The first `codex-m1-rebuild` transient service exited immediately with CLI status 2 before doing any work.
**Root cause:** The launch command combined `--sandbox workspace-write` with `--approve-for-me`, although Codex CLI 0.149.1 defines the latter as an automatic-review mode that already selects the workspace-write sandbox and rejects an explicit sandbox flag.

## 2026-08-26 — Started the user service without the shell proxy environment

**Symptom:** The corrected service loaded Codex but received Cloudflare HTTP 403 responses and exhausted connection retries before touching the repository.
**Root cause:** The interactive shell had `HTTP_PROXY`/`HTTPS_PROXY`, while the persistent user-systemd manager had neither; service environment parity was not checked before launch.

## 2026-08-26 — Invented a repository-global acceptance-criterion namespace

**Symptom:** Remediation 1 made Trust CI reject an ordinary two-package change where both valid specs used their local `AC-001`, contradicting the independent holdout and approved design.
**Root cause:** A bare aggregate `unmapped_ids` representation was treated as proof that criterion IDs had to be globally unique, instead of preserving the actual spec-local identity in the aggregate representation.

## 2026-08-26 — Parsed Git display output as trusted path identity

**Symptom:** Quoted Unicode and control-containing paths could lose protected scopes or disappear from signed spec provenance.
**Root cause:** `GitWorkspace` used line-oriented `git diff --name-only`, then stripped and rewrote its display form instead of consuming NUL-delimited bytes as exact repository paths.

## 2026-08-26 — Imported measured holdout source in place

**Symptom:** Default Trust CI test order created an ignored `.pyc` inside the measured holdout bundle and made the committed digest assertion fail.
**Root cause:** The holdout test loader used importlib beside immutable bundle source, so Python's normal bytecode cache side effect mutated the very tree whose complete file set is hashed.

## 2026-08-26 — Bounded canonical strings without excluding surrogate code points

**Symptom:** Escaped unpaired surrogates passed parsing, then crashed local and trusted semantic digest encoding with raw `UnicodeEncodeError`.
**Root cause:** Structural walkers enforced length, depth, and node counts but assumed every decoded Python string was UTF-8 encodable.

## 2026-09-01 — Treated developer Git objects as exact-checkout inputs

**Symptom:** Trust CI passed both holdouts but failed root unittest because stacked M2/M3 commit objects were absent from its isolated exact-SHA checkout.
**Root cause:** A mandatory state test treated objects reachable only through developer remote refs as part of the repository contract instead of recording the accepted merge-parent proof in durable state.

## 2026-09-01 — Checked only the uncommitted diff for PR hygiene

**Symptom:** Verification reported a clean diff while the committed PR range contained trailing whitespace and 294 PR-only paths bypassed changed-file gates.
**Root cause:** Hygiene inspected only the working tree and inventory used only the stale route base; PR verification must union that exact ancestor with the locally resolved target merge-base range.

## 2026-09-01 — Replaced a review report through delete then add

**Symptom:** An interrupted reviewer rewrite temporarily deleted an evidence report before its replacement was written.
**Root cause:** Replacement was split into destructive delete/add operations instead of one atomic update; preserved reports must be updated in place with a single patch.

## 2026-09-01 — Browser runner lifecycle was not executed

**Symptom:** The browser contract could report `passed: true` and then exit nonzero with `ENOTEMPTY` during cleanup.
**Root cause:** The source-only contract failed to execute the real Chrome child lifecycle, allowing immediate profile deletion while the child was still writing; its replacement execution test then omitted the optional-dependency availability boundary and mistook local host capabilities for the immutable Trust runner contract.

## 2026-09-01 — Used branches as the milestone delivery ledger

**Symptom:** Completed M1-M4 work accumulated across stacked branches while the repository handoff still said M1 had not started, causing M4 to be overlooked.
**Root cause:** Isolated branches were allowed, but completed work was not consolidated back into one active route and repository-level state that separated stack integration from protected-main delivery.

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

# 2026-08-28 — Human approval CLI imported the server graph

Root cause: the shared CLI imported API, worker and PostgreSQL modules before command
dispatch, so human-only approval commands failed on a correctly minimal operator host.
Command entry points must load only the dependency slice selected by the operator.

# 2026-08-28 — Staged diff check did not stop the commit

Root cause: the staged whitespace check and commit ran as independent newline-separated
commands without fail-fast shell behavior, so the commit proceeded after the check
reported Markdown trailing spaces. Commit gates must stop on the first nonzero result.

## 2026-08-27 — Treated post-mutation checks as transactional containment

**Symptom:** Four M2-A remediation rounds kept closing named diagram and queue cases while reviewers found equivalent cleanup races, authority-loss windows, and provenance gaps.
**Root cause:** Publication mutated path components before containment was irrevocably established, and queue analysis encoded examples instead of one explicit provenance/limit contract; post-checks and added cases could not repair those design-level boundaries.

## 2026-08-27 — Expanded an abbreviated commit ID without Git

**Symptom:** An exact-head fitness command used a guessed 40-character SHA and failed because the object did not exist.
**Root cause:** The abbreviated commit output was copied into evidence without first resolving it through `git rev-parse HEAD`; exact identities must always come from Git.

## 2026-08-27 — Used module-name tokens to classify an exhausted dependency frontier

**Symptom:** The final queue fix closed the former 64-round truncation but could still return N/A for a real local queue adapter in a neutral-named module after the 4,096-item worklist exhausted.
**Root cause:** Exhaustion preserved only a boolean and then guessed relevance from module-name tokens instead of retaining the precise unresolved dependency frontier and resolving its local imports.

## 2026-08-28 — Restored provenance over evolved same-path evidence

**Symptom:** Restoring design commit `d3b49b7` produced add/add conflicts and briefly replaced newer M2-stack package files before the local commit was amended.
**Root cause:** The restoration ruling was applied to every historical path without first comparing the target lineage for evolved same-path content. Provenance recovery must restore only missing blobs and merge genuinely absent decisions unless replacement of newer files is explicitly required.

## 2026-08-28 — Secured each governance file without binding the whole snapshot

**Symptom:** Task 2 initially allowed a replacement repository root to splice schemas and registries, accepted zero-valued `O_NONBLOCK`, and digested a handoff schema with unresolved references.
**Root cause:** The loader treated per-file identity checks, partially symmetric flag checks, and keyword-only schema preflight as substitutes for their enclosing contracts: one pinned root identity, every required nonzero capability, and whole-schema reference validation.

## 2026-08-28 — Validated reference targets without matching evaluator depth

**Symptom:** Handoff-schema aliases and cycles named existing object definitions but caused the one-hop validator to drop the referenced digest constraints.
**Root cause:** Reference-graph existence was checked independently of the shared validator's supported one-hop subset. A schema gate must either reject aliases or implement the same bounded transitive resolution and cycle policy as its evaluator.

## 2026-08-28 — Trusted a self-hashed architecture evidence envelope

**Symptom:** A caller could erase adverse fitness, risk, scope, diff, inventory, and adoption evidence, recompute the unkeyed self-hash, and still receive a governance handoff.
**Root cause:** The handoff checked caller-controlled status and aggregate model identity instead of independently deriving the complete exact-state M2 evidence with a trusted risk input and comparing every canonical field.

## 2026-08-28 — Patched a helper at an ambiguous internal context

**Symptom:** The first Task 7 edit temporarily nested the architecture-check body beneath the new governance helper and made the intended path unreachable.
**Root cause:** The patch anchor ended at a repeated inner call instead of the complete function boundary; structural helpers must be inserted against an unambiguous top-level boundary and compiled immediately.

## 2026-08-28 — Bound optional governance by current presence instead of adoption continuity

**Symptom:** Removing every governance registry downgraded an adopted repository to unconfigured, and governance could validate a different architecture snapshot from the preceding architecture check.
**Root cause:** The integration treated independent current-state probes as one continuous authority chain; optional authority needs durable adoption evidence and every downstream gate must consume the exact upstream binding it follows.

## 2026-08-28 — Carried a program base into a stacked milestone verifier

**Symptom:** Final M3 fitness charged the cumulative pre-M2-to-M3 change as 14,611 lines and rejected the frozen governance handoff during contract self-comparison.
**Root cause:** The continuation route retained the program's pre-M2 base instead of exact reviewed M2, while the bounded schema comparator assumed `type` was scalar and had no exact allowance for the already-frozen closed handoff schema.

## 2026-08-28 — Scoped exact exceptions to inputs instead of the compared pair

**Symptom:** A manually truncated base fingerprint broke exact route provenance, while the frozen-schema digest exception classified removal of `$defs`, `$ref`, and `const` constraints as compatible.
**Root cause:** Exact identities were transcribed instead of derived, and the compatibility exception trusted either matching input digest rather than requiring one unchanged reviewed pair.

## 2026-08-28 — Pinned the repository but rewalked nested authority

**Symptom:** A governance snapshot could combine schema and registry files from different nested-directory generations while the repository root remained unchanged.
**Root cause:** Each authority read independently reopened its ancestor directories, so root-only identity checks did not bind the fixed authority topology or the bytes consumed by exact-head evaluation.

## 2026-08-28 — Let repeated evidence overwrite its first observation

**Symptom:** Alternating bytes for one shared evidence path could validate separate rules while only the final exact-HEAD-matching digest survived.
**Root cause:** Evaluation stored path digests with last-write-wins assignment and then reread evidence during liveness checks instead of binding and reusing one immutable first observation.

## 2026-08-29 — Assumed requested mkdir mode survives every umask

**Symptom:** Under restrictive umasks, packaging created a mode-`0000` output parent, then rejected its own default output path and left the directory behind.
**Root cause:** Missing-parent creation trusted `mkdir(mode=0700)` as the final mode instead of binding the new inode, applying exact permissions through its held descriptor, and retaining cleanup ownership across the next validation step.

## 2026-08-31 — Chose the split-hotfix base before checking code lineage

**Symptom:** The first split-hotfix attempt used M1, where `sandbox.py` did not match the failing M2 `workspace.py` implementation.
**Root cause:** The PR base was selected before verifying the failure's code-version lineage; the repair is now based on the exact single-branch M2 stacked base.

## 2026-08-31 — Composed multiple test patch contexts as a tuple

**Symptom:** The first direct classifier test run errored because parenthesized context managers were written as a tuple rather than a parenthesized `with` item list.
**Root cause:** Tuple grouping was used instead of validating the multi-context statement; corrected before behavioral verification.

## 2026-08-31 — Launched root verification during focused remediation

**Symptom:** Two full root verifiers were launched during the focused TR-001 remediation and had to be terminated by their exact PIDs after entering unrelated root coverage discovery.
**Root cause:** The remediation instruction was misread as requiring route/full verification despite the parent retaining final verifier ownership; focused Trust-CI checks were the assigned verification scope.

## 2026-09-01 — Derived a strict deadline from two database clock samples

**Symptom:** The first real PostgreSQL intake violated the exact four-hour constraint by microseconds.
**Root cause:** `accepted_at` and `deadline_at` used separate volatile clock samples; deriving the deadline from the transaction timestamp restored one consistent database-time boundary.

## 2026-09-01 — Added architecture authority without updating every exact-state fixture

**Symptom:** Root receipt and governance tests failed because their isolated repositories contained the new architecture model but not its required factory OpenAPI Git object.
**Root cause:** Only the verification fixture was extended during the first architecture slice; all helpers that materialize canonical architecture must copy every declared contract path as one snapshot.

## 2026-09-01 — Treated task projection changes as lease cleanup

**Symptom:** Cancelling or superseding a leased task cleared its current-run pointer but leaked the run, allocation and capacity counters, after which reconciliation failed on the stale projection.
**Root cause:** Terminal transitions owned only the task row in the original design; the live lease/capacity resource invariant was not centralized under a fixed lock order.

## 2026-09-01 — Validated command evidence without persisting command identity

**Symptom:** API retries could lease twice or return a stale-fence conflict, and CLI UUID keys failed storage constraints.
**Root cause:** Idempotency and correlation were treated as adapter headers rather than durable actor/action/request/result records with a single canonical key format.

## 2026-09-01 — Declared database roles without using them

**Symptom:** Integration tests passed as the database owner while `factory_runtime` retained blanket updates over immutable evidence.
**Root cause:** Role DDL and privilege metadata were mistaken for an effective connection boundary; representative product operations never executed under `SET ROLE factory_runtime`.

## 2026-09-01 — Sampled least privilege and successful idempotency paths

**Symptom:** Null claims changed after queue state, accounting retries ignored the API command identity, and runtime could change capacity ceilings and intake identities.
**Root cause:** The first repair tested representative successful command replays and a subset of immutable tables instead of enumerating every accepted outcome and every policy-bearing privilege inherited from earlier migrations.

## 2026-09-01 — Narrowed policy columns but retained raw policy-table DML

**Symptom:** Runtime could insert a repository ceiling of 999 or reset `active_count`, after which the supported scheduler admitted reader 11 or 21.
**Root cause:** Capacity was treated as a mutable counter implementation detail, so column grants were narrowed without recognizing that counter identity, insertion and assignment collectively constitute admission policy authority.

## 2026-09-01 — Revoked counter mutation but retained allocation release mutation

**Symptom:** Runtime could set `capacity_allocations.released_at`, hide a leased worker from capacity views and leave counters inconsistent while its fence remained valid.
**Root cause:** Least-privilege review covered counter policy and allocation creation but did not enumerate every inherited allocation lifecycle grant or define a live allocation as part of lease validity.

## 2026-09-01 — Required nested containers in a repository-only verifier sandbox

**Symptom:** Exact-head Trust CI repository verification failed when the mandatory factory exit runner could not find Docker.
**Root cause:** The repository verifier treated every PR environment as locally container-capable instead of honoring the immutable runner's explicit `repository-sandbox` capability boundary while preserving the mandatory local exit gate.

## 2026-09-01 — Passed Markdown backticks through a shell-quoted PR body

**Symptom:** The first `gh pr create` attempt launched a local verifier instead of creating the PR and had to be interrupted; no external write occurred.
**Root cause:** A multiline Markdown body containing backticks was embedded in a double-quoted shell argument, allowing command substitution instead of using a literal body file or structured argument boundary.

## 2026-09-01 — Guessed a generated PostgreSQL constraint name

**Symptom:** The first fresh migration `009` run failed while dropping the M0 observation uniqueness constraint.
**Root cause:** The patch used the untruncated logical name instead of querying PostgreSQL's actual 63-byte generated identifier before writing the forward migration.

## 2026-09-01 — Put a destructive repair in an additive migration

**Symptom:** Final architecture fitness rejected migration `009` even though the dropped uniqueness constraint was replaced in the same file.
**Root cause:** The migration optimized the final schema shape instead of preserving the additive, forward-safe history contract; the unaccepted disposable-only draft was corrected before final verification.

## 2026-09-01 — Treated first PostgreSQL readiness as stable image startup

**Symptom:** The disposable exit intermittently lost its first host connection immediately after `pg_isready` succeeded during the image's bootstrap/postmaster handoff.
**Root cause:** The harness proved one readiness sample but did not account for the official image's one-time server replacement before opening external clients.
**Correction:** A fixed delay was still only a timing proxy; the harness now proves `postmaster.pid` belongs to PID 1 and that final server is ready.

## 2026-09-01 — Fixed a security fixture expiry to the delivery date

**Symptom:** The fresh exit suite failed after the calendar crossed a hard-coded bootstrap-exception timestamp.
**Root cause:** A bounded-expiry test encoded the project schedule date instead of deriving the permitted short lifetime from its captured test clock.

## 2026-09-01 — Extrapolated a local milestone ETA to the whole program

**Root cause:** The M4 local implementation forecast was presented as program deadline confidence without checking downstream dependencies and external gates, especially the M8 human cohort and Trust CI. Future status reports must state local milestone forecasts separately from end-to-end deadline confidence and name unresolved human/external gates.

## 2026-09-02 — Treated cache names and default Git answers as complete authority

**Symptom:** Tracked `.venv` artifacts escaped architecture drift, criss-cross history appeared to have one PR merge base, and delivery verification silently lost its local PR-target range.
**Root cause:** Inventory ignored filesystem names without consulting the index, while range selection accepted Git's default single merge-base output and represented an absent delivery target as an ordinary optional result.

## 2026-09-02 — Reused one claim repository across supersede race subtests

**Symptom:** The first GREEN run left writer capacity active because the writer claim selected the reader subtest's queued replacement instead of the task being superseded.
**Root cause:** The concurrency fixture isolated source identities but not scheduler eligibility; each interleaving must use its own repository so a real `SKIP LOCKED` claim cannot select leftover eligible work from another subtest.

## 2026-09-02 — Anchored new tests inside a composite test

**Symptom:** Three retry-limit regression methods were initially inserted before the existing retry/budget test had ended, making its remaining assertions belong to the last new method.
**Root cause:** The patch matched a repeated inner assertion instead of a method boundary; inspect test discovery and surrounding indentation after structural patches, then anchor additions at the next top-level test definition.

## 2026-09-02 — Bypassed the factory project environment for API tests

**Symptom:** A controller invoked API tests with system Python and hit a missing FastAPI import, producing no product evidence.
**Root cause:** The command bypassed the factory-managed environment; focused factory checks must use `uv run --project factory ...`.

## 2026-09-02 — Assumed the default package output path was trusted

**Symptom:** The first `package_stack.py` run rejected `dist/` before creating an artifact because a repository ancestor grants group rename authority.
**Root cause:** Secure packaging validates the whole output ancestor chain; in a shared workspace, generate into a private trusted temporary directory and copy the verified zip and sidecar to the tracked package path.

## 2026-09-02 — Ran root-relative checks from the package directory

**Symptom:** Ruff and JSON validation could not find repository-relative targets, producing no product evidence.
**Root cause:** A mixed verification batch used `packages/` as its working directory; commands with root-relative paths must run from the repository root, while only the sidecar check should change directories.
**Location:** Wrong cwd `/home/pall/grok-projects/adaptive-grok-build-pro-m4-control-plane/packages`; correct root `/home/pall/grok-projects/adaptive-grok-build-pro-m4-control-plane`.

## 2026-09-02 — Shared ambient inventory between packager and verifier

**Symptom:** Five ignored/untracked evidence files entered the ZIP while the common-mode parity test passed.
**Root cause:** Both packager and verifier used the ambient filesystem `rglob` inventory instead of an independent exact Git-tree authority.
**Correction:** Release artifact inventory and bytes must equal the filtered tracked exact `HEAD`, and the shipped-artifact test must derive its expectation independently from Git objects.

## 2026-09-02 — Compared untracked permission bits with Git tree modes

**Symptom:** The first rebuilt artifact matched HEAD inventory and bytes but the regression rejected a clean non-executable file whose worktree mode was `0664` while Git normalized it to `0644`.
**Root cause:** The test compared full POSIX permission bits even though Git records only the executable distinction and the release invariant requires exact inventory, bytes and hashes.

## 2026-09-02 — Treated symbolic HEAD and output paths as stable release inputs

**Symptom:** A release command could report success after `HEAD` moved and could replace an included tracked source chosen as its output.
**Root cause:** Inventory and cleanliness checks re-read symbolic `HEAD`, while publication had neither an immutable ref guard nor a canonical source/output disjointness boundary.
**Correction:** Capture one commit/tree snapshot, guard it before and after reversible pair publication, and reject canonical overlap before creating archive output.

## 2026-09-02 — Treated ambient Git interpretation as raw object authority

**Symptom:** A replacement ref or inherited repository override could make release packaging succeed with bytes outside the raw repository `HEAD`.
**Root cause:** Release and parity-test Git subprocesses inherited replace, graft, repository, index, object and config interpretation controls from their environment.
**Correction:** Bind release Git commands to canonical `ROOT`, strip ambient Git controls, disable replacements and grafts, and keep the parity reader independently sanitized.

## 2026-09-03 — Let shell quoting reinterpret a PR comment

**Symptom:** A Markdown PR comment was posted through a double-quoted shell argument, so backticks executed and mangled the text; the comment was immediately corrected with no repository or SHA impact.
**Root cause:** The command ignored the exec escaping rule; GitHub comment bodies must use a structured payload or single-quoted literal so the shell cannot reinterpret Markdown.

## 2026-09-03 — Let shell quoting reinterpret a search pattern

**Symptom:** A read-only `rg` pattern containing Markdown backticks triggered shell command substitution and printed `013: command not found` before the intended search results.
**Root cause:** The pattern was passed through double-quoted shell text instead of a literal-safe argument; repository searches containing backticks must use single-quoted shell literals or structured argv construction.

## 2026-09-03 — Used ephemeral PGDATA for a restart-persistence probe

**Symptom:** The disposable PostgreSQL restart probe lost the migrated cluster and failed at `SET ROLE factory_runtime` after restart.
**Root cause:** PGDATA was mounted as tmpfs, whose contents do not survive a container restart; restart durability probes require an explicitly named disposable volume that is removed after evidence collection.

## 2026-09-03 — Reused a claim queue across matrix cases

**Symptom:** Later phase-policy cases received a grant for an earlier queued/retry task and reported misleading transition failures.
**Root cause:** The test matrix reused one repository while intentionally leaving claimable rows behind; each independent claim case must use an isolated repository (or explicitly remove prior eligibility).

## 2026-09-03 — Generated bigint JSON bounds through an unsafe numeric type

**Symptom:** Initial inline OpenAPI output rounded PostgreSQL's signed-bigint maximum from `9223372036854775807` to `9223372036854776000`.
**Root cause:** Contract assembly passed the bound through JavaScript `Number`; exact wire integers above `2^53-1` must be emitted as preserved decimal text or corrected and covered by a parsed-value regression.

## 2026-09-03 — Closed the API contract without a complete cross-layer parity matrix

**Symptom:** A follow-up audit found undocumented exact scopes, permissive UUID/config identifiers, mismatched integer bounds and an uncorrelated plain-text 500 after the initial contract checkpoint.
**Root cause:** The first closure tests proved document structure and representative runtime behavior but did not bind every operation and shared scalar/error rule to its runtime producer or parser boundary; future freezes need a table-driven operation/scalar/error parity pass before packaging.

## 2026-09-03 — Proved archive determinism only inside one checkout

**Symptom:** Two builds in the active checkout matched, but the same Git tree in a clean clone produced different ZIP bytes for non-executable members with ambient `0600` versus `0664` modes.
**Root cause:** Release ZIP attributes came from worktree `stat` permissions even though exact Git trees preserve only executable identity; determinism tests must compare distinct clean checkouts with deliberately different non-executable ambient modes.

## 2026-09-03 — Reintroduced credential-shaped synthetic fixtures

**Symptom:** The repository secret heuristic flagged deterministic fake tokens in two test files.
**Root cause:** New tests assigned long token literals directly despite the established scanner convention; construct synthetic credential fixtures from split literals so assignments do not look like committed credentials while preserving runtime behavior.

## 2026-09-03 — Coupled an exact policy test to declaration order

**Symptom:** The first post-rule budget run passed behavior but failed one exact-object assertion on list order.
**Root cause:** The test compared authoring order even though the established loader canonically sorts stable-ID arrays; compare exact objects by stable ID and assert the loader's documented canonical order separately.

## 2026-09-03 — Inherited an unsafe clone-directory umask for packaging

**Root cause:** Ambient umask `0002` created clone and output-parent directories with mode `0775`, violating the packager's ancestor-authority boundary before publication.
**Prevention:** Set an explicit secure umask before clone/build and stat-check both the output parent and its ancestor chain before invoking the packager.

## 2026-09-03 — Ran a long verifier in a turn-bound session

**Root cause:** The roughly ten-minute exact-head verifier ran through a turn-bound interactive exec session, so its handle and process vanished at the automatic session boundary before a receipt was produced.
**Prevention:** Launch long verifiers as detached jobs with explicit PID, log, and exit-status files, then confirm the receipt and fingerprint before treating the run as evidence.

## 2026-09-03 — Resolved a hook against the session cwd instead of the command workdir

**Symptom:** `Hook denied: Production action git-push-branch requires an exact delegated local grant bound to the current SHA.` At `2026-09-03 21:52:25Z`, objective fingerprint `6943dc64...` was written to `/home/pall/grok-projects/google-ads-automation/.grok-stack/runtime/tool-denials.json`, not this M4 worktree runtime. No push occurred.
**Root cause:** `.grok/hooks/pre_tool_use.py` delegated to `.grok-stack/adaptive_grok/_policy_legacy.py:production_action/evaluate_pre_tool`, whose `root_from`/`find_root` resolution used the event/session cwd rather than the nested exec command's explicit workdir; a hook launched or resolved in another repository therefore applied the wrong route and grant state.
**Prevention:** Denials must persist the exact command, effective root, command workdir, and reason so a root mismatch is immediately diagnosable and a production denial cannot be attributed to the intended worktree without evidence.

## 2026-09-03 — Started broad verification before the tracked state was frozen

**Symptom:** A detached full PR verifier was launched while a required `mistakes.md` update and ready-state finalization were still pending; it spent about nine minutes in coverage and unittest work and had to be terminated before producing any usable receipt, wasting compute and electricity.
**Root cause:** The controller scheduled the expensive whole-tree gate by sequence habit before completing all known tracked bookkeeping and finalization and before impact-gating the unchanged factory tree, making the run predictably stale.
**Prevention:** Freeze every known tracked change and artifact input first. For unchanged surfaces or a single failed check, run only the affected or failed check; run the full exact-head PR verifier once on the final frozen candidate, and repeat it only when a tracked mutation or receipt contract truly requires that.

## 2026-09-03 — Treated visible dispatcher tokens as complete execution authority

**Symptom:** Direct wrapper regressions passed, but `xargs -a` could supply a missing Git subcommand or widen a visible branch push, while `chroot` or another unknown dispatcher could hide a root-changing nested shell and borrow the session repository's grant. Later review found that a second supported shell layer, script/stdin shell sources, unresolved production arguments, dynamic Git/GitHub CLI/Docker/npm action selectors, and supported literal `sudo`/`doas`/`env` or shell-option forms could still compose the same bypass. The final verifier also rejected a policy wrapper that temporarily mutated legacy global state under a lock.
**Root cause:** Root resolution required a complete literal sensitive action before marking an unknown/input-driven dispatcher ambiguous, while production classification independently parsed shell chunks; the visible argv therefore did not bind the eventual executable, effective root and exact action as one authority decision. Recursive shell modeling, splitting a quoted shell payload before unwrapping its exact outer shell, a too-narrow literal-prefix grammar, and a variable-only expansion predicate exceeded the parser's proof boundary. The policy wrapper then compensated for overlapping legacy control-plane detection by monkeypatching a module global instead of passing an explicit evaluation option.
**Prevention:** Only a bounded cwd- and argv-neutral wrapper chain and one top-level literal command shell are authority-transparent. One shared, quote-aware authority analysis must bind executable, action selector, production scope operands and execution context; any shell expansion metacharacter in an authority-bearing token, nested or input-driven shell, incomplete executable, or sensitive CLI behind an unproven prefix becomes ambiguous before grant lookup. Policy layers must compose through explicit call parameters rather than temporary global mutation, and compatibility tests remain limited to explicitly inert text, fixed non-escalatable reads and named literal wrapper forms.

## 2026-09-04 — Let exploratory review redefine the acceptance boundary

**Symptom:** Repeated pre-final reviewer probes expanded a locally working milestone into an open-ended sequence of new edge cases, delaying delivery and wasting verification time.
**Root cause:** Exploratory pre-review findings were allowed to expand acceptance scope without a finite severity stop condition.
**Prevention:** From M5 onward, run one fixed verifier/review wave and block only on Critical, core-scenario, authority, tenant-isolation, or data-loss failures; record every other finding in the optimization backlog without reopening the milestone.

## 2026-09-04 — Ported M5 tests and release logic without the final M4 replay/accounting context

**Symptom:** The first targeted PostgreSQL run reported repeated intake-command collisions, owner-login rejections in test-only fault injectors, and retry dispositions for failed runs with residual accounting.
**Root cause:** The semantic graft retained M4 transport replay and capability validation but imported older M5 fixtures that reused one request ID, while the manual release merge selected M4's current-run reservation check instead of the stricter task-wide accounting quarantine required by the combined lifecycle.
**Prevention:** When grafting a successor onto a strengthened predecessor, adapt fixture transport identities and injected stores to the predecessor's capability boundary, then preserve the stricter invariant from either side at every overlap.

## 2026-09-04 — Loaded a package module without its package context

**Root cause:** A one-off diagram regeneration helper loaded `architecture.py` by file path, so its relative imports had no package parent and failed before writing any artifact.
**Prevention:** Invoke repository package modules through their package name after adding the declared package root to `sys.path`; reserve file-path loading for standalone modules without relative imports.

## 2026-09-04 — Routed M7 from test-only wording

**Root cause:** The first route prompt described only a test action and omitted an explicit feature or AI implementation keyword, so routing selected `general_implementer` instead of the required AI write owner.
**Prevention:** State the product behavior, feature intent, and AI domain explicitly before routing; the task was rerouted before implementation.

## 2026-09-04 — Used a reserved classifier substring in M8 routing text

**Root cause:** The route classifier treated the substring `fix` inside `fixed-priority` as bugfix intent despite an explicit feature request.
**Prevention:** Inspect the generated route before package or code changes and avoid ambiguous reserved-token substrings in routing prompts; this was caught and rerouted before implementation.

## 2026-09-04 — Updated release identity without binding the installed runtime version

**Root cause:** Product-version checks compared `VERSION`, README, changelog, and roadmap but omitted `.grok-stack/adaptive_grok.__version__`, allowing the installer-managed runtime to remain at `2.0.11` while the product declared `2.0.13`.
**Prevention:** The focused structure version test must import `adaptive_grok` from the tracked runtime root and require its `__version__` to equal `VERSION`.

## 2026-09-04 — Grafted a successor API into a frozen predecessor contract

**Root cause:** The M6 semantic graft appended six operations to the immutable M4 `factory-control.v1.json` and did not advance every migration, schema, API, and fixture inventory inherited by M8.
**Prevention:** Preserve frozen predecessor contracts byte-for-byte, publish successor surfaces under an additive contract, and update all exact cross-layer inventories in the same source checkpoint.

## 2026-09-04 — Treated the contract inventory as a dependency graph

**Root cause:** Contract fitness rechecked every unchanged contract after any contract change, so unrelated historical schemas with unsupported constructs could poison an otherwise bounded delta.
**Prevention:** Recheck only directly changed contracts and the bounded transitive reverse-`$ref` closure, with regressions for both true dependents and unrelated contracts.

## 2026-09-04 — Bound a stacked route to the delivery-comparison base

**Root cause:** The M9 route stored protected `main` as `base_commit` while its fingerprint and implementation scope were bound to the exact M8 predecessor, conflating PR-target comparison with stacked architecture fitness.
**Prevention:** Bind stacked route commit and fingerprint to the corrected exact predecessor, and keep the independent protected-main diff as a separate verifier check.

## 2026-09-04 — Used the current store against a historical migration fixture

**Root cause:** Schema-14 upgrade fixtures invoked the M6 store after that store began requiring migration-018 intake columns and claim policy, so the fixture failed before exercising the intended upgrade.
**Prevention:** Construct historical rows through a bounded disposable compatibility shim, remove it before migration, and test the real forward migration sequence unchanged.

## 2026-09-04 — Kept a fixed database-suite timeout as the suite grew

**Root cause:** The disposable PostgreSQL runner retained a 300-second inner unittest timeout after the suite expanded to 457 tests, terminating healthy work and producing teardown cascades that resembled database failures.
**Prevention:** Give the bounded unittest-discovery phase an explicit 480-second ceiling, preserving a 120-second margin inside the verifier's outer limit for startup, restart proof, and validated cleanup.

## 2026-09-04 — Stored an executable verifier wrapper inside repository runtime state

**Root cause:** Placing executable `runner.sh` under `.grok-stack/runtime/jobs` made the worktree architecture scanner classify it as an unowned source artifact and invalidated exact-head verification.
**Prevention:** Keep detached executable wrappers outside the repository while retaining only ignored PID, log, and status data beneath `.grok-stack/runtime`.

## 2026-09-04 — Replaced predecessor OpenAPI semantics during successor hardening

**Root cause:** M5 comparator hardening added an undocumented per-`operationId` byte cap and collapsed distinct response-header compatibility rules after final M4 tests had fixed those semantics; focused successor validation did not run the inherited overlap methods.
**Prevention:** Preserve predecessor overlap tests during stacked grafts, bound resources at documented document and traversal limits, and retain specific compatibility reasons instead of substituting a broader category.

## 2026-09-04 — Relied on an undeclared host-only test dependency

**Root cause:** `tests/test_structure.py` imported third-party `jsonschema` even though the root test environment did not declare it, so host verification masked the import failure in the exact pinned Trust CI runner.
**Prevention:** Keep root tests dependency-free where practical and verify import/dependency parity in the exact pinned runner before push.

## 2026-09-04 — Bound release regressions to incidental local Git history

**Root cause:** Historical architecture tests assumed old Git objects remained reachable after a single-branch squash clone, while the published-package test incorrectly compared the immutable release artifact with mutable documentation HEAD.
**Prevention:** Carry digest-verified historical inputs as text fixtures, build synthetic Git histories for selector tests, and verify published artifacts against their tag-bound release record.

## 2026-09-04 — Stopped at targeted unittest coverage after removing final imports

**Root cause:** The clone-independent test repair deleted the final uses of two imports, but its targeted preflight exercised unittest only and omitted static lint for the modified Python files.
**Prevention:** Run targeted Ruff on every modified Python file before push, even when its focused unit tests pass.

## 2026-09-04 — Inferred indexing from incomplete automation visibility

**Root cause:** We inferred non-indexing from one search and an anti-bot-limited origin observation, conflating current automation visibility with search-engine indexing; the user's SERP proves observed indexing.
**Prevention:** Record indexing evidence separately from the ability of an automated client to observe current origin content, and never let one substitute for the other.

## 2026-09-04 — Applied a preview indexing policy to a deployable candidate contract

**Root cause:** Task 1 copied the showcase's `noindex` safety posture into `StaticLandingSpecV1` before the exact indexed target repository was bound, giving provider output authority to contradict source indexing.
**Prevention:** Provider output carries only `preserve_source`; the trusted renderer derives robots, canonical, and hreflang facts from the verified exact target baseline.

## 2026-09-04 — Resolved a Git multicall executable before invocation

**Root cause:** The local clone boundary resolved the `git-upload-pack` symlink to `/usr/bin/git`, changing its multicall `argv[0]` identity and making every no-local clone fail before checkout.
**Prevention:** Resolve the primary Git executable, but preserve the absolute symlink path for Git helper multicall commands and cover the exact clone argv with the focused real-target test.

## 2026-09-04 — Used an empty exception handler in stream cleanup

**Root cause:** The landing stream cleanup used `except Exception: pass` to preserve the original request failure, which made the intended suppression opaque to the security gate.
**Prevention:** Express deliberate cleanup-only suppression with `contextlib.suppress` and run targeted Bandit on every modified production Python path before source freeze.

## 2026-09-04 — Left predecessor tests bound to incomplete global fixtures

**Root cause:** The L5 schema addition did not update one exact global schema inventory, while a long PostgreSQL method compared a module-frozen authority proof with the later wall clock instead of its fixture clock.
**Prevention:** Update every exact inventory with additive contracts and keep fixture-bound authority parsing on the same explicit test clock so suite duration cannot alter semantics.

## 2026-09-04 — Let implementation signals outrun the declared L5 boundary

**Root cause:** A transient stdlib queue and a direct socket import in a denial test advertised capabilities the MVP does not own, while new contracts were incorrectly self-compared against a nonexistent predecessor and pre-L5 AST ceilings were not remeasured.
**Prevention:** Use one bounded awaited intake call, patch denial sentinels by string target, treat an absent contract baseline as vacuous while keeping later changes fail closed, and record finite measured budgets with explicit optimization debt.

## 2026-09-04 — Patched a lookalike instead of the traceback location

**Root cause:** The first deterministic-clock repair matched an earlier near-identical intake call instead of the traceback line inside the failing long-running method, and the isolated method completed before the stale-proof window exposed the miss.
**Prevention:** Bind a repair to the traceback line and enclosing method, then inspect every same-pattern occurrence in that method before rerunning the smallest failed target.

## 2026-09-04 — Treated surface signatures as proof of bounded content

**Root cause:** Landing intake and navigation checks trusted magic prefixes, raw byte substrings, and permissive path parsing instead of establishing canonical path, XML relationship, and media-duration semantics.
**Prevention:** Test adversarial serializations and ambiguous paths, parse only the bounded supported formats, and reject any input whose safety-relevant meaning or duration cannot be established.

## 2026-09-04 — Modeled local resources only across uninterrupted execution

**Root cause:** Accepted jobs, quarantined blobs, and the content-addressed artifact pair had happy-path cleanup but lacked persisted terminal failure, enforced expiry after restart, and exact orphan-pair recovery.
**Prevention:** Define and test every lifecycle at failure, expiry, replay, crash, and restart boundaries before claiming bounded retention or recoverable publication.

## 2026-09-04 — Mistook `nohup` for session detachment

**Root cause:** The long verifier was launched with `nohup` but remained in the exec session, so the command boundary killed PID 3343961 before test stages while its status incorrectly remained `running`.
**Prevention:** Launch long verification through `setsid` or an equivalent detached session, then prove the recorded PID survives a separate command boundary before reporting it as detached.

## 2026-09-04 — Added an untrusted XML parser without its security gate

**Root cause:** The DOCX hardening introduced `xml.etree.ElementTree` while focused functional checks omitted targeted Bandit; the exact verifier correctly caught B405 and B314.
**Prevention:** Run targeted Bandit whenever a modified path parses untrusted formats, and prefer a bounded fail-closed lexical subset when no approved hardened parser dependency exists.

## 2026-09-04 — Validated relationship targets without their source-part context

**Root cause:** The lexical DOCX validator allowed any leading `../` sequence but discarded the `.rels` entry path, so it could not distinguish a legitimate parent reference from traversal above the OPC package root.
**Prevention:** Bind every internal target to its relationship source part and reject it when normalized parent depth exceeds that source directory's package-root depth.

## 2026-09-04 — Invoked an unresolved unittest selector

**Root cause:** The initial targeted validation named a nonexistent unittest class because the exact class and method were not resolved in source before invocation, producing a loader `AttributeError` and executing no test.
**Prevention:** Confirm every targeted selector with `rg` or a source listing before invocation, and treat any loader error as zero verification evidence.

## 2026-09-04 — Used prefix matching for prohibited package members

**Root cause:** The first packaging diagnostic used prefix matching, so allowed `.gitignore`, `.env.example`, and `.gitkeep` files were misclassified as `.git`, exact `.env`, and runtime-state members.
**Prevention:** Use anchored path-component and exact-file predicates, explicitly allow templates and `.gitkeep`, and classify every match before declaring an artifact failure.

## 2026-09-04 — Verified an artifact sidecar from the wrong directory

**Root cause:** The checksum command ran from repository/root context while the sidecar deliberately names only the ZIP basename, so `sha256sum -c` reported that no file was verified despite identical correct archives.
**Prevention:** Run checksum verification from each artifact's `dist` directory, or resolve the sidecar member relative to the sidecar's own directory.

## 2026-09-04 — Reused a release merge as the live main identity

**Root cause:** The immutable `v2.0.13` merge identity was reused as live `origin/main` after later commits because a fetch-and-compare was not a final packaging precondition.
**Prevention:** Before packaging, fetch and bind live claims to `refs/remotes/origin/main` while storing the release merge as a separate historical identity.

## 2026-09-04 — Allowed Markdown backticks to reach Bash substitution

**Root cause:** A read-only `rg` invocation placed Markdown backticks inside a double-quoted Bash pattern, causing unintended command substitution (`main: command not found` and `origin/main: No such file`) even though later checks completed.
**Prevention:** Single-quote literal patterns or pass fixed strings without shell metacharacters, as required by the command-escaping rule.
**Recurrence 2026-09-05:** A documentation audit repeated the same quoting error for `2.0.15`; the command produced only local diagnostic noise, and subsequent literal searches use single-quoted patterns.

## 2026-09-04 — Assumed the configured GitHub merge method was effective

**Root cause:** The effective GitHub mutation rejected `--merge` even though repository metadata reported `mergeCommitAllowed`, so the declared setting was treated as stronger than the mutation response and effective rules.
**Prevention:** Treat the mutation response and effective rules as authority and make at most one fallback to another explicitly allowed merge method.

## 2026-09-04 — Cloned a worktree without its remote-only merge object

**Root cause:** A no-local clone from a worktree did not receive a merge commit that existed only in that worktree's remote-tracking ref.
**Prevention:** Post-merge rebuilds must clone the canonical origin or explicitly fetch the exact merge commit before checkout.

## 2026-09-05 — Spawned outside the active route to probe status

**Root cause:** A collaboration worker was used as a progress probe even though `status_probe` was not route-allowed; it was interrupted before making edits.
**Prevention:** Use `list_agents` and read-only Git/process status for progress checks, and never spawn an agent absent from `allowed_agents`.

## 2026-09-05 — Repeated a passing focused test from stale output

**Root cause:** A fresh normalizer PASS was unnecessarily rerun after stale tool output was mistaken for the current assertion state.
**Prevention:** Inspect the exact current line and diff, trust fresh recorded focused evidence, and rerun only after a source change or failure.

## 2026-09-05 — Mistook component validity for semantic durability

**Root cause:** Component tests treated self-validating JSON and SQLite `quick_check` as durability proof without modeling physical row keys, sealed artifact files, and command replay across process restart.
**Prevention:** Every durable terminal result must have composed close/reopen tests that cross-bind row identity, source, commands, evidence, and external bytes, including tamper and swap cases.
## 2026-09-05 — Created an external issue after invalidating its exact local grant

**Symptom:** Landing issue #1 was created after its exact external-write grant had been materialized, but adding the final body file changed the control worktree fingerprint before `gh issue create`; the ambient execution boundary did not reject the now-stale grant. The issue content and target were intended and explicitly authorized, but the local evidence no longer proved that authorization at effect time.

**Root cause:** The external input file was finalized after, rather than before, freezing the control tree and materializing the grant, and the operator path relied on ambient hook enforcement instead of calling `has_valid_approval` for the exact action/resource immediately before the effect. Future external operations must freeze every local input first, create the exact grant second, explicitly revalidate it third, and permit no repository mutation between validation and the one write.

## 2026-09-05 — Treated an injected test seam as a runnable CLI composition

**Symptom:** Task 5 documented a live command, but `python3 -m pilot` could only return `live_adapter_unavailable` because `__main__` supplied no host composition.
**Root cause:** Readiness stopped at fake dependency injection instead of exercising the public entrypoint through its concrete closed adapters. Future runtime-readiness criteria must include a direct entrypoint contract across fresh processes before the CLI is described as runnable.

## 2026-09-05 — Duplicated the implementation bug in the CSP test oracle

**Root cause:** Both the semantic gate and its positive fixture appended another padding character to an already padded Base64 SHA-256, so they agreed on an invalid browser CSP token. Use an independently calculated literal digest for the positive fixture and compare a closed directive/source map; substring presence does not prove that additional sources or overrides are absent.

## 2026-09-05 — Omitted the new sibling test package from verification

**Root cause:** The verifier discovered root and factory tests but never included the new `pilot/tests` package, allowing a nominal full run to omit the implemented vertical. Explicit pilot discovery now precedes runner-specific early returns, and a temporary passing/failing package regression proves that its actual subprocess result propagates.

## 2026-09-05 — Confused write confinement with read isolation

**Root cause:** The `:workspace` preset prevented outside writes but allowed outside reads; the original probe tested only writes, network and environment-variable names. The repaired profile denies outside reads and both Unix socket forms, and the same pinned configuration is checked against synthetic operator/provider/publisher/sibling sentinels before model execution; no real credential content is probed.

## 2026-09-05 — Launched the targeted recovery loader without the repository import root

**Root cause:** The evidence script ran from a nested directory without placing the repository on `sys.path`, so its first invocation failed during import and ran no test or database recovery. Preserve that failed attempt separately and check the loader path before the one corrected targeted invocation; the subsequent real method and restart probes passed on unchanged source.

## 2026-09-05 — Built before synchronizing the machine-handoff assertion

**Root cause:** The repaired `PROJECT_STATE.json` changed verification status strings before its exact-value test consumer was inspected, causing an avoidable candidate rebuild. Inspect machine-state consumers before source freeze; synchronize the factual assertion without rerunning unrelated suites.

## 2026-09-05 — Left architecture consumers behind the confinement repair

**Root cause:** Adding real synthetic AF_UNIX listeners required a declared local architectural edge, while the previously omitted pilot suite still asserted exact path enumeration instead of longest-prefix ownership. Declare the no-network sentinel boundary and test effective ownership, preserving the separate test node; a public CSP digest fixture must be named as a digest rather than a credential token to avoid the generic secret heuristic's false positive.

## 2026-09-06 — Treated append-only self-learning files as blocked protected paths

**Symptom:** Root `decisions.md` / `mistakes.md` structured edits were denied, so facts were delayed or written only in side worktrees.
**Root cause:** A PreToolUse protected-path deny was read as a standing ban. The user later allowed append-only writes to those two files in every tree, including root. Other protected paths stay blocked.

## 2026-09-06 — Put an HTTP adapter on a network-none landing node

**Symptom:** `landing_live_executors.py` was first listed under `NODE-FACTORY-LANDING-DOGFOOD`, which declares `runtime.network: none`.
**Root cause:** Ownership was treated as "this is a landing file" instead of matching the node's declared network policy. Fitness requires an https edge from the owning node; keep HTTP adapters on a separate injected-capability node.

## 2026-09-06 — Frozen service clock with wall-clock blob expiry

**Symptom:** `test_sqlite_service_restart_retains_revalidates_and_never_replays_artifact` returned `needs_human`/`internal_failure` after 2026-09-06 14:00 UTC.
**Root cause:** The service used `FIXED_TIME` 2026-09-05 14:00 (24h expiry) while `PrivateLandingBlobStore` defaulted to `datetime.now()`. Bind the blob store to the same frozen clock.


## 2026-09-10 — Separate empty qualification accounting from absent delivery

Root cause: a controller-only status assessment treated missing M8 records as a complete inventory of real engineering work. Reconstruct source-project history, merge targets, task acceptance and intervention coverage separately; missing qualified records and User-account merges do not establish zero real tasks or human-operated actions.

## 2026-09-10 — Retain descriptor ownership during rejected snapshot reads

Root cause: handing an opened descriptor to `os.fdopen` before validating its file type assumed the wrapper always took ownership; wrapper construction can fail for a directory and leave it open. Validate with `fstat`, retain an explicit `finally` close, and check rejected reads against a descriptor-count regression; strict timezone offset ranges also need validation before Python normalizes malformed offset minutes.

## 2026-09-10 — Live composition fixtures repeated the mixed-clock expiry defect

Root cause: both live-composition fixture families froze service time but left their private blob stores on wall time, so all three successful-artifact paths began returning `blob_expired` after the fixture date. Inject the same `FIXED_TIME` into each fixture blob store; the original three failures and all 18 surrounding tests then pass with production expiry enforcement unchanged.

## 2026-09-10 — Name replacement did not remove private source facts

Root cause: public analysis replaced source names with case labels while retaining private inventory quantities and operational history. Export only transferable implementation requirements; preserve detailed source findings and reconciliation evidence privately.

- 2026-09-11 test tooling: the first acceleration diff mixed local implementation and Trust CI source; FIT-TRUST-CI-SEPARATION rejected it. Extract the image prerequisite into its own branch and verify the complete PR diff rather than relying on separate commits.

## 2026-09-13 — Trace the actual fitness input before inferring its base

An initial split analysis inferred cumulative code budgets from the verifier's range-union inventory. The architecture check independently constructs its diff from the adopted-model route predecessor; tracing that call path corrected the conclusion before any refs or budgets were changed.

## 2026-09-13 — Count the sealed inventory from its actual constant

Earlier L5 handoff text repeated a 24-member inventory without checking DEPLOY_MEMBERS. The frozen implementation lists 22 publication members (20 prior plus analytics.js/css); source-owned fixture documents are excluded, so delivery documentation now uses the actual constant and source hashes.

## 2026-09-13 — Validate typed change documents before a long verifier run

I generated invariant/forbidden-outcome strings although change-spec v2 requires objects with IDs and evidence mappings, and skipped the available gate validator. The full A verifier then raised during receipt recording instead of returning its report; B was interrupted before the same failure. Correct the object shape and validate every newly generated spec before source freeze; neither attempt is passing evidence.

- 2026-09-13: A shell-tool result with nonzero exit status was treated as successful, starting verification and creating a successor before its source commit existed. Root cause was assuming returned command errors throw; all dependent operations now inspect exit_code before proceeding, and the interrupted run is retained as invalid evidence.

- 2026-09-13: Validating only the staged delta missed whitespace already committed in inherited raw RED logs; A/B full suites passed but cumulative git-diff-check failed. Preserve noisy logs losslessly in JSON and check both genuine route and actual-main ranges before starting a full verification run.

- 2026-09-13: Exact source extraction and passing host tests did not establish the direct FactorySettings/server entrypoint invariants: // aliases bypassed lexical disjointness and one cleanup exception skipped later cleanup. Independent real-SQLite review reproduced both; validate shared path shape before I/O and isolate every owned cleanup stage with finally, then add direct-entrypoint regressions.


## Preserved L5 reconstruction history

These dated notes retain earlier decisions and mistakes. Temporary deferrals and old active-package references describe past phases; current G scope/evidence takes precedence.

## 2026-09-13 — Read the writer-lock error contract before asserting it

The first host regression draft expected `store_in_use` although SQLite writer acquisition emits `store_writer_active`. The root cause was guessing a domain error identifier instead of reading the acquisition path; correct the fixture expectation and rerun the unchanged production source before counting the regression failures.

## 2026-09-13 — Generate ephemeral actor tokens in host fixtures

A hardcoded synthetic actor token matched the repository's generic credential-literal scanner and made the first full verifier report fail its secret check. The fixture mirrored a committed credential shape; generating a fresh UUID token for each test removed the false positive without changing or excluding the scanner.

### 2026-09-13 — Exercise decoder failures through real protocol envelopes

The first Qwen probe redaction test injected a provider exception directly and missed a Unicode encoding error from a syntactically valid HTTP response. The missing step was testing malformed content through the actual decoder; independent review reproduced the escaped surrogate path and required a regression at that boundary.

### 2026-09-13 — Match backup fixtures to parent-directory isolation

The first normal backup/restore fixture placed its control checkout beneath the runtime parent, which the production isolation rule deliberately rejects. Moving the synthetic control checkout into an independent temporary root made the fixture representative; the actual double-slash regression was then reproduced independently of setup errors.

## 2026-09-13 — Publication grant tests missed the issuer contract

The previous synthetic grant fixtures copied the consumer's production/external-write pair without checking whether the issuer could create it; this left real publication unable to authorize. Test an issuer-compatible positive case alongside rejection cases and retain exact resource, current-source and expiry binding.

## 2026-09-13 — Test roots and namespace packages need explicit context

Combining the core, factory and delivery test roots with pytest prepend mode collided on their top-level tests packages, causing 53 collection errors; run the suites separately without changing product packaging. The first boundary resolver also assumed a regular-package initializer below src, but delivery is a namespace package: support an unambiguous src identity and prove it with a real fitness fixture before freezing source.

## 2026-09-13 — Finish broad fast checks before the long verifier

Two closed Factory schema catalogs still omitted additive evidence v2 after focused contract tests passed, forcing a second full-verifier interruption; delivery also needed its existing factory/src import root in the standalone test environment. Keep catalogs exact, run each test root with its required source paths, and finish those fast checks before the long prescribed run.

## 2026-09-13 — PRAGMA shape does not capture SQLite conflict semantics

The publication schema validator checked column/index structure but SQLite PRAGMAs omit ON CONFLICT behavior; REPLACE could pass and overwrite a durable request. Bind the complete supported declaration and explicitly abort insertion collisions, then prove stored-intent preservation with altered-schema regressions.

## 2026-09-13 — Finish operator-document checks before source freeze

Starting the final verifier before the independent documentation audit completed preserved an overstated metrics claim and forced a restart when it was corrected. Bind operator-facing endpoint claims to actual route behavior and finish that audit before freezing source and launching long checks.

## 2026-09-14 — Draft normalization changed validation semantics

The initial PR #82 repair transformed unvalidated arrays and assumed Python string ordering matched the strict contract JSON ordering. That erased the raw item limit, turned malformed section containers into TypeError, and rejected valid mixed-language lists; the original Cyrillic-only positive test did not cover these boundary differences.

## 2026-09-14 — Keep expected-error assertions inside subtests

The first review-repair test draft inspected assertRaises.exception after a subTest had suppressed the intended failure, creating a secondary AttributeError that obscured the product regression. Matching the controlled error inside assertRaisesRegex removed that test-harness artifact before recapturing the red run against unchanged production source.

## 2026-09-14 — Serialized PDF mutation invalidated the page-limit fixture

The existing page-limit test lengthened a serialized Count value while leaving xref offsets and the one-page tree unchanged, so strict parsing correctly failed before counting pages. Real PdfWriter fixtures with 100 and 101 pages exercise the intended boundary without weakening the worker or its independent corrupt-file rejection.

## 2026-09-12 — Force-pushed an unrelated branch pointer from a compound command

**Symptom:** A single compound `run_shell_command` began with `cd /home/pall/grok-projects/adaptive-grok-build-pro` and ended with `git push … refs/heads/perf/parallel-python-tests`. `HEAD` resolved to the session branch, so the push moved PR #33's head branch to `f5e6dcb` (an unrelated merge commit) with a forced update, briefly rewriting the PR head and its diff.
**Root cause:** Two compounding errors. First, a destructive remote write was composed into the same command line as an unrelated `cd`, so the target ref name was reviewed but the ref *source* (`HEAD`) was not — the thing that actually changed. Second, `--force-with-lease` was treated as a safety net while the expected value came from the same mistaken push, so the lease matched and confirmed the damage instead of preventing it. A `||` fallback clause pushed a second path, widening the blast radius of a command that should have had exactly one effect.
**Rule:** Never combine `cd` with a remote write in one command; pass the repository via `git -C <resolved path>` and an explicit `<commit>:<ref>` (never bare `HEAD`). A lease is only meaningful when its expected value is read from the remote first, in a separate prior step. Destructive pushes get no fallback branches in the same invocation, and before any force-push, verify ancestry (`merge-base --is-ancestor`) so that restoring the intended commit is provably lossless.

## 2026-09-13 — A partial read before a follow-up edit silently clobbered a committed paragraph

**Symptom:** The L5 delivery ledger `l5-split-delivery.md` lost its current-head live-probe paragraph (committed in `3eac0f8`) after a later single-row table edit; the regression reached the remote in `7966240` and was caught only by a `git show HEAD:<path>` audit of the committed blob.

**Root cause:** Re-editing the same file after only an `offset/limit` partial read let the edit tool reconstruct the file from a stale pre-edit snapshot, overwriting intervening content; the tool's ambiguous "modified since last read"/empty results hid whether each attempt applied, so no full-content checkpoint existed between edits.

**Rule:** Before editing a file again in a session, full-read it (no offset/limit) or reconstruct deterministically from a committed blob (`git show <commit>:<path>` plus asserted string replacements); after any edit with ambiguous tool status, verify the committed blob — not the working tree — before pushing; never trust a freshness error as proof that nothing was written (see tracker issues #74 and its inverse: both false-failure and silent-clobber directions exist).

## 2026-09-13 — Broke my own verification windows twice while the verifier ran

**Symptom:** `grok_verify --mode pr` reported `source-stability: repository changed during verification checks` on the hardening tree (reviewer reports landed as untracked files mid-run) and again on the release-sync tree, where the second culprit was my own `grok_change transition` editing the tracked `state.json` minutes into the run.

**Root cause:** the running verifier was treated as background rather than as an exclusive read-lock over the tracked tree; package transitions and evidence commits are tracked writes and fall inside the window, and receipts-only runtime state made the distinction easy to forget.

**Rule:** the moment any serial or parallel verification starts, the tracked tree is FROZEN until it ends — transitions, report copies into the package, and receipts that re-bind fingerprints all run strictly after completion; when in doubt, sequence verify last on a committed, quiescent tree.

## 2026-09-13 — `pkill -f` matched my own command line and killed the edit script

**Symptom:** a compound command began `pkill -f 'grok_verify.py --mode pr'`; the heredoc being executed contained that substring, so the wrapper `bash -c` received SIGTERM mid-script and seven asserted edits never ran.

**Root cause:** pattern-based process matching includes the invoking shell's own command line; combining "stop other process" and "do work" in one compound command lets the stop phase destroy the work phase silently.

**Rule:** kill by explicit PID from `pgrep` filtered against self, or use a pattern that cannot match the current command line; never place a process-termination step in the same compound command as the payload it could terminate.

## 2026-09-14 — A local clone omitted the newly merged remote-only commit

A deployment staging checkout failed because a clone of the local worktree repository copied its branch heads but did not include the new merge commit reachable only through the source repository's remote-tracking ref. Fetching the exact merged SHA from GitHub into the independent staging clone restored the missing object, after which checkout and checked-tree identity verification passed. Resolve and fetch the exact deployment commit explicitly instead of assuming a local clone contains recently fetched remote-only history.

## 2026-09-14 — An offline-by-design suite inherited a web-stack test fixture

**Symptom:** `factory/tests/test_landing_backup.py` — whose own subprocess guard asserts that offline backup import must never reach `fastapi`, `uvicorn`, `httpx`, `psycopg` or the HTTP host modules — could not be collected at all on a host without those packages (`ImportError: No module named 'fastapi'`, 0 of 15 destructive-boundary tests executed), and `landing_backup.py` reported 12% in the executed factory suite as if the boundaries were thin rather than absent.

**Root cause:** fixture reuse by class inheritance across a boundary the fixture itself does not respect — one class carried both the offline scaffolding and the single web-stack member (`build_app`), and a loader error at import time is invisible to the merge gate because `factory-unit` runs only four hardcoded modules and never discovers `factory/tests`, so the coupling survived both review and a green exact-SHA check.

**Rule:** share test scaffolding through a non-`test_*` support module whose imports are provably as narrow as the guarantee the suite asserts; prove that narrowness with a guard test that is itself collectable without the heavy dependencies; and treat a loader error as "zero executed", never as a benign skip — a coverage number for an uncollectable module measures nothing.

## 2026-09-14 — Normalising a sentinel made a fail-closed check fail open by directory

**Symptom:** hardening the offline guard's containment test with `os.path.realpath(getattr(spec, "origin", None) or "")` — intended to close a raw-string-prefix bypass — silently changed an unattributable module from always-flagged to flagged-only-sometimes: measured at `cwd=<repo>/factory` the injected spec-less, path-less module was **admitted**, while the same check flagged it at `<repo>` and at `/tmp`. Review round 3 caught it; the earlier rounds could not, because the bypass it reintroduced did not exist before this edit.

**Root cause:** `""` was a sentinel standing for "no location", and wrapping it in a path resolver converted absence into a real, meaningful path — `os.path.realpath("")` *is* the current working directory. A test that then asks "does this location live inside the repository?" is answered by the operator's cwd, so a deterministic guarantee became environment-dependent and errs toward passing. The downstream `if location` filter also stopped discarding anything, since the sentinel had become non-empty.

**Rule:** never pass a sentinel placeholder through a normalising function; keep "absent" as absence (`locations = [realpath(origin)] if origin else []`) and let a missing fact fail closed. After any hardening edit to a security- or environment-boundary check, re-run the *empty/unknown* case from at least two working directories, because a path-shaped false answer is invisible in a single-cwd test.

## 2026-09-14 — A reviewer's appended report carried a blank line the gate rejects

**Symptom:** after five review rounds and every functional check green, `GROK_VERIFY_CAPABILITY=repository-sandbox UV_LOCKED=1 python3 scripts/grok_verify.py --mode pr` returned `RESULT: FAIL` on a single check, `git-diff-check`, with `evidence/code-review.md:445: new blank line at EOF` (exit 2) — 23 files, 2080 added lines, and one whitespace nit stood in front of a fingerprint-bound `verification` receipt.

**Root cause:** review report files were treated as commentary outside the product rather than as committed content of the repository. Each appended round wrote to the end of the same tracked Markdown file, and the final append left a trailing newline pair; nothing in the local pre-flight set (`ruff`, `bandit`, unittest discovery, coverage) examines Markdown whitespace, so the only thing that could surface it was the gate, at the very end of the cycle.

**Rule:** before staging, run the gate's own hygiene check over the diff (`git diff --check <base>`) and lint every evidence file the same way as source — end with exactly one newline, no trailing whitespace — and instruct subagents that append into the tree to do the same. Cheap enough to cost nothing when done before commit; expensive when it costs a full verification window.

## 2026-09-14 — Check the grant scope/action mapping before materializing consent

The first runtime-upgrade grant command paired `production` scope with the `external-write` action and failed before creating a grant because the recovery prose did not distinguish the CLI's supported scope/action matrix. Reading `add_approval` established that host operations require `external-write` scope, after which the same explicitly delegated, resource-bound operation was materialized successfully. Validate the implementation's scope/action mapping rather than inferring it from an operation's production environment.


## 2026-09-14 — Confused an operation not performed with a site not deployed

The L5 rollout performed no site publication, but I phrased that as “the public site is not published” and treated “go ahead” as a new publication task before checking the existing host and the synthetic artifact's content. This conflated the scope of my own actions with external state; read-only HTTPS comparison showed the working site already matched a newer landing main, so no publication or overwrite was performed. Verify the current destination and requested artifact before proposing a deployment, and resolve an ambiguous source-of-truth reference before treating a website as that source.

## 2026-09-15 — Use the credential contract supplied by systemd

The first two local smoke-client preparations rejected the systemd credential before any provider request because they reused an owner-0600 file assumption and then guessed mode-0400. Metadata inspection showed a root-owned mode-0440 credential exposed inside the transient unit; the client now validates that systemd-specific read-only contract without changing the credential or printing its value.

## 2026-09-15 — Assert imported candidate identity before a live probe

A service-user probe could not traverse the developer home, so adding its source path to PYTHONPATH did not establish candidate execution and permitted installed-package fallback; that attempt also timed out. Stage a byte-verified readable copy and assert imported module paths, hashes and adapter version before provider egress; the subsequent probe reached the repaired executor. Its later diagnostic-only TypeError came from omitting the draft decoder maximum keyword, so inspect the callable signature and distinguish executor acceptance from full normalization.

## 2026-09-15 — Match synthetic credentials to the existing scanner convention

A long offline fixture string under api_key matched the repository generic-secret pattern, causing the full verifier to fail after all tests passed. The root cause was treating a descriptive dummy credential as scanner-neutral; replacing it with the existing short test-grok convention passed the exact secret scanner and all74 focused tests without weakening policy.


## 2026-09-15 — Stop carrying completed preparation into current state

The current bootstrap reused old release-preparation and default-off source snapshots as installed-state claims, while tests pinned those obsolete statements. The root cause was treating historical workflow slots as a current product model; archive unique history, refresh dated observations, and test source/release/runtime consistency instead of stale prose.


## 2026-09-15 — Do not preserve decorative inventory as an architecture requirement

The README retained a complete graph because a local instruction and tests required every node pair, even though those edges described no real dependencies. The root cause was treating a presentation invariant as architectural evidence; retire that invariant with the requested graph and preserve the model-based checks.

## 2026-09-15 — Apply provider steering to the active scope immediately

The failover draft kept its original two-provider scope after the user added OpenAI, Claude and OpenRouter and instructed implementation. The root cause was treating that steering as optional future configuration; reread the explicitly authorized selected environment names, update every acceptance boundary to all five providers, and proceed on the already accepted design.

## 2026-09-15 — Discover every closed contract inventory before handoff

The failover implementation added six declared contracts but its focused checks missed four exact inventory assertions in architecture and semantic suites. The root cause was searching only landing-named tests; search existing contract IDs and schema-directory inventory checks across the whole repository, then run those tests and lint before source freeze.

## 2026-09-15 — Test caller boundaries with real transport and CLI ingress

Lexical input exclusions allowed double-slash aliases because normalization was applied only to stored configuration fields; validate every config/input ingress before reads and comparisons. Per-I/O HTTP timeouts were mistaken for complete-exchange deadlines, so trickled headers escaped the bound; use actual cancellation and real Unix-socket regressions. Journal tests stopped at constructor exceptions and missed the CLI contract, so test lock contention and invalid stores through every command and translate expected failures into fixed JSON.

## 2026-09-15 — Establish committed state before testing lost-response recovery

The recovery fixture shared a 0.3-second capability/POST budget and assumed the synthetic artifact had committed before cancellation, so scheduler delay could invalidate its prerequisite. Commit explicitly before dropping the response, block observation until the resume step, and test short deadlines separately from durable recovery.

## 2026-08-30 — Treated imported verification metadata as executable-shaped authority

**Symptom:** Review demonstrated that an imported task could persist `bash -c`, `python -c`, or network-tool argv in RED/GREEN fields while the graph presented them as runnable commands.

**Root cause:** The first implementation validated only that command metadata was an argv-shaped string list; it did not define and enforce a closed read-only verification-command policy at the untrusted-input boundary.

## 2026-08-30 — Reimplemented receipt freshness incompletely

**Symptom:** A three-field forged receipt, or a receipt reached through a symlink, could satisfy workflow advanced-status logic without canonical spec, architecture, governance, kind, or route binding.

**Root cause:** Workflow convergence used an ad-hoc `Path.read_bytes()` predicate instead of the canonical receipt validator and descriptor-bound bounded reads.

## 2026-08-30 — Called check-then-replace an atomic CAS

**Symptom:** Two writers or an interposed filesystem mutation could replace a value after the digest check and lose the competing update.

**Root cause:** The original CAS had no per-target serialization or atomic exchange identity protocol, so its final check and rename were separate operations with a publication gap.

## 2026-08-30 — Let schemas and runtime validation drift

**Symptom:** Runtime accepted 501 tasks, 21 reviewers, 33 argv items, empty/oversized source versions, backslash paths, and ordinary Markdown status was invisible unless a hidden comment existed.

**Root cause:** One generic 500-item string-list helper and annotation-first fixtures were used instead of shared field-specific model validation and native-format counterexamples.

## 2026-08-30 — Validated a CAS competitor before restoring its name

**Symptom:** A symlink, FIFO, oversized, unreadable, or second racing entry displaced by atomic exchange could be deleted by failure cleanup while the new payload remained published.

**Root cause:** Post-exchange validation opened the displaced name before rollback, and cleanup tracked only name existence rather than proving the entry was the operation-owned inode.

## 2026-08-30 — Persisted receipt authority in task source state

**Symptom:** A tracked complete task required a current fingerprint inside the tracked graph, so creating receipts changed the very fingerprint the task required and made verification cyclic.

**Root cause:** The first task contract conflated an imported/native source-status claim with ephemeral effective status instead of deriving verification solely from current canonical receipts at runtime.

## 2026-08-30 — Kept parser scope across independent BMAD headings

**Symptom:** Tasks in a second epic inherited the first epic's identity and dependency chain.

**Root cause:** BMAD normalization selected one heading before scanning tasks rather than resetting section identity, ordinal, and predecessor at each story or epic heading.

## 2026-08-30 — Left authority readers and parser failures outside the shared boundary

**Symptom:** The artifact CLI followed symlinked route/change files and blocked on FIFOs, invalid cover IDs passed direct CAS validation, and recursive JSON parser failures escaped as raw exceptions.

**Root cause:** CLI pointers, runtime task semantics, and JSON recursion were implemented beside—not through—the descriptor-bound loader and shared closed-model validation boundary.

## 2026-08-30 — Dropped ctime and trusted a stat-before-unlink cleanup

**Symptom:** A same-inode content mutation with restored size and mtime passed post-exchange identity checks, while replacement of the temporary pathname immediately before cleanup was deleted.

**Root cause:** CAS identities discarded `st_ctime_ns` after the bounded read, and recovery still treated a prior stat as ownership proof for a later pathname unlink instead of preserving the current entry through a unique no-clobber rename.

## 2026-08-30 — Treated a final pre-syscall identity check as linearization proof

**Symptom:** Content could change after the final target identity check but before `renameat2`, allowing the exchange to displace bytes different from the expected digest.

**Root cause:** CAS validated only metadata around the atomic exchange instead of securely hashing the bounded displaced regular entry after the exchange and before classifying publication as successful.

## 2026-09-06 — Treated local extraction as GitHub delivery

**Symptom:** The session started a side worktree and copied CLI source before answering whether GitHub PRs, checks, and `main` were aligned; the user had to ask twice.
**Root cause:** “Continue to final stage” was read as local file work first. Merge authority is the App-owned check on an exact PR SHA, so GitHub open-PR/check/`main`/tag facts are the first coordination step, not a follow-up after a worktree.

## 2026-09-10 — Do not infer absent real delivery from an empty factory cohort

Root cause: the autonomy assessment treated the controller repository and its landing pilot as the complete evidence universe, overlooking the user-named consumer projects Puls Pump Selector, Google Ads Automation and ii-Tonya. Their GitHub histories and evidence contain real implementation, integration, stand acceptance and native deployment; an unpopulated M8 ledger means qualifying tasks have not been accounted for, not that no real tasks exist. Future assessments must inspect actual delivery branches (Ads uses main while its default branch is codex/bootstrap) and distinguish observed project outcomes from exact-profile autonomy qualification.

## 2026-09-15 Grok merged-release preparation

A no-local clone transferred local branch refs but omitted the merged commit reachable only through the source remote-tracking ref; explicitly fetch the exact merged SHA into the independent clone before checking it out. The coordinator also launched dependent calls without enforcing earlier exit codes, exposing two avoidable preparation errors: external-write belongs to the external-write grant scope, and the non-executable installer must be invoked through sh. No installer ran or release directory was created in those failed attempts; gate every dependent mutation on successful preparation and grant results.

## 2026-09-15 Public current-state drift after live activation

The Grok delivery appended a narrow source fact and recorded activation in PR/runtime evidence, but did not reconcile the existing current-state assertions in README, DARK_FACTORY_ROADMAP, START_HERE and PROJECT_STATE. Historical source-only and release-pending statements therefore remained presented as current facts even after publication and live activation; passing structural/test checks did not detect that semantic contradiction. Future state closure must reconcile the entire canonical current-state set against observed release and runtime evidence, while keeping L5 artifact success distinct from a validated issue-to-human-accepted-PR pilot.

## 2026-09-15 — Accepted an upstream-format claim from placeholder-shaped fixtures

**Symptom:** The port initially asserted "no drift" at BMAD v6.12.0 while genuine upstream story files (`## Epic N:` / `### Story N.M:`, bare `Status:` lines, front-matter `status: in-review`) parsed to nothing and spec-kit's own template emphasis was rejected as YAML authority.
**Root cause:** `source_version` was accepted but never consumed, every fixture used invented H1/`## Status`/`"1"` shapes, and no test ever fed an unmodified upstream artifact body — CI was blind to format drift by construction.
**Durable rule:** Format-currency claims require at least one verbatim-upstream-shape test per pinned release; document known-unparsed subsets explicitly instead of letting silent-empty parses pass as support.

## 2026-09-15 — Asserted a filesystem capability as a security precondition

**Symptom:** After PR #93 merged, the mandatory `root-unittest` command began failing on unrelated pull-request heads (PR #64 failed twice with `verification-failed`) while the identical command passed locally with `715 tests OK`; the single failing assertion was `assertNotEqual(target.stat().st_ctime_ns, original.st_ctime_ns)` inside the serialized-CAS tampering scenario.
**Root cause:** The test proved its tamper was real by requiring `ctime` to advance between two sub-jiffie writes, a property of the local filesystem rather than of the CAS; on the runner's filesystem both reads are equal, so the precondition failed before any product behavior was exercised, and `ctime` had been added to the identity tuple without anyone noting that it is the one field a filesystem may not be able to observe.
**Durable rule:** A test may not treat a timestamp advance as evidence of tampering — assert the fields the product actually restores (inode, size, mtime) plus the content difference, and pin the rejection to its failure code. The CAS guarantee is layered (pre-write expected digest, strict pre-exchange identity, post-exchange displaced digest) and every layer fails closed on its own, so a test that demands strict `ctime` drift is asserting one host's timestamp resolution rather than the product's property.

## 2026-09-15 — Re-ran a full suite locally before reading the retained CI evidence

**Symptom:** About an hour was spent reproducing an external `root-unittest` failure with a clean-worktree full discovery run and a container experiment, both of which passed, while the failure had already been recorded verbatim.
**Root cause:** The Trust CI job stores `result->commands[]` with `stdout_tail`/`stderr_tail` per command, so the exact failing test name, file, line and assertion value were available in `trust_ci_jobs` from the first minute; the diagnosis started from the assumption that an unreproducible failure must be environmental.
**Durable rule:** For any external check failure, query the retained per-command output tails first and reproduce only after the recorded assertion is understood; an assertion that cannot be reproduced locally is more often a precondition the host satisfies by accident than a broken runner.

## 2026-09-09 — Merged a moved config section and silently dropped two required commands

**Symptom:** Merging current `main` into the repository-profile branch conflicted on `trust-ci/config/policy.example.json`, and taking the branch side alone would have shipped a catalog without the `compileall` and `repository-verification` commands that `main` had made required.
**Root cause:** The branch moved `commands` and `holdout` from global policy into per-repository profiles while `main` kept adding entries to the global list, so a structural move and a content addition collided as one text conflict.
**Durable rule:** When a conflict is a moved section, diff both sides as data rather than text: enumerate the entries each side declares and carry every missing one into the new location before staging the file.

## 2026-09-09 — A stale branch measured its architecture against a frozen base

**Symptom:** After a clean merge of `main`, `grok_verify` reported `fitness=fail` with 93 677 changed lines and exceeded byte, line and complexity budgets, while a direct fitness run against `origin/main` passed.
**Root cause:** The worktree's runtime route still carried the branch's original `base_commit`, so the architecture comparison base resolved to a `frozen_adoption` bootstrap commit and every change delivered to `main` in between was attributed to the branch.
**Durable rule:** After merging a new base into a long-lived branch, update the runtime route `base_commit` to the exact new base before reading any architecture, fitness or budget verdict.

## 2026-08-29 — Push continued after delegated-grant failure

**Symptom:** The feature branch was pushed after `grok_approve.py` rejected the requested `external-write` scope.
**Root cause:** Approval creation and `git push` were placed in one shell command separated by `;`, so the push ran despite the failed prerequisite; delegated release operations must use the `production` scope and execute only after a separately verified grant succeeds.

## 2026-08-29 — Editable install polluted the source tree

**Symptom:** Baseline dependency setup created an untracked `trust-ci/src/adaptive_trust_ci.egg-info/` directory.
**Root cause:** `pip install -e trust-ci[test]` was run from the repository instead of building/installing non-editably into the temporary virtual environment. Use a non-editable install or direct `PYTHONPATH` for disposable verification environments.

## 2026-09-16 — Narrated subagent review verdicts before either report existed

**Symptom:** During the v2.0.17 release chain the parent agent reported a review verdict, finding ids and file:line citations for a security and a release review while both reviewing subagents were still running; the cited files did not exist on disk and two cited lines in `DARK_FACTORY_ROADMAP.md` contained unrelated text.
**Root cause:** Absence of a completion signal was read as presence: the only notification in that turn belonged to an unrelated monitor timeout, and the expected shape of a review (taken from the review brief's own checklist) was narrated as if it were its result, while the long delivery chain rewarded reporting planned progress as achieved progress.
**Durable rule:** A review, verification or gate statement may be written only in a turn where its artifact was observed — report file present and non-trivial, receipt bound to the current fingerprint, or the check conclusion read back from the API; while a dependency is unfinished, report its state and never a guess. If such a claim is discovered mid-chain, retract it explicitly in the next message and apply nothing that was derived from it.

## 2026-09-16 — Bulk-validated an ordered edit script against the pristine file

**Symptom:** Two release-synchronisation scripts aborted with `anchor matched 0 times` on anchors that were plainly present after earlier edits in the same run, and a third wrote a broken `PROJECT_STATE.json` by concatenating an anchor that already contained the old value.
**Root cause:** Validation and application were separated: every anchor was counted against the untouched file although later anchors only exist once earlier replacements have been applied, and one edit helper treated a full `key: value` line as a prefix and appended the new value to it.
**Durable rule:** For ordered tree rewrites, simulate the whole plan in memory against the evolving text and write only when every anchor resolved — or address values by JSON path with the enclosing block located by brace depth, never by key name, because release records repeat keys such as `status`, `tree`, `commit` and `notes` at several depths.

## 2026-09-16 — Buffered an object whole to learn it would not be analysed

**Symptom:** Architecture analysis aborted with `worktree file exceeds analysis limit` on any tree tracking a release ZIP, so every artifact-child pull request looked locally red (issue #80), even though the release content was fine.
**Root cause:** the changed-artifact loop needs only size, SHA-256 and a binary marker — `_line_stats` already returns `(None, None)` for content containing a NUL — yet the readers loaded the entire object first, so `MAX_ANALYZED_FILE_BYTES` converted a memory guard into a verdict failure on a file the analyzer was never going to analyse.
**Durable rule:** When a guard rejects input that the consumer only measures, stream the measurement instead of either widening the constant or skipping the entry: skipping silently drops the file from the diff, and a larger constant only moves the cliff. Keep the refusal for the case that genuinely needs the bytes (oversized text, explicit content reads).

## 2026-09-16 — Killed the external Trust CI runner while cleaning up my own verification runs

**Symptom:** A gate job for an open pull request ended `verification-failed` with the
`repository-verification` command exiting 137 (128+9, SIGKILL); the other five mandatory commands had
already passed. The killed job was not mine: it was the self-hosted runner's own container.
**Root cause:** two compounding habits. First, I searched for "my" processes with a pattern matching the
tool name (`grok_verify`), which also matches the runner container's command line, because the runner
executes the same script — my own shell then received SIGTERM from its own pattern. Second, I switched to
`kill -9` on the PIDs the (bracketed) pattern still reported, without inspecting what they were: one was
`docker run --name trust-ci-<job-id>…` and the other the `python3 scripts/grok_verify.py --mode pr
--no-record --json` inside it, i.e. the live gate run.
**Durable rule:** On this host the verifier runs in three places at once — my worktree, an ignored
sibling worktree, and the Trust CI runner container — so a process-name pattern is never an identifier:
list `pid,args`, match the container or `--no-record` signature, and never signal-kill a job whose lease
owner you cannot name. A killed gate leaves a false cause in the durable record, which is worse than a
slow one: the outcome may have been failure anyway, but the stored reason became SIGKILL instead of the
real whitespace finding. Re-derive by pushing a new head so the next job measures the fixed tree.

## 2026-09-16 — Let generated evidence carry trailing whitespace past a local check

**Symptom:** `grok_verify --mode pr` reported `git-diff-check: 2/4 checks passed` on a documentation
branch whose content was already reviewed and green in every other check.
**Root cause:** the whitespace came from two producers, not one: my own heredoc line in a package plan,
and quoted command output pasted into a reviewer report, where `: ` continuation lines keep a trailing
space. I ran the file-writing script and the test module, but not the cheap diff-hygiene check that the
gate itself performs first.
**Durable rule:** Before launching any verification, run `git diff --check <base>..` against the committed
head — not the working tree — and strip trailing whitespace from generated Markdown and from review
evidence the same way as from source, since the reviewer's file is part of the delivered tree.

## 2026-09-16 — Pinned a reviewer's contract fix to tests before letting fitness judge it

**Symptom:** The capability-contract enum entry and its declaration test survived authoring and unit
runs, then the first `grok_verify --mode pr` hard-failed architecture (`unsupported_schema_keyword` on
the contract and `unsupported_openapi_construct` on everything `$ref`ing it), forcing a revert, a test
rewrite and a wasted gate cycle.
**Root cause:** I treated the reviewer's suggested repair as pre-validated and trusted a green unit test
as evidence the gate could carry the change, while contract editability is decided by the fitness
comparator's closed keyword subset, which had never been exercised against this file because no prior PR
touched a published contract.
**Durable rule:** Before building anything on a `factory/contracts/` edit, run
`grok_architecture.py fitness --base … --worktree --pre-risk …` — it is seconds, the gate is minutes, and
only the comparator says whether the contract is editable at all.

## 2026-09-16 — Recurred the same kill-by-pattern mistake twice in one session, destroying two live gates

**Symptom:** two detached `grok_verify` runs were SIGTERM'd by cleanup commands that matched their own
command line (`pkill -f grok_verify` / bracketed variant), and a third run's empty 0-byte log was read as
evidence it had died, when this tool simply flushes everything at exit; three gate cycles were wasted.
**Root cause:** I applied the 2026-09-13 rule only to the *search* pattern and not to the situation: a kill
step inside a compound command whose tail contains the script path matches itself, and liveness of a
detached child must be established by the PID captured at launch, never by log size.
**Durable rule:** capture `$!` (or the first exact-PID probe) at launch, poll only that PID, and never
place pattern-based process termination in a command that mentions the target script at all.
## 2026-09-16 — SR wave missed a human-readable surface the precedent flipped, because no test reads it

**Symptom:** release review FAILed the v2.0.18 successor: `packages/README.md` still named v2.0.17 the latest
published release and v2.0.18 "tag pending" after the tag and Release were live — the exact two lines the v2.0.17
SR (#100) had edited — while all 119 coupled tests stayed green.
**Root cause:** the wave mirrored the machine records and the four tested docs but not the fifth surface, and that
surface has no assertion; mirrored-authoring reused the precedent's file list from memory instead of deriving it
from `git show --name-only` on the precedent commit.
**Durable rule:** when mirroring a precedent wave, derive the touched-file list from the precedent commit itself
and hand-verify every current-state surface that no test covers; untested prose contradicting the record is a real
defect even through a green gate.
## 2026-09-16 — Overrode a reviewer's clean-checkout count with my dirty-worktree measurement, and the runner proved them right

**Symptom:** PR #115's exact-head App check failed `root-unittest` (346 != 352) although the full local gate had passed on the same commit; the frozen parity digest I had added to silence a review finding was the only failing test.
**Root cause:** when my measurement (worktree, 352 payload entries) contradicted the reviewer's (clean clone, 346), I trusted mine and called theirs a counting slip - but a test that pins numbers derived from the checked-out tree is environment-dependent by construction, and the runner checkout, not my scratch worktree, is the authoritative execution site.
**Durable rule:** when a reviewer's and my measurement disagree about a clean-room quantity, re-measure in a fresh clone before overriding them; better, never freeze checkout-derived constants into tests - assert the property against an in-tree recomputation instead.

## 2026-09-17 — Copied a subprocess helper's shape but not its cleanup invariant, and the gate could not see the difference

**Symptom:** PR #101's `_stream_git_blob` streamed a `git cat-file` child but stopped it only inside the two `except` clauses it named; any other escape closed the pipes in `finally` and left the child running on a nobody-waits pipe, and selector/descriptor setup failures escaped raw where the module promises `ArchitectureError(code=...)`. Issue #109 found it; the base tree's architecture suites stayed green (106 test methods in `tests/test_architecture_fitness.py`, 69 in `tests/test_architecture_model.py`).
**Root cause:** the new helper was written beside `_run_capped` and mirrored its read loop, not its cleanup contract — and no test asserted the "child is stopped" property at all (`grep _stop_process tests/` → no hits), so the copy could diverge silently. The exposure class is also invisible to this repo's gate, which executes those suites on POSIX only.
**Durable rule:** when adding a second helper that spawns a child, copy the cleanup contract (terminal stop in `finally`) and assert that invariant for the new path in the same wave; a shape-only copy of a proven routine is a new, untested code path.

## 2026-09-17 — Asked another CLI model "what is going on" while handing it the answer, and read its echo as corroboration

**Symptom:** a delegated summary of a live incident came back well-formatted and confidently wrong about its own provenance: the tool announced it would inspect the tree, the backup and a service state, then restated the six facts I had pasted into its prompt, adding a deploy/no-deploy recommendation as though it had observed anything. It had no repository access (wrong working directory) and ran no check; the pre-plan line leaking into stdout is what gave it away.
**Root cause:** I treated a second model's voice as independent evidence instead of as a function of my own input. A prompt that already contains the conclusions cannot produce findings that disagree with them, so the round trip was guaranteed to look confirming - the same error class as trusting a fixture over the live host, one layer further out.
**Durable rule:** when delegating judgment to another agent CLI, give it the working directory and real tools and deliberately withhold my conclusions, so a disagreement is possible. If the prompt already holds the answer, run the check myself. Never cite an echoed summary as verification in a report or a decision record.

## 2026-09-17 — Tore down a shared worktree on the assumption that its author was dead

**Symptom:** after a "destroy it" order I reverted three tracked files and deleted an untracked change package; minutes later product code in the same tree was edited again, and the runtime's active-change pointer named the directory I had removed. The restore also re-staged those paths as a silent side effect of re-applying the saved patch.
**Root cause:** I attributed uncommitted work to the most recently *finished* foreign session (its rollout log stopped one minute before my turn) and never asked whether a live process owned the tree. In this stack a change package is not paperwork - the runtime active pointer resolves it, so deleting it breaks a running agent mid-task. Ownership was inferred from log recency instead of enumerated from the process table and runtime state.
**Durable rule:** before reverting uncommitted work in any repository another agent may share, enumerate live agent processes by working directory and read the runtime active-change/active-route pointers; if either names the target, leave it in place and copy out to a hold directory instead of deleting. Afterwards verify the index is untouched.

## 2026-09-17 — Edited a file a machine had started reading, and reported my reruns by overwriting the raw rows

Two ways the same sync record lied. First: the stack release I installed began parsing the consumer's own `.grok-stack/AGBP_SYNC.json`, which requires exactly `{schema_version, kept_local}`, while my provenance ledger carried twelve keys before the sync and eighteen after - so `--plan` aborted on the target, and the first "fix" (declaring the seven intentionally divergent managed paths) tripped the next guard, because a declared managed path is honoured only when it is already byte-identical. Second: I recorded the fan-out as "150 units, 141 pass, 10 fail", which is 151, and turned the raw artifact into that story by replacing the two rows I had since rerun, so the file no longer showed that the authoritative gate unit had failed.
**Root cause:** I treated a file as my documentation while a program had made it an interface, and I treated "the failure was explained later" as license to edit the evidence of the earlier run instead of appending to it. Both are the same omission: I never asked who else reads this artifact, and I let the corrected conclusion replace the observation that produced it.
**Durable rule:** when adding a file to a sync, grep the stack for the filename and read any parser that opens it before writing it; if a machine consumes it, satisfy its schema and keep the prose elsewhere. And never rewrite a raw result: append a labelled rerun row, keep the original, make the arithmetic add up in the artifact itself.

## 2026-09-18 — Edited the tree while my own verification run was watching it, then explained a failure I caused

**Symptom:** the first `grok_verify --mode pr` after a stack sync closed `RESULT: FAIL` on one unit, `source-stability: repository changed during verification checks`, while every substantive check in the same run was green. The change it saw was me: I edited a documentation file in the same message that launched the gate.
**Root cause:** I treated the gate as a background job that could overlap my writing, forgetting that the stability unit exists to bind a verdict to one tree. The verdict carried no information about the code, and either reading it as "green apart from noise" or as "the sync broke something" would have been false.
**Durable rule:** freeze the tree, then verify - never interleave edits with a run that observes them. When a gate reports its own observation of change, first ask whether I moved the ground, and re-run on a quiet tree instead of reinterpreting the invalid verdict; a genuinely unrelated defect in the same log stays a separate finding.

## 2026-09-18 — Chased "binary file not supported" through cosmetics for six probes while six throwaway gists piled up

**Symptom:** `gh gist create` refused a 50-line shell script. Renaming it to `.txt` did not help, dropping the shebang did not help, so I suspected encoding and then the extension. The trigger was the literal text `%PDF-1.4` on one line: the uploader sniffs magic bytes in the content and typed a plain-text file as a PDF.
**Root cause:** I reasoned from what the file was to me (a text script) instead of from what a sniffer sees (a magic signature inside the scanned window), and each probe varied a cosmetic attribute rather than the payload. The bisect loop also called `gh gist create` per iteration, so it accumulated six gists in the account - and `gh gist delete -y` failed silently on the wrong flag spelling, which I read as "delete is not permitted".
**Durable rule:** when a tool insists a text file is binary, bisect the content to the smallest failing prefix before touching anything else, and name the trigger byte in the write-up so dropping the magic from the repro costs nothing. Any diagnostic loop whose steps have side effects must print what it created and clean it up; verify the cleanup command's flags once, explicitly, before relying on them in a loop.

## 2026-09-18 — Wrote "RESULT: PASS" from a gate whose verdict I never read, because the pipeline returned tail's status

**Symptom:** a commit announced `grok_verify --mode pr — RESULT: PASS` while the same command, run minutes later, printed `RESULT: FAIL` on `git-diff-check`. The gate had genuinely failed on that tree: trailing tabs in a generated TSV. Nothing about the environment changed between the two runs.
**Root cause:** I chained `python3 scripts/grok_verify.py --mode pr 2>&1 | tail -2` after `&&`. A pipeline's exit status is the last stage's, so `&&` tested whether `tail` succeeded, not whether the gate did; I then read the two lines I had asked for as if I had read the verdict. The same mistake was available to me because the log line I did look at (`PASS source-stability`) belongs to a different unit than the one that failed.
**Correction, measured the same day:** the pipeline story above is not what actually let the bad claim through. `grok_verify.py` exits 1 on `RESULT: FAIL` (verified: a tracked file with a trailing space produced `RESULT: FAIL` and exit code 1; an *untracked* probe file produced no finding at all, because `git diff --check` only inspects tracked diffs). The real mechanism was ordering: the commit was created first and the gate was chained after it, so the message asserted a verdict for a run that had not happened yet. Pipeline status laundering is a genuine separate hazard, but it was not this one's root cause.
**Durable rule:** never write a verification claim into an artifact before the measurement exists; run the check, read its summary line and its exit code, then cite both. If the check is chained after a commit, the commit message must say what it does not yet know rather than name a verdict. (`out=$(cmd); echo "$out" | grep -q '^RESULT: PASS'`), never infer a result from the exit code of a pipeline or from the presence of a `PASS` line for another unit. Restating a gate outcome in a commit message is a claim about a run: quote the line, not the feeling.

## 2026-09-18 — Ran a CPU-bound lint check beside a timing-sensitive full verifier

**Symptom:** the sole #104 PR verifier run failed inside the unrelated factory PostgreSQL suite after 767 tests; `test_semantic_subject_publish_is_exact_replay_safe_and_role_isolated` hit its 5-second database statement timeout during session validation. The full verifier correctly recorded a failure, so the package has no passing verification receipt.
**Root cause:** while that timing-sensitive suite was running, I allowed a sibling package's Ruff/spec/diff checks to run. Issue #40 explicitly says to serialize CPU-bound checks with suites that have wall-clock-pinned assertions; even though the factory test itself was not duplicated, this violated the resource-isolation rule and could have added enough host contention to trigger the timeout.
**Durable rule:** once a full verifier starts, pause CPU-bound checks in every sibling worktree until it exits; if a timing-pinned check fails, preserve that result and diagnose the exact failing test without rerunning the full suite.

## 2026-09-19 — Re-implemented a task that was already delivered, because the route file was read as current state

**Symptom:** a fresh session was told "go" with `.grok-stack/runtime/active-route.json` naming the task "Fix the
remaining #104 fitness comparator blind spot … anyOf composition", created 2026-09-18T20:06:56Z, and an
`engineering/changes/…-4c524b/` directory containing only an empty `evidence/`. The session concluded the work was
unclaimed and unstarted, built a worktree, re-routed, scaffolded a second change package and dispatched a
five-agent design wave — and only at the very end of implementation planning did `git log --all -S'anyOf'` surface
`2cbfa12`, i.e. open PR #133 (`fix/issue-104-openapi-ref-composition`, same base `2f66ba6`, same route id `4c524b`,
**the same task text**) already carrying the implementation, three route-selected reviews and a SUCCESS
App-owned `adaptive-trust-ci/verified@06ecf1c875bc` on its exact head. The duplicate wave was retargeted into an
audit of #133 and #133 was merged as `d871ea6d5d654406281dd65626a3dce61bf933fa`, closing #104.

**Root cause:** the entrypoint rule was followed literally and emptily — `git fetch --all --prune` ran, printed
nothing (no *ref* changes) and was treated as "remotes checked". Open pull requests are not refs of an existing
branch, so a plain fetch does not enumerate them; the mandatory step "fetch remote refs so open milestone
branches/PRs are not missed" requires a PR-list API call, not a fetch. Compounding it, the orphan empty package
directory was read as "work not started" rather than as evidence that a sibling session had started exactly this
task — and the route id suffix `4c524b` in that directory name already matched the delivered PR's change package
name, which is a deterministic signal the duplicate existed, available before any analysis agent was dispatched.

**Durable rule:** before implementing anything from a route, enumerate open PRs and open issues for the task
(`gh pr list --state open --json number,title,headRefName,baseRefOid` + `gh issue list --state open`) and treat an
`engineering/changes/<id>` directory whose suffix matches the active route id as an in-flight delivery by another
session, never as an empty scaffold. The route file is an instruction to work, not a claim that the work is
undelivered; only GitHub's open-PR inventory can support that claim.

## 2026-09-19 — Published "this construct is unanalyzable" from a probe whose inventory could not resolve its own $refs

**Symptom:** a hand-built comparator probe reported that a contract containing `anyOf` returned `unsupported_schema_keyword`
even when base and head were byte-identical, and I carried that claim into agent briefs and a report as "the blind spot is
sharper than the issue says". Measured against the merged fix with the same probe shape it still looked unfixed.
**Root cause:** `_SchemaResolver.resolve` raises `undeclared schema reference` for any cross-file `$ref` whose target is not
in the inventory the caller passes, and `_unsupported_schema` turns that raise into `unsupported_schema_keyword` on the
contract being tested. My probe built its inventory from the 3 contracts named in the task instead of the full declared set,
so it measured my own scaffolding, not the comparator. The same pair gave `unsupported` at 258 `consume()` calls and
`compatible` at 2894 calls once all 38 `factory/contracts/**` records were supplied.
**Durable rule:** when probing a comparator that resolves cross-document references, the fixture inventory must be the whole
declared set, and the report must state the inventory size plus the work-units consumed; an `unsupported` from a small probe
is evidence about the probe. Cross-check any such claim against the real gate path
(`grok_architecture.py fitness --base <sha> --head <probe-sha>`) before quoting it.

## 2026-09-19 — Published a widening metric built by splicing two different measurement conventions

**Symptom:** a change package, its typed spec and an issue comment claimed the contract-closure fix widened
verification from "10 -> 27" target-dependent pairs. Independent review measured the same trees under one stated
method and got 22 -> 27 transitively, 10 -> 17 one-hop. The published figure combined a *direct* count taken from the
unpatched tree with a *transitive* count taken from the patched tree, inflating the effect roughly 2.5x. The same
review also caught a related mislabel: counts described as "declared contracts" had been computed from a
`factory/contracts/**/*.json` glob (38 files), two of which are not declared contracts at all, so four of nine
"lost edges" named files outside the gate's scope.
**Root cause:** two probes written minutes apart at different scopes and depths, then joined in prose without either
being recomputed at the other's scope. No single command produced "10 -> 27"; each endpoint came from a different
convention, and the direction that felt impressive is the direction that went unchecked.
**Durable rule:** every reported before/after pair must come from one script run over both trees, printing both
conventions (direct and transitive) and the inventory it used, and the number quoted in prose must be one of the
printed lines verbatim. When reviewing my own measurement, recompute it with the same tool the reviewer used before
defending or discarding it — here the reviewer was right twice, about the metric and about the inventory label.
## 2026-09-19 — Compared two source trees inside one process and reported the module against itself

**Symptom:** a "canonical before/after" script took both repository paths as arguments, did
`sys.path.insert(0, repo)` and `import adaptive_grok.architecture` per repo, then printed
`base=22 patched=22, new failure paths: 0` — which looked like a refutation of both reviewers. The reviewers' numbers
(22 -> 27) were right; my script was measuring the first tree twice.
**Root cause:** Python caches modules by name in `sys.modules`, so a second `import` of the same package name from a
different `sys.path` entry returns the already-loaded module; changing `sys.path` between iterations has no effect.
Because both trees expose the identical package name, the "comparison" was a self-comparison and its zero differences
were tautological, not empirical.
**Durable rule:** when comparing code across two checkouts of the same package, run one process per tree, have each
emit machine-readable output to a file, and compare the artifacts. Never import the same top-level package name twice
in one process, and treat a suspiciously clean `no differences` from a hand-rolled A/B harness as the default suspicion
it deserves: verify by making the harness report a difference you already know exists (here: the 5 new closure edges).
## 2026-09-19 — Ran two write agents in the same worktree and let a whole-file rewrite destroy the other's evidence

**Symptom:** an issue-#146 follow-up agent reported that its appended section in
`evidence/mutation-matrix.md` had been clobbered and had to be re-appended, and that a second agent had changed
comparator-visible behaviour in files it believed it owned. The controller (me) had also committed the tree while one
of the two was still working in it, so the commit message asserted a state neither agent had finished declaring.
**Root cause:** I treated "one wave = one write owner" as satisfied because I dispatched the follow-up to a *resumed*
task handle, while the earlier handle's work was still live in the same directory. Two writers, one tree, and a tool
that writes whole files: the later write silently deletes the earlier append. Nothing in the contract detects it, and
`git status` looked clean because both authors were working on the same uncommitted content.
**Durable rule:** before launching any agent that edits files, prove no other agent owns that tree — check the running
roster for a task whose write scope overlaps, and give a follow-up to a *quiescent* owner only. If a wave must
continue while its owner is still active, it gets its own worktree, not a second opinion on the same bytes. Before
committing, read the working tree's `git status` and the last-modified time of every file in the diff, and never write
a commit message about a state an agent has not finished reporting. Evidence files must be appended by the tool that
owns them, and the controller must assume whole-file writes are destructive unless the agent reports its append was
verified present afterwards.
## 2026-09-19 — Corrected a package, and in the correcting commit overwrote a lane's true attribution with an unmeasured one

**Symptom:** after a review forced the audit package to re-derive every number on the declared inventory, the
correcting commit `b81849a` introduced a *new* false cell: the blocked-contract table said
`CONTRACT-FACTORY-LANDING-OPENAPI-V1` was carried by a root `servers` key. Measured: that contract
(`factory/contracts/openapi/landing-dogfood.v1.json`) has root keys `components`/`info`/`openapi`/`paths`, no
`servers` at all, and 56 `$ref` occurrences; the root-`servers` shape belongs to a different contract,
`CONTRACT-ADAPTIVE-DEMO-OPENAPI`. The analysis lane's original text had the attribution right, and the rewrite
replaced it with a remembered guess. A reviewer also caught two same-family overclaims in that commit: a claim that
harness blocks printed a number only a shell `ls` prints, and a clause readable as "no unlocked contract used
`anyOf`" when exactly 3 of 25 did.
**Root cause:** in a correction pass, prose that already *looks* verified inherits the trust earned by the numbers
next to it. I re-derived the counts with a script and then filled an adjacent descriptive cell from memory, in the
same edit that confessed to descriptive-from-memory errors. There is no separate gate for "adjective" claims, so the
unit-level discipline has to cover every cell, not just the numerators.
**Recurred immediately, which is the actual finding:** the next correction commit (`fc9d877`'s predecessor review round) invented
three more facts the same way — that a record "carries `urn:`-form `$ref`s" (measured: it has zero `$ref`s of any
kind), that two `urn:` references "resolve to nothing declared" (both resolve through declared `$id`s of other
contracts), and line counts "205 / 209 lines differ" that no command reproduces (`git diff --numstat --no-index`
gives 163/21 and 155/57). So this is not one lapse of attention but a property of correction mode: the pass is
primed to re-derive the *numbers the reviewer quoted* and fills adjacent descriptive prose from recall, and each
fix commit adds a fresh unreviewed surface that the next round must catch.
**Durable rule:** in a correction commit, every changed cell — numeric *or* descriptive — must come from a command
run in that pass, and the commit must state which block or command produced each. Treat the correction diff itself
as unreviewed new code: list every sentence it adds and name the command behind each, before declaring the finding
closed. When overwriting another lane's
text, prove the replacement against the source file before deleting the original; if it cannot be proven, keep the
lane's value. Same-pass additions get the *stricter* review, not the looser one, because nobody has read them yet.

### 2026-09-19 — Runtime upgrade preflight and dependent command ordering

The initial Grok backup failed because preflight checked storage space and state but missed ownership of the existing backups parent; the old unit was resumed before migration, then only that parent was corrected under an exact grant. A separate offline smoke failed because I treated an exec session as completed and launched its dependent client before startup finished. Check parent permissions up front and wait for the actual process result plus readiness before dependent work; preserve both failures instead of reporting an uninterrupted green rollout.

### 2026-09-19 — Validate operational specifications before pushing records

I skipped the full local product suite correctly for an operation-record-only change, but also omitted the cheap gate-profile validation of its new typed specification. The red-risk package therefore omitted mandatory forbidden_outcomes and approvals.required_scopes, making PR151 fail repository-verification after its code suites had passed. Validate changed specs directly before push; a no-op product exemption does not exempt the new document from its own schema.

### 2026-09-19 — Executable-looking operator evidence
Archiving one-off operational command bodies as repository `.py` files incorrectly made the evidence node own executable network clients, including a false TCP inference from `socket.gethostname()`. Preserve exact bytes in indexed inert archives, document the external operator boundary, and verify actual execution bodies separately instead of granting network permissions to the evidence repository.

### 2026-09-19 — Runtime audit executable identity
A read-only post-acceptance audit guessed `adaptive-landing-host` instead of comparing the reviewed unit’s actual `adaptive-landing-server` executable and therefore falsely failed one assertion. Read the installed unit identity rather than infer CLI names; the corrected metadata-only audit passed without any new provider call or service change.

### 2026-09-19 — Refresh origin/HEAD after repointing a local clone

The operational clone retained origin/HEAD from its former local remote, so its linked implementation worktree pointed to a deleted release branch even after fetching GitHub. The full verifier completed every test successfully but correctly rejected that unresolved PR target; `git remote set-head origin -a` repaired the local reference and the unchanged-tree Git check passed without rerunning tests. Refresh this reference and run the cheap Git target check before a long verifier when repointing a clone.

### 2026-09-19 — Keep orchestration helpers outside the source checkout

An ignored Python helper under .grok-stack/runtime was still discovered by the architecture source inventory and correctly rejected as unowned source. Move task-only orchestration scripts to an external temporary path rather than adding an architecture exception; repository evidence can stay in its intended package.

### 2026-09-20 — A "one tree" control that hashed the file list could not see the tree change

The resumed #155 contour needed proof that its four-pass PostgreSQL evidence streak ran against one tree, so the driver recorded `git rev-parse HEAD` plus `git status --porcelain` over the product paths at start and end. Both streaks printed the identical value `8883279fa1bf6795`, and the code reviewer showed that value also stayed identical across a real content change (`test_migrations.py` gained a test at 03:56 between them) — `git status --porcelain` reports paths and staged state, never bytes. The root cause is writing a control to look like the property instead of testing it: nothing asked whether the instrument could distinguish a violation, even though the repository already owns the right primitive (`adaptive_grok.util.tree_fingerprint`, HEAD plus changed-file contents) and the verifier's own `source-stability` unit uses it. Before trusting a self-built control, run its negative case — mutate the exact thing it claims to detect and require the control to move — and state in the record which property it measures and what it therefore cannot prove.

### 2026-09-20 — Read `nproc` as host capacity and reported 22 CPUs on a 28-CPU machine

The session opened by reporting "host: 22 CPU" and planning fan-out from it; the owner corrected the number. Measured: Intel Xeon E5-2680 v4, 1 socket × 14 cores × 2 SMT = 28 logical CPUs, all of `0-27` online, `cpuset.cpus.effective = 0-27`, and the 22 was only the CLI process's inherited affinity mask `0,1,8-27` — `taskset -c 0-27` gives a child all 28. `decisions.md` had already recorded this distinction, so the failure was quoting the convenience signal instead of measuring: `nproc` answers "how many CPUs may this process use", which is not the question "how much machine is there". For capacity take `lscpu`, `os.sched_getaffinity(0)`, `cpuset.cpus.effective` and `taskset -pc $$` together, say which of them a quoted number came from, and size parallel work with the real mask or `xargs -P 28`.

### 2026-09-21 — A corrected message retained the false diagnosis in its exception chain

The #155 compatibility branch renamed a NULL refusal only after `from_dict(None)` had raised `invalid_object`, then chained that parser error into the new StoreError. The root cause was classifying a protocol refusal after contract parsing while testing only the outer message; independent review reproduced the misleading traceback. Classify refusals before parsing and test cause/context as well as displayed text.

### 2026-09-21 — Source reversion is not migration recovery

The #155 recovery document called a whole-commit revert a forward fix, although removing packaged migration 021 makes the migrator reject an already-upgraded database and never replays 018. The root cause was reasoning from the old function body remaining in Git instead of the migrator's immutable applied-prefix semantics. Recovery must retain all applied resources and use a separately tested additive correction with compatible application handling.

### 2026-09-21 — Check newly staged evidence, not only the tracked worktree diff

I checked whitespace before staging new raw evidence files, so the check omitted an untracked failing-test log and patch whose exact bytes contained trailing spaces. The resulting commit would fail the PR-target whitespace gate; I cancelled that verifier through its owned cleanup path, preserved both files as lossless base64 JSON envelopes, and checked the staged and committed diffs. Run the staged check after adding every new evidence artifact, and encode exact-byte logs when their whitespace is part of the evidence.

## 2026-09-21 — Distinguish no-index differences from whitespace errors

The external evidence-archive helper stopped on clean files because it treated every nonzero `git diff --no-index --check` exit as a whitespace error. `--no-index` also reports ordinary content differences with exit 1; check diagnostics and the documented exit classes instead. The helper was corrected before any final evidence or completion claim, with raw bytes preserved.


### 2026-09-21 — Combined schema and Trust CI source repairs across a declared separation boundary

I extended issue #162 with a valid Trust CI source validator repair and focused tests without first checking `FIT-TRUST-CI-SEPARATION` against the route base. The root cause was treating two vocabulary consumers as one delivery unit even though `architecture/rules.yaml` forbids mixing `schemas/**` implementation changes with `trust-ci/**` changes in a single diff; the full gate failed fitness and cascaded into governance. Preserve the historical patch, invert only its four source/test paths on #162, and route a dependent Trust CI successor from a base that already contains the schema fix.


## 2026-09-21 — #153 / #161 consumer installation documentation

An installer fixture assumed a public profile_kind argument without inspecting materialize_new. The existing explicit payload seam exercised both profiles without changing the public API.

## 2026-09-21 — Installer review gaps

The first repair audited rendered documentation but overlooked duplicate source artifacts in the managed inventory. A relocation fixture also lacked the newly required template and could fail for the wrong reason; valid positive controls and a specific refusal now guard that test.


## 2026-09-21 — #168 untracked agent scratch fingerprints

The first fingerprint regression matrix cleaned fixtures only after successful assertions, so expected RED failures caused cascading commit errors. Moving fixture cleanup into finally produced an interpretable RED run before the repair.

## 2026-09-21 — Git path transport changed without its consumers
The first scratch fix changed Git inventory to raw NUL records but retained separator normalization and strict text decoding, conflating legal POSIX filenames and crashing on byte-valued names. Dedicated binary enumeration, lossless filesystem conversion and JSON escaping now preserve identity; independent reviews found both gaps before delivery.


## 2026-09-21 — #147 / #148 schema resolution and bounded diagnostics

The frozen-baseline schema probe copied function globals and bypassed a live module monkeypatch, producing harness errors. Compiling the baseline functions into the live module namespace preserved the spy and yielded expected assertion failures with no errors.

## 2026-09-21 — Keep declared-ID fallback separate from raw-path grammar
The initial precedence-only schema fix conflated a raw-path grammar refusal with failure to resolve a valid declared ID. The shipped-contract census and simple aliases missed this boundary; registered unsafe-looking aliases now have comparator-local fallback and explicit no-ID/duplicate/closure controls.


## 2026-09-21 — Match the complete disposable target-binding contract

The issue166 focused wrapper reused nonce and exact-container binding but chose an issue-specific name without checking the repository preflight name contract; preflight rejected it before tests. The owned container was removed, and changing only the cache wrapper to `adaptive-factory-exit-<12hex>` made the unchanged preflight pass. Reuse the entire target identity contract, not only its nonce checks.

## 2026-09-21: Use the actual Git inventory command grammar
The batch identity collector initially reused diff-specific glob pathspec syntax with ls-tree, which does not support it. Reading a NUL-delimited tree inventory and filtering SQL suffixes preserved the intended complete source comparison without product edits.
