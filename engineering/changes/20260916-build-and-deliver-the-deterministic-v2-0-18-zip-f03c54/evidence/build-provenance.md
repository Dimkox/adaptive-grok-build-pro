# Build provenance — v2.0.18 ZIP+sidecar

- Source: two independent `git clone`s of the local mirror, each checked out detached at
  `fc8d9e6f11bb188ee514784d3b6f614a6da72803` (tree `65d3a996018bf7564866c25b6b869c2493c9e15e`, both clean),
  inside private `0700` staging.
- Command per clone: `python3 scripts/package_stack.py --output <staging>/z-<n>.zip`.
- Result: `z-c1.zip` and `z-c2.zip` `cmp`-identical, SHA-256
  `0bc6adc9f4660e1b60be4cb4895e97f2641338b52b6a5e05ac3c7acd85e59b3a`, 11,160,330 bytes; the sidecar was
  written as `'<sha>  adaptive-grok-build-pro-v2.0.18.zip\n'` (102 B) and its own digest recorded as
  `dd7e2ec5a979d70062f206f381efcb38b92da2f7bfc1129034b459e125a54216`.
- Copy into `packages/` preserved bytes (tracked blob digest equals the build digest; re-verified by both
  route reviewers, who independently rebuilt and matched a third time).
- Falsification arms observed during review: dirty worktree build refused (`tracked HEAD source changed`),
  child-tip and one-byte-edit builds produce different digests — the archive is tree-bound, INV-002.
- Staging dirs and clones were removed after the copy; no secrets or env content ever entered any path here.
