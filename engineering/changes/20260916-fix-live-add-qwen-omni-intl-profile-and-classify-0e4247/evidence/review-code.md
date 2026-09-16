PASS

# Independent code review — commit `f0ef968` (route `0e42477308c4`, kind `code_review`)

Base `98b7769` (= upstream main); `git log --oneline 98b7769..f0ef968` returns exactly one commit.
Reviewed the diff plus the surrounding implementation, read-only. Working tree not modified by this review.

## Observed verification output

`PYTHONPATH=factory/src python3 -m unittest factory.tests.test_landing_live_executors factory.tests.test_landing_host factory.tests.test_landing_server -q`

```
----------------------------------------------------------------------
Ran 95 tests in 4.863s

OK
```

`python3 -m ruff check factory/src factory/tests` (tail)

```
factory/tests/test_autonomy.py:4:54: F401 [*] `dataclasses.replace` imported but unused
factory/tests/test_landing_failover_backend.py:88:62: F401 [*] `adaptive_factory.landing_sqlite_store` imported but unused
factory/tests/test_landing_failover_recovery.py:3:8: F401 [*] `json` imported but unused
factory/tests/test_landing_failover_recovery.py:5:8: F401 [*] `sqlite3` imported but unused
factory/tests/test_semantic_persistence.py:1:33: F401 [*] `dataclasses.replace` imported but unused
factory/tests/test_semantic_persistence.py:8:40: `adaptive_factory.contracts.canonical_digest` imported but unused
Found 6 errors.
[*] 6 fixable with the `--fix` option.
```

All six are F401 in files this commit does not touch (cross-checked against `git show --name-only`) → pre-existing, not introduced.
Ruff restricted to the touched files (`landing_live_executors.py landing_http.py landing_host_config.py settings.py test_landing_live_executors.py test_landing_host.py test_landing_server.py`) → `All checks passed!`.

## 1. Table as single source of truth — holds, with one latent contract gap

- `landing_http.py:93-96` — `__post_init__` compares `(provider_id, base_url, model_id, streaming, media_kinds)` against `HTTP_PROFILES[self.profile_id]` and raises `http_profile_identity` on any mismatch; `for_provider` (`:109-114`) unpacks the same tuple. The new row (`:61-62`) is therefore the only place the intl endpoint/model/streaming/media are stated; server, host-config, settings and probe all derive identity from it, and a forged profile object cannot be constructed.
- `landing_server.py` genuinely needs no change, confirmed rather than assumed: `:92` picks `compose_landing_live_qwen` from `profile.provider_id == "qwen"` (new profile's provider_id is `qwen`); `:95` computes `key_name = GROK_API_KEY_ENV if settings.landing_provider in {"grok", "grok-vision"} else QWEN_API_KEY_ENV` → the Qwen name for `qwen-omni-intl`, and `:96-99` routes provider_id `qwen` to `qwen_api_key(env_file=qwen_env_file)`, which selects only `DASHSCOPE_API_KEY` (`landing_live_executors.py:179-190`). The Grok credential cannot be acquired for this profile.
- `available`/`live_enabled` semantics unchanged: `available=True` is still passed only inside the `if not settings.landing_live_enabled: … else:` branch (`landing_server.py:74-89`), and `landing_host_config.py:32` keeps `type(data["live_enabled"]) is not bool` → reject.
- `qwen-omni-intl` is accepted by every gate named in AC-001: host config tuple (`landing_host_config.py:32-33`), `settings.LANDING_PROVIDERS` (`settings.py:15-17`), `compose_env_landing` (`landing_live_executors.py:681`), `probe_qwen` guard (`:722`) and argparse choices (`:748`).

## 2. Probe output stays closed — holds

- Printed surface is only `canonical_json` of four keys (`landing_live_executors.py:758-759`, `:762-763`). `reason` is the literal `"qwen_probe_failed"` in both arms, so a `LandingProviderError` whose `code` is model/provider-influenced (e.g. `landing_provider.py:33` `profile_identifier: {name}`) can never reach the output — `str(exc)`/`exc.args` are never printed.
- `category` is intersected with a 7-element literal set and defaults to the constant `"protocol"` (`:709-713`); `http_status` requires `type(status) is not int` to fail (so `bool`/`str`/`float` are rejected) plus `100 <= status <= 599`, else `None` (`:714-715`).
- The two new `except` arms print no exception message: `except LandingProviderError as exc` (`:754`) feeds `exc` only through `_probe_failure_fields`, and `except (LandingContractError, SettingsError, OSError)` (`:761`) prints hard-coded `"protocol"`/`None`.
- `httpx` cannot escape into a traceback from this path: the executor converts `TimeoutError` → `LandingProviderError("executor_deadline")` (`:367`), `(httpx.HTTPError, OSError)` → `"executor_transport"` (`:371`) and non-200 → `HttpProviderFailure` (`:341`, `:83`), i.e. everything reaching `main()` is one of the caught types.
- Upstream bodies are structurally excluded before classification: `_http_failure` (`:66-83`) derives `category` only from fixed dicts and a fixed marker set, and `HttpProviderFailure.__init__` (`landing_provider.py:48-54`) stores just `category`/`http_status`.
- Against `git show 98b7769:.../landing_live_executors.py`: the pre-change arm printed the same two keys for all four exception types and never leaked either. The change is strictly additive inside the allowlist, so FORBID-001 holds and INV-002 holds.

## 3. Region pairing — internally consistent evidence

`brief.md` quotes `intl/image` and `intl/audio` as `HTTP 200 model=qwen3.5-omni-plus-2026-03-15 finish=stop done=True` with `prompt_tokens_details={image_tokens: 66, text_tokens: 41}` and `{audio_tokens: 2, text_tokens: 37}`, plus the mainland control at `HTTP 401 invalid_api_key`. The echoed model matches the pinned table row, non-zero `image_tokens`/`audio_tokens` show the media actually reached the model rather than being dropped, and the answers match the fixtures that `evidence/live-omni-probe.py:28-57` deterministically builds. The script mirrors the product request shape (`stream: True`, `modalities: ["text"]`, `stream_options.include_usage`) and the endpoints at `:21-22` equal the two table rows. Nothing in `engineering/runbooks/l5-production-runtime.md:34` or `factory/README.md:72` contradicts the code. I did not (and cannot here) reproduce the live call — read-only review, no egress performed.

## 4. No silent live-behaviour change — confirmed

`PROVIDER_ORDER` (`landing_failover_config.py:14`) is not in the commit's file list; the mainland `qwen-omni` row and its pinned digest (`test_landing_live_executors.py:375`) are untouched and still asserted; probe default remains `qwen-intl` (`landing_live_executors.py:748-749`); `factory/runtime/landing-host.example.json:12-13` still ships `live_enabled: false` / `selected_profile: qwen-omni` and was not modified. `git show --name-only f0ef968` = 21 files: the 12 change-package files, `engineering/runbooks/l5-production-runtime.md`, `factory/README.md`, 4 source files, 3 test files. Nothing under `delivery/`, `trust-ci/`, `architecture/` or the root `README.md`.

## 5. Credential hygiene — clean

`git show f0ef968 | grep -nE "sk-[A-Za-z0-9]|/home/pall|/root/|[A-Za-z0-9+/]{60,}"` returned only two lines: `route.json` `base_fingerprint` (a 64-hex git fingerprint) and a Markdown heading — zero credentials, zero absolute user paths. The tests use `self.value = uuid4().hex` (`test_landing_live_executors.py:737`) as the fake key and assert `assertNotIn(self.value, output)`. `evidence/live-omni-probe.py:23-25` reads `DASHSCOPE_API_KEY`/`FACTORY_LANDING_QWEN_API_KEY` from `os.environ` only and exits if absent; `KEY` is never printed. I did not execute that script and did not open any `.env` or credential file.

## 6. Test quality — real, with one coverage hole

- `test_international_omni_profile_is_streaming_and_five_media` asserts the intl `base_url`, the model, `streaming`, the exact 5-kind tuple, that mainland `qwen-omni` keeps `https://dashscope.aliyuncs.com/...` (`:842`) and that the two `profile_digest`s differ (`:844`). Pointing the new row at the mainland host fails it twice (URL equality and digest inequality).
- `test_probe_cli_reports_authentication_class_without_the_body` asserts `{"category": "authentication", "http_status": 401}` and both `assertNotIn(self.value, ...)` and `assertNotIn("invalid_api_key", ...)`, so an `HttpProviderFailure` message/body leak fails it.
- `test_environment_composition_accepts_both_omni_profiles` asserts the omni names now fail later with `landing_path` while `qwen-never` still fails with `landing_provider` — it distinguishes "admitted" from "widened to anything".
- The two extended CLI dicts (`:816-817` and the malformed-draft CLI test at `:~899`) are a deliberate contract widening matching AC-002's "exactly state, reason, category and http_status"; they keep the old absence assertions and add `assertNotIn(self.value, ...)` (uuid-hex code cannot survive a pass-through of `exc`), so they are not tests bent to fit.

## Findings

### Important

1. **The frozen capability schema does not know the new profile** — `factory/contracts/jsonschema/landing-backend-capability.v1.schema.json` closes `properties.profile` to an `enum` of 8 exact fact objects (`enum[7]` = `qwen-omni`); evaluated `HttpLandingProfile.for_provider("qwen-omni-intl", available=True).to_facts() in enum` → `False`. This contradicts `architecture.md` ("single source of endpoint/model/streaming/media facts", "API and event contracts: None changed") and `change-spec.yaml` `contracts.json_schema: []`. It is latent, not active: the only producer is `landing_failover_contracts.py:35` and `landing_failover_config.py:85` refuses any `profile_id` outside `PROVIDER_ORDER`, so no path can emit the invalid document today. Fix by adding the enum entry (with its digests) or by recording an explicit ruling in the package that omni profiles stay outside the capability contract.
2. **Three of the seven allowlisted classes are unreachable from the probe, and 403/5xx mislabel** — `_probe_failure_fields` (`landing_live_executors.py:706-717`) reads only `exc.category`, but `executor_deadline`/`executor_transport`/`executor_usage` are raised as plain `LandingProviderError` with no attribute (`:367`, `:371`, `:382`, `:498-518`; `landing_sse.py:82,89`), so a timeout or a refused connection prints `"protocol"`. The sibling consumer at `landing_http.py:285-288` already maps those same codes to `deadline`/`transport`/`accounting`, so the operator output and the durable observation (SIG-001) diverge for one failure. Likewise `_http_failure` yields `"permission"` for 403 and `"unavailable"` for 5xx (`:67-69`), neither in the probe allowlist, so both print `protocol` while still showing the real status. `factory/README.md:72` advertises all seven as printable. Reuse the existing code→category map (a shared constant, not a copy) so `deadline`/`transport`/`accounting` become reachable, or narrow the documented set to what the probe can actually emit.

### Minor

3. `factory/README.md:73` adds a bare ``` with no opening counterpart: `grep -c '^```'` is 5 here vs 4 at `98b7769`, so the following prose ("It sends one fixed synthetic request…") renders inside an unterminated code block.
4. AC-002's own guards are untested: no test raises an `HttpProviderFailure` with a non-allowlisted `category` string, nor an `http_status` outside 100..599 (e.g. 0, 999, `True`, `"401"`), which `requirements.md` "Failure and edge cases" names explicitly. The `None`→`protocol` branch is covered only indirectly.
5. The enumeration is duplicated by hand in five places (table row, host-config tuple, settings frozenset, `probe_qwen` guard `:722`, argparse choices `:748`) with no consistency test asserting each literal set is a subset of `HTTP_PROFILES`; `:722` and `:748` are two copies of the same four names. One parametrised test would prevent the next profile from being admitted at only some gates.
6. Style drift the linter does not select here: the added table row's continuation is over-indented (`landing_http.py:62`) and the argparse continuation is under-indented (`landing_live_executors.py:749`), as is the `landing_host_config.py:32-33` wrap; `isinstance(category, str)` at `:711` is inconsistent with the `type(...) is not int` convention used one line below.
7. AC-004's raw artifact is not in the repository: `evidence/` holds only `live-omni-probe.py` and a 3-line placeholder `README.md`; the live transcript survives only as a quotation in `brief.md`. Saving the bounded run output (it contains no credential by construction) would make the P0 claim durable. Separately, `evidence/live-omni-probe.py:81-82` prints up to 400 bytes of an upstream error body — acceptable for a one-shot operator script and outside FORBID-001's scope (the product probe), but it is the one place provider body text could enter a transcript.

## Verdict

No Critical finding; INV-001, INV-002 and FORBID-001..003 hold as written, AC-001..AC-004 are satisfied by the code plus the quoted live measurement, 95 tests pass and the touched files are lint-clean. The two Important findings are a latent contract-enumeration gap and an incomplete (never unsafe) classification, both closable in this pull request without touching the trust boundary or live routing. **PASS with the two Important findings to be closed or explicitly ruled on before merge.**
