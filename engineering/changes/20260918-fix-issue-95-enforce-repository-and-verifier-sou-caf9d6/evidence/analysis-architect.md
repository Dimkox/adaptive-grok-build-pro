# Architecture analysis — issue #95

## Finding

`scripts/grok_verify.py` binds its implementation package to the script checkout but binds the target repository independently to the process working directory:

- `ROOT = Path(__file__).resolve().parents[1]` and `sys.path.insert(0, str(ROOT / '.grok-stack'))` at lines 6–7 select the verifier implementation.
- `verify(find_root(), ...)` at line 21 selects the tree to inspect. `find_root()` starts from `Path.cwd()` by default (`.grok-stack/adaptive_grok/util.py:21-39`), choosing the first ancestor with `.grok-stack`, then falling back to Git top-level.

This allows a copied or absolute-path invocation of a verifier from checkout A while cwd is checkout B: implementation/policy code comes from A, but route, changed files, architecture and receipts are read/written under B. A copied verifier outside any checkout can similarly resolve an unrelated cwd repository. This is an identity split, not just an inconvenient default.

## Constraints and invocation compatibility

- The documented and repository-wide CI entrypoint is `python3 scripts/grok_verify.py --mode pr` from the checkout being verified (`.grok-stack/templates/ci/README.md:12-15`; release/test records also use this form). This normal invocation must continue to work.
- The `scripts/` entrypoint is not an installed console wrapper in the current source: there is no `scripts/grok` file. `scripts/grok_verify.py` itself is the wrapper and uses its own source directory to import `.grok-stack`.
- Other script entrypoints also combine `ROOT = Path(__file__).resolve().parents[1]` with `find_root()` inconsistently; keep #95 bounded to `grok_verify` unless the issue explicitly broadens scope. Do not alter global `find_root()` semantics, which are shared across many CLIs and test-runner invocation contexts.
- No GitHub Actions may be added. CI must call the checked-out repository’s script as before; a new environment variable or flag should not be required in standard CI.

## Minimal bounded design recommendation

Make the verifier entrypoint fail closed unless the script source checkout and target repository are the same resolved worktree root. Derive source root from `Path(__file__).resolve()` (as now), derive invocation root from cwd/Git as today (or an explicit, documented `--root` only if existing caller requirements demand it), canonicalize both, and compare before invoking `verify()` or writing any receipts. If roots differ, emit an actionable diagnostic naming the two roots and exit nonzero before verification side effects. This preserves ordinary local/CI invocation while rejecting external script copies and split-source execution.

Do not silently make script-root win over cwd: that can verify a different checkout than the caller intended, and the verifier is explicitly an operator entrypoint for the working tree. Do not compare only Git common-dir: linked worktrees share common Git metadata but have distinct working trees, routes, and uncommitted diffs; identity must be exact resolved worktree root. Do not accept matching HEAD SHA alone: separate worktrees may have same commit and different modified/untracked files.

A cross-worktree regression should create two temporary checkouts/roots with distinct sentinel route or tracked content, invoke A's absolute script path with cwd B, assert nonzero identity diagnostic, and assert B receives no verification receipt or other mutation. Also assert normal invocation within one checkout still dispatches verification. This tests the boundary without requiring GitHub/network CI.

## Security and compatibility limitations

Resolved-path equality protects against accidental and ordinary copied-script mismatch but is not a cryptographic verifier-source attestation: a caller who can modify the script and implementation in the same checkout can still run modified verifier code. The issue’s requested property is repository/source-root consistency; stronger source signing would be a separate trust-model feature. Symlinked `scripts/grok_verify.py` resolves to the target source checkout; this is desirable for identity comparison and matches current `ROOT` import behavior. Avoid resolving only cwd when it is a file: `find_root` already handles that behavior, and the CLI runs with cwd directories in documented usage.

## Evidence inspected

- `scripts/grok_verify.py` lines 1–21.
- `.grok-stack/adaptive_grok/util.py` lines 21–39 (`find_root`).
- `.grok-stack/templates/ci/README.md` lines 12–15.
- `AGENTS.md`: PR-only delivery, no GitHub Actions, local `grok_verify --mode pr` preflight and exact external Trust CI merge authority.
