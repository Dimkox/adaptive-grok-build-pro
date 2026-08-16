# Architecture

Source of truth: local `grok_verify`. Never GitHub Actions.

1. Delete workflow + dependabot.
2. Template README: never GHA; `make verify` / `grok_verify --mode pr` only.
3. `--with-ci` → SystemExit, no copy.
4. Keep VERSION 2.0.6 (unpublished). Rebuild zip. Then tag that commit.
