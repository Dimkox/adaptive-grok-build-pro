# Tasks — durable delivery of the #104 post-merge audit

- [x] Freeze scope: documentation-only; no product, contract, rules, schema or governance change (INV-002).
- [x] Characterization before writing: re-measure the verdict tables on the declared 50-record inventory from a
      pristine `d871ea6` tree, and label the two truncated-inventory tables and the probe-polluted table as superseded.
- [x] Collect the route-selected analysis reports and the controller tables into this package's `evidence/`.
- [x] Recover the six orphan `mistakes.md` entries by insertion at chronological position; verify zero deleted lines.
- [x] Append this wave's two lesson entries (stale-route duplicate wave; truncated-inventory false `unsupported`).
- [x] Scrub machine-local paths from every committed evidence file (AC-005).
- [x] Fill the typed `change-spec.yaml` and validate it in draft and gate mode (`ok: true`).
- [x] Add `analysis-architect.md` (the soundness lane) after its return, scrubbed, and carry its finding into the
      record as residual R5 plus issue #147 - this is the lane that refuted the controller's own "no false
      certification" claim, so the correction is committed alongside the claim it replaces.
- [ ] Run the selected quality profile: `GROK_VERIFY_CAPABILITY=repository-sandbox UV_LOCKED=1 python3 scripts/grok_verify.py --mode pr`.
- [ ] Complete independent reviews (route-selected: code review for a docs wave) and bind receipts to the final tree fingerprint.
- [ ] Commit, push the branch, open the pull request; wait for the App-owned exact-SHA check (merge is a separate,
      explicitly delegated action).
