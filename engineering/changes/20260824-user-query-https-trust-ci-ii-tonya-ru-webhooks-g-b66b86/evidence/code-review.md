# Code review — retract ChatGPT Trust CI webhook URL

**Agent:** `code_reviewer` (read-only)  
**Route:** `b66b867ba5ab`  
**Change:** `20260824-user-query-https-trust-ci-ii-tonya-ru-webhooks-g-b66b86`  
**Verdict:** **PASS**

User (verbatim): `https://trust-ci.ii-tonya.ru/webhooks/github нет , не трогаем, это ошибка chatgpt`.

This slice is docs + characterization only. The retraction itself matches the brief. Parent implementation (instead of spawned `integration_implementer`) is a **process note**, not a product defect.

## Diff inspected

Tracked mutations that belong to this retraction:

| File | Role |
| --- | --- |
| `trust-ci/tests/test_m0_invariants.py` | `test_operator_docs_do_not_present_chatgpt_webhook_as_live` forbids URL **and** hostname in plan, spec, activation report, README, `decisions.md`. Does **not** scan `mistakes.md` or `engineering/changes/**`. |
| `decisions.md` | New void entry; Apache leftover rewritten **without** `trust-ci.ii-tonya.ru`. `TRUST_CI_PUBLIC_BASE_URL` stays loopback. |
| `mistakes.md` | Names `https://trust-ci.ii-tonya.ru/webhooks/github` as the ChatGPT-as-operator-truth mistake. |

Untracked but in-scope for the optional brief banners:

| File | Role |
| --- | --- |
| `engineering/changes/…cec0c7/brief.md` | One-line **RETRACTED 2026-08-24** banner at top. Body left as history. |
| `engineering/changes/…010964/brief.md` | Same banner; Apache leftovers called out as untouched. |

**Not in this retraction:** `trust-ci/src/**`, `trust-ci/compose.yaml`, gitignored env, Apache/DNS/certbot, GitHub App hook API.

Working-tree dirt **outside** this change (other packages’ `state.json`, other untracked change dirs) is not part of the retraction and was not treated as merge-ready product.

## Must-confirm checklist

| Requirement | Result |
| --- | --- |
| FastAPI / compose / gitignored env **not** changed | **Pass.** `git diff` has no `api.py`, `webhooks.py`, `compose.yaml`, or `env/`. |
| GitHub App webhook **not** set to the ChatGPT URL; no repo webhook; no PEM read | **Pass.** No GitHub API / JWT / PEM usage in the implementation path. Test and docs forbid that URL as a live target. Implementation report states no GET/POST of the ChatGPT URL. |
| Host Apache / DNS / certbot **not** modified this slice | **Pass.** `не трогаем`. Decisions keep leftover Apache as leftover, not as live edge. |
| ChatGPT URL/hostname absent from `decisions.md`, plan, spec, activation report, README | **Pass.** `rg` on those five files: no `trust-ci.ii-tonya.ru`. Plan still uses placeholder `https://<ci>/webhooks/github`. |
| `mistakes.md` names the URL as a mistake | **Pass.** Symptom quotes `https://trust-ci.ii-tonya.ru/webhooks/github`. |
| Sibling briefs have retraction banner; `evidence/**` not rewritten | **Pass.** Banners on `cec0c7` and `010964` briefs. Sibling `evidence/` files still contain historical URL (allowed). This change’s analysis evidence is history of the analysis wave, not rewritten sibling evidence. |
| M0.2 not claimed complete | **Pass.** Plan checkbox remains `[ ] Register repo webhook … **not done**`. Implementation residual risk: public GitHub delivery still absent; loopback HMAC only proven path. |
| Parent implemented because `integration_implementer` spawn was denied by stale `general_implementer` | **Process note only.** Implementation.md records hook deny (`Another write agent is already active: ['general_implementer']`). Diff is still the approved retraction. Not a product defect. |

## Test vs surrounding implementation

The new invariant is the right characterization: a URL-only `assertNotIn` would have been green before retraction because plan/spec/README never had the exact ChatGPT URL; the leak was the **hostname** in `decisions.md`. Forbidding both in the five operator docs, while allowing `mistakes.md` and change-package history, matches architect + requirements.

Sibling brief **bodies** still describe the ChatGPT URL as the intended App webhook / TLS target. That is historical package text, not scanned by the invariant. Banners are the operator stop sign. Do not treat `cec0c7` brief body as current instruction.

## Findings

None blocking.

**N1 (info):** Unrelated `state.json` dirty files (`9d97f8`, `d5291e`) sit in the same working tree. They are not this slice. Do not bundle them into the retraction commit.

**N2 (info):** Stale `general_implementer` lock remains a workflow hazard for future write-agent spawn. Out of grant to clear.

## Residual (unchanged, correctly not “fixed”)

- Host Apache HTTP leftover may still exist; user ordered not to touch it.
- App webhook URL was never applied (JWT/PEM forbidden) and must not be set to the ChatGPT URL.
- M0.2 public webhook remains **not done**.

## Pass / fail

**PASS.** Retract ChatGPT hostname from operator truth; freeze FastAPI, compose, env, GitHub hook config, and host TLS; log the mistake; banner siblings; do not claim M0.2 complete.
