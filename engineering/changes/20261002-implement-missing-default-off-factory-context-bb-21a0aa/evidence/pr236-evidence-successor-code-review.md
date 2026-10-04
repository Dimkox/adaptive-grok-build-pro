# Independent code/evidence review — PASS with one evidence limitation

## Source identity

- Candidate: `<local-path>`
- Reviewed HEAD: `1736c6fedf6b0f69db5801df9910ce28bcc80489`
- Parent: `56103168643662012e0fcc6edaeda2e40d240996`
- Tree: `3cc71c02ccbd1eb715a818f6897478f61a342d81`
- Fingerprint before/after: `a3100727ddfa9dfb221a2a18d1cc35280ff4f853dcbedea4369b11219c0114c0` / same
- Candidate status before/after: clean
- reviewed-tree-modified: no

## Scope and diff

`git diff --name-status HEAD^ HEAD` showed exactly one added diagnostic evidence file. `git diff --check 561031...1736c6...` passed. The product diff from the earlier reviewed source HEAD `5645e1b...` through this HEAD, excluding `engineering/changes/**`, was empty.

## Public GitHub API verification

The reviewer read check run `110953511590` and PR 236. The check was the App-owned `adaptive-trust-ci/verified@06ecf1c875bc` check for exact head `56103168643662012e0fcc6edaeda2e40d240996`. It completed with failure. Its public summary showed `holdout-bundle-integrity: pass`, `external-holdout: pass`, and `root-unittest: fail (exit 1)`. PR 236 was open, non-draft, with the expected head branch and base.

The evidence file therefore correctly requires a new exact-head App check after an authorized push.

## Fresh-clone claim validation

The reviewer created a private public-remote clone under `/tmp/pr236-clean-clone-review.1064UA/repo`, verified exact HEAD `561031...`, and started the documented unittest command. The run was interrupted at 452.83 seconds on coordinator direction before terminal output. It showed sustained passing progress but did not independently prove the recorded `997 tests / 526.048 seconds` result.

The committed evidence contains no raw log, digest, environment identity, or durable receipt for that result. Treat the numeric result as operator-recorded evidence. This limitation does not invalidate the bounded ruling because the diagnostic does not claim a product fix, merge eligibility, or Trust CI bypass.

## Other historical claims

The HTTP 404 rerequest and unchanged-SHA UI retry results were not independently reproduced. Reproduction would require external write authority and was not necessary for review of the immutable evidence-only diff.

## Mutation probes

No mutation probe was applicable because no executable or product bytes changed.

## Decision

PASS for exact evidence-only HEAD `1736c6fedf6b0f69db5801df9910ce28bcc80489`. No Critical or Important findings. The clean-clone terminal count/duration remains an explicit evidence limitation. This review does not authorize merge, tag, release, publication, or deployment.
