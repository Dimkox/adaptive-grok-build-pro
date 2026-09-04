# M2-A final security review — BLOCKED

## Reviewed identity

- Verdict: **BLOCKED**
- Critical findings: **0**
- Important findings: **3**
- Reviewed head: `b995fae3f1c519355bd5b966c4f43249c559cb1e`
- Adoption base: `25bfbe59ea188d9687b20a9caad19e7db3d031f8`
- Review package: `.superpowers/sdd/2026-08-26-m2a-executable-architecture/review-25bfbe5..b995fae.diff`
- Scope check: the packaged/base-to-head file set contains no `trust-ci/**` or `.github/workflows/**` mutation. README and the typed design continue to identify local architecture output and receipts as preflight evidence, not merge authority.

PASS requires zero Critical/Important findings, so this candidate cannot pass.

## Important findings

### I-1 — Deleting the adoption marker disables the adopted architecture gate

`_architecture_adoption()` returns `None` for an absent marker without considering the model or the selected route base (`.grok-stack/adaptive_grok/receipts.py:44-49`). `active_architecture_binding()` immediately propagates that as an unconfigured repository (`receipts.py:82-85`). `_architecture_check()` then emits `skip/not_configured` and does not call base selection, model validation, drift, fitness, diagram checks, or architecture receipt binding (`.grok-stack/adaptive_grok/verification.py:51-63`).

An isolated repository probe committed a valid adopted marker/model/rules, then removed only `architecture/adoption.json`:

```text
before fail fail
after_marker_delete skip not_configured architecture is not configured
```

The pre-deletion failure was fixture drift and is immaterial; the security-relevant state transition is from an active check to `skip`. Removing marker plus both model files has the same bypass. This contradicts the frozen rule that post-adoption deletion/corruption fails closed (`docs/superpowers/specs/2026-08-26-m2-executable-architecture-design.md:135,165`) and permits new locally passing receipts without architecture fields.

Required remediation: determine legacy `not_configured` state from marker **and** both fixed model paths **and** the exact route-base adoption state before returning `None`. A present model with a missing marker, or a route base containing adopted architecture whose head/worktree removes the marker/model, must fail. Add marker-only and marker-plus-both-model deletion regressions for worktree, committed, merge, and shallow/exact-route-base cases.

### I-2 — Repository-local Git configuration can execute a program during analysis

The Git environment disables system/global configuration but leaves `.git/config` active (`.grok-stack/adaptive_grok/architecture_diff.py:141-153`). The fixed `-c` list does not neutralize `core.fsmonitor` (`architecture_diff.py:156-175`). Worktree analysis calls `git ls-files` and `git diff`, so a repository-local fsmonitor command runs before bounded output parsing can protect the caller.

An isolated probe configured `core.fsmonitor` to a local sentinel-producing executable and invoked the production `_git()` wrapper:

```text
['ls-files', '-s', '-z'] executed True
['diff', '--name-only', '-z', 'HEAD'] executed True
['ls-files', '--others', '--exclude-standard', '-z'] executed True
```

This violates the untrusted-input/no-command-selection invariant (`engineering/changes/20260826-m2-executable-architecture-015603/change-spec.yaml:74-79`) and means `grok_verify` or CLI `--worktree` can execute repository-selected code. The capped subprocess implementation and its output/timeout tests (`tests/test_architecture_fitness.py:918-950`) correctly bound the Git child after launch, but do not prevent this child-selected executable.

Required remediation: run Git under a configuration policy that cannot activate local executable integrations; at minimum force-disable `core.fsmonitor` (and audit other read-path executable/config hooks) after all repository configuration, while retaining the existing no-replace/no-textconv/no-ext-diff controls. Add a regression with hostile local config and assert no sentinel process executes for every Git operation used by exact and worktree modes.

### I-3 — Diagram generation follows an ancestor symlink and writes outside `--root`

The explicit diagram write path is assembled lexically and passed to the generic path writer (`.grok-stack/adaptive_grok/architecture_diagrams.py:133-139`). That writer creates the parent and temporary file by pathname and uses `os.replace()` without descriptor-relative no-follow validation (`.grok-stack/adaptive_grok/util.py:56-68`). The CLI exposes this path directly for `diagram` without `--check` (`scripts/grok_architecture.py:143-148`). `compare_generated()` also follows the same ancestor symlink while reading (`architecture_diagrams.py:118-130`).

An isolated probe made `<root>/architecture/generated` a symlink to an outside directory and called the production writer:

```text
reported ('architecture/generated/context.mmd', 'architecture/generated/container.mmd',
          'architecture/generated/deployment.mmd', 'architecture/generated/data-flow.mmd',
          'architecture/generated/trust-boundary.mmd')
outside_created ['container.mmd', 'context.mmd', 'data-flow.mmd',
                 'deployment.mmd', 'trust-boundary.mmd']
```

The command therefore reports repository-contained paths while replacing fixed filenames outside the selected root, contrary to the CLI containment claim (`docs/superpowers/specs/2026-08-26-m2-executable-architecture-design.md:157-161`). Running drift separately would later report a symlink, but the write command performs no such prerequisite and the write has already escaped.

Required remediation: open the repository and `architecture/generated` descriptor-relatively with `O_DIRECTORY|O_NOFOLLOW`, reject symlink/special ancestors, create/fsync/rename each temporary file within the validated directory descriptor, and fail on identity changes. Apply equivalent no-follow handling to `--check` reads. Add direct and CLI ancestor/final-symlink plus directory-swap regressions that assert no outside file is read or changed.

## Positive evidence and checks

- Strict canonical parsing, duplicate-key/ID rejection, Unicode/control/backslash path rejection, schema preflight, size/depth/node/count limits, descriptor-relative no-follow model/contract reads, and bounded drift traversal are present in `.grok-stack/adaptive_grok/architecture.py` and covered by focused adversarial tests.
- Exact commits are restricted to 40 lowercase hex characters and verified as commit objects; Git/stdout/stderr/time/aggregate artifact limits and process-group kill/reap logic are present. Finding I-2 is the remaining pre-execution configuration boundary.
- Fitness emits all 12 mandatory categories, treats applicable `unsupported` as failure, binds applicability inventories, and computes `risk_post=max(pre_risk, escalation)` in `.grok-stack/adaptive_grok/architecture_fitness.py:1298-1379`.
- Secret/trust material is represented as classes rather than values; the reviewed M2-A diff adds no runtime service, deployment, database/queue mutation, external write, human approval material, GitHub Actions, or `trust-ci/**` source change.
- Installer tests confirm target-owned `architecture/adoption.json`, `architecture/system.yaml`, and `architecture/rules.yaml` are not copied or overwritten, including `--force`.

## Verification evidence

```text
git rev-parse HEAD
b995fae3f1c519355bd5b966c4f43249c559cb1e

git diff --check 25bfbe59ea188d9687b20a9caad19e7db3d031f8..b995fae3f1c519355bd5b966c4f43249c559cb1e
PASS (no output)

git diff --name-only 25bfbe59ea188d9687b20a9caad19e7db3d031f8..HEAD -- trust-ci .github/workflows
PASS (no output)

python3 -m unittest -v tests.test_architecture_model tests.test_architecture_fitness \
  tests.test_change_receipts tests.test_verification_doctor tests.test_installer \
  tests.test_manifest_package tests.test_structure
Ran 167 tests in 87.613s — OK

python3 scripts/grok_architecture.py --root . validate --json
ok=true

python3 scripts/grok_architecture.py --root . diagram --check --json
ok=true; mismatches=[]

python3 scripts/grok_architecture.py --root . drift --json
ok=true; findings=[]

python3 scripts/grok_architecture.py --root . fitness \
  --base 25bfbe59ea188d9687b20a9caad19e7db3d031f8 \
  --head b995fae3f1c519355bd5b966c4f43249c559cb1e \
  --pre-risk red --json
fitness_status=pass; risk_post=red; fitness_results=12
```

The passing stock suite and exact fitness output do not cover or negate I-1 through I-3. This is local review evidence only; it is not the App-owned exact-SHA Trust CI check and grants no approval, merge, release, or deployment authority.
