# Task 6 code re-review — fix round 3

## Reviewed identity

- Prior head: `bc9eb4069519f5530e108145543a7519b5fb0994` (tree `6e8ca27c9f82586c915347d5dba66b88f0a4ce85`)
- Fix head: `aaea6f1fd661c4da7c0758024b80d5d200fd6298` (tree `f5ad592aeea3799512bd5b8dfcfeca3b97e67c13`)
- Frozen adoption base: `25bfbe59ea188d9687b20a9caad19e7db3d031f8`
- Route: `0156034c05bd`
- Inputs: prior `evidence/task-6-code-rereview-2.md`, exact Task 6 brief, appended round-three implementation report in `task-6-report.md`, packaged exact fix diff `review-bc9eb40..aaea6f1.diff`, and the actual surrounding implementation and focused tests

## Final verdicts

- **Prior N2: ADDRESSED**
- **New Critical breakage: none**
- **New Important breakage: none**
- **Spec compliance: PASS**
- **Code/test quality: APPROVED**

The fix makes over-limit promotion depend on the exact requested export while preserving fail-closed treatment for proven queue exports and queue-adjacent imports. No Critical or Important finding remains in this scoped fix.

## Prior finding disposition

### N2 — ADDRESSED: source-root ceiling no longer transfers sibling provenance

`_queue_adapter_names()` now computes `export_resolved` immediately after resolving the bounded module and requires it in the over-limit `resolved` branch (`.grok-stack/adaptive_grok/architecture_fitness.py:1318-1339`). The condition can therefore promote only the imported export found in `resolution.exports`; unrelated module-wide signals no longer prove a separate receiver. `_local_queue_resolution()` continues to derive that export inventory from the bounded module's provenance fixed point (`architecture_fitness.py:1241-1268`).

The committed regression uses the exact reported mixed module—Celery `app` beside unrelated `form`—and evaluates both 63 and 64 declared roots, corresponding to 64 and 65 total roots after the implicit repository root (`tests/test_architecture_fitness.py:1168-1216`). It asserts `not_applicable/pass`, no `new_queue`, and monotonic risk on both sides.

An independent exact probe reproduced those outcomes:

```text
unrelated 63: not_applicable / no_background_signal / pass / no triggers / yellow -> yellow
unrelated 64: not_applicable / no_background_signal / pass / no triggers / yellow -> yellow
```

The same 64-declared-root mixed module, when the consumer imports and uses the actual `app` export from the non-queue-adjacent `project.forms` module, remains conservative:

```text
queue non-adjacent above limit: unsupported / queue_provenance_unresolved /
                                fail / new_queue / yellow -> yellow
```

Thus the repair distinguishes the requested exports rather than weakening the root ceiling.

## New breakage assessment

### Critical

None.

### Important

None.

### Minor

None.

## Preserved behavior and invariants

- The existing exact boundary test still covers unrelated below/above-limit changes, relevant at/above-limit changes, and an unchanged queue operation beside a new unrelated call (`tests/test_architecture_fitness.py:1065-1166`). Relevant above-limit provenance remains structured `unsupported`, scopes the changed consumer, fails fitness, and emits `new_queue`.
- Queue-adjacent imports continue to take the conservative over-limit branch before bounded resolution (`architecture_fitness.py:1313-1317`). Non-adjacent imports now require export-specific provenance; a proven requested export still takes the structured over-limit path (`architecture_fitness.py:1328-1339`). Ambiguous/unsupported requested exports retain their prior fail-closed handling (`architecture_fitness.py:1340-1352`).
- Exact semantic delta is still computed as `head.signals - base.signals` before applicability is published (`architecture_fitness.py:1431-1489`), so unchanged queue syntax does not contaminate a newly added unrelated operation.
- One `_QueueProvenanceResult` is still computed once and passed to both `_background_jobs()` and `_risk()` (`architecture_fitness.py:1873-1906`). `new_queue` is derived from that same result, and post-risk remains the maximum of pre-risk and escalation (`architecture_fitness.py:1739-1761`).
- Focused coverage for package initializers, regular modules, multi-hop exports, `src/` roots, ambiguous roots, missing adapters, function/factory uncertainty, depth/module bounds, terminal-name negatives, mixed-file collisions, and source-only queue signals remains green.
- The exact fix range adds no dependency, service, database, migration, queue, framework, provider, systemd unit, external write, `trust-ci/**`, or `.github/workflows/**` change. The read-only diagram and target-owned architecture boundaries are untouched.

## Verification evidence

- Exact prior/fix commit and tree identities matched the assignment; `bc9eb406...` is an ancestor of `aaea6f1...`.
- `git diff --check bc9eb4069519f5530e108145543a7519b5fb0994..aaea6f1fd661c4da7c0758024b80d5d200fd6298`: PASS.
- Exact fix-range path queries under `trust-ci/**` and `.github/workflows/**`: empty.
- Eight focused queue provenance selectors passed in 14.752 seconds, including the exact 63/64 mixed-export regression, relevant root-limit behavior, package/source roots, ambiguity, depth/module bounds, pure terminal-name negatives, mixed-file negatives, and source-only positives.
- Independent 63/64 mixed-export and above-limit non-adjacent proven-export probes produced the exact structured states shown above.
- The appended report's 106-test focused suite, 331-test discovery, static/spec/architecture checks, and no-record PR verification were inspected but not broadly rerun.

## Cannot verify

- Historical RED ordering is reported but cannot be independently reconstructed from the final fix commit.
- This local review is not the App-owned exact-SHA Trust CI Check Run and does not represent any external signed approval.

This report is local independent review evidence only and does not authorize merge, release, deployment, or external mutation.
