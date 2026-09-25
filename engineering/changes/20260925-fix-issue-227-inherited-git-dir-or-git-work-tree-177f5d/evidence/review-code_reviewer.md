# Independent code review — issue #227

## Review binding

- Base SHA: `cb9af4073ba6c3d515145164d771c75ebdfa3224`
- Head SHA: `5f4e8fef003271a9b62198d181ad6be1f1838158`
- Head tree: `eb0e0f649e0e17d55f93be8ab46b859e436d56f7`
- Reviewed diff: `cb9af4073ba6c3d515145164d771c75ebdfa3224..5f4e8fef003271a9b62198d181ad6be1f1838158`
- Scope: implementation and tests for issue #227, checked against the durable plan, requirements, architecture, test plan, and typed change specification.

## Findings

### Critical

None.

### Important

None.

### Minor

None.

## Evidence reviewed

- `.grok-stack/adaptive_grok/util.py:16-23` defines one copied-environment helper and removes `GIT_DIR` and `GIT_WORK_TREE` by key presence. The root discovery probe at `util.py:38-44`, text probe at `util.py:133-150`, binary path probe at `util.py:182-195`, and binary name/status probe at `util.py:198-240` all receive that sanitized environment. The public generic `run(...)` behavior remains unchanged.
- `.grok-stack/adaptive_grok/_policy_legacy.py:593-606` checks selector key presence for both branch and tag pushes and returns a bounded names-only denial. The human-gate and grant calls follow at `_policy_legacy.py:607-611`, so no grant or gate is consulted on this denial path.
- `tests/test_util_fingerprint.py:141-196` compares root discovery, top-level, repository identity, HEAD, changed files, status records, and tree fingerprint against clean-environment results for `GIT_DIR`, `GIT_WORK_TREE`, and both together.
- `tests/test_policy.py:68-104` verifies approval bindings remain rooted in the explicit repository under foreign selectors. `tests/test_policy.py:106-145` exercises the same-tree foreign-`pushurl` bypass without executing push and checks value/URL non-disclosure. `tests/test_policy.py:147-192` covers branch/tag actions, each selector independently, both selectors, empty-string presence, and clean-environment compatibility.
- `tests/test_hooks.py:168-233` exercises the real pre-tool hook, confirms the deny result and names-only reason, verifies the denial ledger stays under root A, and proves both local repositories remain unchanged.
- Surrounding grant logic at `.grok-stack/adaptive_grok/state.py:173-178` and `state.py:268-325` continues to bind repository, route, change, HEAD, tree digest, action, and expiry through the unchanged schema-v2 boolean interface.

## Verification performed

- `python3 -m unittest tests.test_policy` — PASS, 27 tests.
- `python3 -m unittest tests.test_hooks` — PASS, 33 tests.
- `python3 -m unittest tests.test_util_fingerprint` — PASS, 20 tests.
- `python3 -m unittest tests.test_structure tests.test_change_receipts` — PASS, 49 tests.
- `git diff --check cb9af4073ba6c3d515145164d771c75ebdfa3224..5f4e8fef003271a9b62198d181ad6be1f1838158` — PASS.
- Independent mock probe with empty `GIT_DIR` made both `gate_block_reason` and `has_valid_approval` raise if reached; policy denied successfully without invoking either lookup.

No `git push`, network access, external write, Daybreak operation, commit, or source-file mutation was performed during this review.

## Verdict

**PASS** — the exact reviewed head implements the required root-bound probe environment and early fail-closed branch/tag push denial, preserves clean-environment behavior, and has no Critical, Important, or Minor code-review findings.
