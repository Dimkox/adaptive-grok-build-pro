# Independent code review — `fix(verify): decide same-inode CAS tampering by content, not ctime granularity`

**Verdict: PASS.** No security property is weakened, product code is untouched, and both
serialized-CAS scenarios are green and deterministic. Findings below concern the *accuracy of the
change package prose*, not the code: the prose attributed the rejection of the original scenario to
the wrong CAS layer. All findings are addressed in this package before delivery.

Scope of what was reviewed: commit `f10741b` (amended to `ebd9a0a` at 21:48:42 during the review,
adding only `evidence/review-test.md`; `git diff --stat f10741b ebd9a0a` shows that single file, so
the conclusions apply to both identities).

## 1. Does the change weaken a fail-closed CAS property? — No

Product rejection sites, verified by reading `cas_write` and its helpers:

- `.grok-stack/adaptive_grok/workflow_artifacts.py:1410-1412` — `_cas_identity_at` returns the
  six-field tuple `(st_dev, st_ino, st_mode, st_size, st_mtime_ns, st_ctime_ns)`.
- `:1433-1436` — `_rename_exchange` compares the **full** tuple (ctime included, strict `!=`)
  against the expected target identity before the swap and raises
  `"CAS exchange target identity changed"`, `code="race"`.
- `:1646-1651` — `cas_write` compares the current on-disk digest with the caller's expected digest
  and raises `"CAS expected digest mismatch"`, `code="cas"`, before writing anything.
- `:1694-1742` — after the exchange, `_post_exchange_identity_matches` (`:1415-1419`, comparing the
  first five fields with `==` and ctime with `>=`) plus the displaced-digest re-read raise
  `"CAS target changed before atomic publication and was restored…"`.

Measured behavior of the original scenario on this host: the tamper is caught at `:1436` with
`code="race"` and the target keeps the competitor bytes. On a simulated coarse-ctime filesystem
(1 s quantization of `os.stat`/`os.fstat` ctime) the premise holds with equal ctimes, the pre-swap
guard does not fire, and the post-exchange displaced-digest layer still rejects; the tampered bytes
are never published. **Failing closed is preserved on both filesystem classes.**

## 2. Is the replacement precondition sound? — Yes

`inode`, `size` and `mtime` equality plus a content-digest difference state exactly what the
attacker restores and exactly what differs; content drift is the security premise of the scenario,
while a ctime advance is incidental (an unrelated `touch` also advances ctime without changing
anything the CAS must reject). `assertGreaterEqual(st_ctime_ns, …)` is the correct monotonic
statement: strict equality would be wrong on a fine-grained filesystem, strict inequality is wrong
on a coarse one.

## 3. Is the added test deterministic and does it have kill power? — Yes

`test_same_inode_content_change_is_rejected_when_identity_cannot_resolve_it` asserts the five
non-content identity fields equal **before** the rejection, so it cannot pass vacuously: the
competitor bytes differ from `old`, which is what makes the `code="cas"` assertion meaningful, and
nothing in it depends on timestamp resolution. Mutation probes:

- **M1** — remove the `:1650-1651` expected-digest comparison: the original scenario still raises
  `race` (so it does not kill M1), while the new test's code assertion flips from `cas` to `race`
  and **fails**. The new test is the only committed test that dies when the product stops trusting
  the content digest.
- **M2** — M1 plus `publication_valid = identities_valid`: the new test raises nothing and the
  attacker's bytes are published; on a coarse-ctime filesystem the original scenario also stops
  raising. Both **fail**.

## 4. Findings on package prose — 1 Important, 3 Minor (all fixed)

1. **Important** — `brief.md` ("Problem"), `evidence/ci-failure-traceback.md` ("Reading of the
   evidence") and `mistakes.md` (2026-09-15 entry) each stated that the expected-digest comparison
   carries the rejection of the original scenario. It does not: on this host the rejection happens
   at `:1436` with `code="race"` because the pre-swap guard compares ctime strictly; the digest
   layer (`code="cas"`) is what the *new* test pins. Fixed by describing both layers and stating
   which one fires under which filesystem.
2. **Minor** — `brief.md` said `_post_exchange_identity_matches` "already treats ctime as `>=`"
   without noting that `_rename_exchange` compares the same field with strict equality, which is
   the asymmetry that made the flake possible. Fixed.
3. **Minor** — `change-spec.yaml` `INV-002` cited `tests/test_structure.py` as evidence for
   "product code untouched"; a scope statement is better proven by the diff itself. Kept, and the
   scope check below is recorded as the actual evidence.
4. **Minor** — `requirements.md` AC-003 wording implied whole-suite determinism; the claim is
   bounded to the serialized-CAS scenarios. Fixed.

## 5. Scope discipline — clean

- `git show --stat f10741b` → 14 files: 12 under this change package, `mistakes.md`, and
  `tests/test_workflow_artifacts_adversarial.py`.
- `git diff --name-only 4383115 f10741b -- .grok-stack scripts architecture VERSION README.md CHANGELOG.md tests/test_structure.py` → empty: no product,
  hook, schema or identity file changed.

## 6. Residual risk

The layered design means a future edit could re-tighten an identity comparison on a field the host
cannot guarantee; `INV-001` plus the two pinned rejection codes are the guard. A follow-up worth
scheduling: a scenario where the attacker also restores `st_size` *and* the file is large enough to
be re-read after the exchange, exercising only the `:1694-1742` recovery path.

```text
python3 -m unittest tests.test_workflow_artifacts_adversarial   → Ran 25 tests, OK
python3 -m ruff check tests/test_workflow_artifacts_adversarial.py → all checks passed
```

---

*Provenance:* the reviewing agent completed this analysis and returned the verdict, but its process
crashed before writing the file. The text above is reconstructed from that agent's transcript
(43 tool uses, including the mutation probes and the coarse-ctime simulation quoted in §1 and §3);
each product-code and test citation and both measured outcomes were then re-verified independently
in this session — `code="race"` / "CAS exchange target identity changed" with the competitor bytes
retained is reproduced by a direct probe against `cas_write` using the test's own helpers.
