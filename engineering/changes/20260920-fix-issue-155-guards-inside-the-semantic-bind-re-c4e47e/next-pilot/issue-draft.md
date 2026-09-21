Draft only — not posted. Source observed 2026-09-21.

Title: Include Russian landing and roadmap in the browser audit

The current browser audit omits the Russian landing and roadmap. `build-pages.py:LOCALES` includes Russian (`ru-RU`) and current main contains `ru/index.html` and `ru/roadmap.html`, but `tests/site_browser_contract.py:PAGES` contains only the previous six language pairs plus four legal pages. Consequently the audit does not exercise these two shipped pages.

Exact base: `6226aa0b86e1fe08c63724cc3761b3f788146b91`, tree `788a40489683d627457e3780503d6127e44bdabf`.

Acceptance:

1. Register `/ru/` and `/ru/roadmap.html` with expected language `ru-RU` in the real audit's page inventory. The inventory becomes 18 URLs; preserve the prior 16 URL/language mappings.
2. Add an offline regression proving that every supported builder locale has its landing and roadmap represented with the expected language. Derive that expectation from the builder's literal locale declaration (for example, inspect its AST with the Python standard library) rather than duplicating a second hardcoded locale list. The current base must fail this regression specifically because the two Russian routes are absent.
3. Preserve the existing `page_passes` language, heading, overflow, keyboard-focus and browser-warning rejection behavior. Keep current negative cases.
4. Change exactly two mode-100644 files: `tests/site_browser_contract.py` and `tests/test_site_browser_contract.py`. No new dependency, generated-page, CSS, analytics, CSP, archive, deploy, or unrelated-copy change.
5. The focused offline regression and complete configured unittest discovery pass. Report exact candidate SHA, changed files, test commands and actual results; do not describe unit success as a completed live browser audit.

Focused regression command from the target repository root:

```bash
python3 -m unittest discover -s tests -p test_site_browser_contract.py -v
```

Full candidate validation command:

```bash
python3 -m unittest discover -s tests -v
```

These are commands to run during the successor's implementation/validation, not executed in the read-only analysis. The actual bounded pilot still starts its configured full validation command once, with no automatic test/model retry.

Browser dependency boundary: at the pinned current SHA, `selenium` imports in `site_browser_contract.py` are inside browser-execution functions. The focused offline unit command imports `page_passes` and the inventory and does not invoke a browser. Do not add Selenium, a driver, browser packages, network access or a live-site audit to satisfy this issue. A separate real browser run would need its own available browser environment and reported scope. The old PR #3's Selenium failure came from its old-base attempt and cannot be assumed to describe current main.

Relationship to existing work: issue #1 remains a historical old-base v2.0.14 request; PR #3 is closed unmerged with no recorded reason, and its parent is `6990103`. This draft is a current, distinct defect and needs maintainer agreement and separately delegated issue publication. Do not overwrite #1 or reopen #3 as an automatic continuation.

Source links:

- Builder: https://github.com/Dimkox/ai-dark-factory-landing/blob/6226aa0b86e1fe08c63724cc3761b3f788146b91/build-pages.py#L14
- Audit inventory: https://github.com/Dimkox/ai-dark-factory-landing/blob/6226aa0b86e1fe08c63724cc3761b3f788146b91/tests/site_browser_contract.py#L8
- Existing unit regression: https://github.com/Dimkox/ai-dark-factory-landing/blob/6226aa0b86e1fe08c63724cc3761b3f788146b91/tests/test_site_browser_contract.py

Cached source identities (verified by recomputing each Git blob ID from fetched bytes):

| File | Git blob | SHA-256 |
|---|---|---|
| `tests/site_browser_contract.py` | `adaf99be473c61e90ec078ad1e37e90bef20d693` | `45beed3a509c91d390298f0c38cfa0ecdb934e23f769a9cc29092f48d0f42cf4` |
| `tests/test_site_browser_contract.py` | `14653e1f3c068e12b0a8a03b3be4a921b5afc57e` | `8f68861e168722e465ceb51b4f611b388758ee9aec830cf4d9f7e8db1f7f3d0b` |

Copies are under `landing-6226aa0/tests/` adjacent to this draft; `next-pilot-source-manifest.json` binds commit, URL, blob, byte hash and local path. They are observation copies, not an implementation or a reviewed candidate.
