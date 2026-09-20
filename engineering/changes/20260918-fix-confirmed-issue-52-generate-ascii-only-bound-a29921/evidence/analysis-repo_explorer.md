# Repository analysis for issue #52

## Naming path and confirmed reproduction

`scripts/grok_change.py start [--title ...]` is the only current entry point that creates a change package; it delegates to `adaptive_grok.change.start_change()` in `.grok-stack/adaptive_grok/change.py`. With no explicit `--title`, `start_change()` uses `route['task']`; the router stores the original user task there. With `--title`, caller-supplied text is used instead. The ID expression combines the route creation date, `slugify(title)`, and the first six route-ID characters. `slugify()` in `.grok-stack/adaptive_grok/util.py` lowercases and retains `[a-zа-яё0-9]`, replacing other runs with hyphens. Thus it deliberately preserves Cyrillic and prompt-derived words.

Reproduced in a temporary project using task `Исправить обработчик API: удалить утечку персональных данных`: `start_change()` created `20260918-исправить-обработчик-api-удалить-утечку-персонал-f17041`; `change_id.isascii()` was `False`. The directory path was `engineering/changes/<that-id>`. The slug fragment is capped at 48 characters, but the complete ID is up to 64 characters (8 date + 48 slug + 6 route suffix + 2 separators), and the slug embeds a recognizable prefix of the raw task. This is both a non-ASCII path and unnecessary prompt disclosure in a durable directory name.

## Downstream compatibility and callers

The workflow artifact loader and path builder in `.grok-stack/adaptive_grok/workflow_artifacts.py` require change IDs to match `[A-Za-z0-9._:-]{3,128}`. A package generated from a Cyrillic task therefore can be created successfully but later rejected when compiling or locating workflow artifacts. Other package consumers generally trust the active `change_id`/path pair or interpolate the ID; there is no second package-creation implementation found in `scripts/` or `.grok-stack/adaptive_grok/`.

`user_prompt_submit` creates/stores a route, not a package. The raw task reaches package naming only when `grok_change start` defaults its title from the active route; the explicit `--title` route is a second input to the same unsafe slug operation. Replacing or renaming historical directories in place would affect route, state, receipts, specs, and workflow references; migration should preserve existing IDs/paths and constrain new IDs, with any old-path migration handled separately and explicitly.

## Existing test coverage and gaps

`tests/test_change_receipts.py::ChangeTests.test_start_creates_durable_package` creates a package from the Russian task `Добавить Битрикс модуль синхронизации`, but asserts only that it exists and has expected files/content; it does not assert ASCII-only naming or prompt non-disclosure. The same class tests route-required behavior and state transitions. `tests/test_verification_doctor.py` exercises generated package specs using Russian task fixtures, likewise without checking ID character set or maximum total length. `tests/test_hooks.py::test_user_prompt_submit_creates_route` checks that the raw prompt routes successfully, but does not start a package. No current regression test covers `--title`, ASCII-only IDs, full-ID bounds, a generated ID accepted by the workflow-artifact validator, or preservation of pre-existing package paths.

## Evidence boundaries

The reproduction ran entirely in a temporary directory and changed no product files. This is static call-site/test analysis plus a focused reproduction, not a verifier run. The only repository write for this analysis is this evidence note.
