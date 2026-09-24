# Release/provenance review

Result: PASS, with independent rebuild unexecuted because the packaging guard correctly rejected an unsafe scratch ancestor.

## Source identity

- Route: `09407b46cb4b`
- Candidate HEAD: `b8d31280f28b32dffff3d3c51dec06ed7bdc822b`
- Git tree: `255f344f7e728aab357dfc6363e2eb994dd2dd97`
- Adaptive tree fingerprint: `47148ad0ff373961819b13a0d05e4cea55b1a971d94cb7a87c74b298cb94f2ec`
- Reviewer scratch: `/tmp/agbp-release-review.INSk4k/candidate`
- `reviewed-tree-modified: no`; candidate status stayed clean after every probe.

## Probes and outcomes

- `rg -n -S 'ac7f355' ...` — no stale digest prefix.
- `git merge-base --is-ancestor 3f41be92161fef451a2dfa7451eb458ce8f022b3 HEAD` — source parent is an ancestor.
- `sha256sum packages/adaptive-grok-build-pro-v2.0.19.zip` — `4176a872acdca873e840855d0b2c9e379cf8f796c9de69e5560b3e2bf85634b9`; size `14301716` bytes.
- Sidecar read/hash — matching ZIP digest, correct filename, sidecar SHA `77057e0be72b38dd6f6946e31d151f8d80c96b5b7470b92798f7422147791cf8`.
- `python3 -m unittest tests.test_manifest_package tests.test_project_state tests.test_structure` — `Ran 92 tests ... OK`.
- Version/docs/state audit — `2.0.19` is consistent; latest published release remains `v2.0.18`; v2.0.19 tag and GitHub Release are absent/pending; no deployment, hosting or activation claim.
- Independent rebuild attempt — fail-closed with `PackageError: archive output ancestor grants untrusted rename authority` under `/tmp`; no candidate mutation resulted.

Mutation outcomes:

- No candidate files changed; final HEAD and fingerprint matched the initial values.
- Source-parent, digest, publication-state and sidecar-name substitution probes were killed by the direct checks/tests.

Unexecuted claims and limits:

- External App-owned Trust CI, PR merge, tag, GitHub Release and deployment were not executed or claimed.
- The two byte-identical builds are accepted from committed build evidence and direct digest consistency; this review did not independently rebuild them because the secure packaging boundary rejected the scratch location.
