# Security review — workflow artifact adapters (`1b0c02`)

PASS

Baseline: `b6fe340`, head `c4b5e3f`, diff `git diff b6fe340...HEAD`. Reviewer: read-only
security pass; no repository file other than this report was created or modified.

Threat model applied: documents imported from Spec Kit / BMAD / Superpowers trees are
untrusted advisory data and must never acquire route, governance, approval, receipt,
Trust CI or merge authority (INV-001, FORBID-001..003 of this package's `change-spec.yaml`,
`docs/superpowers/specs/2026-08-30-workflow-artifact-adapters-design.md` with the 2026-09-15
amendment, `engineering/adr/0001-workflow-source-version-contract.md`).

No elevation path was found. Findings below are availability, hardening and hygiene items;
the first is the only one worth fixing before merge.

---

## Area 1 — authority boundary in the adapter module and CLI

Confirmed by reading the full module (`1751` lines) and the CLI, not only the diff.

**Descriptor-bound reads.** `_read_regular`
(`.grok-stack/adaptive-grok/workflow_artifacts.py:310`) opens the canonical root with
`O_DIRECTORY|O_NOFOLLOW` (`_open_root`, `:296`), then walks every path component with a
per-component `O_NOFOLLOW|O_DIRECTORY` `dir_fd` open and opens the leaf with
`O_NOFOLLOW|O_NONBLOCK`. Special-file and size limits are enforced *before* any byte is
read (`stat.S_ISREG` plus `st_size > limit` on the pre-read `fstat`, `:324`), the read loop
is chunked against the limit (`:329`), and a full dev/ino/mode/size/mtime/ctime identity
tuple is compared before and after (`:338`-`:350`), so an inode swap or in-place completion
during the read fails closed with code `race`. The platform gate refuses to run at all when
`O_NOFOLLOW`/`O_DIRECTORY`/`O_NONBLOCK`/`O_CLOEXEC` or `dir_fd` support is absent (`:300`).
FIFO interposition therefore cannot block the reader; the behaviour is pinned by
`tests/test_workflow_artifacts.py:115` and
`tests/test_workflow_artifacts_adversarial.py:238`, `:292`.

**Canonicalisation and NFC.** `_relative_path` (`:263`) rejects backslashes, control
characters, `.`/`..`/empty segments, absolute escapes, non-NFC and over-long values;
`_bounded_text` (`:285`) and `_bounded_walk` (`:215`) additionally require every string to
be already-NFC, control-free and length-bounded; `_bounded_markdown` (`:296`) rejects NUL,
non-NFC bodies and per-line/per-document line-count limits before any regex runs. Manifest
paths are additionally require-start-with-the-framework-prefix plus a role-specific prefix
rule and case-fold duplicate rejection (`:386`-`:402`).

**Strict JSON.** `_strict_json` (`:240`) rejects a UTF-8 BOM and over-limit payloads, uses an
`object_pairs_hook` that fails on any duplicate key, rejects non-finite constants, then runs
`_bounded_walk` for depth/node/string bounds. Comment-carried metadata is parsed through the
same function, so imported JSON fragments inherit the bounds
(`:592`, `:663`, `:909` region and `_explicit_claims` `:1053`).

**Active-change containment and runtime authority.** The CLI reads both authority pointers
through the same bounded loader (`scripts/grok_artifacts.py:64-69`,
`workflow_artifacts.py:431`): route payloads must have every key inside `RUNTIME_ROUTE_KEYS`
plus the four required keys and pass `_validate_route` (`:536`) whose `required_evidence` is
validated against a closed receipt-kind set; the active-change pointer must be exactly
`{change_id, path}` with `path == "engineering/changes/<change_id>"` and a pattern-constrained
id (`:453`-`:459`), and the requested change must equal the active change before any work.

**CAS publication.** `cas_write` (`:1510`) validates a lowercase 64-hex precondition, payload
size, target segment count/length/NFC, and an allowlist of leaf forms
(`task-graph.json`, `convergence-report.json`, or paths rooted in `projections`/`exports`),
re-validates derived JSON for the two direct targets including byte-exact canonical
re-serialisation, and takes a per-target `flock` under a `0o700` runtime directory with a
post-lock identity recheck (`:1451`). Publication uses `O_EXCL` plus `os.link` for a missing
target (never clobbers: `FileExistsError` → `CAS target appeared before publication`,
`:1657`), and `renameat2(RENAME_EXCHANGE)` for an existing target with a pre-exchange identity
recheck of both names (`_rename_exchange`, `:1425`). Post-exchange, the displaced entry's
identity *and* digest are verified before the result is trusted, and any mismatch triggers
rollback **before** displaced content is used; a second racing writer's entries are preserved
under bounded recovery names via `RENAME_EXCHANGE`-then-`RENAME_NOREPLACE` rather than
removed (`:1700`-`:1740`). There is no `unlink`, `os.remove`, `shutil`, `O_TRUNC` open or
`.replace()` of a tracked path anywhere in the module (only string `.replace` on status
tokens at `:682`-`:689`), which matches the no-delete recovery contract. Race behaviour is
pinned by `tests/test_workflow_artifacts_adversarial.py:543`, `:568`, `:595`, `:639`, `:677`,
`:715`, `:752`, `:800`.

**No executor.** A repo-wide grep of `workflow_artifacts.py`, `scripts/grok_artifacts.py`,
`receipts.py` and `verification.py` for `subprocess|exec(|eval(|os.system|Popen|__import__|socket|urllib|requests|http`
returns exactly one hit: the *rejection* of network locators in imported argv
(`workflow_artifacts.py:526`). Imported RED/GREEN metadata is only ever shape-validated
(`_verification_command`, `:517`): a `python3 -m unittest` prefix with dotted module targets
matching `SAFE_UNITTEST_TARGET`, or two exact `scripts/grok_verify.py` invocations; anything
else raises. The only non-test consumer of `task-graph.json` in the tree is
`scripts/grok_artifacts.py:102` (it re-serialises it); no hook, skill, script or Trust CI
component reads the graph/report and executes its `red`/`green` fields.
`tests/test_workflow_artifacts_adversarial.py:115` asserts this with `subprocess.run` and
`socket.create_connection` patched to raise around `compile_task_graph` + `converge`;
`:101` covers shell/interpreter/network argv rejection.

Residual advisory note (not a defect): because the graph stores argv verbatim, a human who
copies an allowlisted unittest target into a shell imports whatever module of that name is
importable in the checkout. The allowlist keeps the grammar narrow; the exposure is social,
not automated.

## Area 2 — the `FORBIDDEN_SOURCE` narrowing (`workflow_artifacts.py:101`)

Probed with the shipped regex and the real loader in throwaway temp directories
(document-node tag forms, merge-key forms, anchor-shaped and alias-shaped values,
tab-indented variants, flow-context variants, mid-line variants, CRLF-terminated variants,
plus the upstream emphasis forms the amendment cites). Classification:

Rejected (fails closed at load, code `content`):
- tags appearing at line start or after whitespace, in any position;
- merge-key forms appearing at line start or after whitespace;
- anchor-shaped values in document/sequence position, including tab-indented and
  sequence-item tab variants;
- anchor-shaped values introduced by a colon plus space **or** colon plus tab;
- whole-value alias forms after `: ` or `- `, tab-indented, when the alias is the final token
  of a LF-terminated line.

Accepted after the narrowing:
- line-initial emphasis values (the intended upstream-template class the amendment names;
  these now load, which is the point of the change);
- flow-context merge-key and flow-context alias forms, i.e. the same constructs when the
  indicator is introduced by a brace or bracket rather than by line start/whitespace/colon;
- alias-shaped values followed by further flow content on the same line;
- alias-shaped values whose line ends with CRLF — alternatives 5 and 6 anchor with `[ \t]*$`
  and re.M `$`, which a carriage return defeats; note this specific evasion is *new* with
  respect to the pre-amendment shape, whose bare `(^|\s)[&*]\w+` alternative did catch it;
- tag/anchor indicators not preceded by whitespace or a colon-space (mid-word occurrences);
- anchor-shaped values mid-line after other scalar content.

Authority impact assessment: none of the accepted classes can confer authority in this tree,
because no YAML parser is ever applied to imported content — the module imports only
`hashlib, itertools, json, os, re, stat, ctypes, errno, fcntl, threading, unicodedata,
pathlib, typing` (`:1`-`:17`), and `change-spec.yaml` / `architecture/system.yaml` are parsed
with strict JSON, not YAML (`:490`, `:1085`). Imported text reaches the compiler only through
Markdown-anchored fullmatch extraction of JSON fragments
(`TASK_PATTERN`/`CLAIM_PATTERN`/`STATUS_PATTERN`, `:110`-`:112`) and fixed regex status probes
(`_source_status_is_terminal`, `:668`). What still stops elevation even if a YAML sink were
introduced later: the closed role/type allowlist (`ROLE_MAP`, `:64`, enforced `:382`), the
per-framework path-prefix allowlist, the descriptor-bounded read, every derived candidate row
being hardcoded non-authoritative (`adapt_sources`, `:464`-`:481`: `authority: false`,
`receipt_eligible: false`), `covers` tokens constrained to native
`AC|INV|FORBID-nnn` ids with a hard failure on unknown or missing coverage (`:875`-`:881`),
and the fact that the new verifier check can only *add* failures.

**Finding S2 (low).** The guard is now block-context-only and CRLF-evasive, while the
amendment text (item 1) reads as if tags/merge keys/anchors/aliases "still fail closed"
unconditionally. Remedy: either normalise `\r` out before the search and extend the alias and
merge alternatives to brace/bracket introducers, or state the guard's exact scope in the
amendment so a future YAML sink is not added against a falsely total claim.

## Area 3 — verifier check and receipt hardening

**Finding S1 (medium, only pre-merge item).** `MAX_TASKS` is enforced after full
materialisation: `_task_metadata` builds every generated task row for every source before
`compile_task_graph` compares the total against the limit
(`workflow_artifacts.py:721`-`:724`), while the per-source text limit permits ~19,999 rows per
document (`MAX_MARKDOWN_LINES`, `:23`) and the manifest permits 256 sources (`:19`-`:20`).
Measured on this host: 1 source × 19,999 rows → 0.2 s, +19 MiB; 16 sources × 19,999 rows
(319,984 rows) → 4.4 s, +322 MiB, all produced and held before the 500-row guard fires.
A manifest at the declared maxima extrapolates to roughly 5 million rows (multiple GiB RSS,
~70 s CPU) plus up to 256 MiB of bounded reads/hashes, and the resulting `MemoryError` is not
in the exception tuple caught by `_workflow_artifacts_check`
(`.grok-stack/adaptive_grok/verification.py:341`), so `grok_verify` aborts with a traceback
instead of returning a failed `CheckResult`. Reachability is a repository write, not an
imported document alone — but that is exactly what an external pull request supplies (a
manifest plus the named documents under the framework prefixes), and the local preflight runs
against pull-request trees. Remedy: count and reject inside `_task_metadata` as soon as the
running total exceeds `MAX_TASKS` (and consider a per-run aggregate budget across
`MAX_SOURCES × MAX_SOURCE_BYTES`), and catch `MemoryError`/`RecursionError` in
`_workflow_artifacts_check` so resource pressure surfaces as a clean fail.

**Read-only guarantee (verified).** `_workflow_artifacts_check`
(`verification.py:267`-`:349`) performs no writes: it `lstat`s the manifest, skips when
absent (`INV-002`: historical packages without `workflow/manifest.json` keep skipping, pinned
by `tests/test_verification_doctor.py` `WorkflowArtifactsVerificationTests`), fails on a
symlinked or non-regular manifest, then only calls `validate_evidence` +
`validate_stored_workflow`. The added test snapshots the tree with `rglob` before and after
and asserts byte-identical path sets on the failing path. Independent confirmation: the
`skip` branch also fires before `validate_evidence`, so a hostile manifest cannot turn the
check into a writer. One pre-existing wrinkle, not introduced here and not reachable while
`.grok-stack/runtime` exists: `validate_evidence` transitively touches `runtime_dir`/
`receipt_dir` helpers that `mkdir` (`util.py:43`, `receipts.py:460`).

**Closed receipt set and envelope (verified).** `get_receipt`
(`.grok-stack/adaptive_grok/receipts.py:558`) now requires a pattern-bounded `route_id` and a
`kind` inside `RECEIPT_KINDS`, raises rather than silently returning `None` otherwise, walks
`.grok-stack/runtime/receipts/<route_id>` component-by-component with
`O_RDONLY|O_DIRECTORY|O_NOFOLLOW`, opens the leaf `O_NOFOLLOW|O_NONBLOCK`, requires a
regular file ≤ 256 KiB read within the cap, re-checks the fstat identity tuple, and rejects
duplicate JSON keys, non-finite constants, non-object roots and non-UTF-8. A symlinked
receipt directory, a symlinked/FIFO receipt, or an oversized receipt therefore becomes a
`RuntimeError` that `validate_evidence` converts into a `"<kind>: unsafe receipt: …"` error
(`receipts.py:666`-`:670`) — fail-closed, never followed, never blocking. `validate_evidence`
additionally validates `route_id`, requires a non-empty duplicate-free `required_evidence`
inside the closed set, requires a 64-hex trusted fingerprint, and enforces the ten-field
envelope (`schema_version`, `route_id` match, `kind` match, `status ∈ {pass,fail}`, string
`created_at`, dict `details`, list `criterion_ids`) on top of the pre-existing
stale/status/fingerprint/spec/architecture/governance binding checks. Tightening is
one-directional: an imported artifact can never satisfy this envelope, and no new accepted
receipt shape was introduced. `get_receipt` has no caller other than `validate_evidence`
(repo-wide grep), so the raise-instead-of-`None` signature change breaks no other path.
`tests/test_workflow_artifacts_adversarial.py:473`, `:485`, `:497` pin recursion bounds,
minimal forgery rejection and symlink/FIFO handling.

**TOCTOU.** `verification.py:289`-`:303` inspects the manifest with `lstat`/`is_file`/
`is_symlink` and only later reads it through the descriptor walker; the advisory check can
thus disagree with the authoritative read, but the authoritative read is the one that decides,
so the window is not exploitable for elevation or for following a link. Same shape applies to
`_load_stored` (`:1355`) which funnels through `_read_regular`.

## Area 4 — boundary hygiene

Verified clean:

- **No GitHub Actions.** There is no `.github/` directory in the tree at all, and the diff
  adds none (INV-003; `tests/test_structure.py`).
- **No vendored third-party code.** Filtering the added-path list for
  `node_modules|vendor|third_party` yields zero hits; the only third-party-adjacent additions
  are this repository's own advisory documents, schemas, tests and projections. `ADR-0001` and
  `decisions.md:690` restate the never-vendor rule.
- **Committed projection content.** `.specify/specs/workflow-artifact-adapters/tasks.md`
  carries an explicit non-authoritative header (`:1`-`:5`), declares checkbox status to be
  source claims rather than evidence, and its eight `AGB-TASK` records use only allowlisted
  unittest/`grok_verify` argv and native criterion ids. The dogfooded manifest
  `engineering/changes/20260830-…-d41aa6/workflow/manifest.json` names three existing regular
  files; recomputing its digest in this tree yields
  `aa5985f1…c12b5b`, byte-identical to the committed graph's `source_manifest_digest`, so the
  new `.specify` addition does not silently invalidate a pinned historical record.
- **`toolchain.json` cannot steer doctor/installer.** The new `workflow_sources` block
  (`:206`-`:251`) is consumed only by `tests/test_workflow_sources.py:34`; its `policy` value
  is a prose string, and no non-test code reads `workflow_sources` (repo-wide grep). Doctor's
  install offers and the installer's managed set derive from the pre-existing `tools` array
  and `MANAGED_FILES`/`managed.json`, which this diff extends only with in-repo script and
  schema paths.
- **No new network, secret or unmanaged file-write surface.** No outbound call exists in the
  diff (see the grep in Area 1); the only writes are `cas_write` targets plus its runtime lock
  directory. A pattern scan of added diff lines for private-key markers, provider token
  shapes, credential assignments and personal addresses returned nothing (FORBID-003 holds).
- **Documentation does not over-promise.** The QUICKSTART addition states the CAS/rollback
  semantics and ends with the explicit disclaimer that imported documents and their
  allowlisted RED/GREEN argv are never executed and never become route, governance, approval,
  receipt or merge authority; the README table paragraph and `START_HERE.md:10` describe the
  adapters as advisory with a `workflow_sources` pin; the amendment's authority note keeps
  `source_version` non-authoritative. Only one phrase is loose — **Finding S6 (nit)**: the
  README capability bullet's lead adjective "Safe … artifact imports" reads as a product
  guarantee; prefer "Advisory-only … imports that cannot grant authority".

## Additional findings

**Finding S3 (low).** `cas_write` (`workflow_artifacts.py:1510`-`:1530`) does not itself bind
`change_id` to the active change; containment lives only in
`scripts/grok_artifacts.py:66`-`:69`. Under the same allowlist a future or adjacent caller can
therefore publish into any well-formed change id's `workflow/` subtree, and the
`projections`/`exports` prefix rule constrains only the first segment — leaf names and
extensions are unrestricted (`exports/<anything>`, including executable-looking names), and
for projected targets the payload is not schema-validated the way the two direct targets are.
Impact today is confined to the change-package subtree, and no in-repo caller exercises it.
Remedy: re-check `get_active_change(root)` (or accept only a validated paths bundle) inside
`cas_write`, and constrain leaf names to `[A-Za-z0-9._-]+\.(json|md)`.

**Finding S4 (nit).** The closed receipt-kind set is duplicated as an independent literal in
`workflow_artifacts.py:35` and `receipts.py:40`; the adapter's route validation and the
canonical receipt validator can drift apart silently. Remedy: import the canonical set from
`adaptive_grok.receipts` (one direction) or move it to shared constants and pin equality in a
test.

**Finding S5 (nit).** Runtime scratch created by the CAS path is never reclaimed:
one `<sha256>.lock` per (change, target) under `.grok-stack/runtime/workflow-cas/<change_id>`
(`:1451`-`:1470`) plus retained `.agb-recovery-<24 hex>` payloads (`:1585`-`:1598`). This is
intentional fail-closed retention (no unlink anywhere in the module, and the runtime tree is
excluded from installation by `scripts/install_into.py:76`), but it is unbounded across long
use. Remedy: document an operator cleanup runbook for the `workflow-cas` subtree; do not add
automatic deletion to the publication path.

**Finding S7 (nit).** Dead advisory code shipped as if live: `_advanced_status_hints`
(`:698`) has no call site in `converge` (the amendment discloses this at `:52`-`:57`), and
`converge` calls `effective_task_statuses(graph, receipt_errors)` and discards the result
(`:1292`). Harmless for authority — it makes the status vocabulary strictly *less* influential
than the docs imply — but it means the terminal/non-terminal token sets in `:130`-`:137`
behave as unreferenced constants in the shipped convergence path and should stay labelled
that way in tests and docs until wired.

## Verification performed

- Focused module runs (full suite deliberately not run): `tests.test_workflow_artifacts` +
  `tests.test_workflow_artifacts_adversarial` → 44 tests, OK; `tests.test_workflow_artifacts_cli`
  + `tests.test_workflow_sources` → 13 tests, OK; `tests.test_installer` → 17 tests, OK in
  9.9 s; `tests.test_verification_doctor.WorkflowArtifactsVerificationTests` → 2 tests, OK
  (includes the read-on-fail tree snapshot assertion).
- Observation, not a finding: the whole `tests.test_verification_doctor` module exceeded 120 s
  on this host (its pre-existing end-to-end `verify()` cases run external tooling). The added
  class itself runs in 4 ms, so this is not adapter cost — but it is the same reason the S1
  aggregate budget matters, since the adapter check is now inside that path.
- Guard classification and loader probes were run against the shipped module in throwaway
  temporary directories only; nothing in the worktree was modified by them.
