# Final M2-A code re-review — fix wave

## Reviewed identity

- Route: `0156034c05bd`
- Prior reviewed head: `99de2f9757400f7394b7a9e2c46b3ebce939e438`
- Prior tree: `bae34faabdf968396e393d40f7219d3bbf5a60b5`
- Fix head: `fd5f7eb41fe63c8c0950c0195cfcf54a00dee04d`
- Fix tree: `962d7f858fbf7754dd0f800e65a8f41f8ba5f983`
- Clean fix-head tree fingerprint at review start: `85a51af80642631397208fb0ca4bc2a277d7465b074df44f9f06e308692e2c69`
- Exact package: `.superpowers/sdd/2026-08-26-m2a-executable-architecture/review-99de2f9..fd5f7eb.diff`
- Package SHA-256: `ac1aba14c8498f1c3d1fd6fbd9de7ef7557b09c8c14c9461ce7d5921a3acca54`
- The prior head is an ancestor of the fix head. The exact fix contains 22 files, 1,328 insertions, and 122 deletions. The worktree was clean at review start; a parallel reviewer report appeared later and was not treated as a product input.

## Verdict

**BLOCKED** — the three original code findings are addressed, but the durable-adoption repair introduces one new Important compatibility failure. Finding count for this re-review: 0 Critical, 1 Important, 0 residual Minor.

## Original finding verdicts

### I1 durable adoption — ADDRESSED

The original post-deletion descendant bypass is closed. `_exact_history_has_architecture()` performs an isolated, output-capped, timeout-bounded, exact-HEAD `rev-list --full-history` query for authority paths, validates every returned identity, and shallow absence fails closed (`.grok-stack/adaptive_grok/receipts.py:148-180,183-210`). The focused ordinary-descendant and shallow-descendant tests at `tests/test_verification_doctor.py:322-346` and the later shallow-history case both pass. The original sequence now returns an architecture failure instead of `pass/not_configured`.

This verdict is limited to the original adopted-deletion case. New finding N1 below is a distinct overclassification introduced by searching model/rules history as if it proved explicit adoption.

### I2 unknown line statistics — ADDRESSED

Applicable artifacts with either line count unavailable are now named in `unsupported`; only artifacts with two known counts contribute to the numeric sum (`.grok-stack/adaptive_grok/architecture_fitness.py:951-1018`). The focused NUL and invalid-UTF-8 non-Python regression at `tests/test_architecture_fitness.py:1489-1516` asserts category `unsupported`, overall failure, scoped evidence, and monotonic risk. The test passed independently. The former `None -> 0 -> pass` path is gone.

### I3 process setup cleanup — ADDRESSED

Cleanup ownership now starts immediately after successful `Popen`: pipe validation and selector construction/registration run inside the outer `try/finally`, setup exceptions normalize to `ArchitectureError`, pipes close, and a still-live process group is killed and reaped (`.grok-stack/adaptive_grok/architecture_diff.py:82-151`). The focused real-process regression covers selector construction, `set_blocking`, and registration failures and verifies that no child remains live (`tests/test_architecture_fitness.py:1920-1976`). It passed independently.

## New Important finding

### N1 — Unadopted model drafts in old history are permanently mistaken for explicit adoption

The new history query treats any historical occurrence of `architecture/system.yaml` or `architecture/rules.yaml` as adoption evidence (`.grok-stack/adaptive_grok/receipts.py:148-160`). `_active_architecture_binding()` then reports “adopted architecture marker and model are missing” whenever that query is nonempty (`:183-205`), even if `architecture/adoption.json` never existed.

Independent end-to-end reproduction on the fix head:

1. Start from a normal Git consumer and a pre-adoption route.
2. Commit both model/rules as review drafts without an adoption marker.
3. Delete both drafts and commit the deletion.
4. Add an unrelated later commit.
5. Run production `verify(..., mode='fast', record=False)`.

Observed:

```text
report_status fail
architecture {'configured': True, 'error': 'adopted architecture marker and model are missing', 'status': 'fail'}
```

At the prior reviewed head, the same later-descendant shape was outside the current/direct-parent/route-base checks and remained legacy `not_configured`; the full-history model/rules query is therefore the cause introduced by this fix. No committed test covers an abandoned pre-marker draft.

This contradicts the approved authority boundary: the canonical marker is the explicit durable adoption switch, model/rules become authority only after explicit adoption, and a repository without explicit adoption reports `not_configured` (`engineering/changes/20260826-m2-executable-architecture-015603/architecture.md:11-16`; `docs/superpowers/specs/2026-08-26-m2-executable-architecture-design.md:175-177`). It also conflicts with the documented marker-last review flow (`QUICKSTART.md:22-53`). A consumer that reviews versioned drafts and then abandons them cannot return to M1-compatible unconfigured operation.

Required repair: distinguish historical marker evidence from historical draft-model evidence. Current model/rules without a marker should continue to fail as an incomplete adoption attempt, actual marker history must keep deletion descendants fail-closed, shallow ambiguity must remain fail-closed, and a full-history repository in which the marker never existed must return `not_configured` after draft model/rules are removed. Add an exact regression for that four-commit lifecycle.

## Overlapping fix-wave assessment

- **Queue provenance:** wildcard uncertainty plus bounded tuple/list/starred/subscript/annotated/chained propagation feeds the same result used by background-job fitness and `new_queue`. The positive matrix and unrelated decorator control passed. No new Critical/Important breakage found in this fix.
- **Added contracts:** every added record now self-validates through each applicable comparator before it may pass. The bounded OpenAPI subset handles the frozen JSON, text, and octet-stream media surface and the exact current baseline self-compares compatible. Unsupported added JSON Schema semantics fail. No new Critical/Important breakage found.
- **Repository ownership:** semantic validation rejects exact cross-node ownership ties, runtime resolution rejects equal-specificity ties, and a unique longest prefix remains supported. `trust-ci/compose.yaml` now has one source owner while the Docker runtime stays represented by its edge. No new Critical/Important breakage found.
- **Installer containment:** managed files, `AGENTS.md`, Bitrix guidance, and ensured directories use descriptor-relative no-follow traversal; final symlink, ancestor symlink, FIFO, target-authority preservation, and parent-relocation rollback tests passed. No new Critical/Important ownership/installer defect was found in the fix diff.
- **Scope:** the exact fix changes no `trust-ci/**` or `.github/workflows/**` path and adds no dependency, service, database, migration, queue/runtime capability, provider, or external action.

## Original schema Minor triage

**Resolved for the stated regression risk.** The test still does not enumerate a separate malformed document for every record kind, but it now recursively inventories all 10 system and 13 rules object schemas and asserts for each that `additionalProperties` is exactly false and `required` exactly equals the property set (`tests/test_architecture_model.py:359-384`). Combined with the existing loader/schema-engine behavioral mutations, this directly locks the property-closure invariant whose future weakening the Minor finding was concerned with. I do not carry the old Minor forward.

## Independent evidence

- 13 focused remediation/overlap tests passed in 10.313 seconds: the two durable-adoption cases, legacy control, unknown metrics, all three process setup stages, queue matrix, added-contract semantics, ownership validator/runtime behavior, current seed baseline, and installer symlink/relocation/direct-authority controls.
- Current architecture `validate`, `drift`, and `diagram --check` all exited 0; drift findings were empty and all five projection digests matched.
- Exact adoption-base-to-fix-head fitness exited 0 with all mandatory categories typed, `fitness_status=pass`, risk `red -> red`, exact base/head identities, and architecture-evidence digest `b79b469d7a83bc4bef853ff5ae17d85a57d40617ae752a49171407f9d4f0fefc`.
- Typed change-spec gate exited 0 with `ok=true`.
- `git diff --check` passed and the exact fix path set under `trust-ci/**` and `.github/workflows/**` is empty.
- The implementer's reported 342-test/full-verifier run was inspected in the appended fix report but not broadly rerun for this scoped code re-review. The independent adversarial N1 probe is outside that committed suite.

## Merge-authority disclaimer

This report is local workflow evidence only. It is not merge authority and cannot replace fresh exact-fingerprint verification and all route-selected review receipts, the GitHub App-owned policy-epoch `adaptive-trust-ci/verified@<policy-sha12>` Check Run on the exact pull-request head, branch protection, or required independently signed human approvals.
