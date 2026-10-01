# Repository analysis

The five commits `f3fab717b..5c06cc146` form a 15-path decision-persistence delta over old parent `fa49dc35`. Their paths do not overlap the four PR230 tail fixes. `git merge-tree` predicts a clean replay onto `01b089fcb`; preserve patch IDs and ensure obsolete-base verifier paths disappear from the final diff. Candidate was not modified by the analyst.
