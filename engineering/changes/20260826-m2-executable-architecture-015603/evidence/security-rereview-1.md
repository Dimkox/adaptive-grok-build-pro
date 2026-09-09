# M2-A security remediation re-review 1 — BLOCKED

## Reviewed identity

- Verdict: **BLOCKED**
- Critical findings: **0**
- Important findings: **2**
- Remediation base: `1f54e8660cdaa28eb041aaf8c4a624fbb76ba834`
- Reviewed head: `0430175dc89e787f378e529a5b4fbf1ce8165dd4`
- Packaged diff: `.superpowers/sdd/2026-08-26-m2a-executable-architecture/review-1f54e86..0430175.diff`
- Original report: `engineering/changes/20260826-m2-executable-architecture-015603/evidence/security-review.md`
- Implementer report: `engineering/changes/20260826-m2-executable-architecture-015603/evidence/remediation-final-1.md`

The remediation diff contains no `trust-ci/**` or `.github/workflows/**` mutation. PASS requires zero Critical/Important findings.

## Important findings

### I-1 remains open for exact/worktree architecture evidence: marker-only deletion is accepted

The verifier/receipt entrypoint now detects marker deletion from the checked-out repository using model presence, exact HEAD, bounded direct parents, and route base (`.grok-stack/adaptive_grok/receipts.py:85-135`). Its new worktree, committed, merge, and shallow-with-exact-route-base regressions pass.

The separate exact-state architecture interface is still not adoption-aware. `_materialized_state()` reads only model, schemas, and contracts (`.grok-stack/adaptive_grok/architecture_diff.py:409-437`); `diff_architecture()` constructs both commit states from it without checking `architecture/adoption.json` (`architecture_diff.py:740-784`). `architecture_evidence()` then evaluates and emits that optimistic exact diff directly (`.grok-stack/adaptive_grok/architecture_fitness.py:1441-1453`). Direct CLI `diff`/`fitness` uses the same path.

Independent reproduction:

1. Commit a valid marker, system, and rules as the exact base.
2. Delete only `architecture/adoption.json` and commit the exact head; leave system/rules unchanged.
3. Run the production exact diff and fitness functions.

```text
changed_paths ('architecture/adoption.json',)
baseline_introduced False fitness pass risk red
statuses {
  'background_job': 'not_applicable', 'change_separation': 'not_applicable',
  'code_budget': 'not_applicable', 'contract_compatibility': 'not_applicable',
  'forbidden_edge': 'not_applicable', 'migration_safety': 'not_applicable',
  'module_boundary': 'not_applicable', 'network_client': 'not_applicable',
  'production_import': 'not_applicable', 'secret_flow': 'not_applicable',
  'tenant_authorization': 'not_applicable', 'workspace_trust': 'not_applicable'
}
```

Because marker deletion is absent from semantic changes and triggers, exact evidence also omits the architecture required scope. A consumer of the advertised exact-SHA interface can therefore receive `fitness_status=pass` after adoption authority was removed even though the checked-out verifier would fail. This is the original I-1 trust-state bypass on a second public evidence path and contradicts the post-adoption fail-closed contract.

Required remediation: make adoption state part of commit and worktree `ArchitectureState`, not only receipt discovery. A head/worktree with models but no canonical marker must fail; after an adopted base, marker removal must fail even when both models remain. Absence is allowed only for the explicit legacy/bootstrap state. Bind the marker digest/state into exact diff/evidence and add direct API plus CLI `--head`/`--worktree` tests for marker-only deletion, including merge/shallow exact route-base cases.

### I-2 — New source-job detection is bypassed by simple indirection

The new queue detector compares sets made from queue-family import targets and calls whose function chain remains rooted directly at an import alias (`.grok-stack/adaptive_grok/architecture_fitness.py:959-991`). `_background_jobs()` and risk escalation consistently share that result (`architecture_fitness.py:994-1062,1238-1258`), but unsupported queue semantics that do not create a new recognized set member remain invisible.

With `import celery as c` already present in the exact base, each of these head-only job introductions produced `background_job=not_applicable`, no `new_queue` trigger, and overall `pass`:

```python
factory = c.Celery
app = factory("jobs")
```

```python
app = getattr(c, "Celery")("jobs")
```

A project-wrapper decorator change was also invisible:

```python
from project import app

@app.task
def job():
    return 1
```

Observed output for all three isolated exact base/head probes:

```text
status pass background not_applicable reason no_background_signal triggers () findings ()
```

These are parseable, ordinary Python changes that introduce queue/background execution semantics while bypassing the mandatory job guarantees and the monotonic `new_queue` signal. The direct-call regression added in this remediation does not cover them. This violates the frozen rule that a newly matching or unsupported artifact revokes non-applicability (`docs/superpowers/specs/2026-08-26-m2-executable-architecture-design.md:121,131`) and AC-004's applicable-unsupported fail-closed requirement.

Required remediation: conservatively classify changed executable semantics in a file with a governed queue import as applicable/unsupported unless absence of a new job can be proven. Add bounded alias propagation and recognized decorator/factory handling where supported; unknown calls/attribute transfers rooted in a queue import must fail as `unsupported`, not disappear. Keep category applicability and risk triggers on the same result, and add exact base/head regressions for assignment aliases, `getattr`, decorators, and project adapters.

## Closure status for original findings

- **Original I-1:** **partially closed**. Checked-out verifier/receipt discovery now fails for marker/model deletion across worktree, committed, merge, and shallow exact-route-base cases. The exact evidence/CLI path above remains Important.
- **Original I-2:** **closed in reviewed scope**. Command-line overrides disable `core.fsmonitor`, hooks, paging, external diff, rename inference, attributes/excludes, and replacement objects (`.grok-stack/adaptive_grok/architecture_diff.py:141-180`). An independent hostile configuration matrix covering every used `rev-parse`, `rev-list`, `cat-file`, `show`, `ls-tree`, `ls-files`, exact diff, and worktree diff operation reported `hostile_config_executed False` for fsmonitor, pager, diff command/textconv, and hook sentinels.
- **Original I-3:** **closed in reviewed scope**. Diagram reads/writes now use held descriptor-relative no-follow directories, bounded regular-file reads, temporary `O_EXCL` files, descriptor-relative rename/unlink, fsync, and ancestor identity revalidation (`.grok-stack/adaptive_grok/architecture_diagrams.py:121-365`). Ancestor/final symlink, FIFO/oversize, and deterministic directory-swap tests pass without outside reads or writes.
- **Missing no-follow capability:** **closed**. Independent probes with `O_NOFOLLOW=None` and `O_NOFOLLOW=0` returned structured `ArchitectureError(code="io")` before model, adoption, diagram, or worktree-blob reads. The focused repository tests also passed.

## Verification evidence

```text
git rev-parse HEAD
0430175dc89e787f378e529a5b4fbf1ce8165dd4

git diff --check 1f54e8660cdaa28eb041aaf8c4a624fbb76ba834..0430175dc89e787f378e529a5b4fbf1ce8165dd4
PASS (no output)

git diff --name-only 1f54e8660cdaa28eb041aaf8c4a624fbb76ba834..0430175dc89e787f378e529a5b4fbf1ce8165dd4 -- trust-ci .github/workflows
PASS (no output)

Focused marker/Git/diagram/no-follow/source-job remediation tests
Ran 11 tests in 14.064s — OK

python3 -m unittest discover -q
Ran 317 tests in 122.438s — OK

python3 scripts/grok_architecture.py --root . validate --json
ok=true

python3 scripts/grok_architecture.py --root . drift --json
ok=true; findings=[]

python3 scripts/grok_architecture.py --root . diagram --check --json
ok=true; mismatches=[]

python3 scripts/grok_architecture.py --root . fitness \
  --base 25bfbe59ea188d9687b20a9caad19e7db3d031f8 \
  --head 0430175dc89e787f378e529a5b4fbf1ce8165dd4 \
  --pre-risk red --json
fitness_status=pass; risk_post=red; fitness_results=12
```

The stock suite and current-tree fitness pass do not cover or negate the two adversarial findings above. This report is local review evidence only; it is not merge authority, a human approval, or the App-owned exact-SHA Trust CI check.
