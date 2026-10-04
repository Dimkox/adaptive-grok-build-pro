# Architecture

Paperwork-only. Path-limited `git add` of keepers + `rm -rf` of abandoned untracked dirs. If a DELETE package has tracked files, leave the tracked HEAD copy; only remove untracked extras or the whole untracked dir.

Controller pushes after verify/reviews. Fresh `grok_approve production`.
