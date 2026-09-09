# M2-A second fix-wave test rereview

## Exact identity and final verdict

- Route: `0156034c05bd`
- Prior head: `fd5f7eb41fe63c8c0950c0195cfcf54a00dee04d` (tree `962d7f858fbf7754dd0f800e65a8f41f8ba5f983`)
- Fix head: `52c4ab8fc43a21fe1c6b96ff5404bc39d3f7d2ad` (tree `f142f13d7407d0bf62439acb3f12a4339b21b51a`)
- Exact fix range: `fd5f7eb41fe63c8c0950c0195cfcf54a00dee04d..52c4ab8fc43a21fe1c6b96ff5404bc39d3f7d2ad`
- Packaged diff: `.superpowers/sdd/2026-08-26-m2a-executable-architecture/review-fd5f7eb..52c4ab8.diff`
- Packaged-diff SHA-256: `f6645ae122d1fd000796ace4eb2306e57a9b3a60f5461de6524492c6a34f750b`

**Final verdict: BLOCKED**

Finding count: 0 Critical, 1 Important, 0 Minor. Both exact residuals from `final-test-rereview.md` are **ADDRESSED**, but a newly exposed structured-provenance boundary still produces both a queue false negative and a non-queue false positive.

## Residual verdicts

### Prior queue residual — ADDRESSED for the reported positive and negative matrix

The new regression `test_queue_provenance_is_operation_and_element_specific` has real base/head oracles for:

- Celery wildcard decorator alias;
- Celery wildcard factory/app chain;
- RQ wildcard factory/instance chain;
- dynamic selection from a mixed queue/non-queue container;
- unrelated wildcard receiver;
- exact non-queue tuple sibling;
- exact non-queue list subscript sibling;
- exact non-queue dictionary-key sibling.

It asserts category and overall status, `new_queue` presence/absence, scanned path for positives, and monotonic risk (`tests/test_architecture_fitness.py:788-892`). Independent exact-head probes confirmed the three wildcard aliases and dynamic mixed selection now return `unsupported`, overall `fail`, and `new_queue`; the three previously failing mixed tuple/list/dict negatives now return `not_applicable`, overall `pass`, and no trigger.

The implementation now carries element/key state in `_QueueValue`, follows wildcard uncertainty through assignments/factories, distinguishes literal list/tuple positions and dictionary keys, and treats unresolved mixed selection as uncertain (`.grok-stack/adaptive_grok/architecture_fitness.py:1043-1219`). These are meaningful closures of the exact prior cases, not weakened assertions.

### Prior installer rollback-mode residual — ADDRESSED

`_stage()` now calls `fchmod()` on the opened staging descriptor before publication and removes a failed stage (`scripts/install_into.py:288-320`). The relocation test covers managed, root `AGENTS.md`, and Bitrix paths under umask `077`, asserting both original bytes and exact modes `0751`, `0666`, and `0640`; a separate setup-failure test asserts the operation-created parent and hidden stage are removed (`tests/test_installer.py:261-314`).

An independent actual parent-relocation probe repeated the prior scenario under umask `077` for modes `0666`, `0751`, and `0640`. All three raised `UnsafeInstallTarget`, restored exact bytes and exact mode, and left no `.adaptive-install-*` entry. The prior installer finding is closed.

## New Important finding

### TST-R2-I1 — Structured provenance ignores container mutation and mishandles exact negative indexes

The new resolver models only literal list/tuple/dict construction and direct `Assign`/`AnnAssign` binding. `bind_target()` ignores `Subscript` assignment targets, `queue_value()` has no mutation or binary-container semantics, and `literal_key()` accepts only `ast.Constant` (`architecture_fitness.py:1076-1184`). In Python's AST, a negative integer subscript is an `ast.UnaryOp`, not an `ast.Constant`.

Independent exact-head base/head probes reproduced three real queue false negatives. In each base, a proven Celery object entered a container through an ordinary bounded form; the head added only `@app.task`:

```text
items=[]; items.append(celery.Celery('a')); app=items[0]:
  background=not_applicable overall=pass triggers=()

items={}; items['app']=celery.Celery('a'); app=items['app']:
  background=not_applicable overall=pass triggers=()

items=[] + [celery.Celery('a')]; app=items[0]:
  background=not_applicable overall=pass triggers=()
```

The queue constructor signal already exists in the base, while the derived `app` is classified non-queue; therefore the new real task disappears from exact delta applicability and risk. These forms must either resolve within the bounded value model or make the relevant operation `unsupported`; N/A violates AC-004/FORBID-002 and the approved rule that ambiguous queue-adjacent syntax fails closed.

The same omission creates an exact non-queue false positive. For a mixed literal `[Celery(...), Pipeline()]`, `pipeline = values[-1]` is a statically exact selection of the local `Pipeline`, yet it is treated as an unresolved mixed selection:

```text
negative list index: background=unsupported overall=fail triggers=('new_queue',)
negative integer dict key: background=unsupported overall=fail triggers=('new_queue',)
```

A nested exact unpack negative returned N/A correctly, and positive integer/string selections remain covered. The defect is specifically absent mutation/binary propagation and incomplete literal-key normalization. The committed regression contains no container mutation, concatenation, negative index, or negative dictionary key, so all 348 tests can pass while both false directions remain.

Required closure: add a bounded structured-operation policy. Resolve safe literal mutations/selections, or explicitly taint relevant mutated/combined containers as uncertain so real queue operations fail closed. Normalize signed integer literal keys and Python negative list/tuple indexes so exact non-queue siblings remain N/A. Add Celery and RQ base/head positives and non-queue controls for `append`/`extend`, subscript assignment, list/tuple concatenation, signed list/tuple indexes and signed dictionary keys; assert category/overall status, trigger, scope and monotonic risk.

## New-diff test assessment

- Installer created-directory containment tests cover managed, `AGENTS.md`, Bitrix and ensured-directory boundaries with retained descriptor identity and outside sentinels. The failure cleanup and mode oracles are substantive; no new Critical/Important test gap was reproduced there.
- Marker-only adoption history has an end-to-end abandoned unmarked model-draft regression, while the earlier actual marker deletion, descendants, merges, shallow history and clean legacy controls remain green.
- Frozen handoff digests are compared by a bounded CLI subprocess against all five canonical summary fields; the test requires exactly one labeled 64-hex value per field.
- The prior schema Minor remains **ADDRESSED**: the exact 10 system and 13 rules object schemas are recursively asserted closed and fully required. The selector passed on the fix head.

No other new Critical/Important test gap was found in this fix range.

## Independent verification

- Seven second-wave selectors, including the schema-Minor guard: **PASS**, 7/7.
- `python3 -m unittest discover -s tests`: **PASS**, 348/348 in 213.835s.
- Prior wildcard/mixed exact matrix: **PASS**, all reported positive and negative outcomes corrected.
- Prior installer actual-relocation mode matrix: **PASS**, 3/3 exact modes and bytes restored, no staging leftovers.
- New container-mutation queue matrix: **FAIL**, 3/3 real task deltas reproduced N/A/pass/no trigger.
- New signed-index non-queue matrix: **FAIL**, exact non-queue list and dictionary selections false-triggered `new_queue`.
- Packaged diff applied to an archive of the exact prior head and produced a byte-identical tree to the exact fix head: **PASS**.
- `git diff --check fd5f7eb41fe63c8c0950c0195cfcf54a00dee04d..52c4ab8fc43a21fe1c6b96ff5404bc39d3f7d2ad`: **PASS**.
- Exact fix range under `trust-ci/**` and `.github/workflows/**`: **empty**.
- HEAD/tree remained `52c4ab8fc43a21fe1c6b96ff5404bc39d3f7d2ad` / `f142f13d7407d0bf62439acb3f12a4339b21b51a` throughout review. Concurrent untracked reviewer reports were not treated as product input.

## Disclaimer

This was a read-only product-code rereview; only this report was written. It did not modify product source, runtime receipts, external systems, Trust CI policy/holdouts/state, approvals, branch protection, credentials, or deployment state. Local evidence does not replace the GitHub App-owned exact-SHA policy-epoch check or any required external approval.
