# Analysis — repo_explorer

Change: `20260816-self-scan-and-fix-emerging-product-bugs-3c1039`
Route: `3c10395cf76e` · write owner: `general_implementer`

Read-only hunt on `HEAD` / `refs/heads/main` = `e75f3a1b92e247279fbb6210d46715a90cf7895c` plus the working tree. No application edits. No `.env`. No push / tag / merge / deploy. Unittest / ruff / bandit / `grok_verify` were **not** executed (would dirty receipts). Claims below are from files, tests, and the public GitHub Latest HTML.

| Pin | Fact |
| --- | --- |
| `VERSION` | `2.0.6` |
| Local `main` | `e75f3a1` |
| Tag `v2.0.6` | annotated object `8e7c5b67…` peels to `e75f3a1` |
| GitHub Latest | **v2.0.6** titled Adaptive Grok Build Pro v2.0.6 on `e75f3a1` (16 Aug 18:29). Live body already dropped the last-mile sentence. |
| Root `MANIFEST.sha256` | **absent** right now |
| `.github/` | **absent**. `.grok-stack/templates/ci/` is README only. |

Product bugs only. Change-package dirt is out of scope.

---

## Bugs

### 1. CHANGELOG still says 2.0.5 is GitHub Latest — medium

`CHANGELOG.md:5`

```
Quality contour on this tree. 2.0.5 remains the previous published GitHub Latest until a human last mile.
```

That sentence was true before last mile. Latest is now v2.0.6 on `e75f3a1`. The live GitHub card was already rewritten (`b625b4`); the in-repo changelog was left false (`b625b4/evidence/release-review.md:129`).

README H1 is `v2.0.6`. QUICKSTART has no version / Latest / GHA / Dependabot claim. CHANGELOG §2.0.6 correctly bans Actions; it does **not** still require them.

**Smallest fix:** rewrite line 5 to match the live card lead, e.g. `Quality contour: Ruff, Bandit, coverage ratchet, no GitHub Actions.` Do not claim 2.0.5 is Latest. Leave the historical §2.0.4 GHA bullet (`CHANGELOG.md:41`) as history.

### 2. `dist/RELEASE-NOTES.md` still has the same stale Latest sentence — medium

`dist/RELEASE-NOTES.md:3` is a byte-for-byte copy of `CHANGELOG.md:5`.

`deploy.py:33` and `engineering/runbooks/publish-v2.0.6.md:27` still print:

```
gh release create v{version} … --notes-file dist/RELEASE-NOTES.md
```

`dist/` is gitignored scratch, but it is the notes source of truth for the printer. Using it again would restore the sentence the live card just dropped. `dist/RELEASE-NOTES-v2.0.6-card.md:3` is already the cleaned text.

**Smallest fix:** after CHANGELOG line 5 is honest, copy §2.0.6 into `dist/RELEASE-NOTES.md`. Do not point deploy at the card-only scratch file unless you also change the printer.

### 3. `install_into` does not copy `ruff.toml` / `bandit.yaml` / `.coveragerc` — high

`scripts/install_into.py:16-34` `MANAGED_FILES` is scripts + nine root shims only. Root quality configs are not listed. They are also not under `MANAGED_DIRS` (`.grok`, `.agents`, `.grok-stack`).

`tests/_support.py:33` copies those three files into fixtures. The installer does not. After `python3 scripts/install_into.py /path/to/repo`, a consumer that already has the CLIs on PATH fail-closes on **this product’s own copied scripts**:

| Missing file | What `grok_verify` does | Why it fails |
| --- | --- | --- |
| `ruff.toml` | `ruff check` on `QUALITY_PY_PATHS` (`verification.py:179-185`) | default rules include `E402`; every copied `scripts/grok_*.py` does `sys.path.insert` then import |
| `bandit.yaml` | `bandit -q -r <paths>` without `-c` (`verification.py:194-197`) | product CLIs import/run subprocess; skips `B404`/`B603`/`B607` live only in `bandit.yaml:9-12` |
| `.coveragerc` | `coverage run --rcfile=.coveragerc` in `pr`/`release` (`verification.py:271-277`) | coverage exits non-zero if the rcfile is missing; that check is named `python-unittest` |

Not the same as pulling ruff/bandit/coverage via `toolchain.json` (do not add them as required deps).

**Smallest fix:** append `'ruff.toml', 'bandit.yaml', '.coveragerc'` to `MANAGED_FILES`. Add one installer test that a default install copies those three files and still copies no `.github/workflows`. Optionally gate coverage wrap on `(root / '.coveragerc').is_file()` (`verification.py:271`) so a host `coverage` binary without an rcfile skips instead of failing unittest.

`--with-ci` does **not** leak GHA. `install():96-100` raises `SystemExit` (`forbidden`) before any copy. `.grok-stack/templates/ci/github-actions.yml` is gone. `test_default_install_does_not_copy_workflow_from_grok_stack` locks that.

### 4. `deploy.py` / `grok_deploy.py` do not print stale GHA or 2.0.5 — but they omit `--title` — medium

`deploy.py:13-18` reads `VERSION`. `deploy.py:24-35` prints tag / push / `gh release create v{version}` with `--notes-file`. `scripts/grok_deploy.py` is a thin CLI. No hardcoded `2.0.5`. No workflow commands.

The emerging printer bug is the missing title. `deploy.py:33`:

```
f'gh release create v{version} packages/{zip_name} packages/{zip_name}.sha256 --notes-file dist/RELEASE-NOTES.md'
```

No `--title "Adaptive Grok Build Pro v{version}"`. That is why v2.0.5 and the first v2.0.6 card shipped empty names. Live v2.0.6 was patched with `gh release edit`, not by fixing the printer. `publish-v2.0.6.md:27` has the same argv. `tests/test_deploy.py:107-108` locks notes-file, not `--title`.

**Smallest fix:** add `--title "Adaptive Grok Build Pro v{version}"` in `_human_commands` and the 2.0.6 runbook; assert the flag in `test_dry_run_ready_is_ok_without_receipt`. Do not print GHA.

Note: on this already-published `VERSION=2.0.6` tree the printer still emits `gh release create v2.0.6`. That is version-dynamic, not a stale 2.0.5 string. Humans must not re-run create for an existing tag.

### 5. `__version__` is still `2.0.0` — low

`.grok-stack/adaptive_grok/__init__.py:3`

```
__version__ = "2.0.0"
```

Packager and deploy read `VERSION`, not this string. Tests pin `VERSION == 2.0.6` (`test_structure.py:114`, `test_manifest_package.py:113`). Honesty mismatch only.

**Smallest fix:** set `__version__` from `VERSION` (or hardcode `"2.0.6"`). Optional one-liner test that they match.

No other product Python hardcodes `2.0.5` / `2.0.0` as identity. `tests/test_policy.py:76,102` uses `gh release create v2.0.4` as an invocation example, not a version pin.

### 6. Doctor vs leftover `MANIFEST.sha256` — high (latent)

Root `MANIFEST.sha256` is **not present now**, so `test_project_doctor_has_no_failures` should pass on this tree.

The code still plants the landmine:

| Site | Behavior |
| --- | --- |
| `scripts/package_stack.py:19-20` | `generate_manifest(root)` writes root `MANIFEST.sha256`, then zips it |
| `package_stack.py` | never unlinks the leftover |
| `.gitignore` | does not ignore `MANIFEST.sha256` |
| `doctor.py:86-94` | if the file exists, `verify_manifest` must be clean or doctor **fail** |
| missing file | `info`, not fail (`doctor.py:93-94`) |

Already bit this repo: after the 2.0.5 package, later change-package writes made `tests/test_verification_doctor.py:525-528` fail; the leftover was deleted by hand (`ad4090/evidence/implementation.md:122-124`). The next `make package` recreates it.

**Smallest fix:** after the zip is written, `Path.unlink` the root leftover (zip already embeds its copy). Add `MANIFEST.sha256` to `.gitignore`. Keep doctor verify-if-present for a packaged checkout that still has the file. Add a test that `write_archive` on a temp tree leaves no leftover, or that a stale leftover on ROOT is not required for doctor pass after unlink.

### 7. Tests do **not** still expect GitHub Actions workflow files

Keep-GHA tests were inverted. No remaining assertion that `adaptive-grok.yml` / `github-actions.yml` / Dependabot **exist**.

| Test | Expects |
| --- | --- |
| `tests/test_structure.py:113-118` | `VERSION==2.0.6`; no workflow yml; no Dependabot; no template |
| `tests/test_deploy.py:193-201` | those files absent |
| `tests/test_deploy.py:203-215` | CI README bans Actions |
| `tests/test_installer.py:73-113` | `--with-ci` is `forbidden`; default install copies no workflow / `github-actions.yml` |
| `tests/test_manifest_package.py:111-127` | `included_files()` + shipped 2.0.6 zip have no workflows / Dependabot / template |

No test change required unless you add `--title` or installer quality-config assertions.

---

## Checked, not bugs

- README / QUICKSTART do **not** claim Dependabot or GitHub Actions are required. README license/verify paragraph is local `make doctor` / `make verify` / `grok_verify --mode pr`.
- `CHANGELOG.md:41` “This-repo GitHub Actions…” is 2.0.4 history. Leave it.
- `--with-ci` cannot copy a template that does not exist; it exits first.
- `Makefile` verify/deploy targets are local only.
- `.grok-stack/templates/ci/README.md` bans Actions.
- No product `eval(` / `exec(` outside planted tests (bandit excludes `tests/`).
- `detect_repo` (`repo.py:82`) still only treats `pyproject.toml` / `requirements.txt` as `python:project`. Copying `ruff.toml` will not flip kind.

---

## Related docs contradiction (optional, still product)

`AGENTS.md:99` says “The Stop hook **blocks** completion while required evidence is missing or stale.” Actual hook is warn-only (`stop_gate.py:1,38-41`; `README.md:131`; CHANGELOG 2.0.4). `install_into` ships `AGENTS.md` into consumers.

**Smallest fix:** change “blocks” to “warns about”.

---

## Static quality (not executed)

Did not run `python3 -m unittest`, ruff, bandit, or `python3 scripts/grok_verify.py --mode pr`. From the tree:

- Official verify on `e75f3a1` was recorded green (ruff, bandit, 177 unittests, coverage 76% / fail-under 74).
- This change package lives under `engineering/`, which ruff and bandit exclude.
- No leftover root `MANIFEST.sha256`, so doctor should not fail **until** the next `package_stack.py`.
- No remaining test would fail solely because workflow files are absent.

Do not invent a red suite. After the writer lands the docs/installer/doctor/title fixes, run `python3 scripts/grok_verify.py --mode pr` on the final tree.

---

## Writer ledger (smallest vertical)

1. `CHANGELOG.md:5` + refresh `dist/RELEASE-NOTES.md`.
2. `install_into.py` `MANAGED_FILES` += `ruff.toml`, `bandit.yaml`, `.coveragerc` + installer test. Optional: coverage wrap only if `.coveragerc` exists.
3. `package_stack.write_archive` unlink leftover `MANIFEST.sha256`; gitignore it.
4. `deploy.py` + runbook `--title "Adaptive Grok Build Pro v{version}"` + deploy test.
5. Optional honesty: `__version__ = "2.0.6"`; `AGENTS.md:99` “warns”.

Do not re-add `.github/workflows/`, Dependabot, or a `--with-ci` copy. Do not retag. Do not rebuild `packages/…-v2.0.5.*`. Do not touch `.env`.
