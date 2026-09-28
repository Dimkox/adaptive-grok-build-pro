# Test review — does `tests/test_spec_expectation_sets` lock issue #202?

## Verdict

The module does not lock issue #202. It locks most of the prose grammar this change chose for proposal item 1, including the previous review's named holes (textual selector tokens, cross-entry member assembly, plural `allowed deviations`, exact `{A, B}`, sentence-local `exactly`, and the route-base error census). It does not lock proposal items 2 or 3, and it does not lock the mutation/undo callable shape the issue and AC-002 require.

Issue: https://github.com/Dimkox/adaptive-grok-build-pro/issues/202 (open). Proposal item 1 is a per-member liveness proof or a non-empty upper bound. Item 2 is a scope-gate read-path for a detector that lives in another change's immutable evidence. Item 3 is a committed producer-output fixture for rules of the form "all keys of class K equal V".

HEAD `69585da2955a2ee0ba15ad7784ba04a38bf5e143`. `tests/test_spec_expectation_sets.py` SHA-256 `77cb8d439e129faf231d83131d0b6e04765ff094a113755ebd79fa45e72f982a`. `.grok-stack/adaptive_grok/spec.py` SHA-256 `ca24c500c8145cd519d284564fa93fe3144d997d20e4f5cdac0599c2626120ba`. Before this report, `git status --porcelain=v1` showed only the pre-existing untracked `engineering/changes/20260925-reject-unsatisfiable-expectation-set-members-in-113055/evidence/next-gap.md`. `git diff --stat` was empty. Startup CPU measurement and `adaptive_grok.util.tree_fingerprint` were not recorded: the shell circuit breaker blocked that objective after an ambiguous-sensitive-shell denial, and it was not retried.

reviewed-tree-modified: no

## What the 31 tests do lock

`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_spec_expectation_sets -q` on the candidate: `Ran 31 tests in 0.716s` / `OK`.

The same command in the scratch snapshot below: `Ran 31 tests in 0.730s` / `OK`. One focused rerun of `ExpectationSetTests.test_dead_member_of_an_exact_set_is_rejected_and_named` also passed (`0.018s`).

Those runs lock the following item-1 claims by assertion:

- An exact set `{css-link-count, frozen-plan-text}` with a probe only for `css-link-count` fails in the gate and draft profiles, names `AC-001` and `'frozen-plan-text'`, and does not treat the finding as a warning (`SpecError` code `incomplete`).
- The same shape on invariants and forbidden outcomes is rejected.
- Both members pass only when resolvable `unittest` selectors call the trusted helper with those literals. One selector may carry both calls. Empty evidence does not.
- Nonexistent selectors, a method with no helper call, a wrong literal, a local pass-only lookalike, a module-level rebinding of the imported helper, a helper call nested in an uncalled function, a local `TestCase` lookalike, and assembling `alpha` plus `agents` into `alpha-agents` are rejected.
- `receipt`, `attestation`, and `production_signal` evidence do not prove a member. Evidence that names a different member does not.
- `subset of {…}` without a non-emptiness cue is rejected; `non-empty subset` is accepted. Plural `allowed deviations` is an upper-bound cue.
- `{TITLE}`, `{0, 1}`, `{X}`, `{"a": 1}`, `{}`, a brace list with no local quantifier, and `exactly` in a previous sentence are not obligations. Exact `{A, B}` is an obligation.
- Malformed criterion rows are skipped. The path API reports the spec path. The helper itself checks absent, produced, and restored.
- AC-005 compares full gate errors of the current validator with `git show 5713b407818dbb6c2d1acfcb0b0d9661c32e1153:.grok-stack/adaptive_grok/spec.py` for every committed `engineering/changes/**/change-spec.yaml` at that base (the test requires more than 90). Criterion keys stay equal to the example holdout's pinned `id` / `statement` / `evidence` set.

## What is not locked

Proposal items 2 and 3 have no test. The module never mentions `verification_scope`, a detector read-path, `NOT_ATTEMPTED`, or a producer sample. Passing this file leaves both issue cases reproducible: a frozen-text detector can still be declared satisfiable by a toy probe, and a universal literal can still contradict its producer.

The toy probe is the hole inside item 1 as well. `ExpectationSetProbeTests` proves `css-link-count` by flipping a dict entry. `test_every_member_with_a_probe_is_accepted` then accepts an exact set once each literal appears in such a call. Nothing requires the cited selector to redden the member through the detector the criterion is about. That does not lock the issue reproduction ("try to redden Y without touching frozen artifacts").

These item-1 obligations are implemented in `.grok-stack/adaptive_grok/spec.py` and named by AC-002 or the architecture note, but no assertion in the module fails if they are removed. Mutation execution of those weakenings was blocked by the shell circuit breaker (details below), so they are unexecuted, not measured kills or survivors:

- `complete_call` at `.grok-stack/adaptive_grok/spec.py:975` requires four positional arguments or the keywords `observe`, `mutate`, and `undo`. Every negative fixture that expects rejection already fails for a different reason (binding, literal, or selector). No fixture is only `exercise_expectation_member("css-link-count")`. AC-002 says the declaration is valid only when those callables are present.
- The same line does not require the keyword values to be callables. `observe=1, mutate=2, undo=3` is not a test input.
- Non-emptiness is applied only to the brace group's sentence (`.grok-stack/adaptive_grok/spec.py:1037`). The cross-sentence test covers `exactly`, not a leading "The observation is non-empty." followed by a later `subset of {…}`. An upper-bound cue in a preface sentence is also untested. Singular `allowed deviation` is accepted by the regex and is not asserted; only the plural form is.
- Function-body rebinding of `exercise_expectation_member` is stripped at `.grok-stack/adaptive_grok/spec.py:954`. The shadow test rebinds only at module level.
- The helper's `finally` undo when `mutate` raises is not asserted. `test_probe_helper_executes_absent_present_restored_contract` covers the three successful-call failure modes only.

`test_upper_bound_with_non_emptiness_is_accepted` calls `expectation_set_findings` without `root`, so it does not show that a dead member is legal inside a non-empty upper bound once probes are resolved. That behavior follows from the code, but this test does not lock it.

## Mutation probes

Scratch parent `/home/pall/.grok-review-private` (mode `0700`, not sticky). Snapshot `/home/pall/.grok-review-private/issue202-69585da2/repo`, also mode `0700`, built with `rsync -a` from the candidate excluding `.git`, `packages`, `__pycache__`, `.venv`, and `node_modules`. The pre-existing untracked `next-gap.md` was included. A temporary symlink to the candidate `.git` let AC-005's `git show` / `git ls-tree` read objects; the unmutated scratch suite passed; the symlink was then removed. After that, `cmp` showed scratch `spec.py`, `spec.py.orig`, and the candidate `spec.py` identical.

Executed probe: unmutated `tests.test_spec_expectation_sets` on the snapshot. Result: 31 tests, OK, exit 0. Candidate HEAD was still `69585da2955a2ee0ba15ad7784ba04a38bf5e143` and porcelain was still only `next-gap.md`.

Not executed, circuit breaker: `python3 -c`, in-place edits of scratch `spec.py`, and later script writes were denied as rewrites of the earlier ambiguous-sensitive-shell objective and were not retried. No kill/survive result is claimed for M1–M11. The unexecuted claims are the bullet list in the previous section.

## Scope note

`brief.md` already says this contour is proposal item 1 only and must not close issue #202. The tests match that narrower grammar except for the unlocked callable, sentence-cue, and in-method shadow edges above. They still do not lock the issue.

VERDICT: FAIL
