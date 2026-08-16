# Implementation — 2.0.8 identity rebuild

Write owner: `general_implementer`  
Route: `37141fbe6302`  
Change: `20260816-user-query-пересобирай-себя-под-следущей-версией-37141f`

No push, no tag, no `gh release`. Controller owns last mile.

## Sequence

1. Failed the 2.0.7 pins first (renamed `test_version_is_2_0_8_…`, hardcoded `'2.0.8'` in structure + manifest tests). `unittest` was red: `VERSION` still `2.0.7`.
2. Bumped identity surfaces to `2.0.8`.
3. Wrote `engineering/runbooks/publish-v2.0.8.md` (clone of 2.0.7; `publish-v2.0.7.md` untouched).
4. Wrote gitignored `dist/RELEASE-NOTES.md` as CHANGELOG §2.0.8 only.
5. Packed **after** the bump, then copied siblings into `packages/`.
6. Logged `engineering/decisions.md` pin-after-bump + pack-after-VERSION.
7. `python3 -m unittest tests.test_structure tests.test_manifest_package -q` → 23 tests, OK.
8. Path-limited commit of the 2.0.8 ship set only.

## Changed files

| Path | Action |
| --- | --- |
| `VERSION` | `2.0.7` → `2.0.8` |
| `.grok-stack/adaptive_grok/__init__.py` | `__version__ = "2.0.8"` |
| `README.md` | H1 `v2.0.8` |
| `CHANGELOG.md` | inserted `## 2.0.8 — 2026-08-16` (left `## 2.0.7`) |
| `packages/README.md` | added 2.0.8 row |
| `tests/test_structure.py` | pin renamed to `_2_0_8_`; assert `2.0.8`; self-learning lock kept |
| `tests/test_manifest_package.py` | version + in-zip `VERSION` asserts `2.0.8` |
| `engineering/runbooks/publish-v2.0.8.md` | created |
| `dist/RELEASE-NOTES.md` | scratch, gitignored |
| `packages/adaptive-grok-build-pro-v2.0.8.zip` | packed after bump |
| `packages/adaptive-grok-build-pro-v2.0.8.zip.sha256` | sibling |
| `AGENTS.md` | already dirty: first heading `## Agent self-learning` |
| `engineering/mistakes.md` | already dirty: 2026-08-16 authorship omission |
| `engineering/decisions.md` | appended pin-after-bump entry |
| this change package | tasks/requirements/state + this report |

## Commands and results

```
python3 -m unittest tests.test_structure.StructureTests.test_version_is_2_0_8_and_github_actions_are_absent \
  tests.test_manifest_package.PackageTests.test_included_files_and_shipped_zip_have_no_github_actions -q
```

Red as intended: `'2.0.7' != '2.0.8'` (two failures).

```
python3 scripts/package_stack.py
# stdout: …/dist/adaptive-grok-build-pro-v2.0.8.zip
# not v2.0.7
test ! -f MANIFEST.sha256   # ok
cp dist/adaptive-grok-build-pro-v2.0.8.zip* packages/
( cd packages && sha256sum -c adaptive-grok-build-pro-v2.0.8.zip.sha256 )  # OK
```

In-zip `adaptive-grok-build-pro/VERSION` is `2.0.8`.  
`packages/adaptive-grok-build-pro-v2.0.7.zip.sha256` still starts `ec48d3174248e15e241519546b1414a7698857509cf97ac61e078dbd204de01c`.  
No root `MANIFEST.sha256`. No `pyproject.toml` / `requirements.txt` / `setup.py`. No `.github/workflows`.

```
python3 -m unittest tests.test_structure tests.test_manifest_package -q
# Ran 23 tests in 0.202s
# OK
```

## Residual risk

- Leftover on-disk change packages (ad4090, 39b13f, 5be23b, 864726, 2929c0 extras, 3c1039, ec0388, d55ce4) stay unstaged. `package_stack` still embeds them in the zip because `included_files()` walks the live tree. Same class as 2.0.7. Do not expand excludes.
- GitHub Latest stays v2.0.7 on `02376cc` until a later human runs the printed `grok_deploy` / `publish-v2.0.8.md` last mile. Do not write that into product notes.
- Official `grok_verify --mode pr` and independent `code_review` are not recorded here. Controller runs those after this commit (fingerprint includes HEAD).
- Expired 2.0.7 production approvals must not be reused.

## Suggested controller commands

After this commit and a green independent review:

```bash
python3 scripts/grok_verify.py --mode pr
python3 scripts/grok_review.py code_review --status pass --report \
  engineering/changes/20260816-user-query-пересобирай-себя-под-следущей-версией-37141f/evidence/code-review.md
python3 scripts/grok_approve.py production --reason "push v2.0.8 identity to origin/main"
git push origin main
```

Do **not** `git tag`, `git push origin v2.0.8`, or `gh release create`.
