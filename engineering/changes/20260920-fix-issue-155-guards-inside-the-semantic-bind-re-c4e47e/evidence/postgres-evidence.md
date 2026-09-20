# Issue #155 evidence — `semantic_bind_repair_child` guard rejections and postgres load flake

Worktree `fix/issue-155-repair-binding-rejections`, baseline HEAD
`90078959ff816068af374ad42f4bb80fdbaec866`. PostgreSQL 17.11 on
`postgres:17-alpine` in the disposable container used by
`factory/tests/run_disposable_exit.py`. Ubuntu 24.04.5 x86_64, Python 3.12.3.

Everything below was measured on this host; nothing is inferred from the issue text.

---

## 1. Guard count and enumeration (correcting the brief)

The file `factory/src/adaptive_factory/resources/018_semantic_validation_bridge.sql`
contains **56** `RETURN NULL` occurrences, but the function
`factory.semantic_bind_repair_child(char,text)` spans only lines **1335–1525** and holds:

- **8** literal `RETURN NULL` statements, and
- **1** `ELSE NULL` arm of the `RETURN CASE …` in the already-bound branch,

i.e. **9 NULL-returning guard paths, not ~15** as the issue estimated. Paths by line:
1353, 1367, 1373, 1377, 1393, 1403 (`ELSE NULL`), 1409, 1512, 1523.

The ninth path (line 1512) is a single `IF … THEN RETURN NULL; END IF;` whose predicate is
**49 clauses joined by 48 `OR` connectors** across lines 1432–1512 (`awk 'NR>=1432&&NR<=1512' … | grep -oc '\bOR\b'`
→ 48 connectors) — which is why counting clauses and counting guard paths differ so much.

| # | 018 line | Guard condition (abbrev.) | New reason | clauses |
|---|---|---|---|---|
| 1 | 1350–1353 | isolation ≠ `read committed`; digest not `^[0-9a-f]{64}$`; canonical NULL or > 262144 octets | `command_input_invalid` | 5 |
| 2 | 1355–1367 | `execution_contract_hash` ≠ digest; not a jsonb object; key count ≠ 4; missing keys; `schema_version` ≠ `'1'`; proposal/intent digest and child UUID regexes | `binding_payload_invalid` | 8 |
| 3 | 1369–1373 | child proposal row absent, or `proposal_state` ≠ `pending_handoff` | `proposal_not_pending` | 2 |
| 4 | 1375–1377 | parent task row `NOT FOUND` | `parent_task_missing` | 1 |
| 5 | 1385–1393 | child task `NOT FOUND`; state ∉ (`queued`,`retry`); a newer `generation` exists for the same source | `child_task_unavailable` | 3 |
| 6 | 1395–1403 | proposal already bound to a *different* digest/task/intent/body (`CASE … ELSE NULL`) | `binding_conflict` | 4 |
| 7 | 1404–1409 | `child_task_id` or `child_intent_digest` already bound to another proposal | `child_already_bound` | 2 |
| 8 | 1432–1483 | identity/actor/source/base/architecture/spec/governance/policy/route/change/acceptance/head-digest/parent-subject/issuer agreement | `lineage_mismatch` | 32 |
| 9 | 1484–… | `accepted_at - observed_at NOT BETWEEN 0 AND 300 seconds` (child and parent) | `authority_not_fresh` | 2 |
| 10 | … | `child_task.deadline_at > parent_task.deadline_at`; `> child.body->>'deadline_at'` | `deadline_exceeded` | 2 |
| 11 | …–1512 | 7 parent-limit + 6 proposal-budget `>` comparisons | `child_limits_exceeded` | 13 |
| 12 | 1521–1523 | `EXCEPTION WHEN unique_violation OR check_violation OR foreign_key_violation OR invalid_text_representation OR numeric_value_out_of_range OR data_exception` | `store_write_rejected` | — |

All 9 anonymous paths are now reason-bearing; the 49-clause block is partitioned into four
contiguous named groups (rows 8–11: 32 + 2 + 2 + 13), which is how 9 guard paths became 12
reason codes. Across the ten `IF … THEN RETURN` blocks the function carries **70 guard
clauses** (per-block `OR`-connector count; now pinned offline by
`test_repair_child_guard_structure_maps_each_reason_to_one_clause_group`).

## 2. BEFORE — the misleading diagnostic (measured, not quoted from the brief)

Direct measurement of the mapping chain, `factory/src/adaptive_factory/store.py:746` →
`semantic_repair.py:257` → `semantic_contracts.py:35`:

```
$ python3 -c "…RepairChildTaskBindingV1.from_dict(None)…"
EXC: ContractError -> 'invalid_object: repair_child_task_binding'
is ValueError subclass: True
```

`ContractError` subclasses `ValueError`, so `store.py`'s
`except (TypeError, ValueError)` swallows it and re-raises the anonymous
`StoreError("semantic repair child binding rejected")`. Confirmed live against
PostgreSQL 17.11 (guard list above omitted): the pre-fix function returns bare SQL `NULL`
for every one of the 9 paths — no reason channel of any kind existed.

## 3. BEFORE — the load flake, reproduced deterministically

Waiting for a 1-in-3 stochastic failure is not evidence, so the mechanism was isolated
first. `factory/src/adaptive_factory/store.py:2272` assigns the deadline from the
**server** clock:

```sql
deadline_at = now()+(%s * interval '1 second')
```

while `test_postgres_integration.py:5308` measured the child's inherited wall budget
against a **client** clock captured before several connection setups:

```python
remaining_wall = int((parent_repair.child_proposal.deadline_at - intake_now).total_seconds()) - 1
```

The child's real deadline is therefore `server_now + (proposal_deadline − client_now − 1)`,
so the guard `v_child_task.deadline_at > (v_child.body->>'deadline_at')::timestamptz`
trips **iff the client→server divergence exceeds one second**. In the affected test
`repository_id="owner/m6-repair-status-indexes"` also sends `payload()` down its
non-default branch, which opens an extra `psycopg` connection and INSERT — three
connection setups sit inside that one-second window, which is why this specific test is
the one that flakes.

Probe (`.qwen/tmp/p155_probe.py`, not shipped): runs only
`test_semantic_repair_functions_use_exact_digest_index_conditions`, and optionally
injects a scheduling delay inside the window by wrapping `TaskIntakeV1.from_dict` —
exactly where host latency lands. The control case is required to flip.

| run | injected delay | outcome |
|---|---|---|
| control A | 0 s | `OK` — `Ran 1 test in 4.128s` |
| control B | 2 s | `FAILED (errors=1)` — `Ran 1 test in 13.494s` |

Control B failed with the issue's chain verbatim, at the same line:

```
  File ".../factory/tests/test_postgres_integration.py", line 7072, in test_semantic_repair_functions_use_exact_digest_index_conditions
    self.assertEqual(semantic_store.bind_repair_child(binding), binding)
  File ".../adaptive_factory/store.py", line 748, in bind_repair_child
    raise StoreError("semantic repair child binding rejected") from exc
adaptive_factory.contracts.ContractError: invalid_object: repair_child_task_binding
...
adaptive_factory.store.StoreError: semantic repair child binding rejected
```

So both defects are reproduced on demand; the flake is not "environment".

## 4. AFTER — typed, named rejection

Same probe, same 2 s injected delay, after the fix:

```
### injected 2.0s scheduling delay inside intake window
Ran 1 test in 8.427s
OK
### probe: PASS (delay=2.0s)
```

Store-level rejection, forced by pinning the child fixture to a stale injected clock
through the new `intake_now=` seam (`.qwen/tmp/p155_after.py`, 600 s stale):

```
### raise StoreError(f"semantic repair child binding rejected: {rejection}")
### adaptive_factory.store.StoreError: semantic repair child binding rejected: authority_not_fresh
```

No `invalid_object` frame appears any more; `invalid_object` is reachable only when the
payload is genuinely malformed. Reasons straight from the SQL boundary:

```sql
SELECT factory.semantic_bind_repair_child('0'||repeat('0',63), '{"schema_version":"1"}');
 {"repair_child_rejection": "command_input_invalid"}
SELECT factory.semantic_bind_repair_child(repeat('a',64), '{"schema_version":"1"}');
 {"repair_child_rejection": "binding_payload_invalid"}
```

`test_semantic_subject_publish_is_exact_replay_safe_and_role_isolated` (the method holding
the superseded-child, deadline and budget scenarios) passes and asserts the named reasons
`child_task_unavailable`, `deadline_exceeded` and `child_limits_exceeded`.

## 5. Envelope adopted, and why it matches precedent

The brief named `DraftRejection`/`WorkerRejection` introduced by #152/#154 as the shape to
follow. **Neither name exists in this tree** — `grep -rn "DraftRejection\|draft_rejection"`
returns nothing, and `git show f12807c` (#154) touched only `landing_http.py` and landing
tests. What #154 actually shipped, and what this change follows, is:

- `landing_http.py:78` `_DRAFT_FAILURE_REASONS` — a fixed dict from internal code to a
  bounded public code, with `_draft_failure_reason()` falling back to
  `"draft_validation_failed"` so *"Contract details can contain model-supplied keys; only
  emit fixed local codes"*. Reused as: closed allowlist + fold-unknown, here
  `REPAIR_CHILD_REJECTIONS` / `UNKNOWN_REPAIR_CHILD_REJECTION = "binding_rejected"`.
- `018:284` `semantic_escalations.reason … CHECK (reason IN (…))` and
  `semantic_repair.py:24` `ESCALATION_REASONS` — the repo's existing snake_case
  semantic reason vocabulary, matched in style (`deadline_exceeded` beside
  `deadline_exhausted`, `authority_not_fresh` beside `context_not_fresh`).

Channel: `{"repair_child_rejection": "<reason>"}` — a single key that can never collide
with a binding, because the function's own payload guard requires exactly four keys and
`_closed()` rejects extra keys on the Python side. `repair_child_rejection_reason()`
returns `None` unless the payload is *exactly* that one key, so a malformed envelope
still falls through to `from_dict` and keeps the `invalid_object` diagnosis. No new SQL
function, view or type was introduced, so no new privilege surface exists beyond the
redefined function itself.

## 6. Migration-runner findings (read, then verified on a live cluster)

`factory/src/adaptive_factory/migrations/__init__.py` **does not exist**; the runner is the
module `factory/src/adaptive_factory/migrations.py`. What it actually does:

- `discover_migrations()` iterates `importlib.resources.files("adaptive_factory.resources")`,
  matches `^(\d{3})_([a-z0-9_]+)\.sql$`, sorts by version and **requires contiguity from
  001**, so `021_…` had to be exactly 021. `factory/pyproject.toml` ships
  `resources/*.sql` by glob, so no packaging edit was needed.
- `plan_migrations()` returns `available[len(applied):]` — an already-applied resource is
  **never re-run**, which is why a new resource is the only viable carrier.
- Before that, it compares recorded `(version, name, sha256)` for the whole applied prefix
  and raises `MigrationError("migration drift at version N")`. So editing 018 in place
  would break **every existing database**, not just new ones. 018 is byte-untouched here;
  `git diff` shows no hunk in `resources/`.
- `apply()` runs all pending resources in one transaction under
  `pg_advisory_xact_lock`, with `SET LOCAL lock_timeout='5s'; SET LOCAL statement_timeout='5s'`.
  021 is a `CREATE OR REPLACE FUNCTION` plus `REVOKE`/`GRANT` on the same signature — no
  data touch, no index work, comfortably inside 5 s.
- Capability readiness is dynamic: `store.py:1309`, `admin.py:328` and `server.py:39`
  compare against `len(discover_migrations())`, which is what made several test stubs
  hardcoding `20` fail (see §8).
- Signature deliberately unchanged (`char,text` → `jsonb`), so the `pg_proc` privilege
  matrix assertion at `test_postgres_integration.py:6690` and 018's `REVOKE`/`GRANT` stay
  valid; `CREATE OR REPLACE` preserves grants and `pg_proc` cardinality.

Live confirmation on a cluster that already had 001–020 applied, read from `schema_migrations`:

```
21|021_semantic_repair_child_rejection_reasons.sql
20|020_execution_v2_priced_usage.sql
19|019_usage_token_components.sql
```

No drift error. **Strength of this evidence, stated exactly:** the run above is a
non-shipped scratch probe, so the `001–020 → 021` *prefix-digest* upgrade path is confirmed
by observation, not by a test in the delivered tree. Shipped DB tests exercise older base
versions (v8/v12/v14/v16) and the disposable-exit harness applies 021 into its own fresh
cluster, which is a full apply rather than an incremental one. Filed as #166 so the gap is
tracked instead of being remembered as stronger than it is.

## 7. Deterministic fixture

Two changes in `semantic_repair_fixture`, keeping every assertion intact:

1. The intake clock is now **one server-clock reading** (`SELECT now()`), injectable via
   the new `intake_now=` parameter, instead of a client `datetime.now()`. This removes the
   client↔server clock class error entirely rather than outwaiting it.
2. `CHILD_DEADLINE_SAFETY_SECONDS = 120` is subtracted from the inherited wall budget.
   Every remaining fixture round trip is capped by the store's 5 s `lock_timeout`/
   `statement_timeout`, so 120 s cannot be crossed mid-test, while a parent horizon of
   14 400 s still leaves hours of child budget.

No timeout was widened and the digest/index assertions are unchanged: the same test still
fails if a rejection reason is wrong, because the superseded-child case now asserts
`child_task_unavailable` instead of the old `assertIsNone`, and the limit/deadline cases
assert their specific reason rather than the substring `binding rejected`.

## 8. Files changed

| file | +  | −  | what |
|---|---|---|---|
| `resources/021_semantic_repair_child_rejection_reasons.sql` | 227 | — | new resource (untracked) |
| `factory/src/adaptive_factory/semantic_repair.py` | 37 | 0 | allowlist + `repair_child_rejection_reason()` |
| `factory/src/adaptive_factory/store.py` | 17 | 1 | map rejection before `from_dict`; malformed keeps its own message |
| `factory/tests/test_migrations.py` | 242 | 3 | 20→21 counts; five offline tests: envelope strictness, vocabulary equality, channel disjointness, NULL-vs-malformed diagnosis, guard-structure pins |
| `factory/tests/test_postgres_integration.py` | 129 | 20 | clock seam, safety margin, typed reasons, applied-list counts, **plus the request-time authority stamp and the `stale_m0` refusal assertion of §13** |
| `factory/tests/test_execution_persistence_postgres.py` | 18 | 10 | applied-list/`max(version)`/fresh-cluster counts, dynamic counts |
| `factory/tests/test_server.py` | 11 | 5 | readiness stub `schema_version` now `len(discover_migrations())` |
| `factory/tests/postgres_restart_probe.py` | 4 | 3 | harness readiness pin and applied-version range now derived |

Tracked total: **458 additions, 42 deletions** (`git diff --numstat`, plus the 227-line new resource).

`git diff --numstat -- factory/tests/` = **404 additions, 41 deletions**. The brief
expected "additions only"; that is not accurate — the 40 deletions are the replaced lines
(hardcoded `20` counts and applied-migration lists, the bare `assertIsNone`, three
`"binding rejected"` regexes, the duplicated `import psycopg`, the client-clock line, and
the two import-clock authority stamps replaced in §13).

Several of those count edits were not optional. Capability readiness is computed as
`len(discover_migrations())` in `store.py:1309`, `admin.py:328` and `server.py:39`, so
appending resource 021 invalidated every test that hardcoded `20` — including
`postgres_restart_probe.py:319`, which is part of the mandatory harness itself. All of
them are now derived from `discover_migrations()` where the number was only ever meant to
mean "current", and pinned to 21 where the test is specifically about a fixed prefix.

No file under `factory/contracts/`, `schemas/` or `architecture/` was edited
(`git status --porcelain` and `git diff --numstat` on those paths both return zero), no
`.grok-stack/**` file was touched, no compatibility policy was touched, no `VERSION`
bump, no commits.

## 9. Verification

- `python3 -m unittest -q tests.test_architecture_fitness tests.test_structure` → `Ran 144 tests OK`.
- `ruff check` over `factory/src/adaptive_factory/ factory/tests/ tests/` → 6 findings, all
  pre-existing `F401`. Baseline was measured by stashing the change: **no new findings**.
  Note `factory/src/adaptive_grok*` from the brief's command does not exist in this tree,
  so that glob contributes only `E902 No such file or directory`.
- `git diff --check` → clean.
- All 54 Docker-free factory modules → `Ran 629 tests`, only
  `test_landing_api.…published_package_are_frozen` fails, and it fails identically on the
  stashed baseline (pre-existing, unrelated).
- `test_migrations.py` is Docker-free and covers §5/§6 offline, including the
  guard-conditions-verbatim comparison and the SQL↔Python allowlist equality.
- Postgres runs: see §10.

## 10. Mandatory disposable-exit runs

Protocol: sequential runs of `python3 -u factory/tests/run_disposable_exit.py`, success
criterion = **4 consecutive passes**, up to 7 attempts. Every attempt is kept, including
durations and host load. Driver: `.qwen/tmp/p155_streak.sh` (scratch, not shipped); raw log:
`.qwen/tmp/p155_streak.log` (592 KB, not shipped — the numbers below are read out of it).

PostgreSQL 17.11 in `postgres:17-alpine`, disposable container per run; 776 tests per tier;
`taskset -c 0-27` (the harness inherits a 22-CPU affinity mask from the CLI process, and
`decisions.md` records that all 28 CPUs are available to explicitly configured children).

| # | window (UTC) | rc | wall | tier time | load before → after | verdict |
|---|---|---|---|---|---|---|
| 1 | 03:08:53 → 03:14:51 | 0 | 358 s | `Ran 776 tests in 341.506s` | 1.94 → 2.33 | `PASS: disposable PostgreSQL + API + effective roles + actual restart/reconciliation` |
| 2 | 03:14:51 → 03:20:50 | 0 | 359 s | `Ran 776 tests in 341.882s` | 2.33 → 2.27 | `PASS: …actual restart/reconciliation` |
| 3 | 03:20:50 → 03:26:50 | 0 | 360 s | `Ran 776 tests in 343.610s` | 2.27 → 2.78 | `PASS: …actual restart/reconciliation` |
| 4 | 03:26:50 → 03:32:55 | 0 | 365 s | `Ran 776 tests in 347.760s` | 2.78 → 2.87 | `PASS: …actual restart/reconciliation` |

```
TARGET_MET: 4 CONSECUTIVE PASSES after 4 attempts
STREAK end=2026-09-20T03:32:55Z product_fingerprint=8883279fa1bf6795 best_consecutive=4 attempts_used=4
```

Two things the streak proves beyond "green":

1. **One tree — with a caveat that matters.** `8883279fa1bf6795` at streak start and at
   streak end, from `git rev-parse HEAD` + `git status --porcelain` over `factory tests
   scripts trust-ci architecture engineering/contracts`. That value hashes the *list and
   status* of paths, **not their bytes**: it proves nothing was added, removed or staged
   mid-streak, and it would not notice a content edit inside an already-modified file. The
   code reviewer caught exactly this — the same value appears across streaks even though
   `test_migrations.py` changed between them (mtime `03:56:13`). Streak 2 is therefore
   pinned by a content fingerprint instead (§14). Package Markdown written during a streak is
   outside the product set by construction — deliberate, and disclosed rather than hidden.
2. **Past the window.** Each tier ran 341-348 s, i.e. every pass was obtained *after* the
   300 s authority window that made a run of this length red before §13's fix. The passes
   are therefore evidence for AC-004 in the tier itself, not only in the probe.

Not recorded as evidence, and explicitly disclaimed: no attempt in this streak failed, so
this table carries no failure-reproduction value. The failure reproductions are §3 (delay
injection, before/after) and §13 (aged fixture clock, before/after), both run as single
tests with a control that flips.

## 11. What I could not verify / remaining risk

1. **The original 1-in-3 stochastic flake was never observed live on this host.** The
   reproduction is a controlled equivalent (an injected delay in the proven window, with a
   control that flips). That is stronger than waiting for the race, but it is not the same
   observation.
2. **`semantic_plan_repair` keeps the identical anonymous-NULL defect → filed as #163.**
   `store.py:692-694` maps any unreadable response — including a guard's SQL `NULL` — to
   `StoreError("stored semantic repair result is corrupt")`: a precondition refusal is
   reported as corruption of stored data. Measured scope on this tree: the function spans
   `018:1527-2044` and holds **13 `RETURN NULL` statements plus 2 `ELSE NULL` arms = 15
   anonymous paths**, against the 9 fixed here. Out of #155's stated boundary, so it is
   deliberately not folded in; #163 carries the same remedy shape.
3. **A second, independent load coupling in the same mandatory tier — found, measured,
   filed as #164, and fixed in this branch (see §13).** `contracts.py:150-152` refuses an
   m0 authority whose age exceeds 300 s (`stale_m0`), while
   `test_postgres_integration.py:53` fixed `NOW` at module import and `payload()` stamped
   `observed_at = NOW`. Any HTTP-path test therefore expired once the *tier* had been
   running longer than 300 s before reaching it. Measured boundary, with the control that
   must flip:

   ```
   authority age    0s -> accepted
   authority age  299s -> accepted
   authority age  301s -> rejected: stale_m0
   authority age  418s -> rejected: stale_m0
   ```

   This is what failed
   `test_http_intake_deduplicates_fresh_proof_and_conflicts_on_command_reuse`
   (`422 != 201` at line 1882) in the attempts whose tier ran 418–479 s, and it is also
   what turned the first streak attempt of this continuation red. Nothing in the fix
   touches `contracts.py` or the 300 s window; it is fixture-only, and it stayed in scope
   because the declared success criterion (four consecutive tier passes) was otherwise
   unreachable on this host. The earlier judgement in this file — "a fixture-wide change
   well outside #155's scope, deliberately NOT fixed" — was wrong on the second half and
   is superseded by §13.
4. Guard-condition equivalence is argued structurally (same clauses, re-grouped `OR`,
   enforced by a text-equality test) and exercised by the existing scenario tests; it is
   not proven by an exhaustive truth table over the 48 clauses.

## 12. Recommended reviewer attack order

1. **The 48-clause partition in 021.** Verify that regrouping `OR` into four `IF` blocks
   cannot change accept/reject. The argument is that `A OR B` is TRUE iff some operand is
   TRUE, and NULL operands never make a group TRUE on their own, so the re-grouped union
   rejects exactly the same rows; `test_migrations.py` enforces clause-level text
   equality, but only a reviewer can judge whether re-ordering changes *which* reason a
   multi-violation row reports (accepted: first matching guard wins).
2. **Whether `store_write_rejected` is too coarse.** The EXCEPTION arm still collapses six
   constraint classes into one reason, as it did into one NULL before.
3. **The 120 s safety margin.** Is it the right bound, given each fixture round trip is
   capped at 5 s? A reviewer should challenge the arithmetic, not the constant.
4. **The two siblings and the tier's own clock class.** `semantic_plan_repair`'s identical
   anonymous-NULL defect is #163 (deliberately not fixed here). The `stale_m0` import-clock
   coupling is #164 and **is** fixed here (§13) — a reviewer should challenge that
   judgement, since it goes beyond the issue text as filed: the argument is that a success
   criterion nobody can pass is not a scope boundary but a blocker, and the fix is
   fixture-only with the guard itself re-asserted.
5. **The new harness dependency on `discover_migrations()`** in
   `postgres_restart_probe.py`, which makes the mandatory evidence itself depend on the
   resource count rather than pinning it.
6. **Whether four consecutive identical tier runs are the right criterion at all.** Both
   clock couplings are now removed by construction and pinned by controls that flip in
   ~1.2 s (§3, §13), so ~25 minutes of repeated full-tier execution may be buying
   nothing; that trade-off belongs to the reviewer, not to the implementer's convenience.

## 13. Continuation addendum (2026-09-20, later that night): the tier's own clock coupling, measured and fixed

The session that wrote §11.3 died before the evidence streak finished: its **attempt 1
(02:27:29Z–02:34:36Z, `Ran 776 tests in 418.887s`)** came back red, and its attempt 2 was
killed mid-run at ~02:43Z with the log ending inside
`test_recovery_raw_page_caps_at_100_then_empty_page_wraps`. The takeover therefore starts
from that red attempt rather than from the claim.

**The crashed session's attempt 1 — before any new code — the only failure is the one §11.3
predicted, and it is not a #155 failure:**

```
FAIL: test_http_intake_deduplicates_fresh_proof_and_conflicts_on_command_reuse
  File ".../factory/tests/test_postgres_integration.py", line 1882, in test_http_...
    self.assertEqual(accepted.status_code, 201)
AssertionError: 422 != 201
```

**Mechanism.** `test_postgres_integration.NOW` is captured once at module import;
`payload()` stamps every `m0_authority.observed_at` from it; `api.py` routes validate with
`datetime.now(timezone.utc)` per request; `contracts.py:150-152` refuses an outside-age of
`0..300` s. Service-path tests are immune because they hand the same `NOW` to
`service.intake(..., now=NOW)` — age 0 by construction. Only the HTTP comparison straddles
two clocks. The tier has ~776 tests and no HTTP intake test can be reached before ~300 s
have elapsed, which makes the failure deterministic, not flaky: the harness grew from the
201 tests / 173 s recorded in the issue body to 776 tests / 341–419 s.

**Control, run as a single test in ~1.2 s instead of waiting through a 7-minute tier.** The
probe ages `tpi.NOW` by exactly the amount a long tier would, before instantiating the
test; the control that must flip is the aged arm:

| arm | fixture clock aged by | before the fix | after the fix |
|---|---|---|---|
| control A | 0 s | `Ran 1 test in 1.881s OK` | `Ran 1 test in 1.187s OK` |
| control B | 400 s | `FAILED (failures=1)` — `AssertionError: 422 != 201` | `Ran 1 test in 1.193s OK` |

**What changed (fixture only).** `payload()` accepts an explicit `authority_at`;
`record_authority()` persists the matching `m0_authority_observations` row; the HTTP test
takes one `proof_at = datetime.now(timezone.utc).replace(microsecond=0)` reading and derives
every proof in the test from it (`refreshed_at = proof_at - 2 s`), following the precedent
already in `test_api.py:286`. ~200 service-path `now=NOW` call sites are untouched — they
were never wrong, they pass the same clock twice.

**What did not change, and how that is now pinned.** No timeout, no window, no harness
protocol, nothing under `contracts.py`. The same test additionally POSTs a proof stamped
400 s in the past and asserts the exact refusal:

```python
(422, {"error": "invalid", "code": "stale_m0", "detail": "contract validation failed"})
```

so the guard is asserted rather than assumed, and the fixture change cannot rot into a route
around it. Filed as #164 with the boundary measurements; the residual that `create_app()`
has no clock seam is recorded there too.

**Corollary for the streak below:** attempts 1–4 each ran the tier in 341.5–347.8 s — i.e. every
pass in §10 was obtained *past* the 300 s window that used to make such a run red, which is
the direct evidence that AC-004 holds in the tier and not only in the probe.

## 14. Review wave, its fixes, and the second streak on the fixed tree

Four route reviews ran against the §10 tree: `security-review.md`, `code-review.md`,
`test-review.md`, `data-review.md`. All four returned `VERDICT: pass`, and all four produced
defects worth fixing in the delivered tree — a pass verdict is not an absence of findings.

**Fixed in product/test code (tree T2, streak 2 below):**

| finding | fix | proof |
| --- | --- | --- |
| §1 arithmetic wrong: the block is **49 disjuncts joined by 48 `OR`**, the lineage group is **32** not 30, `command_input_invalid` is **5** not 3 | corrected here, in `tasks.md`, `requirements.md`, `architecture.md` and `change-spec.yaml` (FORBID-003), grepped tree-wide so no echo survives | per-block re-count in §1 |
| 9 of 12 reason↔guard pairings had no assertion, and `_guard_lines` drops every `THEN RETURN …` line, so it cannot see a group boundary at all | `test_repair_child_guard_structure_maps_each_reason_to_one_clause_group`: per-reason clause counts (5/8/2/1/3/2/32/2/2/13), per-reason literal uniqueness, replay-`CASE` arm order, frozen sha256 of the superseded `018` body | mutation battery in scratch copies under `~/.cache` (`engineering/` included, `.git` excluded) |
| `store.py` reported `payload is malformed` for **any** unparseable response, including the bare NULL a pre-`021` cluster returns — the same false shape claim #155 exists to remove | NULL now diagnosed as `store_returned_null`, deliberately kept out of the twelve-code SQL vocabulary; `malformed` reserved for a real document | `test_bind_repair_child_separates_an_unexplained_store_refusal` (offline, mocked `_connect`, both arms) |
| `authority_not_fresh` — the guard the original flake was about — had no shipped assertion, and the `intake_now=` seam was unused in delivered tests | new tier block asserting that exact reason for a 400 s-old child authority | live single-test run on PostgreSQL 17.11: `Ran 1 test in 26.974s OK` |

Mutation results after the fixes (`python3 -m unittest -q factory.tests.test_migrations`):

| arm | mutation | result |
| --- | --- | --- |
| base | none | `Ran 24 tests OK` |
| mut1 | replay `CASE` arms inverted (the bind would hand back NULL as a binding) | `FAIL: …maps_each_reason_to_one_clause_group` |
| mut2 | guard-group boundary deleted (two named groups merge) | `FAIL: …maps_each_reason_to_one_clause_group` |
| mut3 | one lineage clause removed from `018` **and** `021` together (accept/reject really changes) | `FAIL: …maps_each_reason_to_one_clause_group` |

These are precisely the arms `test-review` and `data-review` reported as caught by nothing on
the pre-review tree. Two of my own first attempts at this fix were wrong and were caught by
running them rather than by writing them down: a `THEN RETURN jsonb_build_object(` coverage
count that failed on the *clean* tree (the `CASE` and `EXCEPTION` arms are not that shape), and
a self-referential `sum(expected_clauses.values()) == 70` that would have held for any
implementation. Both are gone; `measured == expected_clauses` already pins a missed block.

**Streak 2 — the mandatory tier on the post-review tree T2.** Same protocol, separate log
(`.qwen/tmp/p155_streak2.log`; 4 attempts, target 4 consecutive), with the product content
fingerprint `sha256(git diff -- factory tests + untracked factory files)` =
**`4bb744dce1eb2d49` at streak start and at streak end** — the property §10's list-based hash
could not actually measure:

| # | window (UTC) | rc | wall | tier | load before → after |
|---|---|---|---|---|---|
| 1 | 04:31:14 → 04:37:11 | 0 | 357 s | `Ran 779 tests in 339.567s` | 3.12 → 5.75 |
| 2 | 04:37:11 → 04:43:08 | 0 | 357 s | `Ran 779 tests in 340.190s` | 5.75 → 4.64 |
| 3 | 04:43:08 → 04:49:11 | 0 | 363 s | `Ran 779 tests in 345.966s` | 4.64 → 3.60 |
| 4 | 04:49:11 → 04:55:10 | 0 | 359 s | `Ran 779 tests in 342.038s` | 3.60 → 2.55 |

```
TARGET_MET: 4 CONSECUTIVE PASSES after 4 attempts
```

779 tests where §10 had 776: the three new offline cases are inside the tier. Every attempt
again ran past the 300 s window, and no attempt failed.

**After streak 2 (tree T3): test- and doc-only refinements from `code-review-delta.md`.** The
delta review of these fixes returned `pass` and asked for three more things, all applied: the
mock test now pins the `malformed` arm as well as the NULL arm, so the diagnosis the NULL fix
must not absorb is itself tested; the self-referential sum line is gone; the digest comment
states its byte-sensitivity as deliberate. Wording corrected in `architecture.md` (the
caller-visible message is `…payload is malformed`, `invalid_object`/`unknown_fields` are the
nested codes, and "the old path" no longer covers NULL) and in `release.md` (SIG-001 must not
promise "one of the twelve reasons" on a pre-`021` cluster). Re-verified:
`Ran 24 tests OK`, `ruff check` clean, base green and all three mutation arms red.

T3 changes no production behaviour — one test file plus package prose — so it is re-certified
by the **authoritative gate's own** `factory-postgres-exit` tier run against the committed
tree; that pass, not a claimed four-streak, is what this record offers for T3. AC-005's four
consecutive passes exist on tree T2 (`4bb744dce1eb2d49`) and on the pre-review tree (§10), and
saying which tree each streak belongs to is the reason the fingerprint is recorded at all.

**Review findings deliberately not folded in**, each with an issue so the record is not
self-serving: #163 `semantic_plan_repair` (15 anonymous paths), #166 no shipped
`001–020 → 021` incremental upgrade test, #162 `data_review`/`bitrix_review` uncitable in a
typed spec, and `store_write_rejected` still collapsing six constraint classes into one reason.

