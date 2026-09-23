# Documentation research — issues #186 and #36

Role: `docs_researcher`
Route: `93d9feecc1dc`
Change: `20260923-resolve-issue-186-owner-mapping-and-issue-36-exi-93d9fe`

The analysis below is historical/base evidence for origin/main at
130ce4a42d9f9bbd1b56772d40b19ae530283205. Candidate package identity is
recorded separately in owner-mapping.md and the review reports; this report
does not claim that the candidate tree has the base commit.

This is read-only repository research. I ran `git fetch --all --prune` and
`python3 scripts/grok_status.py` from `/tmp/agbp-issues-186-36`. The checkout
was clean at `130ce4a42d9f9bbd1b56772d40b19ae530283205`; only this report is
being added.

## Findings

1. The active package's governing task is in
   `engineering/changes/20260923-resolve-issue-186-owner-mapping-and-issue-36-exi-93d9fe/brief.md`
   and `change-spec.yaml`. It explicitly requires: identify an exact
   repository-owned source/command owner for the exit-status recorder; if one
   exists, add a failing regression test and minimal fix for #36; otherwise
   record a durable local disposition for #186 and an explicit external-owner
   linkage for #36, without speculative code or Trust CI scope mixing.

2. The prior backlog disposition is in
   `engineering/changes/20260921-research-open-backlog-map-each-item-to-its-sourc-d54d3a/evidence/analysis-docs_researcher.md:24-34`.
   It states for **#36**: “shell recorder turns failed command into success”
   is a failure pattern from another gate; no matching recorder was found in
   this Python checkout. It specifically records that the current verifier
   uses subprocess return codes at
   `.grok-stack/adaptive_grok/verification.py::_command_check`, while Trust CI
   shell checks use explicit `set -e`/`sha256sum --check`. Its recommendation
   is `cmd || code=$?` plus a start-failure regression test only when a matching
   shell gate exists; no current-repository correction should be claimed yet.

3. A history search for `#186`, `186`, `#36`, `issue36`, `issue-36`, and
   `exit-status` (`git log --all --oneline -S'<term>' -- ...`) found no
   repository-owned issue #186 implementation or exit-status recorder. The
   issue-number hits are release/change-package bookkeeping (not an owner or
   acceptance implementation). The relevant historical release commits are
   `3dd3d2ff`, `ff733ded`, `61777d9a`, and `48a1f8a8`; their package evidence
   preserves external issue-closure scope but does not identify a #36-owned
   source path.

4. The current documentation reinforces the ownership boundary: `AGENTS.md`
   says external issue closure and Trust CI authority must be evidenced
   separately, and `README.md` describes local verification as preflight only.
   Therefore local package evidence can establish the repository-side
   absence/disposition, but cannot invent an external repository, maintainer,
   path, command, or closure fact.

## Acceptance and evidence recommendation

Use these durable acceptance statements in the active package (and mirror the
same bounded wording in the issue update):

- **#186:** “Repository audit complete at commit
  `130ce4a42d9f9bbd1b56772d40b19ae530283205`: no repository-owned source or
  command implementing the reported exit-status recorder was found in the
  current tree or reachable repository history. The repository disposition is
  ‘no local owner / no speculative fix’; the prior #36 audit remains the
  supporting evidence.”
- **#36:** “The reported recorder is not owned by this repository. This issue
  remains an external-owner linkage only; no external repository, exact path,
  command, maintainer, or closure is asserted until supplied by an
  authoritative issue/PR reference. If a concrete owner is later provided,
  reproduce the failure there and add the `cmd || code=$?` regression before
  claiming a fix.”

Bind the statements to the exact audit commands and paths above, preserve #186
and #36 as separate issue scopes, and do not claim a failing test, code fix,
issue closure, or Trust CI result. The prior disposition is the durable
repository-local evidence; the only missing input is an authoritative external
owner/link for #36.

## Exact research commands

```bash
git fetch --all --prune
python3 scripts/grok_status.py
rg -n -S '(#186|issue.?186|#36|issue.?36|exit-status|exit status|recorder|owner)' \
  engineering docs README.md .github
git log --all --oneline -S'#186' -- .
git log --all --oneline -S'#36' -- .
git log --all --oneline -S'exit-status' -- .
```
