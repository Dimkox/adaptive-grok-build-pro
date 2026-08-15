# Test plan

Installer tests: required runner called; no-deps skips; optional only with all_deps.
HTTP(S) install strings: action `manual-url`, runner never invoked (case-insensitive scheme).
Dry-run: action `would-install`, runner never invoked.
Older copy-only installer tests inject a no-op runner so host apt/sudo cannot run.
