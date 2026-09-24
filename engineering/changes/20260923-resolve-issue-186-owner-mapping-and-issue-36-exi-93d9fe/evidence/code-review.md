# Code review — issues #186 and #36 disposition

Verdict: PASS

## Review basis

- Candidate worktree: /tmp/agbp-issues-186-36
- Route/base commit: 130ce4a42d9f9bbd1b56772d40b19ae530283205
- Implementation snapshot audited: origin/main at 130ce4a42d9f9bbd1b56772d40b19ae530283205, tree 3b51c9d21550627bb35fdb06753d2bedd5cf97ff
- Candidate commit reviewed before this report was persisted: 8dac90df509bd197ca14c670c30b5fc2ab5e73c2
- Candidate tree fingerprint for that review snapshot: 355d42f9f2d7f1b4ca3406bd2c01825b14c1bdf43eeb9c9505b3a9935df4efd6
- reviewed-tree-modified: no
- Private scratch used by the reviewer: /tmp/agbp-rereview.yDQkzA
- The final verification receipt must bind the post-report-persistence tree; this report records the exact snapshot that was reviewed.

## Scope and commands

The review used the route base, not HEAD^, as the comparison point.

    git diff --name-status origin/main..HEAD
    git diff --check origin/main..HEAD
    git status --short
    git grep -n -E 'if !|\$\?|exit_code|exit status|status_file|status.*file|write.*status' origin/main -- scripts trust-ci '*.sh' tests delivery
    git log --all --oneline -G 'if !.*cmd|code=\$\?|exit[_ -]status.*(file|record)|record.*exit' -- scripts trust-ci factory tests

The exact route-base diff contained 20 paths: decisions.md, mistakes.md, and the active change package's architecture, brief, change-spec, evidence, release, requirements, rollback, route, state, tasks, and test-plan files. It contained no product source, product test, OpenAPI/event/SQL contract, deployed verifier, or Trust CI implementation change.

The source/history search returned no repository-owned shell recorder or reachable implementation of the reported pattern. The current Python and Trust CI owners preserve explicit subprocess return codes, but that is not treated as ownership of the absent shell defect.

## Characterization probe

The reviewer ran the reported shell shape and two safe captures:

    bash -c 'set +e; if ! bash -c "exit 7"; then code=$?; printf "if-not status=%s\n" "$code"; fi; bash -c "exit 7"; code=$?; printf "direct capture status=%s\n" "$code"; if bash -c "exit 7"; then :; else code=$?; printf "else capture status=%s\n" "$code"; fi'

Observed result:

    if-not status=0
    direct capture status=7
    else capture status=7

## Claim outcomes

- Initial review scope error using HEAD^..HEAD: killed; the corrected review uses origin/main..HEAD.
- No committed product diff for #36: confirmed.
- No repository-owned recorder in the audited tree or reachable history: survived.
- Evidence-only disposition is the smallest coherent change: survived.
- #36 remains an external/misrouted report with no closure claim: survived.
- #35, #36, #39, and #48 remain separate ownership boundaries: survived.
- No speculative helper, regression test, API change, or Trust CI change was introduced: survived.

## Limitations

- No GitHub issue edit was made and no external owner link was available to verify.
- This review cannot claim that #36 is fixed or closed.
- If an authoritative external repository, path, command, or PR is supplied later, it needs a new routed change with a failing regression, minimal repair, and fresh verification.

## Final assessment

The candidate is an honest repository-local owner mapping and disposition for #186/#36. It preserves the blocker instead of pretending that an absent local implementation was fixed.

## Refresh after base merge — 2026-09-24

- Reviewed HEAD `89dd75ec38855b47e975bdd3bb8e21e7b2ffce53`, tree `ac391f07f4c1276c0eb04fdd40442f8e2162b638`, against `origin/main` `08b1cdc8ae50212f596fd891fa1ae2a4a8d1b5dc`.
- `git diff --check` passed; no product-code diff exists relative to `origin/main`.
- The #186/#36 no-local-owner disposition and the landed #167 focused verifier remain intact; no speculative helper, regression, API, or Trust CI authority change was introduced.
- Verdict: **PASS**. The refreshed full verifier is required for the persisted evidence tree.
