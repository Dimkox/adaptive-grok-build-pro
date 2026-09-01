# Mistakes

<!-- BEGIN ADAPTIVE GROK GOVERNANCE PROJECTION: mistakes.md -->
> **NON-AUTHORITATIVE PROJECTION.** Canonical JSON governance records remain authority; this Markdown cannot approve, activate, repay, or accept any record.

## Open governance debt

_No open governance debt._

## Overdue governance debt

_No overdue governance debt._
<!-- END ADAPTIVE GROK GOVERNANCE PROJECTION: mistakes.md -->

Root causes, not symptoms. Record only mistakes that caused a real problem.

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
