# Red/green and measurement record — issue #202 contour

All commands ran in `/home/pall/grok-projects/adaptive-grok-build-spec202` on branch
`fix/issue-202-evidence-expectations` (base `cb9af4073ba6c3d515145164d771c75ebdfa3224`, session tag
`qwen-202`) on 2026-09-25. The "before" validator and schema in the comparison below were extracted with
`git show HEAD:<path>` into a private tree, so the baseline is the shipped code, not the edited worktree.

## 1. Reproduced before the fix

A criterion declaring an exact expectation set where one member has no probe was silently accepted:

```text
BEFORE (cb9af407 validator+schema): ACCEPTED {'ok': True, 'digest': '32bc84805158eec81f8fb60ba61e90db9d5d0b43c7ed1d9391e39477acadf197'}
AFTER  (working tree): REJECTED -> acceptance criterion AC-001 declares the exact expectation set member
  'frozen-plan-text' without a liveness proof: no test evidence of AC-001 names 'frozen-plan-text', so the
  member cannot be shown reachable; either attach a test that produces 'frozen-plan-text' through its own
  detector path, or declare the set as an upper bound and assert non-emptiness
```

Document under test: `After the config flip the historical verifier reddens exactly {css-link-count,
frozen-plan-text}; the comparison is a literal set equality.` with `test` evidence naming only
`css-link-count`. This is the scrubbed shape of issue case 1: the unprovable member is the one whose detector
reads a frozen historical artifact.

The second half of the reproduction is the repository-wide measurement: with the shipped validator, **0** of
the criteria in the 106 recorded packages declare any brace group at all, i.e. no static check has ever looked
at such a declaration. The defect class was invisible, not tolerated.

## 2. Contract compatibility, measured

`python3 /tmp/issuewave/beforeafter202.py` — gate-validates every recorded package with both the shipped and
the repaired validator over the same tree:

```text
packages=106
gate_rejecting_packages=15 verdict_diffs=0
historical_packages_with_new_findings=0
```

The 15 rejecting packages are pre-existing (draft-era specs with `UNKNOWN` objective fields plus this
contour's own scaffold at the moment of the run); they reject identically in both validators.
`verdict_diffs=0` is the acceptance evidence for "existing specs in `engineering/changes/**` must still load"
— no historical package was edited.

The rejected prose form of issue #202 item 3 was measured the same way before being dropped: 40 criteria match
an "all/every … equals V" pattern, of which **9** carry only `receipt` evidence and would newly fail a
fixture-requiring rule. That is why item 3 is not enforced here.

## 3. Negative control (mutation battery)

Each mutant was written to a private copy with its own schema tree; the new module ran against it.
`killed=n/19` is the number of tests that failed, so a nonzero value means the suite detects the weakening:

| Mutant | Change | Result |
| --- | --- | --- |
| M1 | exact-set branch disabled | killed=11/19, dead-member spec ACCEPTED |
| M2 | member extraction disabled | killed=12/19 |
| M3 | probe match inverted | killed=15/19 |
| M4 | non-emptiness clause removed | killed=1/19, upper bound accepted |
| M5 | any evidence kind proves liveness | killed=1/19 |
| M6 | placeholder filter removed | killed=1/19 |
| M7 | rule restricted to the gate profile | killed=1/19 (draft test fails) |
| M8 | placeholder guard removed at the eligibility step | killed=1/19 |
| M9 | rule computed but not wired (warning-only) | killed=4/19 |

The unmutated baseline reports the intended four cells:
`dead-member=rejected  fully-probed=ACCEPTED  upper-no-nonempty=rejected  upper-nonempty=ACCEPTED`.

## 4. Local verification actually run

- `python3 -m unittest tests.test_spec_expectation_sets -q` → `Ran 19 tests ... OK`
- Full parallel sweep over all 38 `tests/test_*.py` modules with `xargs -P 4`: no `FAIL` line printed.
- `python3 -m ruff check .grok-stack/adaptive_grok scripts tests` → `All checks passed!`
- `git diff --check` → exit 0 (the single trailing-whitespace line in
  `.grok-stack/templates/change/requirements.md` is pre-existing scaffold debt at HEAD, tracked as #211; only
  its line number moved).
- `python3 scripts/grok_spec.py validate <this package>/change-spec.yaml --gate --json` →
  `ok= True profile= gate errors= []`, criterion coverage 5/5 and 10/10 across categories,
  digest `f2bcc95e99f5b5ed0a04a009c078510e48bf2f29f571d67994980fabf4020170`.
- `python3 scripts/grok_verify.py --mode pr` (one authoritative run, 2026-09-25T00:45:58Z→01:04:46Z),
  every step `PASS` (`workflow-artifacts` `SKIP`, not configured) and:

```text
RESULT: PASS | mode=pr profiles=base,contracts | changed=19 checked=0 focused_tests=none
```

The run recorded a passing `verification` receipt for route `113055515b8e` bound to
`spec_digest f2bcc95e...` and `tree_fingerprint dd704030bc45afdf...`. That fingerprint covers the tree at
01:04:46Z, which is the pre-commit content of this same delivery; any later commit — including this evidence
file — moves HEAD and makes a fresh verifier run necessary before a receipt may be claimed against it.
