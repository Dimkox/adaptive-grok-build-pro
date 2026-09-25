# Security review — issue #227 inherited Git repository selectors

## Verdict

**PASS** for exact base `cb9af4073ba6c3d515145164d771c75ebdfa3224` through exact HEAD `5f4e8fef003271a9b62198d181ad6be1f1838158` (HEAD tree `eb0e0f649e0e17d55f93be8ab46b859e436d56f7`).

The reviewed change closes the scoped inherited-`GIT_DIR`/`GIT_WORK_TREE` authorization split with two independent controls: repository identity and fingerprint probes ignore the selectors, while branch and tag push policy denies selector **key presence** before consulting a local human gate or delegated grant. The denial is secret-safe and the focused offline regression suite passes. No push, remote access, grant creation in the candidate worktree, or external write was performed by this review.

## Findings

### Critical

None.

### Important

None.

### Minor

None.

## Security boundary and abuse-case evidence

### Independent controls

- `.grok-stack/adaptive_grok/util.py:16-23` defines one closed selector set and constructs a copied environment with both keys removed by presence.
- `.grok-stack/adaptive_grok/util.py:38-44`, `133-145`, `182-205` applies that environment independently to root discovery, textual Git output, binary `-z` path inventory, and name-status inventory. Consequently repository identity (`.grok-stack/adaptive_grok/state.py:173-178`), HEAD, changed files/statuses, and the tree binding (`.grok-stack/adaptive_grok/util.py:243-368`) remain rooted at the explicit `cwd`.
- `.grok-stack/adaptive_grok/_policy_legacy.py:589-606` independently denies both `git-push-branch` and `git-push-tag` when either selector key is present. Probe sanitization therefore cannot create a split-brain allow for an eventual environment-inheriting push.

### Presence, ordering, and coverage

- The policy uses `name in os.environ`, not value truthiness (`.grok-stack/adaptive_grok/_policy_legacy.py:593-596`), so empty values deny.
- The selector denial precedes both `gate_block_reason(...)` and `has_valid_approval(...)` (`.grok-stack/adaptive_grok/_policy_legacy.py:607-612`). An independent probe replaced each of those functions with an exception and obtained 12 denials across branch push, version-tag push, explicit tag-ref push, `--tags`, individual selector keys, both keys, and empty values. Neither replacement was reached.
- Branch/tag classification is shared through `production_action` (`.grok-stack/adaptive_grok/_policy_legacy.py:268-286`). Existing command-local selector, `git -C`, nested-shell, executable-path, and wrapper variants remain covered by the conservative root/authority parser (`.grok/hooks/_lib.py:176-302`) and the nearby hook regressions (`tests/test_hooks.py:340-400`).
- The clean-environment allow arm and per-key/empty/tag denials are explicit at `tests/test_policy.py:147-192`. The matching foreign checkout/push-destination abuse case is exercised without execution at `tests/test_policy.py:43-64,106-145`, and grant creation/validation remains rooted at A at `tests/test_policy.py:68-104`.

### Disclosure and hook boundary

- The denial constructs output from selector names only and never interpolates environment values (`.grok-stack/adaptive_grok/_policy_legacy.py:594-605`).
- The hook records generic action labels plus hashes, not inherited environment values (`.grok/hooks/pre_tool_use.py:67-76,156-190`). Its integration test confirms denial output and ledger placement without selector-value, target-path, or push-destination disclosure (`tests/test_hooks.py:168-233`).
- Hook root discovery is also selector-sanitized through `find_root`, so inherited selectors cannot redirect the denial ledger into the foreign repository (`.grok/hooks/_lib.py:93-95`; `tests/test_hooks.py:230-233`).

## Verification performed

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_policy tests.test_hooks tests.test_util_fingerprint
Ran 80 tests in 44.433s
OK

independent early-denial probe (gate/grant replaced with exceptions)
12 branch/tag/single/both/empty/name-only cases
PASS

git diff --check cb9af4073ba6c3d515145164d771c75ebdfa3224..5f4e8fef003271a9b62198d181ad6be1f1838158
exit 0; no output
```

The regression fixtures use disposable local repositories and read-only Git inspection. Review of the executed paths found no `git push`, fetch, socket, HTTP, GitHub, Daybreak, merge, release, or deployment operation.

## Residual risk and authority separation

- A push destination changed in the intended repository's own configuration, and inherited Git/config selectors other than the two scoped keys, remain outside this issue. The change package explicitly bounds that residual; it should remain a follow-up rather than be described as solved by this patch.
- The pre-tool hook remains a local soft/fail-open workflow control (`.grok/hooks/pre_tool_use.py:229-237,304-312`). This PASS establishes the scoped local grant-boundary repair, not a general OS enforcement boundary.
- Local scope/design gates, delegated grants, verification receipts, and this review are workflow evidence only. They neither create nor replace the GitHub App-owned exact-SHA `adaptive-trust-ci/verified@<policy-sha12>` check, deployed policy/holdout validation, branch protection, or any human-signed external approval required by Trust CI.

reviewed-source-modified: no
