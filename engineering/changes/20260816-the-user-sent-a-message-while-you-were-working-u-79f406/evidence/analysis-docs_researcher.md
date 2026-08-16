# Docs research — current product-state facts the README must state

Route: `79f406e449de`. Change: `20260816-the-user-sent-a-message-while-you-were-working-u-79f406`.

Question: quote the facts the README must state as current product state: VERSION 2.0.8, CHANGELOG 2.0.8 still says engineering/ paths (stale vs root logs), GitHub Latest is v2.0.7, no v2.0.8 tag, GHA banned, no pyproject.toml, Stop hook warns, self-learning first in AGENTS.md.

Read-only. No APIs invented. No `.env`. No push / merge / deploy.

Loaded `/adaptive-delivery` from `.grok/skills/adaptive-delivery/SKILL.md`. This agent is in `allowed_agents`. `write_agent` is `ai_implementer`. `workflow_skills` are `adaptive-delivery` + `feature-workflow` + `ai-rag-change`. `human_gates` are empty. Required evidence: `verification`, `code_review`, `test_review`, `security_review`.

---

## Verdict

Every named claim is a standing fact. The README is the current-state document (not a historical changelog). It must say these things so a human or LLM can pick up the tree without treating CHANGELOG 2.0.8 or GitHub Latest as if they matched HEAD.

| Fact the README must state | Standing? | Source |
| --- | --- | --- |
| Tree identity is **VERSION 2.0.8** | **Yes.** | `VERSION` = `2.0.8`; README H1 already `# Adaptive Grok Build Pro v2.0.8`; `tests/test_structure.py` `test_version_is_2_0_8_and_github_actions_are_absent` |
| CHANGELOG **2.0.8** still names **`engineering/decisions.md` / `engineering/mistakes.md`** | **Yes. Stale vs live root logs.** | `CHANGELOG.md` §2.0.8; live sinks are root `decisions.md` / `mistakes.md`; `engineering/` files are two-line stubs |
| GitHub **Latest is v2.0.7** | **Yes. Live.** | https://github.com/Dimkox/adaptive-grok-build-pro/releases/latest titled Adaptive Grok Build Pro v2.0.7 on `02376cc` |
| **No v2.0.8 tag** and no GitHub Release `v2.0.8` | **Yes. Live.** | Local tags stop at `v2.0.7`; `/releases/tag/v2.0.8` is 404 |
| **GitHub Actions banned** | **Yes.** | `decisions.md` 2026-08-16 Never GitHub Actions; CHANGELOG 2.0.8/2.0.7/2.0.6; `.grok-stack/templates/ci/README.md` |
| **No `pyproject.toml`** (also no `requirements.txt` / `setup.py`) | **Yes.** | `decisions.md` 2026-08-16 Ruff lives in ruff.toml; `test_product_tree_has_no_packaging_markers` |
| **Stop hook warns** (does not block) | **Yes.** | `AGENTS.md` Verification; CHANGELOG 2.0.7/2.0.4; `.grok/hooks/README.md`; README Hooks already says “Stop warning” |
| **Self-learning is first** in `AGENTS.md` | **Yes.** | `AGENTS.md` first `##` is `## Agent self-learning`; `test_agents_md_starts_with_self_learning` |

`engineering/adr/` is empty. `engineering/contracts/{openapi,asyncapi,schemas}/` are empty. There is no product API, OpenAPI, or ADR that names a README current-state section. Do not invent one.

This change’s `release.md`: “Docs only. VERSION 2.0.8. No tag unless user later asks to publish.” Do not treat this README rewrite as a `gh release create`.

---

## Sources

Standing (authority):

- `VERSION` (single line `2.0.8`)
- `CHANGELOG.md` §§2.0.8, 2.0.7, 2.0.6, 2.0.4
- `README.md` (current tree; K10 already landed in a13da8)
- `AGENTS.md` `## Agent self-learning` + Verification + Prohibited routine actions
- Root `decisions.md` / `mistakes.md`
- `engineering/decisions.md` / `engineering/mistakes.md` (stubs)
- `QUICKSTART.md` (version-silent; no current-state block)
- `.grok/skills/adaptive-delivery/SKILL.md` §7
- `.grok/skills/feature-workflow/SKILL.md`
- `.grok/hooks/README.md`, `.grok/hooks/stop_gate.py`
- `.grok-stack/templates/ci/README.md`
- `engineering/runbooks/publish-v2.0.{7,8}.md`
- `packages/README.md`
- `dist/RELEASE-NOTES.md` (same stale 2.0.8 engineering/ bullets as CHANGELOG)
- `tests/test_structure.py`
- `LICENSE` MIT
- Live GitHub: `/releases/latest`, `/releases/tag/v2.0.8`
- Local `.git/refs/tags/` (`v2.0.0` … `v2.0.7` only)

Predecessor packages that already recorded the same snapshot:

- `20260816-user-query-пересобирай-себя-под-следущей-версией-37141f` (2.0.8 identity; Latest stays v2.0.7; no tag)
- `20260816-user-query-я-все-еще-не-вижу-файлов-из-промпта-д-ba1615` (root logs vs CHANGELOG `engineering/` ship record)
- `20260816-the-user-sent-a-message-while-you-were-working-u-a13da8` (K10 graph; CHANGELOG 2.0.8 left stale)
- `20260816-the-user-sent-a-message-while-you-were-working-u-2f9f5d` (Latest still v2.0.7 @ `02376cc`; no v2.0.8 tag)

This package: `brief.md` (user wants a full README with links, graph, and current-state context), `test-plan.md` (extend README structure tests for first-reads and current-state strings), `release.md` (docs only).

---

## 1. VERSION is 2.0.8

Quote, `VERSION` entire file:

```
2.0.8
```

`README.md:1` already:

```
# Adaptive Grok Build Pro v2.0.8
```

`tests/test_structure.py` `test_version_is_2_0_8_and_github_actions_are_absent`:

> `self.assertEqual((ROOT / 'VERSION').read_text(...).strip(), '2.0.8')`

`decisions.md` 2026-08-16 — Pin tests after bump, pack after VERSION:

> Pack only after `VERSION` is `2.0.8` so the zip name and in-zip `VERSION` cannot still say `2.0.7`.

`packages/README.md` lists `adaptive-grok-build-pro-v2.0.8.zip` as a tracked copy. That is a **local package**, not a GitHub Release.

**README must state:** current tree / product identity is **2.0.8**; source of truth is the `VERSION` file. Do not imply GitHub Latest is 2.0.8.

37141f already ruled: do **not** write “2.0.7 remains Latest until a human last mile” into **CHANGELOG §2.0.8** (that sentence was the 2.0.6 stale-changelog bug). The **README** is the live snapshot; it *should* say Latest is still v2.0.7.

---

## 2. CHANGELOG 2.0.8 still says `engineering/` paths (stale vs root logs)

Quote, `CHANGELOG.md` §2.0.8:

```
## 2.0.8 — 2026-08-16

Agent self-learning is the first AGENTS.md rule.

- `AGENTS.md` starts with log-to-`engineering/decisions.md` / `engineering/mistakes.md`
- Structure test locks that placement so a rewrite cannot drop it
- Still no GitHub Actions
```

`dist/RELEASE-NOTES.md` repeats the same three bullets. That is the 2.0.8 **ship record**, frozen when identity was cut.

Live contract, `AGENTS.md:3-6`:

```
## Agent self-learning

- If you make a decision that turns out to be correct and worth the effort, log it in decisions.md (pattern + why it worked, no more than 3 sentences).
- If you make a mistake that leads to a problem, identify the root cause (not the symptom) and record it in mistakes.md.
```

Live sinks exist at repo root. `decisions.md` header: “Patterns that paid for themselves.” `mistakes.md` header: “Root causes, not symptoms.”

Old paths are stubs only. `engineering/decisions.md` and `engineering/mistakes.md` each:

```
# Moved

Canonical log is /decisions.md. Do not append here.
```

(`engineering/mistakes.md` points at `/mistakes.md`.)

`tests/test_structure.py` now **forbids** the CHANGELOG wording in live `AGENTS.md`:

- first heading `## Agent self-learning`
- prefix contains `log it in decisions.md` / `record it in mistakes.md`
- prefix does **not** contain `engineering/decisions.md` or `engineering/mistakes.md`
- `engineering/` files are ≤5 lines, contain `Canonical log is /…`, `Do not append here`, and no `## 20` dated entries

`decisions.md` 2026-08-16 — Move the live logs; stub the old path:

> `git mv` (not copy) keeps one source of truth and blame. A two-line stub at the old `engineering/` path stops a stale writer from starting a second log. Root `decisions.md` / `mistakes.md` are what the original prompt named and what a root listing shows.

`mistakes.md` 2026-08-16 — Hid the prompt files under engineering/:

> **Symptom:** A user listing the repo root next to `AGENTS.md` still could not see `decisions.md` or `mistakes.md`.
> **Root cause:** We rewrote the original prompt filenames to `engineering/decisions.md` / `engineering/mistakes.md` on purpose…

a13da8 `evidence/analysis-docs_researcher.md` already recorded: CHANGELOG §2.0.8 “Still says log-to-`engineering/…` (the 2.0.8 ship record). ba1615 left it. This package does not require a 2.0.9 bullet.”

**README must state:** live logs are **root** `decisions.md` / `mistakes.md`. CHANGELOG 2.0.8 (and `dist/RELEASE-NOTES.md`) still name the old `engineering/` paths; those files are now stubs. Do not “fix” CHANGELOG 2.0.8 as if it were current state, and do not send agents to append under `engineering/`.

---

## 3. GitHub Latest is v2.0.7; there is no v2.0.8 tag

Live fetch 2026-08-16, https://github.com/Dimkox/adaptive-grok-build-pro/releases/latest:

- Title: **Adaptive Grok Build Pro v2.0.7**
- Badge: **Latest**
- Tag: `v2.0.7` → commit `02376cc` (`02376cc097d7640d56dd308b98efe4e026f4c253`)
- Released 16 Aug 19:57
- Body is CHANGELOG §2.0.7
- Page reports **2 commits to main since this release**

Live fetch of https://github.com/Dimkox/adaptive-grok-build-pro/releases/tag/v2.0.8: **404** “This is not the web page you are looking for.”

Local `.git/refs/tags/` contains only:

`v2.0.0`, `v2.0.1`, `v2.0.2`, `v2.0.3`, `v2.0.4`, `v2.0.5`, `v2.0.6`, `v2.0.7`

No `v2.0.8`. `v2.0.7` object is `2407833d1c985c4fc703f87388e6e2c686dfd746` (annotated tag; peels to `02376cc` per 37141f / 2f9f5d).

2f9f5d `evidence/analysis-repo_explorer.md` and `release-review.md` recorded the same residual after `main` already carried 2.0.8 (`22762a77`): Latest stays v2.0.7; closing that gap is a later authorized publish.

`engineering/runbooks/publish-v2.0.8.md` is the **print-only** list that would create the missing tag/Release. This change’s `release.md` does not authorize running it.

Current `README.md` Package section is misleading:

> Published copies live in `packages/` and on the GitHub Release.

That sentence does not name *which* Release. A first-read will assume Latest == `VERSION` == 2.0.8. It is not.

**README must state:** GitHub Latest is **v2.0.7** on `02376cc`. There is **no** `v2.0.8` tag and **no** GitHub Release `v2.0.8`. Tracked zip `packages/adaptive-grok-build-pro-v2.0.8.zip` is local only. Last mile remains `python3 scripts/grok_deploy.py` + humans running printed `git tag` / `git push origin v2.0.8` / `gh release create` — not this docs change.

---

## 4. GitHub Actions are banned

`decisions.md` 2026-08-16 — Never GitHub Actions:

> Local `make verify` / `python3 scripts/grok_verify.py --mode pr` is the only quality gate. Do not add `.github/workflows/`, Dependabot, `--with-ci` copies, or another CI SaaS. `install_into --with-ci` is `SystemExit` / forbidden.

`.grok-stack/templates/ci/README.md`:

> This product never uses GitHub Actions.
> Do not add `.github/workflows/` or Dependabot.
> … Local `python3 scripts/grok_verify.py --mode pr` is the only gate.

`CHANGELOG.md` 2.0.8 / 2.0.7: “Still no GitHub Actions.” 2.0.6: “No GitHub Actions / Dependabot; local `python3 scripts/grok_verify.py --mode pr` is the only gate. `--with-ci` is forbidden.”

`tests/test_structure.py` `test_version_is_2_0_8_and_github_actions_are_absent` asserts no `*.yml` under `.github/workflows`, no `.github/dependabot.yml`, no `.grok-stack/templates/ci/github-actions.yml`.

`AGENTS.md` Prohibited routine actions: no unapproved merge / publish / deploy. It does not name Actions as a last-mile path.

adaptive-delivery §7:

> Do not deploy, publish, merge, or perform external writes as part of closure. Those are separate, explicitly approved actions. The last mile is `python3 scripts/grok_deploy.py`; humans own the printed commands.

GitHub **Release** (`gh release create`) is not GitHub **Actions**. Standing docs already split those.

Current README never says “no GitHub Actions.” It only describes local `grok_verify`.

**README must state:** this product **never uses GitHub Actions**. Do not add `.github/workflows/` or Dependabot. The only quality gate is local `python3 scripts/grok_verify.py --mode pr` (`make doctor` / `make verify`). `--with-ci` is forbidden.

---

## 5. No `pyproject.toml`

`decisions.md` 2026-08-16 — Ruff lives in ruff.toml, not pyproject.toml:

> `grok_verify` runs Ruff/Bandit without a packaging marker. Config is root `ruff.toml` (and `bandit.yaml`). Do not add `pyproject.toml` / `requirements.txt` / `setup.py` — those flip `detect_repo` and, with pytest on PATH, skip `python-unittest`.

`decisions.md` 2026-08-14 — Run unittest from verify without a packaging marker: same prohibition.

`CHANGELOG.md` 2.0.4:

> `grok_verify` runs `python-unittest` when `tests/test*.py` exist, even without `pyproject.toml` / `requirements.txt` / `setup.py`

`tests/test_structure.py` `test_product_tree_has_no_packaging_markers` asserts those three filenames **do not exist** at repo root.

Root listing has `ruff.toml`, `bandit.yaml`, no `pyproject.toml`.

Current README names Ruff / Bandit / Coverage fail-under 74. It does **not** say there is no packaging marker.

**README must state:** there is **no** `pyproject.toml`, `requirements.txt`, or `setup.py`. Do not add them. Ruff is `ruff.toml`; Bandit is `bandit.yaml`; unittest is discovered from `tests/test*.py`.

---

## 6. Stop hook warns; it does not block

`AGENTS.md` Verification and completion:

> A receipt is stale after any repository change. The Stop hook warns when required evidence is missing or stale.

`CHANGELOG.md` 2.0.7: “Stop hook wording is warn-only.”

`CHANGELOG.md` 2.0.4:

> `stop_gate.py`: missing/stale evidence → **warn only**, never block stop; missing route → allow

`.grok/hooks/README.md`:

> **Stop**: evidence gaps are **warnings only**, never block the agent

`.grok/hooks/stop_gate.py` module docstring: `Stop gate — soft (warn only, never block stop).`

Current `README.md` Hooks already:

> Missing evidence is a Stop warning, not a hard block.

Keep that sentence. Promote it into the current-state block so a first-read does not miss it under Hooks.

**README must state:** Stop hook **warns** on missing/stale evidence; it does **not** hard-block stop. Missing route allows. Policy still denies real production invocations when the stack imports cleanly.

---

## 7. Self-learning is first in AGENTS.md

`AGENTS.md` title is `# Adaptive Grok Build Pro Engineering Contract`. First `##` heading is `## Agent self-learning`. Live bullets name **bare** `decisions.md` / `mistakes.md` (quoted in §2). Next heading is `## Mandatory entrypoint`.

`CHANGELOG.md` 2.0.8 opening sentence is still true even though the path bullets are stale:

> Agent self-learning is the first AGENTS.md rule.

`tests/test_structure.py` `test_agents_md_starts_with_self_learning` locks that placement.

`tests/test_structure.py` `test_readme_names_root_self_learning_logs` already requires README to contain `decisions.md`, `mistakes.md`, and `self-learning` or `Agent self-learning`.

Current README What-this-is:

> `AGENTS.md` starts with the self-learning rule and writes to `decisions.md` / `mistakes.md`

Keep it. The current-state block should repeat that this is the **first** heading, and that `engineering/` copies are stubs.

---

## 8. What the current README already has vs what it still omits

Already present (keep; a13da8 K10 + ba1615 root logs):

- H1 `v2.0.8`
- MIT / commercial / free / public / no EULA / no paid tier
- Caption `Simple complete graph: every core piece is linked to every other.`
- K10 mermaid + 45 `---` edges + node table naming `AGENTS.md`, `decisions.md`, `mistakes.md`
- Manual copy list includes the two root logs
- Stop warning under Hooks
- Scripts loop ends at prepare-only `grok_deploy.py`
- Toolchain table; `grok_verify` Ruff / Bandit / coverage 74

Missing as an explicit **current product state** (this is the user complaint: a first-read cannot tell HEAD from Latest):

1. `VERSION` file = **2.0.8** (H1 is not enough if Latest still says 2.0.7).
2. GitHub Latest = **v2.0.7** @ `02376cc`.
3. **No** `v2.0.8` tag / Release. `packages/…v2.0.8.zip` is not Latest.
4. CHANGELOG 2.0.8 / `dist/RELEASE-NOTES.md` still say `engineering/decisions.md` / `engineering/mistakes.md`; live logs are root files; `engineering/` paths are stubs.
5. **No GitHub Actions**; local `grok_verify --mode pr` is the only gate.
6. **No** `pyproject.toml` / `requirements.txt` / `setup.py`.
7. Stop hook **warns**, never blocks (already under Hooks; restate in the snapshot).
8. `AGENTS.md` first rule is Agent self-learning → root `decisions.md` / `mistakes.md`.

`QUICKSTART.md` is version-silent and has no graph, no logs, no Latest. a13da8 already: skip QUICKSTART or one pointer at README § Stack graph. Do not paste a 45-edge mermaid or a second current-state essay there.

Do not add CHANGELOG.md, QUICKSTART.md, VERSION, or `engineering/changes/` as mermaid nodes. The K10 contract is locked by `test_readme_stack_graph_is_complete`.

---

## 9. Related docs this change must not treat as APIs

| Surface | Fact |
| --- | --- |
| `engineering/adr/` | Empty. No ADR to amend. |
| Contracts | Empty. No OpenAPI/event/schema for README or release identity. |
| `feature-workflow` | Outcome → acceptance; no README API. |
| `install_into.py` | Merges `AGENTS.md`. Manual copy list may name root logs; do not invent `MANAGED_FILES` entries in this docs change. |
| CHANGELOG §2.0.8 | Historical ship record. Leave the stale `engineering/` bullets unless a later 2.0.9 / identity change owns a correction. |
| `publish-v2.0.8.md` | Print-only last mile. Not authorized here. |
| `packages/README.md` | Lists the 2.0.8 zip as a tracked artifact. That is not GitHub Latest. |

---

## Fact for the write owner

Quote these eight current-state facts in README (a dedicated “Current state” / first-read block, not a changelog rewrite):

1. **VERSION is 2.0.8.** File `VERSION` is the identity. README H1 already matches.
2. **CHANGELOG 2.0.8 is stale on log paths.** It still says `AGENTS.md` starts with log-to-`engineering/decisions.md` / `engineering/mistakes.md`. Live contract writes **root** `decisions.md` / `mistakes.md`. The `engineering/` files are stubs: “Canonical log is /…. Do not append here.”
3. **GitHub Latest is v2.0.7** (Adaptive Grok Build Pro v2.0.7 on `02376cc`).
4. **There is no v2.0.8 tag** and no GitHub Release `v2.0.8`. Local tags stop at `v2.0.7`.
5. **GitHub Actions are banned.** No `.github/workflows/`, no Dependabot. Only gate: `python3 scripts/grok_verify.py --mode pr`.
6. **No `pyproject.toml`** (and no `requirements.txt` / `setup.py`). Ruff/Bandit live in `ruff.toml` / `bandit.yaml`.
7. **Stop hook warns** on missing/stale evidence; it does not block stop.
8. **Self-learning is the first `AGENTS.md` heading.** Log correct decisions in `decisions.md`; record root causes in `mistakes.md`.

Keep the K10 complete graph and the MIT/commercial/free wording. Lock new current-state strings from `test-plan.md` in `tests/test_structure.py`. Do not bump `VERSION`, do not tag, do not `gh release create`, do not add GHA or `pyproject.toml`, do not invent installer/doctor/OpenAPI APIs.
