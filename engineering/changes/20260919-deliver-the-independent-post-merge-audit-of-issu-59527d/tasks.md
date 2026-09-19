# Tasks — durable delivery of the #104 post-merge audit

- [x] Freeze scope: documentation-only; no product, contract, rules, schema or governance change (INV-002).
- [x] Characterization before writing: re-measure the verdict tables on the declared inventory from a pristine
      `d871ea6` tree (both units: 38 declared `json_schema` records, 50 declared records of all kinds), and label the
      two truncated-inventory tables and the probe-polluted table as superseded.
- [x] Collect the five analysis reports and the controller tables into this package's `evidence/`, naming which lane
      route `59527d5a28f8` selected and which one came from route `4c524b83df59`.
- [x] Recover the six orphan `mistakes.md` entries by insertion at chronological position; verify zero deleted lines.
- [x] Append this wave's two lesson entries (stale-route duplicate wave; truncated-inventory false `unsupported`).
- [x] Scrub machine-local paths from every committed evidence file (AC-005).
- [x] Fill the typed `change-spec.yaml` and validate it in draft and gate mode (`ok: true`).
- [x] Add `analysis-architect.md` (the soundness lane) after its return, scrubbed, and carry its finding into the
      record as residual CAR-5 plus issue #147 - this is the lane that refuted the controller's own "no false
      certification" claim, so the correction is committed alongside the claim it replaces.
- [x] Independent review of the delivered record found two impossible numbers, one wrong edit-class cell, a
      self-contradicting test predicate, two colliding identifier lists and an unlabelled refutation. Re-derive every
      number in a separate process per tree, correct the tables, commit `evidence/measurement-harness.md` with the
      commands and their printed output, rename the controller's residuals to CAR-1 … CAR-5 with a mapping table,
      annotate (never rewrite) the two agent passages the corrections contradict, and fix `test-plan.md` so its
      predicate asks for what the record now says.
- [ ] Run the selected quality profile: `GROK_VERIFY_CAPABILITY=repository-sandbox UV_LOCKED=1 python3 scripts/grok_verify.py --mode pr`.
- [ ] Complete independent reviews (route-selected: code review for a docs wave) and bind receipts to the final tree fingerprint.
- [ ] Commit, push the branch, open the pull request; wait for the App-owned exact-SHA check (merge is a separate,
      explicitly delegated action).
