# Integration analysis — issue #218 clean squash delivery

## Ruling

The safe candidate is one new commit whose sole parent is
`cb9af4073ba6c3d515145164d771c75ebdfa3224` and whose tree, except for this route's
new delivery package, is mode/blob-identical to source
`68dfc70c5f58adcc927f731c5d88de09a1b4b242`.

Do not transplant only `9dedad01..68dfc70c`. The #218 implementation consumes the
stacked #220 receipt-v2 completion model, #227 root-bound Git environment, #226
timeout/receipt failure behavior, and the intervening architecture, review, and
parallel-verifier fixes. The delivery is an integrated source-tree squash, not an
independent two-commit backport.

At the read-only observation point, the delivery branch remained at the exact base,
the staged index differed from `68dfc70c` on zero paths, and the unstaged product
diff was empty. The new delivery package was still untracked. This is a transient
construction observation and must be repeated after the package and reviews are
finalized.

## Source and candidate identity evidence

- `cb9af407..68dfc70c` contains 40 commits and 186 changed paths.
- The final endpoint `git diff --check cb9af407..68dfc70c` passes. The stacked
  development history is intentionally not the candidate history: its repaired
  intermediate whitespace would be rejected by the new scanner.
- `git diff --cached 68dfc70c` named zero paths during this audit, establishing
  complete staged-tree equality at that moment, not merely equality of the three
  verifier modules.
- Neither #219 tip is an ancestor of the source: `e17ac251` (managed-skill lane)
  and `2b832f5e` (Trust CI lane) both fail the ancestor test against `68dfc70c`.

After the write owner makes the sole commit, acceptance must rederive:

```text
parent(candidate) = cb9af4073ba6c3d515145164d771c75ebdfa3224
count(cb9af407..candidate) = 1
tree(candidate) - delivery-package = tree(68dfc70c) - delivery-package
```

No source receipt, fingerprint, scan digest, or review receipt survives this new
commit identity. All completion evidence must be regenerated on the clean squash.

## Selected-base chain behavior

The source implementation in `verification.py` has the required composition:

1. `_git_range_selection()` captures one exact `HEAD` and independently records
   route and PR-target provenance. Route comparison/scan base is the exact ancestor
   `route.base_commit`; PR comparison/scan base is the unique merge base of the
   captured local target tip and captured head.
2. `_enumerate_scan_identity()` enumerates each selected
   `scan_base..head_sha`, retains a range row and commit digest per source, and
   unions commits by exact object ID.
3. `_build_chain_scan()` inspects every parent edge of every unioned commit,
   deduplicates regular postimage blobs by object ID, enforces commit/path/blob/
   aggregate bounds, and exposes only bounded metadata findings.
4. `_git_diff_check()` checks every parent edge for whitespace;
   `_secret_scan()` combines committed-blob findings with the final staged,
   unstaged, and untracked snapshot. Any incomplete enumeration/object/worktree
   coverage is a preflight failure.

I exercised five focused source regressions on exact source HEAD `68dfc70c`; all
passed in 2.501 seconds: add/delete sensitive content, repaired intermediate
whitespace, every merge-parent edge, commit-bound failure, and rejection of a
scanless verification PASS receipt.

I also exercised a divergent real Git graph directly. The selector produced both
`route` and `pr-target` rows with distinct exact scan bases and a common captured
head; the scan was complete, its union contained two commits and two unique parent
edges, and paths from both ranges were present. The existing add/delete regression
uses identical route/PR bases and proves deduplication: two provenance rows remain,
while union commit count and unique blob count are not doubled.

For the genuine one-commit delivery graph, both selected bases should resolve to
`cb9af407` while retaining two rows:

| Kind | Source tip | Comparison/scan base | Range work |
| --- | --- | --- | --- |
| `route` | route base `cb9af407` | `cb9af407` | one candidate commit |
| `pr-target` | local `origin/main` tip `cb9af407` | unique merge base `cb9af407` | same candidate commit |

Expected aggregate scope is one unique commit and one unique parent edge. A count
of zero means verification ran before the squash commit; a count above one means
old stack history or an extra commit remains and is not the approved delivery shape.

## Receipt-v2 integration

The report remains schema v1 and adds the closed
`adaptive-grok.verification-scan/v1` object. A verification PASS receipt remains
schema v2 under #220 and embeds that report in `details`. `validate_evidence()` now
reselects current route/PR bases and compares contract, exact head, normalized
ranges, chain digest, and union commit count; missing, malformed, incomplete, or
stale scope is an evidence gap. Review PASS receipts continue to bind the canonical
verification-receipt digest, so replacing verification invalidates review evidence.

This correctly preserves #220 sequencing:

1. Finish and persist the delivery package and review reports.
2. Create the sole commit and require a clean exact HEAD/ready lifecycle.
3. Run recording PR verification; require complete scan scope and successful
   receipt publication.
4. Record review receipts only against that current verification receipt.
5. Confirm status has no evidence gaps.

The source logic covers the identity recheck, but the newly added focused tests do
not directly mutate the local PR target ref or forge an otherwise well-shaped chain
digest. The delivery review should include those two mutations, plus a two-commit
candidate whose first commit introduces and second repairs whitespace. These are
test-evidence gaps, not observed implementation failures.

## #219 exclusion boundary

The exclusion is exact and currently satisfied:

- `git diff cb9af407..68dfc70c -- trust-ci` is empty.
- The staged candidate had zero paths under `trust-ci/` and zero #219 change-package
  paths.
- Each of the five Trust CI lane paths remains byte-identical to the base:
  `trust-ci/config/policy.example.json`,
  `trust-ci/holdout.example/change_spec_validate.py`,
  `trust-ci/src/adaptive_trust_ci/runner.py`,
  `trust-ci/tests/test_change_spec_holdout.py`, and
  `trust-ci/tests/test_runner.py`.

Do not import either #219 package or its runner/holdout/policy/test deltas. The local
receipt-kind set present through other prerequisites does not authorize claiming
#219 Trust CI parity. Repository-local verification also remains preflight only;
the App-owned exact-head policy-epoch check is still the merge authority.

## Final acceptance matrix

Before delivery, require all of the following on the committed candidate:

- exact sole parent/base, exactly one post-base commit, and whole-tree mode/blob
  equality to `68dfc70c` except the named delivery package;
- zero `trust-ci/**` and #219-package delta;
- report inventory with the exact candidate head, both base provenance rows, one
  unique commit, complete worktree/chain status, and a fresh digest;
- endpoint and per-edge whitespace checks PASS; secret scan coverage complete with
  no secret content rendered in output;
- the five focused source regressions plus target-ref staleness, forged scan digest,
  two-commit whitespace mutant, timeout/object/limit failure, and no-expensive-lane
  assertions;
- schema-v2 verification receipt current for the squash, followed by fresh code,
  test, security, and release receipts bound to its digest; and
- unchanged candidate tree/fingerprint before and after every independent review.

Any post-verification amend, package edit, ref/base change, or extra commit changes
the evidence subject and requires verification and reviews again. No network,
external write, commit, receipt write, or product edit was performed in this
analysis.
