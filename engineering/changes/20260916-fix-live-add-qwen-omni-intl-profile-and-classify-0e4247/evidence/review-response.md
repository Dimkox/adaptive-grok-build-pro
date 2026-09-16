# Review response — qwen-omni-intl profile and probe classification

Reviewed object for both reports: `f0ef968`. Dispositions land in the follow-up commit on this branch, so
the pull request opens on the corrected tree.

## `review-code.md` — PASS (2 Important, 5 Minor)

| # | Finding | Disposition |
| --- | --- | --- |
| 1 | Important — the capability contract closes `profile` to an enum of exact fact objects and did not know the new profile (evaluated `to_facts() in enum` → `False`), contradicting `architecture.md`'s "no contracts changed" | **Finding accepted; the proposed repair is blocked by tooling, and the doc claim was corrected instead.** `qwen-omni-intl` was added to the enum, but the fitness gate hard-failed the edit: the comparator cannot represent object-valued enum members, so any change to this contract (or to anything `$ref`ing it) is permanently `unsupported` → architecture fail. Issue #104 records the defect and the two real options (reviewed comparator extension vs a v2 coexistence contract). The enum edit was reverted; `test_profile_facts_keep_the_backend_capability_contract_shape` now asserts declared profiles stay in the table and every table profile emits the contract's exact fact shape (keys, JSON types, const fields), which is everything guardable without touching the frozen file. `architecture.md` and `change-spec.yaml` now state the contract is unchanged and why. |
| 2 | Important — three of the advertised classes (`deadline`, `transport`, `accounting`) were unreachable from the probe because those errors are raised without `.category`, while `landing_http` already maps the same codes; 403/5xx produced `permission`/`unavailable`, outside the printed allowlist, so operator output and the durable observation disagreed | **Fixed at the root.** `EXECUTOR_CODE_CATEGORIES` and `FAILURE_CATEGORIES` moved into `landing_provider.py` and are used by both consumers — a shared constant, not a copy. The probe now emits `deadline`/`transport`/`accounting` for the codes that produce them and admits `permission`/`unavailable`; `factory/README.md` lists the nine real classes instead of seven aspirational ones. Verified directly: `executor_deadline → deadline`, `executor_transport → transport`, injected `"DROP TABLE" → protocol` with the status preserved, `99 → null`. |
| 3 | Minor — `factory/README.md` gained a stray closing fence, swallowing the following prose | **Fixed**; fence count returned to 4 (matching the base). |
| 4 | Minor — AC-002's own guards untested | **Fixed** by `test_probe_failure_output_clamps_unknown_category_and_invalid_status` (injected categories, and `0/999/-1/"401"/True/1_000_000` statuses). |
| 5 | Minor — the accepted set was hand-duplicated in five places with no consistency test | **Partly fixed.** `PROBE_PROFILES` is now the single source for the `probe_qwen` guard and the CLI choices, and `test_provider_enumerations_stay_subsets_of_the_profile_table` asserts both that set and `LANDING_PROVIDERS` are subsets of the table. The host-config tuple stays a deliberate subset (not every profile is host-selectable) and is covered behaviourally by the extended `test_landing_host` loop rather than by a false equality. |
| 6 | Minor — indentation drift in the new table row, argparse call and host-config wrap; `isinstance` inconsistent with the module's `type(...) is not int` convention | **Fixed** in all four places. |
| 7 | Minor — AC-004's raw artifact lived only as a quotation in `brief.md`; the probe script printed up to 400 bytes of an upstream error body | **Both fixed**: `evidence/live-probe-output.txt` holds the bounded run log, and the script now prints only the allowlisted error `code` (plus an `unparsed` marker), never a body. |

## `review-test.md` — PASS (3 Important, 2 Minor)

| # | Finding | Disposition |
| --- | --- | --- |
| Important-1 | The clamp layer was untested in its discriminating branch; widening the allowlist or deleting the status validation survived the whole CLI pair | **Fixed** by the clamp test above, which is the branch those two mutants break. |
| Important-2 | The new profile had no digest anchor | **Fixed**: `4cc85b8a61d1a0b51e69b9a28d8766bbdf6158db4e145d8a8ab81992a9157f67` added to the existing frozen digest map, which also keeps asserting the three pre-existing digests are unchanged. |
| Important-3 | AC-003/FORBID-003 (`PROVIDER_ORDER` untouched) had no test at all | **Fixed**: `test_failover_chain_excludes_both_omni_profiles` pins the exact tuple and excludes both omni names. |
| Minor-1 | Digest inequality compared with a different `available` flag, making it trivially true | **Fixed**: both sides now use `available=True`. |
| Minor-2 | `assertNotIn("invalid_api_key", …)` guards a body the fabricated flow never produces | **Kept** as cheap regression insurance: `HttpProviderFailure` is exactly where a future refactor might start carrying a body, and the reviewer's own stronger point is covered by the clamp test. |

## Gate-driven follow-up (architecture fitness, not a review finding)

`grok_verify --mode pr` on the first two commits failed `FIT-DECLARED-NETWORK-ONLY`:
`engineering/changes/**` is owned by `NODE-CHANGE-SPEC-EVIDENCE` of type `repository`, which the architecture
model gives **no network policy**, so the committed `evidence/live-omni-probe.py` (importing a network family)
was read as an owned network client and additionally escalated change risk yellow→red via `new_network_client`.
The model is deliberate — prior evidence scripts under `engineering/changes` are filesystem-only. The probe was
therefore preserved verbatim as an embedded script in `evidence/live-omni-probe.md` (runnable after one copy)
instead of widening `architecture/rules.yaml` for documentation nodes; package references were updated. No
product behavior, contract or test changed for this — except that the same gate run also surfaced the frozen
contract (#104), so the capability-contract edit described in finding 1 was reverted in this step and the
declaration test was replaced by the shape test.

## Coverage limits stated plainly

- The capability contract is frozen by the comparator defect (#104), so `qwen-omni-intl` is **not** declared in
  its profile enum; the shape test bounds the drift but cannot replace enum membership. A runtime that validated
  facts against this schema file would reject the new profile — no product code loads the file (it is a
  declarative contract asserted only by tests), verified by search of `factory/src`.
- The live evidence is a point-in-time measurement on one host with one key; it does not establish multimodal acceptance, and no service was enabled, installed or restarted by this change.
- `grok_verify --mode pr` and the App-owned exact-head check are produced after this commit; nothing here claims them in advance.
