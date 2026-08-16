# Docs research — GHA ban vs `gh release`, current CI contracts

Route: `9fd2741e5d1b`. Change: `20260816-ban-gha-rebuild-and-verify-2-0-6-publish-9fd274`.
Question: what standing docs, CHANGELOG, CI template README, installer `--with-ci`, and `test_deploy` actually say about GitHub Actions versus `gh release`, and what the user ban now overrides.

Read-only. No application-code edits. No `.env`. No push / merge / deploy. No APIs invented.

## Sources

- This change package (`brief.md`, `requirements.md`, `architecture.md`, `release.md`, `rollback.md`, `test-plan.md`, `tasks.md`, `state.json`)
- Sibling stub `engineering/changes/20260816-ban-github-actions-publish-2-0-6-without-them-39b13f/` (user wording only)
- `.grok-stack/templates/ci/README.md` (full file)
- `.grok-stack/templates/ci/github-actions.yml`
- `scripts/install_into.py` `--with-ci`
- `CHANGELOG.md` §§2.0.6, 2.0.5, 2.0.4
- `tests/test_deploy.py`, `tests/test_installer.py`, `tests/test_policy.py`
- `README.md`, `QUICKSTART.md`, `AGENTS.md`, `VERSION`, `Makefile`
- `engineering/decisions.md`, `engineering/mistakes.md`, `engineering/adr/` (empty)
- `engineering/runbooks/publish-v2.0.4.md`, `publish-v2.0.5.md`, `publish-v2.0.6.md`
- `.grok/skills/adaptive-delivery/SKILL.md`, `.grok/skills/feature-workflow/SKILL.md`
- `.grok-stack/adaptive_grok/deploy.py`, `.grok-stack/adaptive_grok/policy.py`, `.grok-stack/config/toolchain.json`
- Prior packages `99b743`, `ec0388`, `864726`, `cd8a96`, `ef7b14`
- Parallel `evidence/analysis-repo_explorer.md` (this change)

`engineering/contracts/{openapi,asyncapi,schemas}/` have no product APIs. `engineering/adr/` has no files. There is no ADR that either added or banned GitHub Actions.

---

## 0. User rule that now outranks older CI docs

This package `brief.md`:

> User rule: never GitHub Actions. Rebuild the 2.0.6 package under that rule, verify locally, finish the unpublished GitHub Release.

This package `architecture.md`:

> Source of truth: local `grok_verify`. Never GitHub Actions.
>
> 1. Delete workflow + dependabot.
> 2. Template README: never GHA; `make verify` / `grok_verify --mode pr` only.
> 3. `--with-ci` → SystemExit, no copy.
> 4. Keep VERSION 2.0.6 (unpublished). Rebuild zip. Then tag that commit.

Sibling stub `39b13f/brief.md` records the raw user line:

> НИКОГДА НЕ ИСПОЛЬЗУЕМ ЕБАНЫЕ GITHUB ACTOIONS!!!!!!!

Source-of-truth order (`AGENTS.md`): user-approved scope beats ADRs and existing implementation. There is no named human gate on this route. The ban is the scope.

Out of scope in this package: another CI vendor, `pyproject.toml`, touching v2.0.5.

---

## 1. Quote: `.grok-stack/templates/ci/README.md` (entire current file)

There is no `templates/ci/` at repo root. The only CI template README is `.grok-stack/templates/ci/README.md`:

```1:19:.grok-stack/templates/ci/README.md
# CI templates

Optional GitHub Actions workflow: `github-actions.yml`. This repository copies it to `.github/workflows/adaptive-grok.yml` (verify + conditional package; no publish).

Local `make verify` is the source of truth. Hosted CI is optional and does not publish.

This project is MIT open source and does not depend on paid hosted CI.

Local checks (free, any machine):

```bash
make doctor
make verify
python scripts/grok_doctor.py
python scripts/grok_verify.py --mode pr
```

If you self-host CI (Woodpecker, Forgejo Actions, GitLab, Drone, Jenkins, …),
wire the same commands. Do not require GitHub-hosted runners.
```

Facts from that file, not inferences:

| Claim | Status after user ban |
| --- | --- |
| GHA is **optional** | Overridden: never GHA |
| This repo **copies** the template to `.github/workflows/adaptive-grok.yml` | Overridden: delete that copy |
| Job shape is verify + conditional package; **no publish** | Historical. Ban deletes the job; it never published |
| Local `make verify` is source of truth | **Kept.** Matches this package architecture and `Makefile` `verify:` → `python3 scripts/grok_verify.py --mode pr` |
| Hosted CI does not publish | Still true; last mile is not Actions |
| Do not require GitHub-hosted runners | Compatible with the ban |
| Self-host Woodpecker / Forgejo / GitLab / Drone / Jenkins | This package: **another CI vendor is out of scope**. Do not add a replacement workflow |

Architecture for this change says rewrite that README to: never GHA; local `make verify` / `grok_verify --mode pr` only.

---

## 2. Quote: installer `--with-ci`

`README.md` and `QUICKSTART.md` do **not** document `--with-ci`. The only user-facing install examples are:

```75:78:README.md
# from this package root — copies the stack and installs missing required tools
python3 scripts/install_into.py /path/to/your/repo
# skip host installs: --no-deps
# also PHP/Node/gh: --all-deps
```

```14:18:QUICKSTART.md
   python3 scripts/install_into.py /path/to/repo
   # installs the stack and missing required tools (use --no-deps to copy only)
```

The flag exists only on the CLI and in tests.

### 2.1 CLI contract

```188:188:scripts/install_into.py
    parser.add_argument('--with-ci', action='store_true', help='Install a generic GitHub Actions verification workflow.')
```

Default is off (`with_ci: bool = False`). A normal `install_into.py /path` does not copy a workflow.

### 2.2 Current copy behavior (to be forbidden)

```119:127:scripts/install_into.py
    if with_ci:
        ci_src = source / '.grok-stack/templates/ci/github-actions.yml'
        ci_dst = target / '.github/workflows/adaptive-grok.yml'
        if ci_dst.exists() and different(ci_src, ci_dst) and not force:
            raise SystemExit(f'{ci_dst} already exists with different content; use --force only after review.')
        print(f'{"OVERWRITE" if ci_dst.exists() else "COPY"} {ci_dst.relative_to(target)}')
        if not dry_run:
            ci_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ci_src, ci_dst)
```

Today `--with-ci` writes GitHub Actions YAML. This package requires: `--with-ci` exits forbidden and writes **no** workflow (`requirements.md`, `architecture.md` item 3, `test-plan.md` item 2).

`SystemExit` is already used by the installer for conflicts. There is no existing “GHA forbidden” message to reuse.

### 2.3 Test that currently locks the copy

```73:82:tests/test_installer.py
    def test_with_ci_preserves_unrelated_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'target'
            workflows = target / '.github/workflows'
            workflows.mkdir(parents=True)
            unrelated = workflows / 'existing.yml'
            unrelated.write_text('name: existing\n', encoding='utf-8')
            install_silent(ROOT, target, force=False, dry_run=False, with_ci=True)
            self.assertEqual(unrelated.read_text(encoding='utf-8'), 'name: existing\n')
            self.assertTrue((workflows / 'adaptive-grok.yml').is_file())
```

That test **requires** `--with-ci` to create `adaptive-grok.yml`. After the ban it must invert: nonzero exit, no `adaptive-grok.yml`, unrelated workflow left alone. No other installer test mentions `--with-ci`.

Default install still must not write `.github/workflows/` (already true when `with_ci=False`).

---

## 3. Quote: CHANGELOG

### 3.1 Current 2.0.6 section (still unpublished identity)

```3:11:CHANGELOG.md
## 2.0.6 — 2026-08-16

Quality contour on this tree. 2.0.5 remains the previous published GitHub Latest until a human last mile.

- `grok_verify` runs Ruff from `ruff.toml` without a packaging marker; local skip-if-missing; CI fail-closed after `pip install`
- Bandit AST next to regex `secret-scan`; excludes `tests/` and `engineering/`
- Coverage.py report in `pr`/`release` after a measured fail-under of 74 (ratchet, not a guessed 90)
- Dependabot for GitHub Actions only
- Optional consumer Semgrep / Trivy config / npm prettier|format when those signals exist; not enabled on this tree
```

`dist/RELEASE-NOTES.md` is a byte-identical copy of that 2.0.6 section.

What 2.0.6 currently **advertises** that the ban retracts:

- “CI fail-closed after `pip install`” — that `pip install` lives only in `.github/workflows/adaptive-grok.yml` / the template (`actions/setup-python` + `python -m pip install 'ruff>=0.6,<1' 'bandit>=1.7,<2' 'coverage>=7,<8'`). Local `grok_verify` still skip-if-missing.
- “Dependabot for GitHub Actions only” — that is `.github/dependabot.yml` `package-ecosystem: github-actions`. Architecture: delete it.

What 2.0.6 must **keep** (this package: stay on unpublished 2.0.6; do not open 2.0.7; do not touch v2.0.5):

- `VERSION` is `2.0.6`
- Ruff from `ruff.toml` without a packaging marker
- Bandit next to `secret-scan`
- Coverage fail-under 74 in `pr`/`release`
- No `pyproject.toml` (`decisions.md` 2026-08-16; this package out of scope)

### 3.2 2.0.4 — the section that both added GHA and distinguished `gh release`

```25:43:CHANGELOG.md
## 2.0.4 — 2026-08-15
…
- Production policy matches command invocations (`git push`, `gh pr merge`, `docker push`, `npm publish`, `gh release create`), not bare words in paths or arguments
…
- This-repo GitHub Actions: verify plus a conditional package job (no publish)
```

Those are two different bullets. The changelog already treats `gh release create` as a **production CLI invocation** and GitHub Actions as a **hosted verify/package job**.

2.0.4 history stays as history. Do not rewrite past sections to pretend GHA never shipped. The 2.0.6 section is the one that must stop promising Dependabot-for-GHA and CI-fail-closed.

---

## 4. Quote: `tests/test_deploy.py`

### 4.1 Last mile prints `gh release create` and must keep doing so

```92:109:tests/test_deploy.py
    def test_dry_run_ready_is_ok_without_receipt(self) -> None:
        …
            self.assertIn('python3 scripts/package_stack.py', joined)
            self.assertIn(f'cp dist/adaptive-grok-build-pro-v{version}.zip* packages/', joined)
            self.assertIn(f'git tag -a v{version}', joined)
            self.assertIn('git push origin', joined)
            self.assertIn(f'gh release create v{version}', joined)
            self.assertIn('--notes-file dist/RELEASE-NOTES.md', joined)
```

`deploy.py` `_human_commands` is the implementation of that list. `test_prepare_sources_do_not_execute_publish_commands` forbids `subprocess` / `os.system` in `deploy.py` and `grok_deploy.py`. Printed `gh release create` is **not** GitHub Actions and is **not** executed by the agent.

This package `release.md` still uses that last mile:

> Last mile: tag `549f29d` successor, push main, push v2.0.6, `gh release create`.

After the GHA-removal commit, the tag target is that successor, not the current `549f29d` (which still contains workflows).

### 4.2 Tests that currently require GitHub Actions (must invert)

```193:213:tests/test_deploy.py
    def test_root_workflow_equals_template(self) -> None:
        workflow = ROOT / '.github/workflows/adaptive-grok.yml'
        template = ROOT / '.grok-stack/templates/ci/github-actions.yml'
        self.assertTrue(workflow.is_file())
        self.assertEqual(workflow.read_bytes(), template.read_bytes())

    def test_template_package_job_is_conditional_and_has_no_publish(self) -> None:
        text = (ROOT / '.grok-stack/templates/ci/github-actions.yml').read_text(encoding='utf-8')
        self.assertIn("hashFiles('scripts/package_stack.py')", text)
        self.assertNotIn('gh release', text)
        self.assertNotIn('docker push', text)
        self.assertNotIn('git push', text)

    def test_workflow_installs_quality_tools(self) -> None:
        text = (ROOT / '.grok-stack/templates/ci/github-actions.yml').read_text(encoding='utf-8')
        self.assertIn('pip install', text)
        self.assertIn('ruff', text)
        self.assertIn('bandit', text)
        self.assertIn('coverage', text)
        self.assertIn('python -m unittest discover -s tests', text)
        self.assertIn('grok_verify.py --mode pr', text)
```

`test_template_package_job_is_conditional_and_has_no_publish` is the in-tree lock that **`gh release` is not part of GitHub Actions**. The workflow YAML is asserted to omit the string `gh release`.

Those three tests, plus `test_with_ci_preserves_unrelated_workflow`, are the keep-GHA suite named in `analysis-repo_explorer.md`.

---

## 5. Confirmed: `gh release` ≠ GitHub Actions

Independent in-repo sources, not a web definition:

| Surface | What it is | Path / quote |
| --- | --- | --- |
| GitHub Actions | Hosted runner jobs from `.github/workflows/*.yml` using `actions/checkout`, `actions/setup-python`, `actions/upload-artifact` | `.github/workflows/adaptive-grok.yml` = template |
| Dependabot for Actions | Weekly PRs for those `actions/*` pins | `.github/dependabot.yml` `package-ecosystem: github-actions` |
| `gh` | Optional **GitHub CLI** for the `release` profile | `toolchain.json` id `gh`, name `GitHub CLI`; README “GitHub CLI (`gh`) \| for GitHub Release” |
| `gh release create` | Human-owned last-mile command that creates a **GitHub Release** object and attaches zip + sha256 | `deploy.py` `_human_commands`; `publish-v2.0.6.md`; CHANGELOG 2.0.4 production-invocation bullet |
| Policy gate | `PRODUCTION_INVOCATIONS` includes `('gh', 'release', 'create')` next to `git push` / `npm publish` | `policy.py` 48–54; `test_policy.py` 70–76 |
| GHA must not publish | Template asserted to contain **no** `gh release` / `git push` / `docker push` | `test_deploy.py` 199–204 |
| Adaptive-delivery close | “Do not deploy, publish, merge… The last mile is `python3 scripts/grok_deploy.py`; humans own the printed commands.” | `.grok/skills/adaptive-delivery/SKILL.md` §7 |

`99b743` architecture (the change that **added** this-repo GHA) already split them:

> **CI:** copy template to `.github/workflows/adaptive-grok.yml`. … No publish job.
>
> human later: grok_approve production → printed tag/push/gh release

Banning GitHub Actions therefore does **not** ban:

- `gh release create v2.0.6 …` (this package’s last mile)
- `gh release delete v2.0.6 --yes` (this package’s rollback)
- the `gh` toolchain pin
- `--all-deps` installing `gh`

Banning GitHub Actions **does** ban:

- `.github/workflows/**`
- `.github/dependabot.yml` (ecosystem is `github-actions` only)
- installer copy of `github-actions.yml`
- CHANGELOG / template README that present GHA as a product feature

No document equates `gh release` with Actions. The only place both appear in one test file is `test_deploy.py`, which asserts they are disjoint.

---

## 6. Standing contracts the ban must not break

### 6.1 Local verify remains the gate

`Makefile`:

```4:5:Makefile
verify:
	python3 scripts/grok_verify.py --mode pr
```

`AGENTS.md` / adaptive-delivery §5: `python scripts/grok_verify.py --mode pr` before reviews.

`ec0388` architecture (still correct after GHA deletion):

> Source of truth is `grok_verify`. CI installs tools and runs the same command.

After the ban, only the first sentence remains operational. Local skip-if-missing for ruff/bandit stays (CHANGELOG 2.0.6). There is no remaining “CI fail-closed after pip install” path.

### 6.2 Version / package / last mile

| Contract | Source | Implication for this change |
| --- | --- | --- |
| `VERSION` is SoT; packager follows it | CHANGELOG 2.0.1; `package_stack.py` `_default_output` | Stay on `2.0.6`; rebuild `dist/` then `cp` to `packages/` |
| Do not retag v2.0.5 | `cd8a96`, this package out of scope | Leave tag/release `v2.0.5` |
| 2.0.6 is unpublished | This `brief.md`; `repo_explorer` report: no local/remote `v2.0.6`, Latest is v2.0.5, `/releases/tag/v2.0.6` 404 | Last mile still required after rebuild |
| Human owns tag / push / `gh release` | `publish-v2.0.6.md:5`; adaptive-delivery §7; `AGENTS.md` prohibited routine actions | Agents print; humans run |
| Receipts after last tree write | `decisions.md` 2026-08-14; `mistakes.md` | Ban + rebuild + CHANGELOG/README rewrite first; then `ready` → verify → reviews |
| No `pyproject.toml` | `decisions.md` 2026-08-16; this package out of scope | Do not add one to replace GHA `pip install` |

`864726` (publish-only draft) pinned zip digest `b34af685c8d277aafcfbc4aa3f393286b12af2b092e5efa2b74ab6f5ba41b610` and tag of `549f29d`. **That digest and SHA are stale for this change.** Architecture: rebuild after GHA removal, then tag the successor. Do not attach the current zip (it still contains `.github/workflows` via `included_files()`, which does not exclude `.github`).

### 6.3 Grok hooks are not GitHub Actions

`CHANGELOG` 2.0.5 / `decisions.md` 2026-08-15: root hook shims into `.grok/hooks/`. Those are Grok Build lifecycle adapters (`hooks.json`, `adaptive.json`), not `.github/workflows`. This package must not delete them. `repo_explorer` already listed the keep set.

---

## 7. Conflicts the write owner must resolve in docs

| Older claim | Where | Ruling |
| --- | --- | --- |
| GHA is optional hosted CI | `templates/ci/README.md` | User ban. Rewrite to never GHA; local verify only |
| This repo copies the workflow | same README; `install_into.py --with-ci` | Delete copy path; `--with-ci` → SystemExit |
| Dependabot for GitHub Actions only | CHANGELOG 2.0.6; `ec0388` acceptance (checked) | Retract in 2.0.6 notes; delete `.github/dependabot.yml` |
| CI fail-closed after `pip install` | CHANGELOG 2.0.6; `test_workflow_installs_quality_tools` | Retract. Local skip-if-missing stays |
| CI template and workflow stay byte-identical | `ec0388` requirements | Superseded: both go away |
| Publish existing `549f29d` zip, do not rebuild | `864726` brief | Superseded: rebuild after ban |
| `99b743` added this-repo GHA | CHANGELOG 2.0.4; `99b743` architecture item 4 | Historical. New user rule wins. Do not revert 2.0.4 history text |
| Self-host Woodpecker / GitLab / … | template README | Out of scope. Do not add a vendor |

No OpenAPI / AsyncAPI / schema change. No ADR to write unless the write owner wants a one-paragraph record; `engineering/adr/` is empty and this route did not require one.

---

## 8. Facts for implementer (docs only)

1. Quote and rewrite `.grok-stack/templates/ci/README.md`; do not leave “optional GitHub Actions”.
2. `--with-ci` is undocumented in README/QUICKSTART; changing it to forbidden does not break a documented consumer flag, but it **does** break `test_with_ci_preserves_unrelated_workflow`.
3. Amend CHANGELOG **2.0.6** (and `dist/RELEASE-NOTES.md`) to drop Dependabot-for-GHA and CI-fail-closed. Keep 2.0.6 identity. Keep 2.0.4 history.
4. Keep `gh release create` in `grok_deploy.py`, runbooks, policy, and `test_dry_run_ready_is_ok_without_receipt`. That is GitHub Release via GitHub CLI, not GitHub Actions.
5. Invert the three `DeploySourceAndCiTests` that require a workflow file / template contents.
6. Local gate stays `make verify` / `python3 scripts/grok_verify.py --mode pr`.
7. Rebuild zip after those tree edits so in-zip `VERSION` is 2.0.6 and in-zip `.github/workflows` is absent.
8. Do not invent a replacement CI API or vendor.

This report is analysis only. It does not authorize `git push`, `git tag`, or `gh release create`.
