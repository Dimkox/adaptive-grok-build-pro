# Code review — issue #53 change-package path boundary

Reviewer: independent `code_reviewer` (route `cba934e15911`), read-only, effort high.
Candidate reviewed: HEAD `cb9af407` plus the staged diff of `.grok-stack/adaptive_grok/change.py`,
`tests/test_change_path_safety.py` and this change package. The reviewer was forbidden from
writing to the tree; `git status --porcelain` before and after the review was identical.

## Independent measurements taken by the reviewer

- `ruff check --no-cache .grok-stack/adaptive_grok/change.py tests/test_change_path_safety.py` → `All checks passed!`
- Over-tightness probe (the brief's Q2): **0 of 148** directory names under `engineering/changes/`
  in this worktree are refused by `change_id_block_reason`; widened to the union across sibling
  worktrees, **0 of 275** refused, longest name 97 bytes. The 19 Cyrillic names pass.
- Symlink containment was confirmed empirically for three cases: a link to an existing outside
  directory, a **dangling** link (non-strict `resolve()` still reports the link target, so it is
  caught), and `changes/x -> ..`.
- Legitimate-title battery: Cyrillic, `:`-bearing, `/`-bearing, URL and multi-line `\n` titles
  all accepted; no existing test in `tests/` supplies a title, `route_id` or `created_at` that
  the new gate would refuse, and nothing asserts `FileNotFoundError` from `transition`.
- For string inputs `_derive_change_id` is byte-identical to the replaced f-string on ASCII,
  Cyrillic and punctuation-heavy probes, so no derived id diverges from history and no new
  collision is introduced (`route_id` is a 12-hex `sha256` prefix, so `[:6]` behaves as before).
- `scripts/grok_artifacts.py:65` and `workflow_artifacts.py:486,517` build
  `engineering/changes/<id>` from caller input but bind it to the validated active-change record;
  no other code path `mkdir`s under the packages root.

## Findings

### Critical
None. Nothing constructible reached `shutil.copytree`, `dump_json`/`atomic_write_text` or
`_mirror_checkpoints` with a target outside one safe component.

### Major (all three fixed in this contour)
1. `change_id_block_reason`/`package_dir` — `candidate.resolve()` on a symlink loop raised
   `RuntimeError: Symlink loop from '<absolute repo path>/engineering/changes/loopa'`, an
   uncaught traceback that prints the host path: fail-open on exactly the surface #53 is about,
   and `RuntimeError` collides with `start_change`'s "No active route" type. **Fixed**: the
   resolve is wrapped and answered with the printable `ValueError`; the suite now covers a
   symlink-to-outside and a two-node symlink loop and asserts the absolute path is absent.
2. `title_block_reason` screened Windows shapes only, so a POSIX absolute path handed as a
   title still published host identity: `/home/pall/secrets/new-chat/notes` derived
   `20260925-home-pall-secrets-new-chat-notes-<rid6>`. **Fixed** with an anchored
   `ABSOLUTE_PATH_TITLE` rule (two or more segments, at the start of the title), deliberately
   narrower than a mention-level scan so `/goal …`, `api/v1 vs api/v2`, a relative
   `scripts/grok_verify.py`, an embedded `https://…` URL and prose that merely contains such a
   path later on stay accepted.
3. `TITLE_CONTROL_BYTES` refused `\r` (a CRLF-pasted prompt failed on the default no-`--title`
   path, where `start_change` uses the raw route task) and `scripts/grok_change.py` catches
   nothing, so the operator got a traceback. **Partly fixed here**: tab, LF and CR are now
   ordinary whitespace and covered by a test. The CLI's missing `except ValueError →
   parser.error(...)` is **not** fixed here because `scripts/grok_change.py` is contended by
   another contour in this wave; recorded as a required follow-up (the established sibling
   pattern is `grok_gate.py:50`, `grok_governance.py:53`).

### Minor
4. `_derive_change_id` coerced non-string route fields with `str(...)`, so `created_at=None`
   produced a `None-…` id and a `None` route prefix destroyed the uniqueness suffix (two
   same-day same-slug packages would then return each other's state). **Fixed**: route fields are
   type-checked before use and refused with a printable message.
5. No bound on the echoed value: a 200 000-character title produced a 200 183-character message,
   copying the whole raw prompt (possibly with credentials) to stderr. **Fixed** with a 160-char
   limit plus a truncation marker, asserted directly.
6. NTFS reserved names (`CON`, `nul.txt`) and a trailing `.`/space were accepted — unreachable
   through `start_change` (the id always starts with eight digits) but reachable through a
   caller-supplied `change_id`. **Fixed** (`RESERVED_WINDOWS_NAMES` plus the trailing `.`/space
   rule), and the leading-dash case the test review measured is refused as well.
7. Paperwork precision in this package: the tracked-path count quoted in `test-plan.md` was
   stale (3937 at snapshot time, 3949 with the staged package) and three tests legitimately read
   the live checkout (read-only, descriptor-based). Corrected in `test-plan.md`.

## Informational, left alone on purpose
- A package symlink aimed at a *sibling inside* the packages root passes containment and would
  rewrite that sibling's `state.json`; it needs pre-existing attacker-created filesystem state,
  and the containment rule as written is the documented idiom elsewhere in this codebase.
- `trust-ci/**` regexes and `schemas/change-spec.schema.json:29` (which still allows `:` in
  `change_id`) remain looser than the writer rule; recorded as accepted debt in
  `requirements.md`, and `trust-ci/**` is issue #58's contour.
- The untracked half of #53 (working-tree litter, which `git ls-files` cannot see) is not
  covered by this seam.

## Verdict
PASS for merge-pending-push quality — no Critical defect, no orphaned package, no test or
type regression. Findings 1, 2, 3(partial), 4, 5 and 6 were fixed in this contour before the
final gate; the CLI exception handling in finding 3 and the schema looseness above are recorded
as follow-ups rather than silently absorbed.
