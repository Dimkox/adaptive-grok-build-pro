# Tasks — Trust CI activation

- [x] Read AGENTS.md, GROK_BUILD_HANDOFF.md, design, plan, runbook.
- [x] Fast-forward `feat/trust-ci-control-plane` and confirm no GitHub Actions workflows.
- [x] Reproduce local baseline on HEAD `04348db`.
- [x] Repair baseline regressions (structure tests, runner mutation constructor, backup tamper test, holdout digest, draft webhooks, live PostgreSQL harness).
- [x] Run live PostgreSQL integration (8/8) and restart drill (PASS).
- [ ] Build and pin immutable images and holdout digest.
- [ ] Create/install GitHub App (worker-only key, API-only webhook secret).
- [ ] Deploy isolated API/worker/postgres/holdout/TLS intake.
- [ ] Prove webhook → App-owned check on PR #2.
- [ ] Apply app-bound branch protection only after that check exists.
- [ ] Commit, update draft PR #2, record independent reviews.
