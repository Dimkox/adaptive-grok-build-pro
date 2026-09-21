VERDICT: pass
Base `9007895`; delta = working tree. Delta mtimes 04:27:33 `store.py`, 04:27:54 `test_migrations.py`, 04:29:21
`test_postgres_integration.py`, 04:32:46 docs — after `code-review.md` 04:21:40.
`python3 -m unittest -q factory.tests.test_migrations` → `Ran 24 tests in 0.052s OK`.
**1 — NULL vs malformed (`store.py:744-764`): PASS.** The envelope check (`:746`) precedes `try:` (`:752`), so the
reason channel cannot be masked; `:755-761` fires only when the decoded `response is None`, `:762-764` keeps
`malformed` for any non-null document. `from_dict(None)` → `ContractError`, a `ValueError` (`contracts.py:18`,
`semantic_contracts.py:33-36`), so the arm is reachable (`python3 -c` probe: `None ContractError caught(TV)= True
rejection= None`). SQL NULL → `store_returned_null`; jsonb `'null'` document → `store_returned_null` (psycopg3
decodes both to `None`; the name states what the client got — no shape claim); text `'null'` →
`store_returned_null` (decoded at `:744-745` first); bad non-null document → `malformed`. Comment premise holds:
`021` has no `RETURN NULL` left (`grep -c` → 0; the replay `CASE` at `021:97-98` can only return a non-null
`v_existing.body`), pinned by `test_migrations.py:445`.
**2 — vocabulary: PASS, no overclaim.** `store_returned_null` is Python-only: absent from `REPAIR_CHILD_REJECTIONS`
(13 = 12 SQL + `binding_rejected`) and from `021` (per-reason grep = 1 × 12). The pinned assertion subtracts the
fold code — `emitted == set(REPAIR_CHILD_REJECTIONS) - {UNKNOWN_REPAIR_CHILD_REJECTION}`, `len(emitted)==12`
(`test_migrations.py:472-476`) — so it never calls NULL a SQL reason. Wording to fix: `architecture.md:18`
"Anything else keeps the old path, so a malformed payload still produces `invalid_object`" — the caller-visible
text is `…payload is malformed` (`store.py:763`), `invalid_object` is only the nested code for non-Mapping input,
and "the old path" no longer covers NULL; and `release.md:19` "every `bind_repair_child` rejection names one of the
twelve reasons" (mtime 03:17, pre-delta) — false on a pre-`021` cluster, which names a 13th. `requirements.md:21` is correct.
**3 — the two new offline tests: PASS, one vacuous line.** `test_migrations.py:524-547` asserts the exact NULL
message plus `assertNotIn("malformed", …)`; deleting the arm turns it red. `:549-602` is non-tautological:
independent recompute gives 5/8/2/1/3/2/32/2/2/13 (sum 70), dropping one lineage clause moves 32→31, relabelling a
group produces a `zzz` key plus a missing `deadline_exceeded` so `:578` fails loudly, and a `CASE` arm swap breaks
`:587-591` (all verified by in-memory string mutation). Only `:579`
(`assertEqual(sum(expected_clauses.values()), 70)`) is self-referential — true for any implementation. The digest is
byte-exact: one added space in `018` flips `49400d2f…`→`9e808aca…`, but that is a *correct* failure (`018` is
shipped, so any byte change is `plan_migrations` checksum drift, `migrations.py:77`; `PRE_RECOVERY_MIGRATIONS` pins
only v1–16, making this the sole offline pin for `018`'s bind body). Intent documented at `:593-595`; byte-sensitivity is not — one clause would help.
**4 — `authority_not_fresh` tier block: PASS, not vacuous.** `test_postgres_integration.py:6459-6473`, inside
`…exact_replay_safe_and_role_isolated` (`:5685`). Early refusal is impossible: `M0AuthorityV1.from_dict` measures
age against the *same* injected clock (`contracts.py:149-152` → age 0) and `factory.m0_observation_valid`
(`009:39-44`) checks existence/`check_name` only. So only the bind can refuse: `tasks.accepted_at` is
`DEFAULT now()` (`001:31`; the intake INSERT at `store.py:2273-2280` omits the column) vs the 400 s-old
`observed_at` at `021:176-180`. With `intake_only=True` the fixture returns at `:5469` before any bind and `:5430`
guards the clock math, so an intake-side refusal escapes the fixture call → unittest ERROR; a non-firing guard
makes `assertRaisesRegex` fail with "StoreError not raised". Live 600 s confirmation: `evidence/postgres-evidence.md:127-131`.
The 400 s arm is static-only — a tier is already running in this worktree, so I did not re-run it.
**Defects: none introduced by the delta.** Residuals: (a) suggestion — `store.py:762-764` is still the only changed
message with zero test references (`grep -rn "payload is malformed" --include=*.py .`), so the arm the NULL fix must
not absorb stays unpinned (one extra `fetchone` arm at `:524` closes it); (b) doc — the two quoted lines in item 2;
(c) pre-existing, not delta — a non-JSON *text* response raises `json.JSONDecodeError` at `store.py:744-745` outside
`StoreError` wrapping, identical at base (`git show 9007895:factory/src/adaptive_factory/store.py`, lines 743-744)
and unreachable while the function is `RETURNS jsonb` (`021:32`).
