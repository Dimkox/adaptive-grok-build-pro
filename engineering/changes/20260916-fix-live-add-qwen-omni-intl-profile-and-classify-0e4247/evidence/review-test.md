PASS

# Test review — f0ef968 (route 0e42477308c4, kind test_review)

Scope reviewed: `factory/tests/test_landing_live_executors.py`, `factory/tests/test_landing_host.py`,
`factory/tests/test_landing_server.py` against production code in `factory/src/adaptive_factory/`
(`landing_http.py:59-62`, `landing_live_executors.py:653-722,747-768`, `landing_host_config.py:32`,
`settings.py:14-17,99-111`) and the contract in `change-spec.yaml`. Baseline verified: commit is HEAD
of `fix/qwen-omni-intl-and-probe-class`, parent `98b7769`, working tree clean.

## 1. Kill power of the named mutations

- (a) `qwen-omni-intl` pointed at the mainland host — **killed**.
  `test_international_omni_profile_is_streaming_and_five_media` asserts
  `base_url == "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"` verbatim
  (test_landing_live_executors.py:834-836). The digest map at :372-375 does not pin this profile,
  so the base_url assert is the sole guard — sufficient for the claim.
- (b) media kinds reduced to `("docx","text")` — **killed**: exact tuple assertion
  `("audio","docx","image","pdf","text") == profile.media_kinds` (:839).
- (c) `_probe_failure_fields` returning the raw exception code as `category` — **killed from both
  sides**: with `str(exc)` as category, the bare-credential CLI test
  (`test_probe_cli_failure_never_prints_exception_or_credential`, side_effect
  `LandingProviderError(self.value)`) would print the value → exact four-key dict equality
  (:816-818) and `assertNotIn(self.value, ...)` both fail; with a `HttpProviderFailure` the raw code
  is `"executor_http"` ≠ `"authentication"` and the exact-dict check at :826-828 fails.
  **But** the allowlist-membership branch itself is not bound: I monkeypatched (in-process probe,
  tree untouched) a variant that passes any `str` category through —
  `d/c' probe: "c': category unallowlisted -> failures: 0 errors: 0"`, and it leaks
  `{"category":"permission","http_status":403,...}` where the real code prints
  `{"category":"protocol","http_status":403,...}`. No test ever feeds a non-allowlisted string
  category ("permission", "unavailable" — both producible by `_http_failure`,
  landing_live_executors.py:68-69). See Important-1.
- (d) `http_status` printed unvalidated (range/type clamp removed) — **NOT caught**. Verified
  empirically: mutant `no_status_validation` → `failures: 0 errors: 0` on both CLI tests. No test
  constructs `HttpProviderFailure` with status 99/600/non-int. Important-1.
- (e) removing `qwen-omni` from `compose_env_landing`'s accepted set (landing_live_executors.py:681)
  — **killed** (static, exact-message reasoning): the gate then raises `LandingProviderError("landing_provider")`,
  while `test_environment_composition_accepts_both_omni_profiles` (:846-853) asserts
  `str(raised.exception) == "landing_path"` for the loop name. Removing `qwen-omni-intl` likewise killed.
  The CLI-choices enumeration (`main`, `--profile` choices) is killed by :823 (argparse `SystemExit(2)`
  before `main()` returns 1). The **probe_qwen-internal accepted set**
  (landing_live_executors.py:721-722) is NOT killed for `qwen-omni-intl` — every CLI test patches
  `probe_qwen` away and the real-probe tests use the default `qwen-intl`. Important-3.

## 2. `test_environment_composition_accepts_both_omni_profiles` design

The mechanism (accepted names must fail *after* the gate; unknown name refused *as* provider) is the
right idea, and the refused-branch assertion `== "landing_provider"` is sound. But pinning the exact
string `"landing_path"` pins an incidental ordering inside `compose_env_landing`:
gate → `for_provider` → `qwen_api_key` → `_absolute_env_path` (landing_live_executors.py:681-703,
653-660). A later refactor that hoists path validation into the server preflight, renames the code,
or tightens key parsing would break the test while the real gate behaviour stays correct — a false
alarm, which for a security-adjacent gate is the tolerable direction but still brittle. Stronger
still-cheap assertion: `self.assertNotEqual("landing_provider", str(raised.exception))` for the two
omni names (asserts exactly the claim "passed the provider gate", nothing about which later check
fires), keeping the exact `"landing_provider"` only for the unknown name. Cheap upgrade path: supply
the three `FACTORY_LANDING_*_PATH` absolute temp paths in `environ` and assert the raised code is
neither `"landing_provider"` nor `"landing_path"`.

## 3. Extended CLI expectations

The original purpose is still fully asserted. `self.value` is a per-test `uuid4().hex` used both as
the fabricated credential and as the exception message (setUp :730-736); the exact four-key dict
equality plus `assertNotIn(self.value, output)` (pre-existing test) still forbid exception text and
credential. Printed values are a closed set: `reason` is a literal; `category` is clamped to the
seven-member allowlist else `"protocol"`; `http_status` is `int` in 100..599 or `None`
(landing_live_executors.py:706-716). Attacker-controlled text cannot today reach `category`
production-side either: `_http_failure` (:67-85) derives category from a status-code mapping and
compares body markers against a fixed set — body content is never copied into the exception, only
read. The new authentication/401 test does assert absence of the body marker
(`assertNotIn("invalid_api_key", ...)`); it is weak on its own (the failure is a fabricated
side_effect, so no body exists in the flow) — the load-bearing body-absence property is instead
covered by `test_malformed_provider_unicode_is_closed_at_decoder_and_probe_cli`, which drives the
real executor through `httpx.MockTransport` with a hostile surrogate body and asserts the exact
closed four-key output. Good.

## 4. Determinism and isolation

No network: every provider call uses `httpx.MockTransport` (test_landing_live_executors.py:59-66,
884-892); the three CLI failure tests patch `live.probe_qwen` (:812-815, :823-827) — confirmed
patched-transport/patched-probe, no live calls. No `/etc`, no `~`: credentials only via explicit
`environ=` mappings or a 0o600 file inside `tempfile.TemporaryDirectory` (setUp :730-736); the
process environment is never consulted because `environ` is always supplied. No dependency on
installed release directories in the diff's tests. `test_landing_host.py` binds a real AF_UNIX
socket, but only inside the fixture's temp dir (:334-352) — pre-existing, not network, not touched
by this commit. Observed wall clocks: three landing suites `Ran 95 tests in 3.406s` (real 0m4.272s);
`tests.test_change_spec` `Ran 30 tests in 0.117s` (real 0m0.285s); ruff real 0m0.059s.

## 5. Coverage vs claims

- AC-001 enumerations: host-config `selected_profile` validator — asserted
  (test_landing_host.py:45 loop through `load_host_config`, and it also proves the settings enum
  downstream via `config.settings.landing_provider`); settings enum — genuinely asserted by
  test_landing_server.py:82-83, because `validate_landing` raises the *different* message
  "invalid landing enablement or provider" (settings.py:100-101) before the expected
  "landing paths must be absolute and normalized" (settings.py:111), so reaching the expected error
  requires enum acceptance; env composition — asserted (:846-856); probe CLI choices — asserted via
  argparse at :823. **Only implied:** the `probe_qwen` internal accepted set for `qwen-omni-intl`
  (see 1e; Important-3).
- AC-003 digest independence: existing bindings are really pinned and unchanged —
  `test_all_enabled_qwen_profile_digests_retain_existing_bindings` (:371-381) freezes
  qwen/qwen-intl/qwen-omni digests, and mainland endpoint retention is asserted (:840-842).
  The mainland/intl digest inequality check (:843-844) is apples-to-oranges (`available=True` vs
  default `False`, and `available` is inside `to_facts`), hence trivially true — Minor-1.
  On the frozen map: `qwen-omni-intl` should stay **deliberately excluded** from
  `test_all_enabled_qwen_profile_digests_retain_existing_bindings` (its purpose is "previously
  pinned digests stay valid"; a brand-new profile has no prior binding), but its digest should be
  pinned once somewhere (Important-2 covers a natural home).

## 6. Required command runs (observed)

```
$ PYTHONPATH=factory/src python3 -m unittest factory.tests.test_landing_live_executors \
    factory.tests.test_landing_host factory.tests.test_landing_server -q
Ran 95 tests in 3.406s
OK
(real 0m4.272s)

$ python3 -m unittest tests.test_change_spec -q
Ran 30 tests in 0.117s
OK
(real 0m0.285s)

$ python3 -m ruff check factory/tests -q
(no output, exit 0)
(real 0m0.059s)
```

## Findings

**Important-1 — the clamp layer of AC-002/INV-002 is untested in its discriminating branch.**
`_probe_failure_fields` (landing_live_executors.py:709-715) is defense-in-depth, but no test feeds
(a) a non-allowlisted string category (production-producible: `_http_failure` emits "permission"
for 403 and "unavailable" for 5xx, :68-69) or (b) an out-of-range/non-int `http_status`. Both
mutants (c′ allowlist widened, d validation removed) survive the full CLI test pair — observed
`failures: 0 errors: 0`. AC-002's words "restricted to" are therefore only half bound.

**Important-2 — `qwen-omni-intl` profile facts have no digest anchor.** Its `profile_digest` is
asserted nowhere frozen; any future edit to its HTTP_PROFILES tuple (limits, streaming, media) is
invisible to the suite (base_url/model/media are pinned, but the 18 remaining `to_facts` fields are not).

**Important-3 — AC-003 "PROVIDER_ORDER untouched" and FORBID-003 have no test backing at the named
evidence.** `factory/tests/test_landing_failover_providers.py` (9 tests) never mentions omni or
`PROVIDER_ORDER`; `grep -rn PROVIDER_ORDER factory/tests/*.py` → zero matches. The claim currently
holds only structurally (the commit does not touch `landing_failover_config.py:14`, where neither
omni name appears) — a future commit adding omni to the durable chain would not fail these suites.

**Minor-1 — trivially-true digest inequality** at :843-844 (compare with the same `available` flag,
or drop it: base_url equality already binds the separation).

**Minor-2 — `assertNotIn("invalid_api_key", ...)` in the authentication test** guards against a body
that never exists in that fabricated flow; harmless redundancy given §3's stronger unicode test.

## 7. Residual risk and required follow-up test

Residual risk: the bounded-output promise degrades silently — `_http_failure` and `_probe_failure_fields`
can drift apart (new internal categories like "permission" escaping, or `http_status` bypassing the
clamp) with a fully green suite, because the only failing-input tests bypass exactly those branches.

Required follow-up (single test): a table-driven CLI test patching `probe_qwen` with
`HttpProviderFailure("executor_http", cat, status)` and asserting exact printed dicts for, e.g.,
`("permission",403)→protocol/403`, `("unavailable",503)→protocol/503`, `("authentication",999)→authentication/null`,
`("policy","x")→policy/null` — killing both Important-1 mutants; fold `qwen-omni-intl` into
`test_all_enabled_qwen_profile_digests_retain_existing_bindings` as its own frozen-digest entry
(new map or explicit "additive" case) for Important-2, and add `("qwen","qwen-omni")`-excluded
assertion on `landing_failover_config.PROVIDER_ORDER` for Important-3.

Verdict: **PASS** — all five requested mutations except (d) — and the discriminating half of (c) —
are killed by exact assertions; the suite is hermetic, deterministic and clean (95+30 OK, ruff
silent). The three Important findings are coverage gaps in secondary clamp/failover/digest
properties, not misstated claims.
