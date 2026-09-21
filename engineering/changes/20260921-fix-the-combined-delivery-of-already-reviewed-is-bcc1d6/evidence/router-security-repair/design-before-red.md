# Router security-signal regression: prepared repair

Route `bcc1d645c438`; sole writer `integration_implementer`. Frozen source baseline: `4a8e8925478e390d7bf12f2bf4faab8fc0e0c70c`.
Status: proposal only. No batch working-tree/index edits, tests, product imports, compilation, lint, Docker, database work or behavioral probes have been performed for this preparation. Wait for the coordinator to release both the review freeze and the CPU lane.

## Root cause and bounded scope

Static comparison against delivered main `839d3aa26bc90417424d814ee48d8b5cd3be367e` confirms the reported regression. The original domain scorer treated configured `auth` and `роль` as substrings. The #156 matcher now routes every word-shaped term of four or fewer characters through the whole-word predicate. Full security words such as `authentication`, `authorization`, British `authorisation`, abbreviations `authn`/`authz`, and `ролью` consequently lose the security domain. `_risk` already uses whole-word `auth`, so it supplies no alternative signal for these isolated inputs; downstream risk, skill, reviews, receipts and gate obligations disappear.

The intended short-token boundary fix remains necessary: returning to substring matching would incorrectly restore security matches for `author`, `authority`, `authentic`, or a larger Russian word such as `гастролью`. The correction belongs only in the shared domain matcher, used by real `build_route` and `is_development_prompt`. This tree has no `looks_like_development_prompt` function.

After measured RED, add a finite, documented alias vocabulary for these two canonical configured security terms only. Match every alias through the existing Unicode-aware whole-word predicate. Keep the configured short word itself valid and leave other domains, abbreviations, long stems, intent/risk selection, owner precedence, review/gate logic, runtime reader and authority rules unchanged.

Proposed finite vocabulary, all semantically meaningful words already recognized by the original `auth`/`роль` substring implementation:

- `auth`: `authn`, `authz`; `authenticate`, `authenticates`, `authenticated`, `authenticating`, `authentication`, `authentications`, `authenticator`, `authenticators`; `authorize`, `authorizes`, `authorized`, `authorizing`, `authorization`, `authorizations`; British `authorise`, `authorises`, `authorised`, `authorising`, `authorisation`, `authorisations`; `reauthenticate`, `reauthenticates`, `reauthenticated`, `reauthenticating`, `reauthentication`, `reauthentications`; `unauthenticated`, `unauthorized`, `unauthorised`.
- `роль`: `ролью`. Other Russian case forms that never contained `роль` are outside this compatibility repair.

`matched_keywords` continues to contain the canonical configured term (`auth` or `роль`) when either it or one of its documented aliases matches. It is diagnostic evidence naming the matched routing rule, not a verbatim token excerpt. Document this explicitly beside the alias table/matcher and in the integration repair evidence; no new route field or reader exception is required. Alias matching must not increase that canonical term's score when several synonyms appear together.

No product repair patch has been written before measured RED. The planned implementation is a small local alias table plus an explicit fallback in the existing short-keyword matching branch, using the existing word predicate.

## Prepared test-only patch

`router-security-tests.patch` adds three methods to `tests/test_repo_router.py` against the exact baseline file. Patch SHA-256: `adef4213bdd01d9ecd21843a8d8ef61f8de3828cbc08784527f0fc80217130e1`.

1. `test_security_aliases_keep_high_risk_route_obligations`: 42 literal prompt cases, including standalone existing `auth`/`роль`, the reported US/British/abbreviation/Russian aliases, representative authenticated/unauthorised/reauthentication forms, uppercase and punctuation boundaries. Each real route must retain exactly the security task/domain, high risk, high-risk complexity, security skill, security/release reviewers and evidence, and `scope_and_design_approval`. It also checks the canonical explanatory match.
2. `test_security_aliases_are_development_signals_without_intent`: eight neutral observations with no implementation-intent keyword. These exercise the actual `is_development_prompt` entry point and cannot pass merely because `Fix` caused the intent shortcut.
3. `test_security_alias_boundaries_do_not_route_unrelated_words`: thirteen unrelated or embedded-token negatives, including `author`, `authority`, `authentic`, `xauthn`, `authz_name`, `xauthentication`, `authorizationx`, `authorisation_name`, and `гастролью`. Real routes must remain generic/low/micro, with no security skill/review/evidence/gate; neutral prompt detection must remain false.

Empty temporary repositories isolate the task signal from repository-derived domains. Literal expected obligations are independent of the matcher and configuration vocabulary. The supported base-commit/fingerprint overrides supply irrelevant fixture metadata without mocking route construction, domain detection or obligation selection and avoid needless Git subprocesses.

## Execution sequence after release

First confirm the target source/test bytes still match `proposal.json`. Apply only the test patch; do not apply product changes yet. On the exclusively allocated lane run this exact RED command from the batch worktree:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.test_repo_router.RouterTests.test_security_aliases_keep_high_risk_route_obligations \
  tests.test_repo_router.RouterTests.test_security_aliases_are_development_signals_without_intent \
  tests.test_repo_router.RouterTests.test_security_alias_boundaries_do_not_route_unrelated_words -v
```

Estimate only: 1–5 seconds; reserve a 15-second slot. No execution duration or failure count is yet measured. Expect genuine assertions in the two positive methods while the negative controls and explicit standalone tokens retain existing behavior; any import/setup error must be investigated instead of being recorded as successful reproduction.

After the coordinator sees measured RED, implement the bounded alias fallback and run the same focused command for GREEN. Then, within separately allocated lane time, run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_repo_router tests.test_workflow_artifacts -v
```

This adjacent command exercises the original short-token negatives, standalone specialists, persistence and bounded route reader together. The coordinator still owns the mandatory full combined verification, independent renewed review wave and final fingerprint receipts. No old full result or exact-source parity proof can certify the repaired product tree.

## Evidence and recovery

Preserve the original batch source-identity report and failed code/security/test reviews as historical facts. Add a distinct integration-repair record with the measured RED/GREEN commands, exit codes, durations, source/test hashes and narrow delta against `4a8e8925`; update the current identity claim to say these two paths intentionally differ from the imported #156 candidate. Do not rewrite original source package evidence.

The coordinator owns shared README/bootstrap and learning records. Suggested mistake fact: preserving short-token boundaries by token length alone treated semantic security abbreviations as unrelated lexical tokens; previous tests omitted isolated authentication/authorization obligations, allowing the suite to pass while dropping security reviews and gates. Preserve representative legitimate inflections alongside false-positive controls when narrowing keyword recognition.

Recovery remains a source-only corrective PR; no host, database, external policy or deployment change is involved. Newly corrected routing affects subsequently generated routes and does not retroactively manufacture evidence for existing packages.
