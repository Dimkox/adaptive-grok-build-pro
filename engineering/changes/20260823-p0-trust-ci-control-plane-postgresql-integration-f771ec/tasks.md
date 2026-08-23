# Tasks — Trust CI activation

- [x] Read AGENTS.md, GROK_BUILD_HANDOFF.md, design, plan, runbook.
- [x] Fast-forward `feat/trust-ci-control-plane` and confirm no GitHub Actions workflows.
- [x] Reproduce local baseline on HEAD `04348db`.
- [x] Repair baseline regressions (structure tests, runner mutation constructor, backup tamper test, holdout digest, draft webhooks, live PostgreSQL harness).
- [x] Run live PostgreSQL integration (8/8) and restart drill (PASS).
- [x] Resume crashed README/QUICKSTART/toolchain pass: K16 graph, two-file compose docs, optional docker/syft/trivy/cosign pins.
- [x] Local image build-without-push smoke (this slice): `/tmp` env-file, two-file compose build api/worker/runner-image, inspect Ids (not a pin), example holdout unittest, evidence only. No product-file digest, no `up`, no push.
- [x] Docker-push already-built `:2.1.0` images to `ghcr.io/dimkox/adaptive-trust-ci-{api,worker,runner}` and record host-bearing RepoDigests in untracked env only (no digest in git).
- [ ] Build and pin immutable images and holdout digest (operational; remaining after GHCR push: deployed policy/env, holdout bundle, cosign).
- [ ] Create/install GitHub App (worker-only key, API-only webhook secret).
- [ ] Deploy isolated API/worker/postgres/holdout/TLS intake.
- [ ] Prove webhook → App-owned check on PR #2.
- [ ] Apply app-bound branch protection only after that check exists.
- [ ] Commit, update draft PR #2, record independent reviews.
