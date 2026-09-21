# CR-165-01 / T165-1 repair plan

Read-only investigation at HEAD `21046dff16a1b927d5a781ae0ec61708ebed89bc` confirms the independent reviews' boundary finding. `collect_worktree()` preserves raw POSIX filename bytes as surrogate-bearing strings, while the new lifecycle copies those strings into canonical state. The existing strict UTF-8 serializer cannot write them, and the strict canonical parser would reject escaped surrogates on readback. The failed initial creation leaves the rendered template file, so pathname existence does not establish successful canonical creation.

The original failed reviews and their independently measured probe remain preserved by the coordinator. The earlier 25-test focused PASS and component results of the failed full run remain historical evidence; they do not cover this newly reproduced persistence case.

## Shipped regressions, execution pending

Three new methods in `tests/test_package_status.py` exercise:

1. Actual lifecycle CLI creation with a raw-byte branch and dirty filenames, raw-byte distinctions, literal escape/hex/object-looking names, replacement-character and valid Unicode names, strict state readback, repeated start, and actual status CLI reload while those names still exist.
2. Actual first-implementation CLI persistence, unchanged initial HEAD/history, strict inspection, blocked/resumed implementation without duplicate checkpoints, and repeated lifecycle/status reload.
3. A path set below the existing Git count/output caps whose hexadecimal representation would exceed the canonical state reader's byte limit. Both lifecycle observations must persist explicit unknown dirty state, retain actual HEAD/route base, and never report a clean or zero-ahead success.

Requested measured RED command, before product repair:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_package_status -k raw_byte -v
```

Expected cost at preparation: 3–6 seconds, with a 60-second cap. The coordinator owns CPU allocation. New logs use lossless JSON envelopes rather than whitespace-bearing raw logs.

## Bounded representation proposed for the measured repair

Ordinary UTF-8 names remain strings. Non-UTF-8 filesystem names become explicit records with exactly `encoding=hex` and `value` containing the original bytes as lowercase hexadecimal. A string that happens to look like an encoded record remains a string, preventing identity collisions. Apply this representation to observed paths and branch names before lifecycle serialization, with a bounded per-name and aggregate representation budget; an exceeded budget leaves the dirty observation unknown with an explicit diagnostic.

Do not change the strict canonical parser, generic JSON utility, route/receipt authority fields, or merge another issue's implementation. Existing receipt validation stays authoritative. If the focused status test exposes a legacy receipt-fingerprint Unicode failure, represent that validation as explicitly unavailable at the observational CLI boundary rather than changing its fingerprint or claiming a passing result.

Suggested root-cause learning for the coordinator: filename collection and durable persistence are different contracts. NUL-safe collection and Unicode-only fixtures missed the strict serializer/parser boundary; persistence regressions must include raw bytes, literal lookalikes, and the encoded representation's size budget.

## Measured RED and current repair

The coordinator allocated the three-test RED after the batch full verifier finished. The exact command above exited **1** with **three assertion failures and no errors**: unittest elapsed **1.879 s**, measured process wall elapsed **2.0907751969934907 s**. All failures capture actual lifecycle CLI `UnicodeEncodeError` from the existing strict UTF-8 writer: first implementation, initial creation with the deep/raw path set, and initial creation with the raw branch/name collision controls. Complete lossless output is [review-repair-red.log.json](review-repair-red.log.json), raw SHA-256 `93eb3fa3d930a847c5258f25b228029b9ee47190ea3dac9427f4dfcf42beb756`. The CPU lane was released immediately after recording that result.

After RED, the sole writer changed only the bounded observation module: valid UTF-8 names remain strings; other byte names become `{"encoding":"hex","value":"..."}` records. The same conversion covers observed branch names. The path set retains raw-byte identities for deduplication and sorting before conversion, and caps the ASCII JSON representation plus formatting reserve at 32 KiB; an exceeded budget produces `git_path_representation_limit` and unknown dirty state. Each observed name is capped at 4096 input bytes. The canonical parser, generic serializer, receipt validator, authority fields, and lifecycle machinery are unchanged.

GREEN is pending the next allocated slot. No post-repair tests, compilation, lint, or broad verification have run. In particular, no speculative receipt/status change was made: the actual status reload regression will establish whether another bounded diagnostic is needed.
