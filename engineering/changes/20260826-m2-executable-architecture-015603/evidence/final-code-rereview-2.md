# Final M2-A code re-review 2 — second consolidated fix wave

## Reviewed identity

- Route: `0156034c05bd`
- Prior reviewed head: `fd5f7eb41fe63c8c0950c0195cfcf54a00dee04d`
- Prior tree: `962d7f858fbf7754dd0f800e65a8f41f8ba5f983`
- Fix head: `52c4ab8fc43a21fe1c6b96ff5404bc39d3f7d2ad`
- Fix tree: `f142f13d7407d0bf62439acb3f12a4339b21b51a`
- Clean fix-head tree fingerprint at review start: `e148eaf7c2ee908fcc3f71164e6cbbf3a052c08b9f7d0c944468037d519adbfd`
- Exact package: `.superpowers/sdd/2026-08-26-m2a-executable-architecture/review-fd5f7eb..52c4ab8.diff`
- Package SHA-256: `f6645ae122d1fd000796ace4eb2306e57a9b3a60f5461de6524492c6a34f750b`
- The prior head is an ancestor of the fix head. The exact range contains 17 files, 877 insertions, and 89 deletions. It changes no `trust-ci/**` or `.github/workflows/**` path and passes `git diff --check`.

## Verdict

**BLOCKED** — prior code N1 is addressed and all three originally closed code findings remain addressed, but the second wave introduces two Important defects in queue provenance and installer failure recovery. Finding count: 0 Critical, 2 Important, 0 Minor.

## Prior finding verdicts

### Code N1 — abandoned pre-marker drafts versus marker-only durable adoption: ADDRESSED

`_exact_history_has_architecture()` now queries bounded full history only for `architecture/adoption.json` (`.grok-stack/adaptive_grok/receipts.py:148-171`). Current model/rules without the marker and exact route-base/current-tree partial states still fail independently (`:141-145,186-203`), while a complete-history repository in which the marker never existed may return legacy `not_configured`. The new end-to-end four-commit regression proves the abandoned draft lifecycle returns `pass/not_configured` (`tests/test_verification_doctor.py:348-369`).

Actual marker-backed adoption remains durable: post-adoption deletion after unrelated descendants still fails (`tests/test_verification_doctor.py:322-346`), and the existing merge/shallow deletion and shallow-history ambiguity cases remain present (`:480-546`). Thus the repair distinguishes abandoned drafts from actual adoption without reopening the original deletion bypass.

### Original I2 unknown line statistics: remains ADDRESSED

The second wave does not change code-budget accounting. Applicable artifacts whose added or deleted line count is unavailable still contribute a named `unsupported` finding rather than zero (`.grok-stack/adaptive_grok/architecture_fitness.py:973-1017`). The focused NUL/invalid-UTF-8 regression passed.

### Original I3 bounded-process setup cleanup: remains ADDRESSED

The second wave does not change `_run_capped()`. Selector construction, nonblocking setup, and registration remain inside cleanup ownership; streams close and a live process group is stopped/reaped in the outer `finally` (`.grok-stack/adaptive_grok/architecture_diff.py:82-151`). The focused real-process setup-failure regression passed.

## Important findings introduced by this fix

### I1 — alternative assignments can erase proven queue provenance and make a real queue operation pass as N/A

The new fixed-point resolver stores only one `_QueueValue` per name. Every syntactic assignment overwrites the preceding value, including mutually exclusive control-flow branches (`.grok-stack/adaptive_grok/architecture_fitness.py:1128-1133,1167-1184`). It does not join possible runtime values or mark the target uncertain. Consequently the result depends on AST traversal order rather than runtime reachability.

Independent exact-head base/head probe:

```python
import celery
class Pipeline:
    def task(self, fn): return fn
if enabled:
    receiver = celery.Celery("jobs")
else:
    receiver = Pipeline()
# added in head:
@receiver.task
def stage(): return None
```

Observed at the fix head:

```text
background_job=not_applicable reason=no_background_signal
overall=pass triggers=() risk=yellow->yellow
```

Reversing the two branches changes the same possible-value set to `unsupported` with `new_queue`, confirming traversal-order dependence. At runtime the first form can execute the Celery branch, so this is a fail-open false negative under AC-004/FORBID-002 and the package-aware fail-closed provenance contract. The prior implementation monotonically retained queue-derived names and did not have this exact false-negative behavior.

The same root problem appears in the new keyed representation. `literal_key()` accepts booleans through `isinstance(True, int)` but serializes `True` and `1` as distinct strings (`:1076-1082`), even though Python dictionary keys compare equal. For `{True: Pipeline(), 1: celery.Celery("jobs")}`, runtime `values[True]` is the latter Celery object, while the analyzer selects the earlier non-queue entry (`:181-192,1108-1115`) and the added `@receiver.task` again returns N/A/pass/no trigger.

The committed matrix covers straight-line assignments, distinct literal indices/keys, and one dynamic mixed selection (`tests/test_architecture_fitness.py:788-892`), but neither alternative assignments nor equal-key collisions. Required repair: conservatively join all reachable definitions of a name (queue plus non-queue becomes `uncertain`) and model supported Python key equality exactly or fail closed on aliases/collisions. Add both branch orders and bool/int collision orders as base/head regressions asserting `unsupported`, overall failure, `new_queue`, scoped evidence, and monotonic risk.

### I2 — rollback publication failure leaves replacement bytes and an untracked staging file

After the first `os.replace`, `stage` is cleared (`scripts/install_into.py:335-340`). If relocation is then detected and an original file existed, recovery allocates a second stage in the local variable `rollback` and immediately publishes it (`:351-361`). That name is never transferred to the outer cleanup owner. If the rollback `os.replace` raises, the `finally` sees an empty `stage`, leaves the rollback stage under the target root, and leaves the already-published replacement bytes/mode in the retained parent (`:365-378`).

An independent exact-head fault-injection probe allowed the first publication, forced the existing changed-parent recovery branch, and raised on the second `os.replace`. It observed:

```text
OSError: rollback publication failed
destination bytes=b'replacement\n' mode=0600
target staging entries=['.adaptive-install-…']
```

The new tests prove directory-creation rollback, exact-mode restoration when rollback succeeds, and cleanup when the initial `_stage()` fails (`tests/test_installer.py:214-314`). They do not fail rollback allocation or rollback publication. Because managed files, root `AGENTS.md`, and Bitrix guidance share `tree.write`, this exception path violates the claimed failed-install containment/recovery boundary across all three surfaces.

Required repair: give every staging artifact one cleanup owner before publication and exercise rollback allocation/publication failures. The recovery contract must either restore exact original bytes/mode and remove all staging/created-parent residue, or redesign publication so this relocation window cannot leave a partial external mutation.

## Other second-wave assessment

- Directory creation now tracks operation-created components with retained parent descriptors, reproves each complete root-relative prefix, and performs identity-checked reverse rollback. The focused managed/AGENTS/Bitrix/ensure-dir relocation test passed; the distinct post-publication rollback failure is I2.
- `_stage()` now applies the requested mode with `fchmod`, and successful relocation rollback preserves bytes and mode under restrictive umask. Its focused regression passed.
- Frozen composite/system digests in `requirements.md` equal the current canonical summary, and the new bounded structure regression checks all five literals (`engineering/changes/20260826-m2-executable-architecture-015603/requirements.md:17-25`; `tests/test_structure.py:14-36`). The typed spec gate reports `ok=true`, 7/7 criteria mapped.
- Package status prose remains conservative: the second candidate requires fresh independent review, AC-007 and final receipts remain open, and `state.json` remains `implementing`. No new Important documentation claim was found apart from implementation claims invalidated by I1/I2.
- The original schema-test Minor remained closed and was untouched.

## Independent evidence and limits

- Ten intended focused regressions passed after correcting an initial reviewer-only unittest class-name typo: abandoned drafts, durable deletion descendants, queue operation/element matrix, shared package provenance, unknown metrics, process setup cleanup, directory relocation, mode restoration, initial-stage cleanup, and frozen digest equality.
- Two adversarial queue probes independently reproduced N/A/pass false negatives: mutually exclusive queue/non-queue assignments and Python-equal `True`/`1` dictionary keys. Reversing branch order produced `unsupported`, demonstrating order dependence.
- One installer fault-injection probe independently reproduced replacement bytes/mode plus `.adaptive-install-*` residue after rollback-publication failure.
- Architecture summary and typed change-spec gate passed. The implementer's reported 348-test and full-verifier results were inspected but not broadly rerun for this scoped rereview; the two failing scenarios above are absent from that suite.
- A concurrent untracked security-review report appeared after the clean-start identity was captured. It was treated only as overlap context and not as reviewed product input.

## Merge-authority disclaimer

This report is repository-local review evidence only. It is not merge authority and does not replace corrected source on a new immutable head, fresh exact-fingerprint verification and all route-selected reviews/receipts, or the GitHub App-owned policy-epoch `adaptive-trust-ci/verified@<policy-sha12>` check and required external approvals on the exact pull-request head.
