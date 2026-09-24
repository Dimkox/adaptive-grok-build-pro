# Repository exploration: issue #36 owner mapping

## Scope and exact source

- Audited `origin/main` after `git fetch --all --prune`.
- Exact commit: `130ce4a42d9f9bbd1b56772d40b19ae530283205`; tree: `3b51c9d21550627bb35fdb06753d2bedd5cf97ff`.
- The requested local branch `fix/issue-36-recorder-status-20260922` points at the same commit and has no commits ahead (`git diff --stat origin/main...fix/issue-36-recorder-status-20260922` is empty).

This report is intentionally historical/base analysis of the implementation
tree. The candidate evidence package identity is recorded separately in
owner-mapping.md and the review reports; no candidate product change is implied
by this base-tree search.

## Current-tree audit

Commands used:

```text
git ls-tree -r --name-only origin/main
git grep -n -E 'if !|\$\?|exit_code|exit status|status_file|status.*file|write.*status' origin/main -- 'scripts/**' 'trust-ci/**' '*.sh' 'tests/**' 'delivery/**'
git grep -n -i -E 'issue.?36|#36|issue.?186|#186' origin/main
```

The tracked shell files are limited to runtime/install and Trust CI operational scripts. None contains the reported `if ! cmd; then code=$?` recorder pattern or a shell exit-status file writer. `scripts/grok_verify.py` has no shell recorder owner; its command execution is Python-side. Trust CI records command results as Python model data (`trust-ci/src/adaptive_trust_ci/models.py`, `runner.py`, `sandbox.py`), not through the reported shell construct. Existing `exit_code` schema/model fields are not the issue #36 shell recorder.

## Reachable-history audit

Commands used:

```text
git log --all --oneline -G 'if !.*cmd|code=\$\?|exit[_ -]status.*(file|record)|record.*exit'
git log --all --oneline -S'if ! ' -- scripts trust-ci factory tests
git log --all --oneline -S'code=$?' -- scripts trust-ci factory tests
git log --all --name-only --pretty='COMMIT %H %s' -- 'scripts/*.py' 'scripts/*.sh' 'trust-ci/**/*.sh' 'trust-ci/**/*.py'
```

No reachable product/script/test history introduces the exact recorder seam. Historical commit `ff733ded6bd1a0b33996ff9a152f1621bfafb55b` (`docs: bound external issue closure scope`) explicitly records that “#36 remains external/unowned” and links it through #186; it is disposition evidence, not an implementation. Historical Trust CI exit-status work (`800802a0…`, “record an externally killed command as an abort”) is Python Trust CI process handling and does not own the reported shell recorder.

## Safe shell reproduction

Command:

```bash
bash -c 'set +e; if ! bash -c "exit 7"; then code=$?; printf "if-not status=%s\\n" "$code"; fi; bash -c "exit 7"; code=$?; printf "direct capture status=%s\\n" "$code"; if bash -c "exit 7"; then :; else code=$?; printf "else capture status=%s\\n" "$code"; fi'
```

Observed output:

```text
if-not status=0
direct capture status=7
else capture status=7
```

This confirms the bug mechanism: inside the `then` body of `if ! cmd`, `$?` reports the successful negation (`0`), not `cmd`’s original failure (`7`). Capturing immediately after the command, or in the `else` branch without negation, preserves the status.

## Recommendation

No live repository-owned owner exists for issue #36 in the exact current `origin/main` tree or reachable product history. Do not add speculative code or a regression test to this repository. Keep #36 as an explicit external-owner/no-owner disposition linked through #186, with the shell reproduction above as binding evidence; pursue implementation only after the external source/owner is identified.
