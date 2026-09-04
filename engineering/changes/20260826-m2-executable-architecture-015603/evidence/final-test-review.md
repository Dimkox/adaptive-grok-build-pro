# M2-A final whole-branch test review

## Verdict

**BLOCKED**

Exact route: `0156034c05bd`.

Exact adoption base: `25bfbe59ea188d9687b20a9caad19e7db3d031f8` (tree `b6bb74f00fba7fd194ac1da01a00cca7aea89bf5`).

Exact reviewed head: `99de2f9757400f7394b7a9e2c46b3ebce939e438` (tree `bae34faabdf968396e393d40f7219d3bbf5a60b5`).

Finding count: 0 Critical, 1 Important, 1 Minor. PASS requires zero Critical/Important findings, so the route's test gate is not satisfied.

## Important finding

### TST-FINAL-I1 — Queue-root wildcard and structured assignment dataflow silently hide real new jobs

The approved queue provenance design requires proven queue roots and assignments to resolve, and requires ambiguous queue-adjacent syntax to return `unsupported`; the same result must drive both background-job applicability and `new_queue` risk. The current implementation does neither for three ordinary AST forms:

- `from celery import *` records `*` as the queue name, so a subsequently added `@shared_task` decorator is not related to the already-present queue import;
- tuple unpacking only propagates into a direct `ast.Name` target, so `app, backup = apps` loses provenance;
- `queue_derived()` does not traverse `ast.Subscript`, so `app = apps[0]` loses provenance.

The relevant implementation is `.grok-stack/adaptive_grok/architecture_fitness.py:994-1068`: `queue_derived()` handles only names, attributes and calls, while the assignment loop accepts only direct name targets. Existing positive tests at `tests/test_architecture_fitness.py:548-631` cover direct aliases, factories, `getattr`, simple multi-hop names and local adapters, but contain no wildcard, tuple/list destructuring, or subscript-derived queue object. Collision tests prove that unrelated `.submit()`, `.delay()` and `.task` names remain N/A; they do not exercise an expression already rooted in Celery/RQ provenance.

An independent exact-head base/head probe changed only the decorated job in each case and produced:

```text
wildcard     background=not_applicable overall=pass triggers=()
tuple_unpack background=not_applicable overall=pass triggers=()
subscript    background=not_applicable overall=pass triggers=()
control      background=unsupported    overall=fail triggers=('new_queue',)
```

The control used the supported direct assignment `app = celery.Celery(...)` and confirms the probe's policy/model and oracle are live. The three false N/A results are not conservative classification: the exact head delta contains a real `@shared_task` or `@app.task` job, yet the gate passes and risk remains green. This violates AC-004 and FORBID-002, as well as the approved design's explicit fail-closed rule for ambiguous queue-adjacent syntax.

Required closure: classify wildcard queue imports as `unsupported` when a changed callable/decorator can depend on their unknown exports; either resolve bounded tuple/list unpacking and subscript-derived aliases or classify the queue-rooted expression as `unsupported`. Add exact base/head regressions for Celery and RQ covering wildcard import, tuple/list destructuring, indexed containers, annotated/chained variants, malformed/ambiguous counterparts, and unrelated negative controls. Every applicable/unsupported case must assert category status, overall failure, `new_queue`, scanned scope and monotonic post-risk.

## Minor finding

### TST-FINAL-M1 — Closed-schema mutation coverage is not exhaustive per authoritative record type

The SDD ledger already records this deferred limitation. `test_every_authoritative_object_is_closed_and_required` removes every field from the system root, node, runtime, edge, failure-behavior and rules root, but it does not perform the same required-field and unknown-field mutation matrix for every trust-domain, data-classification, secret, signal, contract, and individual rule-record shape (`tests/test_architecture_model.py:301-346`).

The schemas themselves set `additionalProperties: false` and required lists, and independent spot probes confirmed rejection of a trust-domain unknown field, a missing data-classification field, a background-job-rule unknown field and a missing risk-rule field. Therefore this is a regression-test breadth limitation, not a reproduced parser acceptance defect. Expand the mutation matrix to make future per-definition schema weakening observable.

## Coverage and oracle assessment

- Strict parsing/schema: meaningful coverage exists for canonical JSON, duplicate keys/IDs, version rejection, closed roots, required fields, UTF-8/size/depth/item limits, stable identities and repository-path safety. The remaining per-record mutation breadth is recorded above.
- Model/diff/drift: tests bind adoption state and exact base/head, typed added/removed/changed objects, deterministic digests, contract inventory, no-follow reads, symlink/special-file rejection, file/byte limits, path identity and repository drift. Assertions inspect typed reasons and exact identities rather than only exit codes.
- Fitness: tests assert the complete set of 12 mandatory categories, all four result states, N/A evidence shape, unsupported-as-overall-fail, exact changed-source subtraction, and nondecreasing risk. Contract directionality, migration identity/history, code budgets, module boundaries, network families, tenant/secret/workspace policies and change separation have positive and negative oracles. The queue gap above is the only reproduced Critical/Important fitness oracle hole.
- Queue bounds/collisions: package and regular-module relative imports, `from . import child`, parent-relative exports, multi-hop aliases, factories/`getattr`, ambiguous roots, depth/module/source-root/AST ceilings and mixed unrelated terminal-name collisions are exercised. Tests correctly distinguish common-name collisions from proven queue provenance, but omit the queue-rooted wildcard/structured-assignment forms in TST-FINAL-I1.
- Risk/evidence/receipts: tests bind deterministic inventory/diff/evidence digests, preserve typed M1 criteria, bind adopted architecture/base/head/tree/contract state, reject stale contract/route-base/Git-head/tree bindings, and retain explicit legacy-consumer compatibility.
- Installer/consumer packaging: installer, manifest and structure tests verify delivery of code, schemas, examples and runnable CLI without creating or overwriting target-owned authority; force/idempotency/conflict/no-GitHub-Actions cases have stateful assertions. The architecture-focused inventory is 41 model, 43 fitness, 22 receipt, 18 installer, 11 manifest/package and 12 structure tests.
- Read-only diagrams: unit tests snapshot repository inventory and bytes and reject mutation-shaped opens/syscalls. An independent CLI probe ran both `diagram --json` and `diagram --check --json`; Git status and every `architecture/**` file digest were unchanged. Both modes succeeded.
- TDD evidence: the SDD ledger records task commit ranges, review rounds, deferred findings and remediation decisions. It is coherent with the final tests inspected, but it is workflow evidence rather than independent merge authority, and it did not include the missing queue regressions above.

## Independent checks

- `python3 -m unittest discover -s tests`: **PASS**, 331/331 in 175.186s on the exact reviewed code tree.
- Independent queue provenance matrix: **FAIL as an acceptance oracle**; three real new-job deltas reproduced N/A/pass/no-risk-trigger, while the direct-assignment control failed closed.
- Independent closed-schema spot matrix: **PASS**, 4/4 malformed documents rejected.
- `python3 scripts/grok_architecture.py diagram --json`: **PASS**, repository status and architecture bytes unchanged.
- `python3 scripts/grok_architecture.py diagram --check --json`: **PASS**, repository status and architecture bytes unchanged.
- Packaged diff SHA-256: `385aef31d68d78ce9f68b824900bba01d9980e66bf5370897cda77b2dac49a01`.
- Packaged diff `.superpowers/sdd/2026-08-26-m2a-executable-architecture/review-25bfbe5..99de2f9.diff` applied to an archive of the exact base and produced a byte-identical archive tree to the exact head: **PASS**.
- `git diff --check 25bfbe59ea188d9687b20a9caad19e7db3d031f8..99de2f9757400f7394b7a9e2c46b3ebce939e438`: **PASS**.
- Exact range under `trust-ci/**` and `.github/workflows/**`: **empty**.
- HEAD and tree identity remained `99de2f9757400f7394b7a9e2c46b3ebce939e438` / `bae34faabdf968396e393d40f7219d3bbf5a60b5` during review.

## Coverage limitations and disclaimer

No coverage percentage was recomputed; adequacy was assessed from the exact tests, their assertions, the implementation paths they exercise, the complete suite, and distinct adversarial probes. The review did not mutate deployed Trust CI policy, holdouts, PostgreSQL state, external approvals, branch protection, production systems, or product code.

This report is local, exact-head review evidence only. It does not replace the GitHub App-owned `adaptive-trust-ci/verified@<policy-sha12>` check on the exact pull-request head or any required externally signed approval.
