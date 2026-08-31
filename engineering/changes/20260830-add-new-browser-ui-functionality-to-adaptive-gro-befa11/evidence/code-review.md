# Code review — investor-ready local product MVP

## Verdict

**PASS**

No Critical or Important correctness, security, maintainability, packaging, API/client, or investor-truthfulness issue remains in the reviewed local-demo scope.

## Inspected identity and diff state

- Route: `befa117340b9`; selected role: `code_reviewer`; approved base: `2cf89e40e5c3f33cddf87eecd7956ecf4a201df3`.
- Git HEAD at review: `2cf89e40e5c3f33cddf87eecd7956ecf4a201df3`; the implementation was an uncommitted worktree delta from that approved base.
- Inspected pre-report tree fingerprint: `18938996520573fdc032ded1401f340e363f71bd0789f4a28c7cc624f572fbfb`. Replacing this report is the only change made by the reviewer after that fingerprint was captured.
- Inspected 33 changed product/evidence paths reported by `changed_files`, including the router and verification extensions, complete demo service/HTTP/UI/fixture tree, launcher, OpenAPI contract, installer/package/version/docs integration, tests, and route evidence.
- Local package at review: `dist/adaptive-grok-build-pro-v2.1.0.zip`, SHA-256 `5969f951e416f2fb93b3d453267a91efded59ce109058b79b8ebf765ee89cec6`, matching its adjacent checksum file.

## Prior Important findings and remediation

### Resolved — demo initialization invoked Git subprocesses

The pre-remediation application constructed route metadata through `git_default_base()` and `tree_fingerprint()`, contradicting the documented no-Git/no-shell demo boundary. The implementation now uses explicit fixed, non-authoritative `DEMO_ROUTE_METADATA` solely as the deterministic route seed; the normal `build_route` defaults remain unchanged for non-demo callers. Neither `demo.py` nor the HTTP handler imports or invokes the Git helpers.

The regression test patches `subprocess.run` before both `DemoApplication` and `create_server` construction, then separately guards request handling and runtime state. Both paths pass, so the earlier test blind spot is closed.

### Resolved — alternate scenario falsely claimed low risk

The bundled alternate is now a real documentation-review prompt. The server computes its route with the same repository router and publishes both the route projection and a label derived from the computed intent/risk/write owner. Direct re-execution produced `intent=review`, `risk=medium`, `domains=[api]`, `write_agent=None`; the visible label is `Use contrasting review route · medium risk · no write owner`.

The neutral pre-load UI, dynamic client assignment, investor guide, and regression assertions agree with those values and contain no fabricated low-risk claim.

## Security, correctness, and truthfulness assessment

- The server binds only `127.0.0.1`, serves a literal asset allowlist, rejects hostile Host/Origin, emits no CORS permission, requires the demo header for preview POST, bounds body and prompt sizes, rejects duplicate/unknown JSON fields and unsupported methods, and returns stable safe errors with security/no-store headers.
- Browser-controlled text reaches only in-memory router/spec preview logic. It cannot select a filesystem path, command, URL, repository root, Git ref, credential, destination, approval, release, or deployment action.
- Dynamic UI content is rendered through `textContent`; there are no inline/remote scripts, unsafe HTML sinks, browser persistence, service worker, or external resource URL.
- Sample verification is strictly validated and labelled `bundled_sample`; entered prompts receive `computed_preview` and verification `not_run`. The UI and docs explicitly deny merge authority, live Trust CI verdicts, approval, publication, and deployment.
- Architecture and governance use canonical read-only loaders with bounded partial-degradation responses. The normal router remains backward compatible because its new overrides are optional and preserve the existing default behavior.
- Installer and archive inventories include the launcher, engine, assets, fixtures, contract, and guide without adding a root package marker, JavaScript dependency tree, database, provider adapter, background service, or GitHub Actions workflow.

## Verification reproduced by this reviewer

- `python3 -m unittest tests.test_demo tests.test_demo_http tests.test_installer tests.test_manifest_package tests.test_structure -q`: **67 tests passed**.
- The focused remediated demo/API portion within that run: **20 tests passed**, including both prior-finding regressions.
- `git diff --check 2cf89e40e5c3f33cddf87eecd7956ecf4a201df3`: passed.
- Direct alternate-route comparison and archive/checksum comparison: passed.

## Severity-classified residual findings

### Critical

None.

### Important

None.

### Minor

1. The UI assurance is portable structural/HTTP integration rather than a real browser screenshot/E2E run. This matches the approved test plan, but a future Playwright smoke test would improve visual-regression confidence.
2. The OpenAPI document freezes the path/method/request boundary but does not fully schema every success response. This is adequate for the bundled same-repository client; add response-schema conformance before supporting independent API consumers.
3. `HTTPServer` is intentionally single-process and local-only. If the surface ever becomes remote or long-lived, adopt connection/read timeouts and a hardened production server before exposure.

## Completion boundary

This PASS supports the local investor-demo product scope only. It is not merge, release, deployment, production mutation, signed approval, or App-owned exact-SHA Trust CI evidence.

---

## Post-merge review — remediation required

### Verdict

**FAIL**

This later verdict supersedes the pre-merge PASS above for merge commit `3af0e803c8d763f227f0669e3c614806a90fc75b`.

### Inspected merge identity

- Merge HEAD: `3af0e803c8d763f227f0669e3c614806a90fc75b`.
- First parent (verified MVP): `9dcdf5880b619f29c01dbe76e0f598ff1fad9f9b`.
- Second parent (`origin/main`): `1c06299894279a88b881defa3f19b004fa742223`.
- Clean post-merge tree fingerprint before review evidence/test changes: `16b5ca33aa8e72bbf2d724cf6c767d4f541f7a217e5784c340310df9f8d49858`.
- First-parent delta: `AGENTS.md`, `PROJECT_STATE.json`, `README.md`, and `START_HERE.md`. The sole textual merge conflict was `README.md`; its K16 graph remained complete and its v2.1.0/demo/Trust-CI boundaries remained intact.
- The reported full `grok_verify --mode pr` run on this exact merge HEAD passed all checks; targeted README graph, version, and demo-documentation tests were independently reproduced and passed.

### Critical

None.

### Important — rank-3 bootstrap source directs fresh agents to obsolete M1 work

The newly merged `PROJECT_STATE.json` and `START_HERE.md` claim that M1 is the active milestone, M1 implementation has not started, PR #8 / `milestone/m1-typed-intent-evidence` is the current branch, and Task 1 of the old M1 plan is the next action. The actual first parent already contains locally completed M1, M2, M3, and the investor-demo MVP, and the current active branch is `mvp/investor-ready`.

This is an authority/workflow regression, not merely stale prose: the same merge changes `AGENTS.md` to elevate `PROJECT_STATE.json` into source-of-truth rank 3 and explicitly instruct a fresh agent to continue the branch named there. A clean-clone agent would therefore be directed away from the current candidate into obsolete work. The claims also contradict README's current-state M1/M2/M3 implementation bullets and are included in the product archive.

Required remediation: update both bootstrap artifacts to identify the v2.1.0 investor candidate, its current PR/branch and locally complete candidate layers, while keeping external exact-SHA Trust CI, required approvals, merge, release, and deployment explicitly pending. Add a regression test that rejects the obsolete PR #8/M1-not-started claims.

### Minor — README merge removed useful product sections

The first-parent delta removed the prior `## Bitrix` and `## License` tail sections. MIT identity and the Bitrix example remain linked elsewhere, so this is not a release-authority or licensing failure, but restoring the sections avoids a product-documentation regression from the merge.

### Other assessment

No product code, API, demo security boundary, packaging mechanism, GitHub Actions policy, or external merge-authority regression was found in the merge. A fresh review is required after the bootstrap and README remediation is committed and reverified.

---

## Final post-fix review

### Verdict

**PASS**

This final verdict supersedes the post-merge FAIL above for remediation commit `c711bd7912d7ba44e137db8a1afda44eae16897b`. No Critical or Important issue remains.

### Exact inspected identity

- Product HEAD: `c711bd7912d7ba44e137db8a1afda44eae16897b`.
- Parent/pre-fix merge: `3af0e803c8d763f227f0669e3c614806a90fc75b`.
- Inspected pre-report worktree fingerprint: `53464d59f61364821a22d97c94ded9013964c231d2fddde9cdc222f91a0cebdc`.
- Product worktree matched HEAD exactly; the only pre-existing worktree changes were independently owned `code-review.md` and `test-review.md` evidence updates. Appending this section is the reviewer's only subsequent mutation.
- Remediation delta is bounded to `PROJECT_STATE.json`, `START_HERE.md`, `README.md`, and `tests/test_structure.py`.

### Important finding resolution

Resolved. `PROJECT_STATE.json` now identifies source identity `2.1.0`, locally complete M1/M2/M3/investor-demo candidates, active PR #15 on `mvp/investor-ready` targeting `main`, and a delivery state of external exact-SHA Trust CI pending, required approvals pending, merged false, and deployed false. The old `3af0e803...` SHA is explicitly context-only and cannot be reused as current evidence.

`START_HERE.md` carries the same bounded truth, contains no PR #8, obsolete M1 branch, M1-not-started, or Task-1 restart instruction, and directs the next agent to the current PR head plus external exact-SHA/approval gates. It does not claim Trust CI success, merge, release, or deployment. This restores consistency with the rank-3 source-of-truth role assigned by `AGENTS.md` and with README's current-state layers.

### README resolution

The K16 graph remains complete, the source identity remains v2.1.0, and the current-state section now describes M2 and M3 as locally complete source candidates while retaining explicit fresh verification, PR, external Trust CI, approval, merge, and deployment boundaries. The Bitrix and MIT License sections removed by the merge are restored.

### Verification evidence

- Parent reported a fresh full `python3 scripts/grok_verify.py --mode pr` PASS on this product HEAD.
- Independently reproduced four focused structure checks: bootstrap state, restored Bitrix/License sections, complete README graph, and version identity — **4/4 passed**.
- `PROJECT_STATE.json` parsed successfully with `python3 -m json.tool`.
- Stale bootstrap-claim search across `PROJECT_STATE.json`, `START_HERE.md`, and `README.md` returned no match.
- Current PR/branch and pending external-authority assertions were present in both machine-readable and human-readable handoffs.
- `git diff --check 3af0e803c8d763f227f0669e3c614806a90fc75b..c711bd7912d7ba44e137db8a1afda44eae16897b` passed.

### Severity-classified findings

#### Critical

None.

#### Important

None.

#### Minor

None introduced by the remediation. The pre-existing local-demo residual notes in the pre-merge review remain non-blocking and unchanged.

### Authority boundary

This PASS is local code-review evidence for the exact product HEAD only. The App-owned policy-epoch check on the exact current PR SHA, required human-signed approvals, merge, release publication, and deployment remain separate pending operator-controlled gates.
