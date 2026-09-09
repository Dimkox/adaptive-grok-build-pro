# M2-A security remediation re-review 3 — BLOCKED

## Reviewed identity

- Verdict: **BLOCKED**
- Critical findings: **0**
- Important findings: **5**
- Remediation base/tree: `aa445ad0b2b8a25d85de7629e54bd188a5c1086d` / `8be847232fc1df9db5dd97917a237bfa87cc42dd`
- Reviewed head/tree: `11bc554a16d9092798543fa986da086708c165de` / `41e8a17d867fdce3f5eabd4b71c6ce2f81a58bad`
- Packaged diff: `.superpowers/sdd/2026-08-26-m2a-executable-architecture/review-aa445ad..11bc554.diff` (`sha256:dc61850f78919c4864bbd4295a75bef1c9bdf3e2cb813fb4bf06342f8b6513c0`)
- Implementer evidence: `engineering/changes/20260826-m2-executable-architecture-015603/evidence/remediation-final-3.md`

The exact range contains no `trust-ci/**` or `.github/workflows/**` mutation and `git diff --check` passes. PASS requires zero Critical/Important findings.

## Important findings

### I-1 — Backup cleanup can still delete a directory after it has been relocated outside the repository

Publication now renames the old `architecture/` entry to a randomized backup and publishes staging relative to the held repository-root descriptor (`.grok-stack/adaptive_grok/architecture_diagrams.py:346-384`). It then opens the backup directory and recursively unlinks `generated/*` and all authority entries through held directory descriptors (`architecture_diagrams.py:273-343`). Those descriptors pin inodes, not containment. If the backup is renamed outside after the open at line 323, cleanup continues deleting from the relocated external inode. The pathname identity check occurs only after those destructive operations.

Independent deterministic reproduction wrapped the production `os.listdir(fd)` boundary, moved `.architecture.<token>.old` to a sibling temporary root after `_discard_architecture_entry()` had opened it, and then allowed production cleanup to continue. The result was:

```text
outcome ArchitectureError:io
relocated_backup ['.architecture.<token>.old']
outside_files_after_cleanup []
original_file_count 7
published_context_changed True
```

Thus the command detected the race only after every file in the external backup had been removed and the new tree had been published. The committed relocation tests move the old `architecture/` before `_replace_generated()`; they do not relocate the backup during recursive cleanup (`tests/test_architecture_model.py:626-701`). This leaves the requested repository-contained diagram I/O boundary open.

Required remediation: do not recursively delete through a movable directory descriptor. Use a publication/recovery design that performs no destructive backup cleanup until containment is guaranteed at each mutation, or preserve the backup for explicit safe recovery. Add a regression that relocates the opened `.architecture.*.old` directory before its first child unlink and asserts zero external mutation.

### I-2 — Projection publication can overwrite concurrent target-owned authority and widen directory permissions

`write_generated()` hard-links the three authority files into a newly created mode-`0755` staging directory, checks identities only while staging them, closes the original authority descriptor, and later replaces the whole `architecture/` directory (`architecture_diagrams.py:447-533`). There is no root-relative authority identity/content or directory-metadata check at the publication boundary.

Independent reproduction atomically replaced `architecture/system.yaml` with concurrent target-owned bytes inside a wrapper immediately before the production `_replace_generated()` call. `write_generated()` returned success, but publication restored the stale hard-linked bytes and backup cleanup deleted the concurrent update. The same probe set the original directory to `0700`; the successful writer changed it to `0755`:

```text
writer_returned True
concurrent_update_lost True
architecture_mode_after 0o755
```

This lets a diagram-only command overwrite architecture authority and relax its filesystem permissions. It violates the target-owned marker/model/rules boundary and the fail-closed concurrent-mutation requirement.

Required remediation: avoid replacing the authority container, or condition publication on an atomic/otherwise non-racy authority identity plus metadata match and preserve its mode/ACL/xattrs. Add regressions for an atomic authority-file replacement immediately before publication and a restrictive `architecture/` mode; the command must fail without losing the update or preserve the metadata exactly.

### I-3 — Local queue-adapter resolution fails open at explicit bounds and common relative imports

The new provenance engine handles the committed direct adapters and ordinary-method negative controls, but `_local_queue_exports()` returns an empty set when its 32-module or depth-8 ceiling is reached (`.grok-stack/adaptive_grok/architecture_fitness.py:1048-1064`). Empty is treated as proven absence, so the fail-closed `except ArchitectureError` path in `_new_queue_sources()` is never reached (`architecture_fitness.py:1123-1152`). `_queue_adapter_names()` also silently skips relative imports (`architecture_fitness.py:1090-1108`).

Two independent exact base/head probes added only `@app.task` to a changed worker source. Both contained an exact local adapter that ultimately constructed a Celery app:

```text
relative_local_adapter background=not_applicable reason=no_background_signal overall=pass triggers=()
adapter_module_budget_exhaustion background=not_applicable reason=no_background_signal overall=pass triggers=()
```

The first used `project/jobs.py -> from .celery_app import app`; the second placed 32 bounded unresolved local imports before a valid `from project.jobs import app`. Both are valid UTF-8 Python and remain within the advertised bounds, yet applicable job behavior disappears from fitness and monotonic `new_queue` risk. Direct/multi-hop Celery, RQ, `getattr`, proven project-adapter positives and unrelated `.submit/.delay/.task` negatives do pass their committed tests.

Required remediation: reaching a module/depth bound or encountering unresolved local provenance must produce an explicit unsupported signal, not N/A. Resolve bounded relative package imports (or fail closed on them), preserve exact base/head subtraction, and add boundary tests at and beyond both ceilings plus relative re-export adapters.

### I-4 — File-wide queue provenance fabricates applicability for unrelated calls

Once any `queue_names` entry exists, `_queue_provenance()` records every non-queue-derived call and decorator in the file as an `unknown-provenance-*` signal (`architecture_fitness.py:1022-1044`). Exact subtraction therefore labels an unrelated new operation as a new queue merely because unchanged queue code is co-located in the same module.

An independent exact base/head probe kept an existing `rq.Queue` and a local `Form` unchanged, then added only `form.submit()`. Production output was:

```text
mixed_rq_local_call background=unsupported overall=fail triggers=('new_queue',)
```

The receiver is proven local, not queue-derived. The committed ordinary-method controls place no queue provenance in their files (`tests/test_architecture_fitness.py:658-712`), so they do not exercise this mixed-file boundary. This is a load-bearing availability/oracle error: it fabricates both mandatory fitness failure and monotonic queue risk for ordinary code.

Required remediation: bind unknown-operation fallback to the callable/receiver's transitive provenance, not merely a nonempty file-wide provenance set. Add mixed-file negative controls for generic calls, `.submit()`, `.delay()`, and local `.task` decorators alongside unchanged RQ, Celery, and proven local adapters; retain the existing positive exact-delta cases.

### I-5 — Legacy `not_configured` compatibility still depends on descriptor-relative metadata support

Adopted authority bytes correctly require secure no-follow reads, while stable legacy absence is supposed to remain compatible without those primitives. However, `active_architecture_binding()` unconditionally opens a directory descriptor and the initially absent branch unconditionally calls `os.stat("architecture", dir_fd=root_fd, follow_symlinks=False)` (`.grok-stack/adaptive_grok/receipts.py:49-77,230-239`). `NotImplementedError` is not converted or handled.

In an empty non-Git repository, with `O_NOFOLLOW=0` and descriptor-relative `os.stat` unavailable, the production binding raised raw `NotImplementedError: dir_fd unavailable` instead of returning `None`/`not_configured`. The committed compatibility test pre-creates an empty `architecture/` directory and therefore does not execute this missing-directory operation (`tests/test_verification_doctor.py:333-341`).

Required remediation: provide a repeated, identity-bound metadata fallback for clean absence on advertised legacy platforms, while continuing to require no-follow byte reads once any authority entry is observed. Add a clean no-directory test with `O_NOFOLLOW` and `stat(dir_fd=...)` unavailable.

## Confirmed closed boundaries

- **Architecture adoption:** exact and worktree marker deletion, malformed markers, merge/shallow deletion, and adoption digest/state binding all pass. `_ArchitectureState` still requires a canonical matching marker for model-bearing states; only the frozen or internally revalidated bootstrap can be absent.
- **Hostile local Git configuration:** `.grok-stack/adaptive_grok/architecture_diff.py` has the identical blob `c0f63200221edac2c0f31869659079b534ebbf4f` at both ends of this range. Its fixed executable/config overrides and bounded process runner remain unchanged; the exact-head hostile-fsmonitor test passes and prior external-diff/textconv/pager/hook probes remain applicable. No new Git execution path was introduced.
- **Named diagram boundaries:** ancestor/final symlinks, special/oversized generated files, replacement symlink, relocation of the old generated directory, relocation of the old architecture directory before publication, and compare/write swaps pass without following the tested outside target. I-1 and I-2 are later mutation windows not covered by those tests.
- **Supported-platform absence/no-follow behavior:** authority created during the first absence observation is detected on the POSIX descriptor path; a stable clean legacy tree remains `not_configured` with `O_NOFOLLOW=0`; an observed adopted marker, model, schema, contract, worktree artifact, or diagram still fails closed when no-follow is unavailable.
- **Queue collision controls:** unrelated `Form.submit`, `Timer.delay`, local `Pipeline.task`, and an unresolved nonexistent adapter remain N/A only in files without queue provenance; known direct and derived queue operations revoke N/A. I-3 covers silent provenance truncation and I-4 covers mixed-file false applicability.

## Verification evidence

```text
git rev-parse HEAD
11bc554a16d9092798543fa986da086708c165de

git diff --check aa445ad0b2b8a25d85de7629e54bd188a5c1086d..11bc554a16d9092798543fa986da086708c165de
PASS (no output)

git diff --name-only aa445ad0b2b8a25d85de7629e54bd188a5c1086d..11bc554a16d9092798543fa986da086708c165de -- trust-ci .github/workflows
PASS (no output)

Focused marker, Git, no-follow, queue, legacy-absence, symlink, relocation and diagram race tests
Ran 17 tests — OK

python3 -m unittest -q tests.test_architecture_model tests.test_architecture_fitness tests.test_change_receipts tests.test_verification_doctor
Ran 145 tests in 113.113s — OK
```

The green repository suite does not exercise the five adversarial cases above. This report is local review evidence only; it is not merge authority, a human approval, or the App-owned exact-SHA Trust CI check.
