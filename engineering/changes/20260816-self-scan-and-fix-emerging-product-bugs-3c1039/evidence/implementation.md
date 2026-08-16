# Implementation — 2.0.6 leftover product bugs

Write owner: `general_implementer`  
Route: `3c10395cf76e`  
Change: `20260816-self-scan-and-fix-emerging-product-bugs-3c1039`

Identity stays **2.0.6**. No GitHub Actions restored. No `pyproject.toml`. No tag / push / `gh release`.

Reviews and `ready` are for the controller after this report.

## Tests first

Five new assertions failed on the pre-fix tree, then passed after the product edits:

| Test | Pre-fix failure |
| --- | --- |
| `test_default_install_copies_quality_configs` | `ruff.toml` missing on target |
| `test_dry_run_ready_is_ok_without_receipt` | `--title "Adaptive Grok Build Pro v2.0.6"` absent |
| `test_changelog_2_0_6_does_not_claim_stale_latest` | “until a human last mile” still in §2.0.6 |
| `test_package_version_matches_version_file` | `__version__` was `2.0.0` |
| `test_write_archive_unlinks_root_manifest_but_embeds_it` | root `MANIFEST.sha256` left behind |

## What landed

1. `CHANGELOG.md:5` → `Quality contour: Ruff, Bandit, coverage ratchet, no GitHub Actions.`
2. `dist/RELEASE-NOTES.md` rewritten the same way (gitignored scratch; next `grok_deploy` notes).
3. `scripts/install_into.py` `MANAGED_FILES` += `ruff.toml`, `bandit.yaml`, `.coveragerc`.
4. `deploy.py` `_human_commands` adds `--title "Adaptive Grok Build Pro v{version}"`. Runbook `publish-v2.0.6.md` matches.
5. `.grok-stack/adaptive_grok/__init__.py` `__version__ = "2.0.6"`.
6. `package_stack.write_archive` unlinks root `MANIFEST.sha256` after the zip is written (zip already copied the bytes). `.gitignore` now lists `MANIFEST.sha256`.
7. `AGENTS.md` Stop hook **warns** (does not block) when evidence is missing/stale.

## Files

### Tests
- `tests/test_installer.py` — default install copies quality configs; still no `.github/workflows`
- `tests/test_deploy.py` — printed `gh release create` includes `--title`
- `tests/test_structure.py` — CHANGELOG §2.0.6 stale-Latest lock; `__version__` == `VERSION`
- `tests/test_manifest_package.py` — leftover root manifest gone; zip member present

### Product
- `CHANGELOG.md`
- `dist/RELEASE-NOTES.md` (gitignored)
- `scripts/install_into.py`
- `.grok-stack/adaptive_grok/deploy.py`
- `.grok-stack/adaptive_grok/__init__.py`
- `scripts/package_stack.py`
- `.gitignore`
- `AGENTS.md`
- `engineering/runbooks/publish-v2.0.6.md`

## Commands

```bash
python3 -m unittest tests.test_installer tests.test_deploy tests.test_structure tests.test_manifest_package -q
python3 -m unittest discover -s tests -q
```

Results: targeted suite green; discover **181** tests, **OK**. Root `MANIFEST.sha256` absent (`NO_ROOT_MANIFEST`).

Not run: `git tag`, `git push`, `gh release`, `git commit` (left to controller). Suggested subject if the controller commits:

`Fix 2.0.6 leftovers: installer configs, deploy title, stale notes`

## Residual

- Live GitHub card for v2.0.6 already has the cleaned lead; this change only stops the in-repo / notes-file regression.
- Printer still emits `gh release create v2.0.6` because `VERSION` is 2.0.6. Humans must not re-create that tag.
- Coverage wrap still requires `.coveragerc` on the consumer after a default install (now copied).
- Stop hook behavior was already warn-only; only the `AGENTS.md` sentence was wrong.

## Rollback

Revert the listed product and test files. Do not restore GHA, `pyproject.toml`, or a VERSION bump.
