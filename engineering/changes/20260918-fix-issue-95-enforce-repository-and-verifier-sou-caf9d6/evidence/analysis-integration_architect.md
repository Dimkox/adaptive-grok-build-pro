# Integration analysis — issue #95

## Reproduced boundary

`scripts/grok_verify.py` first computes its source checkout as `Path(__file__).resolve().parents[1]` and prepends that checkout's `.grok-stack` directory to `sys.path`. It then calls `find_root()` without an argument. `find_root()` starts from the process working directory, searches upward for `.grok-stack`, and only then falls back to `git rev-parse --show-toplevel`. Therefore `python /checkout-A/scripts/grok_verify.py --mode pr` launched with cwd inside checkout B imports `adaptive_grok` from A while `verify()` reads and, unless `--no-record` is set, records evidence against B. The CLI currently neither compares these roots nor offers an explicit root contract.

The same pattern appears in other script entrypoints, but issue #95 is specifically the verification command and its evidence. A mismatched verifier is material even with `--no-record`: all checks and the resulting report describe B while executing A's verification policy and implementation. With recording enabled it can also persist a receipt in B. The risk applies to arbitrary external script copies as well as a second local worktree.

## Installer and caller compatibility

`scripts/install_into.py` includes both `scripts/grok_verify.py` and `.grok-stack` in its managed payload. Thus a properly materialized target has its own verifier and Python package, and the documented invocation from that target (`python3 scripts/grok_verify.py --mode pr`) satisfies a strict same-root rule. The installer does not need to create a cross-root launcher or rely on the source checkout at runtime.

Repository examples and workflow code invoke the relative `scripts/grok_verify.py` from the checkout being verified. Those callers also satisfy same-root identity. Any external automation that intentionally invokes an absolute verifier path from another checkout would be rejected; it can use the target checkout's own script instead. Before changing behavior, check the full caller inventory for any deliberate source-A/target-B verifier use, but do not preserve that ambiguity as an implicit mode.

## Enforceable contract

At the CLI boundary, resolve the verifier source root from `__file__` and the selected repository root from the normal `find_root()` behavior, canonicalize both, and require equality before invoking `verify()` or performing any receipt/runtime writes. On mismatch, print both resolved paths, explain that the target checkout's own `scripts/grok_verify.py` must be used, and exit nonzero. Do not attempt to import target code after importing source code, or silently switch roots: Python imports have already established which verifier implementation is active. Keep root discovery based on cwd/Git for same-root invocations; the identity check closes the dangerous split-source case without inventing a new target-root override.

If product requirements later demand an explicit root option, it must not relax verifier-source identity: the explicit target root must still resolve to the source checkout. An option that intentionally authorizes foreign verifier code against another tree would restore the defect and make the report/receipt's implementation provenance ambiguous.

## Regression coverage

Use two isolated checkout roots (or equivalent roots with `.grok-stack` markers), invoke A's verifier by absolute path with cwd B, and assert a nonzero identity failure before any verification checks, runtime directory/receipt creation, or target-tree mutation. Also invoke the verifier with cwd A and assert normal same-root dispatch still occurs. The mismatch test should cover recording enabled, since that is the path that can write a false local receipt; a subprocess-level test is preferable to a unit test of `find_root()` alone because it exercises Python's source `sys.path` and the CLI's target selection together.

## Limits

This check proves that the CLI source root and the selected checkout root are the same canonical filesystem tree at startup. It does not authenticate the checkout, prove its code is trustworthy, detect later source changes by another process, or replace external Trust CI. Symlink aliases that resolve to the same physical root are equivalent; distinct Git worktrees are distinct roots even when they share Git object storage, which is the intended fail-closed behavior for source/evidence identity.
