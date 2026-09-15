# Independent test review — `f10741b` (branch `fix/ctime-granularity-adversarial-test`, base `4383115`)

## VERDICT: **PASS**

The edited scenario still verifies the security property it is named for, the added test is
deterministic on both fine- and coarse-ctime filesystems, and it is the only committed test that
dies when the product stops trusting the content digest. Nothing was skipped, nothing was turned
from a rejection into an acceptance, and product code is untouched (`git show --name-only f10741b`
lists 0 paths under `.grok-stack/`; the only non-paperwork files are
`tests/test_workflow_artifacts_adversarial.py` and `mistakes.md`). Findings 4–5 are polish
suggestions, none blocking.

Scope reviewed: `tests/test_workflow_artifacts_adversarial.py:677-755` (edited test + new test),
helpers `:522-543`, neighbouring committed scenario `:757-791`, and the driven product API
`.grok-stack/adaptive_grok/workflow_artifacts.py:1410-1436` (`_cas_identity_at`,
`_post_exchange_identity_matches`, `_rename_exchange`), `:1528-1751` (`cas_write`),
`WorkflowArtifactError.code` at `:157-160`.

---

## 1. Coverage — the named property is preserved; what the removed assertion really added (Info, no loss)

Removed (base `tests/test_workflow_artifacts_adversarial.py:701`):

```python
self.assertNotEqual(target.stat().st_ctime_ns, original.st_ctime_ns)
```

That line was a **premise** assertion about the *test's own* tamper, evaluated on
`target.stat()` — it never observed a product decision, so its removal cannot weaken any
product guarantee. What it did supply was an *indirect* witness that the in-place write was
observable to `_rename_exchange`, whose target check at
`workflow_artifacts.py:1435-1436` compares the **full** identity tuple *including* `st_ctime_ns`
(`_cas_identity_at`, `:1410-1413`).

It is replaced by a **direct** and strictly stronger premise
(`tests/test_workflow_artifacts_adversarial.py:707-710`):

```python
self.assertNotEqual(hashlib.sha256(target.read_bytes()).hexdigest(),
                    hashlib.sha256(old).hexdigest())
```

Content drift *is* the security premise of the scenario; a ctime advance is not (an unrelated
`touch` also advances ctime while changing nothing the CAS must reject). The restored-field
equalities that the product actually promises to detect — `st_ino` `:699`, `st_size` `:700`,
`st_mtime_ns` `:701` — are all kept, and the four repeated `target.stat()` calls are now one
cached snapshot (`:698`), which removes the possibility of two assertions observing different
stats.

**What is genuinely lost:** the edited test no longer tells a reader *which* defense fired, and
that branch is host-dependent (measured, §2). On ext4 the rejection comes from the pre-syscall
target-identity guard; on a coarse-ctime filesystem the exchange actually proceeds and the
rejection comes from the post-exchange displaced digest (`:1703`) plus rollback
(`workflow_artifacts.py:1706-1745`). Both are fail-closed outcomes with `code="race"`, and the
final assertion `self.assertEqual(target.read_bytes(), bytes(competitor))` (`:722`) still proves
the tampered bytes survived the attempt. `INV-001` (no rejection became an acceptance) holds;
`FORBID-001` holds (no product check changed); `FORBID-002` holds (no skip/expectedFailure — the
file contains none, `grep -n "skip\|expectedFailure"` → 0 hits).

## 2. Determinism — passes on both a ctime-advancing and a ctime-blind filesystem (verified)

Reasoning over each assertion, not assumption:

*Edited test (`:677-722`).* `st_ino`: in-place `open("r+b")` write cannot reallocate the inode
(`:693-696`). `st_size`: the byte flip is length-preserving (measured: `old` is 266 bytes,
`competitor` 266 bytes). `st_mtime_ns`: `os.utime` is re-set to `original.st_mtime_ns` (`:697`),
and that value is by construction representable on the hosting FS, so it round-trips.
`assertGreaterEqual(st_ctime_ns …)` (`:706`): ctime is monotonic against the FS's own granularity
— either equal (coarse) or greater (fine). Content digest differs: always. So the test's own
assertions hold under both granularities; the product then rejects on both paths, and both paths
end with the competitor bytes on disk (on the fine path because the guard fires *before*
`renameat2`, on the coarse path because the rollback restores them).

New test (`:724-755`): reaches neither ctime-sensitive comparison at all — `cas_write` reads
`current` via `digest_target` *after* the tamper and fails at
`workflow_artifacts.py:1650-1651`, before the stage file or the exchange exist. Filesystem-
independent by construction.

Empirical confirmation (in-process emulation, no repository file touched): patched
`os.stat`/`os.fstat`/`os.lstat` to round `st_ctime_ns` down to a 1 s tick, i.e. exactly the
runner condition `1789503…670 == 1789503…670` from
`evidence/ci-failure-traceback.md`:

```text
[native ext4]  ...with_restored_mtime_is_rejected            ok=True codes=[('race','CAS exchange target identity changed')]
[native ext4]  ...when_identity_cannot_resolve_it            ok=True codes=[('cas','CAS expected digest mismatch')]
[native ext4]  test_syscall_gap_..._by_displaced_digest       ok=True codes=[('race','CAS target changed before atomic publication and was restore')]
[coarse-ctime] ...with_restored_mtime_is_rejected            ok=True codes=[('race','CAS target changed before atomic publication and was restored; recover')]
[coarse-ctime] ...when_identity_cannot_resolve_it            ok=True codes=[('cas','CAS expected digest mismatch')]
```

Whole module, both hosts: `Ran 25 tests … OK` (native, 0.455 s) and `Ran 25 FAIL 0 ERR 0` under
the 1 s emulation. `python3 -m unittest tests.test_workflow_artifacts_adversarial.SerializedCasTests -v`
→ `Ran 9 tests in 0.065s / OK`. The reported `root-unittest` failure mode is eliminated.

Residual host assumption that remains (pre-existing, not introduced): `:739-742` asserts
`st_dev/st_ino/st_mode` equality, so a filesystem that does not keep a stable inode or reports a
stable mode across an in-place write (some FUSE/9p/NFS configurations for `TMPDIR`) hard-fails the
precondition instead of skipping it. Failing is the right disposition for a test whose premise is
"same inode", but see §6.

## 3. Mutation sensitivity of the new test — YES, it fails (verified, and the sibling does not)

Executed in-memory mutants of `workflow_artifacts.py` against the real test module (`T.ARTIFACTS`
swapped, no file written):

| Mutant | new test `…when_identity_cannot_resolve_it` | edited sibling `…restored_mtime_is_rejected` |
|---|---|---|
| M1 — drop `if current != expected_digest` (`:1650-1651`), i.e. trust identity fields | **FAIL** `AssertionError: 'race' != 'cas'` | PASS (survives) |
| M2 — M1 **and** `publication_valid = identities_valid` (`:1703`) | **FAIL** `WorkflowArtifactError not raised` | PASS (survives) |

So the exact mutation asked about is caught, and it is caught *specifically* by
`self.assertEqual(raised.exception.code, "cas")` (`:754`) — under M1 the product still raises a
`WorkflowArtifactError` (the post-exchange displaced digest fires and rolls back), so the bare
`assertRaises` at `:746` and the byte check at `:755` both still pass; only the pinned code
discriminates. `test_concurrent_cooperating_writers_serialize_one_winner` also dies under M1/M2
(`sorted(outcomes)` becomes `['pass','pass']`), so the digest authority is covered twice over.
Note the converse is also true and was measured: making `_post_exchange_identity_matches` require
`==` on ctime instead of `>=` is killed by 2 tests, so the `>=` semantics is protected.

## 4. Anti-pattern review (Minor)

- **No skipped / expected-failure tests.** `FORBID-002` respected; the unsupported assumption was
  removed instead of the scenario.
- **`assertRaises` strength.** The new test pins the outcome (`:746` `as raised` + `:754`), which is
  *better* than the file's prevailing bare form. The edited sibling keeps the bare form at `:714` —
  unchanged by this commit, and now the only one of the two without a code pin (see §6).
- **`code == "cas"` is not perfectly unique.** Five raise sites share `code="cas"`:
  `workflow_artifacts.py:1496`, `:1530`, `:1555`, `:1581`, `:1651`. With these inputs the first four
  are unreachable (digest is 64 lowercase hex; `self._graph("ours")` is a valid canonical task
  graph; the target is a 266-byte regular file; the lock is created by the product), but a one-line
  `self.assertIn("expected digest", str(raised.exception))` would make the pin name the exact
  defense rather than the code family. Minor.
- **The copied `competitor[-2]` trick cannot mask a no-op tamper.** Measured for this payload:
  `canonical_json` emits `…old"}\n`, so `[-2]` is always `}` → replaced by a space; length is
  preserved (266 → 266, which is what makes the `st_size` equality at `:740` meaningful), the digest
  differs, and the result is no longer parseable JSON. The `if … != ord(" ")` guard makes a space at
  `[-2]` flip to `x`, so no branch of the ternary can be identity. Duplication is now across three
  tests (`:685`, `:732`, `:764`) — a shared helper would be the tidy form, but the copies are
  literal and each is checked.
- **Vacuity check of the new test's ordering — it cannot pass vacuously.** `:739-742` (identity
  equality) does *not* by itself prove content drift: with a no-op tamper all five fields are equal
  too. The proof is the combination `assertRaises` (`:746`) + `code == "cas"` (`:754`) + the fact
  that the expected digest argument is literally `sha256(old)`: if `competitor` equalled `old`,
  `cas_write` would find the digest matching and *succeed* (the identical `_graph("ours")` payload
  is committed to succeed at `:826-831`), so both `:746` and `:755` fail loudly. The rejection therefore cannot be reached
  without real content drift — the premise is enforced post-hoc rather than asserted up front.
  Adding `self.assertNotEqual(target.read_bytes(), old)` next to `:739` would state the premise in
  the same place it is used, mirroring `:707-710`. Minor.
- **Near-vacuous assertions (both kept deliberately, flagged for honesty).** `:755`
  `assertEqual(target.read_bytes(), bytes(competitor))` — nothing has touched the target by then, so
  it can only fail if the product writes before verifying the digest (a legitimate tripwire, keep).
  `:706` `assertGreaterEqual(tampered.st_ctime_ns, original.st_ctime_ns)` — true for every real
  filesystem; it can only fail if the wall clock steps backwards mid-test, so it is a (small) new
  flakiness vector for zero discriminating power. Dropping it, as the new test does, is cleaner.
  Minor.

## 5. Style / conventions (Minor)

`python3 -m ruff check tests/test_workflow_artifacts_adversarial.py` → `All checks passed!`
(`ruff.toml`: `line-length = 120`, `select = ["E4","E7","E9","F"]`; the longest new lines, `:740-741`,
are 109 chars, so they are also inside the repo's informal width budget). No unused imports: nothing
was removed from the import block and `os`/`hashlib`/`tempfile`/`Path`/`patch` are all still used
(F401/F811 clean). Naming, `-> None` annotation, `with tempfile.TemporaryDirectory() as tmp:`
scaffold, `self._workflow` / `self._graph` helper use, and comment style match the surrounding
`SerializedCasTests` body; the new test needs no `patch.object`, consistent with the other direct
`cas_write` cases (`:582`, `:826`). Test order within the class keeps the two same-inode scenarios
adjacent, which reads well.

Naming nit: `…when_identity_cannot_resolve_it` is precise only for the five fields the test pins.
On this host `st_ctime` *does* advance, and in this code path nothing compares identity at all —
`cas_write` decides on the digest (`workflow_artifacts.py:1650`) before any identity tuple is used
for a decision. `…rejected_by_expected_digest_before_exchange` (or adding one line asserting the
digest is what rejects) removes the ambiguity with `test_syscall_gap_content_change_is_rejected_by_displaced_digest`,
which is the file's existing name for "the digest carried it". Minor.

## 6. Residual risk to tell the maintainer, and follow-ups

1. **Host-dependent branch inside the edited test (low, already backstopped).** After this change,
   the coarse-ctime branch of `…with_restored_mtime_is_rejected` (exchange proceeds → displaced
   digest → rollback) only runs on coarse hosts. It is not untested: the committed
   `test_syscall_gap_content_change_is_rejected_by_displaced_digest` (`:757-791`) forces exactly
   that branch on any filesystem by patching `_post_exchange_identity_matches` to return `True`,
   so suite-level coverage of "content, not ctime, decides" is filesystem-independent. No action
   required for merge.
2. **Follow-up worth a separate small commit — pin the code in the sibling test and name the
   digest in the new one.** Add `code` capture (`as raised`) at `:714` (both granularities yield
   `race`, so it is safe) and `self.assertIn("expected digest", str(raised.exception))` at `:754`.
   This closes the two "which defense fired" ambiguities above for two lines.
3. **Real coverage gap this review found, pre-existing and not a regression:** the two pre-syscall
   identity guards in `_rename_exchange` (`workflow_artifacts.py:1433-1436`) are not detected by
   *any* test in this module. Measured: deleting either guard (M3 target, M4 temporary) leaves
   `Ran 25 tests … 0 failures`. They survive because the displaced-digest backstop reproduces the
   same `code="race"` and the same on-disk bytes, so the security property is intact — the missing
   guarantee is "the swap never happened", which is what those guards exist for. A follow-up test
   should spy `_renameat2_exchange_call` and assert it was **not** called when an in-window
   same-inode tamper is detected. Suggested as an issue, not a demand on this commit.
4. **Filesystem matrix (nice-to-have).** The new test hard-fails rather than skips when `TMPDIR`
   cannot preserve inode/mode across an in-place write (§2 end). If the project ever claims
   support for FUSE/9p runners, add an `unittest.skipUnless` capability probe *for the premise*
   (inode stability), never for the rejection — and note that a coarse `mtime` (vfat 2 s) is
   already safe here because `os.utime` re-applies a value the filesystem itself reported.
5. **Process.** This is the only change needed to unblock the mandatory `root-unittest` command;
   the App-owned policy-epoch check on the new head SHA remains the sole merge authority and local
   evidence (this report, `grok_verify.py --mode pr`) cannot substitute for it.

## Addendum — tree moved while this review ran (Important for the receipt owner)

Reviewed object: `f10741b`. While the report was being written the branch was amended to
`ebd9a0a` (same subject). Verified: `git diff --stat f10741b ebd9a0a` shows the **only** change is
this `evidence/review-test.md` file, and `git diff f10741b ebd9a0a -- tests/test_workflow_artifacts_adversarial.py`
is empty, so every finding and measurement above applies unchanged to `ebd9a0a`. Because local
receipts bind to HEAD plus the dirty tree, any fingerprint-bound receipt recorded against
`f10741b` (including a `grok_verify`/review receipt) is stale for `ebd9a0a` and must be re-recorded
after the final commit, and this report's file:line citations are relative to
`tests/test_workflow_artifacts_adversarial.py` as it exists in both commits.
