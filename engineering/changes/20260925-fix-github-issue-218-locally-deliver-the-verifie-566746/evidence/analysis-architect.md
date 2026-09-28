# Issue #218 delivery-candidate architecture analysis

## Ruling

A single clean squash commit with parent
`cb9af4073ba6c3d515145164d771c75ebdfa3224` is the safest delivery shape, provided
that it preserves the complete final source tree at
`68dfc70c5f58adcc927f731c5d88de09a1b4b242` outside this new delivery package and
is verified and reviewed again as a new exact HEAD.

This does not weaken the full-chain scan. The security subject is the commit graph
actually proposed for delivery, not every discarded local development commit. The
new verifier must still select the unchanged route base, capture the exact candidate
HEAD, and scan every commit and parent edge in `base..HEAD`. For the proposed graph
that complete range contains exactly one commit and one parent edge. Removing the
old commits from ancestry before verification is remediation of the delivery
history; changing the scan base to hide reachable commits, retaining the old commits
in ancestry, or squashing after verification would be a bypass and is forbidden.

## Read-only evidence

The source range contains 40 linear commits and changes 186 paths. The final
`cb9af407..68dfc70c` diff passes `git diff --check`, while per-commit inspection
found historical whitespace errors in three intermediate commits:

- `912b33de`: a new blank line at EOF in the #227 integration analysis;
- `dde3a260`: five trailing-whitespace findings in #226 evidence; and
- `e3ec07fe`: four trailing-whitespace findings in #224 review evidence.

Those findings are absent from the final tree, so a base-to-final net check passes;
the new chain scanner correctly rejects the original 40-commit delivery graph. A
clean squash replaces that graph rather than asking the scanner to ignore any edge.

At analysis time the delivery worktree remained at the clean base commit, with the
source result already staged by the coordinator. A mode/blob/path comparison of the
entire index against `68dfc70c` had zero mismatches. Both the staged diff and the
source final diff passed `git diff --check`. The new delivery package was untracked
and therefore was not part of that equivalence observation.

The source and staged deltas contain zero paths under `trust-ci/` and no #219 change
package. Thus the candidate does not include the #219 Trust CI runner, holdout
example, tests, or illustrative policy-digest work. This is a source-tree separation
finding only; it does not assert anything about deployed Trust CI state.

No network, receipt write, commit, branch mutation, external operation, or product
edit was performed for this analysis.

## Candidate construction contract

The write owner should create one root-relative candidate commit with these closed
invariants:

1. Its sole parent is exactly `cb9af4073ba6c3d515145164d771c75ebdfa3224`.
2. Excluding
   `engineering/changes/20260925-fix-github-issue-218-locally-deliver-the-verifie-566746/`,
   every repository path has the same Git mode and blob identity as
   `68dfc70c`. This compares the whole tree, not only a hand-selected #218 file list.
3. The only permitted tree delta from `68dfc70c` is the completed delivery package
   for route `566746aef130`; no generated runtime receipts or machine-local route
   state is committed.
4. `trust-ci/**` and any #219 package remain byte-identical to the base. The delivery
   must not opportunistically absorb #219.
5. `git rev-list --count cb9af407..candidate` is one, the endpoint diff is whitespace
   clean, and no merge parent or historical source commit remains reachable in that
   range.

The whole-tree rule matters because the two visible #218 commits depend on the
preceding #227, #226, performance, #224, #222, and #220 stack. Applying only the
small #218 diff directly to `cb9af407` would not preserve behavior. The squash is an
integrated 186-path delivery candidate, not a claim that #218 is independently
backportable to the base.

## Verification and evidence semantics

Imported source reports remain useful development provenance, but their recorded
heads, tree fingerprints, range digests, and receipt relationships do not become
completion evidence for the squash. A new commit has a new identity and a different
chain digest even when all product blobs are identical.

Use the repository's committed-tail lifecycle on the one-commit candidate:

1. Complete the delivery package and run diagnostic verification with
   `--no-record` while the candidate is still uncommitted.
2. Have every route-selected reviewer inspect the complete integrated candidate;
   historical reviews may be cited, but cannot replace review of the squashed
   snapshot. Persist the returned reports, finish the package, and transition it to
   `ready` before the sole commit.
3. Commit once. On the clean exact HEAD run recording PR verification. The report
   must show the unchanged explicit scan base, the new exact head, complete scan
   status, one unique commit, one inspected parent edge, and a fresh chain digest.
4. Record review receipts only after that current verification PASS receipt, then
   require read-only status to report no gaps. Never copy or reinterpret receipts
   from `68dfc70c` as current.

The final verifier and receipt path must preserve #220's commit-before-completion
rules and #226's truthful failure reporting. A scan, receipt-write, source-stability,
or evidence-validation failure returns FAIL; it must not leave a usable PASS receipt.
The existing bounded secret diagnostics remain metadata-only and must not reproduce
matched content.

## Trust boundaries and #219 separation

- Repository-local verification and review evidence are preflight only. The
  App-owned policy-epoch Check Run on the exact PR head remains merge authority.
- Squashing a real credential out of a local graph would not revoke exposure from
  any previously published ref. If any finding is suspected to be a real credential
  rather than the documented synthetic fixture, stop delivery and use the separate
  human-controlled incident/rotation process; never serialize the value in evidence.
- #219 may proceed as a separate Trust CI source change. If it lands first and the
  delivery base changes, rebase/reconstruct the candidate from the new approved base
  and rerun all exact-head evidence. Do not merge its runner/holdout/policy paths into
  this squash merely to avoid that refresh.
- The route's `scope_and_design_approval`, independent security/release reviews, and
  external exact-SHA Trust CI result remain explicit gates. No repository commit can
  modify deployed policy, holdout, keys, database state, or branch protection.

## Acceptance and adversarial checks

Before delivery, require evidence for all of the following:

- whole-tree mode/blob equivalence with `68dfc70c`, excluding only the named new
  delivery package;
- exact base parent and exactly one post-base commit;
- zero `trust-ci/**` and #219-package changes;
- complete `verification-scan/v1` scope bound to the candidate HEAD/base with one
  commit, fresh digest, no chain coverage failure, and no current worktree gap;
- endpoint whitespace cleanliness and all existing #218 regressions, including
  rejection of an add-then-delete sensitive fixture and intermediate whitespace in
  a synthetic multi-commit graph;
- mutation coverage that still kills changing the scan base, scanning only the net
  diff, using symbolic HEAD after capture, first-parent-only traversal, omitting a
  parent edge, and accepting an old source receipt on the squash; and
- fresh code, test, security, and release review over the integrated candidate.

A useful delivery-specific mutant is a two-commit candidate in which the first
commit introduces and the second repairs whitespace. It must fail full-chain
verification. The genuine one-commit candidate must pass without any special-case
"squash" or "historical" exemption in verifier code.

## Rollout and rollback

There is no runtime migration or deployed-state action. Rollout is the ordinary
PR-only path: create the one clean candidate, obtain fresh local evidence, then wait
for the exact-head external Trust CI check and required signed approvals. Do not push,
merge, or publish under this read-only analysis task.

Before merge, rollback is simply to abandon the candidate commit and its stale local
evidence. After merge, one coherent revert restores the `cb9af407` behavior but also
reopens #227, #226, performance, #224, #222, #220, and #218 defects bundled by the
squash; a targeted forward fix is therefore safer for an isolated regression. Any
revert or forward-fix commit changes the exact head and requires fresh verification,
reviews, and external Trust CI. Historical source commits and their reports should
remain immutable records, not be rewritten to look current.
