# Stream cleanup: stop the child on every path (#109)

> Typed authority: [`change-spec.yaml`](change-spec.yaml).

#101's `_stream_git_blob` closed pipes but stopped the git child only for two exception classes; anything else (selector setup on an unsupported platform, an unnamed error) propagated raw and left `git cat-file` running on a nobody-waits pipe — reproduced by the issue probe and now by a red-then-green test using a real sleep child. The sibling `_run_capped` typed the same setup; this makes the stream match. The `_profile_worktree_blob` finally could leak the directory fd behind a failing first close; nested guard fixes the order. The issue's own text carried one false claim (platform dispatch) — corrected publicly, not quietly.
