# PR 236 Trust CI root-unittest diagnostic

Recorded: 2026-10-02

## Source identity

- Candidate HEAD: `56103168643662012e0fcc6edaeda2e40d240996`
- Pull request: 236
- Trust CI check run: `110953511590`

## Observations

- The external Trust CI check failed only the `root-unittest` check.
- Holdout integrity passed.
- External holdout passed.
- An exact clean remote clone at the same HEAD ran `python3 -m unittest discover -s tests`.
- The clean-clone run passed 997 tests in 526.048 seconds.
- One check-rerequest endpoint call returned HTTP 404.
- Closing and reopening the pull request on the unchanged SHA did not create a new Trust CI job.
- Moving the unchanged pull request from draft to ready did not create a new Trust CI job.

## Ruling

The available evidence does not establish a product-code defect. The local clean-clone result and the external result differ on the same source SHA. The Trust CI service deduplicates the unchanged SHA, so UI state changes cannot request new exact-head evidence.

This evidence-only commit creates a new source SHA. It does not change product behavior, claim that Trust CI will pass, bypass the external gate, or authorize push, merge, tag, release, or deployment.

## Required next evidence

After an authorized branch push, require a new App-owned Trust CI check on the new exact SHA. Preserve the new check result independently of this diagnostic record.
