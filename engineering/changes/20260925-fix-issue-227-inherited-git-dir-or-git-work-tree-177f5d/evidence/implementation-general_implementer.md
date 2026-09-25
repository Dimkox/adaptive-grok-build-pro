# Implementation evidence — general_implementer

Route: `177f5dc1d5cf`

## Root-cause evidence

The explicit repository root was passed as `cwd`, but every Git probe inherited
`GIT_DIR` and `GIT_WORK_TREE`. Those variables redirected grant repository,
HEAD, inventory and fingerprint inputs, while the eventual shell push would
inherit the same redirection. The safe repair therefore requires both root-bound
read-only probes and an early push denial when either selector key is present.

## RED

No production code had been edited when these commands ran.

### Root-bound probes

Command:

```text
python3 -m unittest tests.test_util_fingerprint
```

Result: exit 1; `Ran 20 tests`; `FAILED (failures=3)`.

The assertion `self.assertEqual(expected, observed)` failed for `GIT_DIR`,
`GIT_WORK_TREE`, and both together. Observed repository root, remote identity,
HEAD, dirty inventory/statuses, and fingerprint came from or were distorted by
the foreign repository instead of remaining equal to root A's clean-environment
baseline.

### Grant, policy, and hook boundary

Command:

```text
python3 -m unittest tests.test_policy tests.test_hooks
```

Result: exit 1; `Ran 60 tests`; `FAILED (failures=8)`.

- branch `GIT_DIR`, branch `GIT_WORK_TREE`, and combined tag cases failed
  `self.assertFalse(allowed)` because policy returned allow;
- empty-key cases failed because the reason was the generic missing-grant text
  and did not contain the required `unset` recovery;
- a grant created for root A stored repository `example/foreign` instead of
  `Dimkox/adaptive-grok-build-pro`;
- the same-tree foreign-pushurl policy fixture returned allow; and
- the real pre-tool hook returned `allow` instead of `deny`.

All fixtures were disposable local repositories. The tests inspected the
foreign push URL with a read-only local Git query and never executed `git push`
or accessed the network.

## GREEN

### Focused policy, hook, and fingerprint suite

Command:

```text
python3 -m unittest tests.test_policy tests.test_hooks tests.test_util_fingerprint
```

The first post-implementation run reached the intended denial behavior but
reported one test-only failure: the hook's expected denial ledger and Python
import caches changed the disposable repository's untracked-file list. The
assertion was narrowed to the actual no-operation contract (HEAD, refs, remotes,
index, and tracked worktree), without changing production code.

Final result: exit 0; `Ran 80 tests`; `OK`.

### Nearby contract suite

Command:

```text
python3 -m unittest tests.test_structure tests.test_change_receipts
```

Result: exit 0; `Ran 49 tests`; `OK`.

Fresh handoff rerun after all source, test, checklist, lesson, and evidence edits:

```text
python3 -m unittest tests.test_policy tests.test_hooks tests.test_util_fingerprint tests.test_structure tests.test_change_receipts
```

Result: exit 0; `Ran 129 tests`; `OK`.

### Focused static checks

Commands and results:

```text
python3 -m ruff check .grok-stack/adaptive_grok/util.py .grok-stack/adaptive_grok/_policy_legacy.py tests/test_policy.py tests/test_hooks.py tests/test_util_fingerprint.py
# All checks passed!

git diff --check
# exit 0, no output
```

## Changed files

- `.grok-stack/adaptive_grok/util.py`: one selector-scrubbed environment for
  root discovery, textual Git output, binary path inventory, and name-status
  inventory.
- `.grok-stack/adaptive_grok/_policy_legacy.py`: presence-based, secret-safe
  branch/tag push denial before human-gate or grant lookup.
- `tests/test_util_fingerprint.py`: different-HEAD dirty-root probe regression.
- `tests/test_policy.py`: grant-binding, same-tree foreign-pushurl, empty-key,
  branch/tag, clean-environment, and no-push regressions.
- `tests/test_hooks.py`: real hook subprocess denial, denial-ledger placement,
  secret-safety, and no Git state mutation.
- This implementation evidence and task checklist; `mistakes.md` records the
  corrected test-harness assumption.

## Residual risk and rollback

Root-local `remote.origin.pushurl` mutation without inherited selectors remains
out of scope, as do unreviewed repository/config selectors beyond `GIT_DIR` and
`GIT_WORK_TREE`. A process that intentionally exports either covered key is now
denied even when it points back to the intended root; recovery is to unset it
and retry from a clean environment.

Rollback is forward-fix only: do not restore the vulnerable allow path. Disable
delegated agent Git pushes while correcting any regression, then rerun the
foreign-selector probe, policy, and hook cases before re-enabling the path.

The controller still owns full `grok_verify --mode pr`, independent reviews,
fingerprint-bound receipts, commit/delivery, and external Trust CI. No commit,
push, network call, GitHub write, Daybreak action, or external operation was
performed by this implementation task.
