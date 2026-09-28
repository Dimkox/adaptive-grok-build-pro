# Issue 169 — analyzer scope documentation research

Route: `7e7193c77d53`. Role: `docs_researcher`. Research date: 2026-09-21.
Repository: `/home/pall/grok-projects/adaptive-grok-build-consumer-coverage`.
Route base: `21ced3709dff48abf3e15aff62e2493de75f2fa0`.

This is static analysis, not verification or approval. I read the engineering contract, entrypoint and selected current-state fields, actual route, active brief, preserved prior design, issue body, configured analyzer commands and primary upstream documentation/source. No tests, analyzer commands, compiler, native project scripts, Docker, installation or version/process probes were run. The only repository write is this report. The parent owns integration, the CPU lane, source changes and shared-memory updates.

## Local facts and version boundary

- `.grok-stack/adaptive_grok/verification.py:815` defines `QUALITY_PY_PATHS`, a fixed stack-oriented list. `_existing_quality_paths` retains existing entries. An arbitrary consumer `src/` or `engineering/` is not thereby an analyzer input.
- `_ruff` at line 840 executes `ruff check <existing-quality-paths>`; `_bandit` at line 849 excludes the top-level `tests` input, then executes `bandit [-c bandit.yaml] -q -r <paths>`. Neither result currently carries analyzer-selected file evidence.
- `_command_check` at line 353 interprets exit zero as pass and retains only the last 12,000 characters of each stream. Those tails are unsuitable for parsing a complete inventory or JSON document.
- Root `ruff.toml` excludes `engineering`, `packages`, `examples` and other directories. Root `bandit.yaml` similarly excludes `engineering` and tests, among other paths. These are current factory settings, not a definition of consumer ownership.
- The base quality profile lists Ruff and Bandit as optional. Existing tests explicitly retain missing-tool skips. The proposed aggregate applicability check can reject uncovered relevant product changes without turning every individual skip into a failure.
- `trust-ci/runner.Dockerfile:24` pins **Ruff 0.16.2** and **Bandit 1.9.4**. Consumer `_ruff`/`_bandit` only check executable availability; `toolchain.json` and the Core test requirements do not enforce these two versions. Therefore the tagged findings below qualify those versions, not every executable a consumer might place on `PATH`.

## Evidence vocabulary

| Fact | Honest meaning | Insufficient substitute |
| --- | --- | --- |
| Relevant changed product paths | Independently inventoried verification obligations | Analyzer input arguments or detected repository language |
| Discovered candidate files | Paths returned by a tool's discovery stage | Files successfully analyzed |
| Completed analysis paths | Files for which the actual invocation provides processing evidence without a per-file error | Zero diagnostics, exit zero, or a nonempty candidate list |
| Findings | Violations reported under the active rule/suppression policy | Number of analyzed files |
| Bandit `loc` | Its own nonblank, non-comment line metric | File count, test coverage percentage, or proof of successful AST analysis |
| Unknown scope | Required evidence is missing, ambiguous or incomplete | Empty scope or not-applicable |

In particular, an empty but successfully processed Python file can legitimately have zero Bandit LOC. A fixed `loc > 0` success threshold would confuse absence of code with absence of a check. The file-level intersection with relevant changes is the useful obligation.

## Ruff: discovery is not completed linting

Ruff resolves the closest eligible configuration per file, supports explicit inheritance, and gives dedicated CLI options precedence. An explicitly supplied configuration changes relative-path interpretation and disables normal per-directory discovery. Direct files normally bypass discovery exclusions; `force-exclude` changes that. Git ignore files and nested configuration also affect discovery. Copying root exclusion patterns into a second homemade matcher would not reproduce these semantics. [Official configuration documentation](https://docs.astral.sh/ruff/configuration/#config-file-discovery), [tagged 0.16.2 configuration documentation](https://github.com/astral-sh/ruff/blob/0.16.2/docs/configuration.md).

The advertised `--show-files` interface is a cheap discovery pass, but in **0.16.2** it writes sorted, newline-delimited `to_string_lossy()` paths. It neither emits a JSON array nor uses the diagnostic output formatter; adding `--output-format=json` does not make this listing JSON. It silently flattens individual discovery errors and returns success for an empty list. Treat its output as candidate evidence only, with ambiguous/non-UTF-8 names, incomplete output or discovery uncertainty marked unknown. This is an explicit boundary, not a request to implement issue 129 here. [Tagged `show_files.rs`](https://github.com/astral-sh/ruff/blob/0.16.2/crates/ruff/src/commands/show_files.rs#L18-L47), [early dispatch in `lib.rs`](https://github.com/astral-sh/ruff/blob/0.16.2/crates/ruff/src/lib.rs#L218-L255).

There is an additional material mismatch: normal linting applies **`settings.linter.exclude` after discovery**, whereas `--show-files` does not. Normal checking skips that exclusion only for explicit root files when `force-exclude` is false. Some discovery/read failures become warnings and empty diagnostics when `E902` is disabled. Its internal debug total counts attempted result slots, including error paths, and cannot prove that product files completed analysis. Thus a nonempty listing plus exit zero is not a general coverage attestation. [Tagged normal checking](https://github.com/astral-sh/ruff/blob/0.16.2/crates/ruff/src/commands/check.rs#L75-L175).

Root arguments are marked `ResolvedFile::Root`; directory descendants are `Nested`. Root entries take precedence during deduplication. Resolver-level `exclude`/`extend-exclude` filters are normally applied to descendants, with forced exclusion filtering explicit arguments as well. Consequently changing a directory invocation into explicit changed-file arguments can change user scope even with identical configuration bytes. This can be a deliberately documented mode, but is not a transparent observation of the original invocation. [Tagged resolver](https://github.com/astral-sh/ruff/blob/0.16.2/crates/ruff_workspace/src/resolver.rs#L394-L654).

Cache semantics matter only if attempting to derive processing from debug lines: a cache hit returns before the `Checking:` log line. That line is emitted before source reading, so it is not completion evidence either. Source-read failures can again become warnings when `E902` is off; extension mappings can alter the interpretation of a `.py` argument. Avoid interpreting debug output as a stable machine contract. [Tagged diagnostics/cache implementation](https://github.com/astral-sh/ruff/blob/0.16.2/crates/ruff/src/diagnostics.rs#L169-L266).

For ordinary Python source that reaches parsing, parse-error diagnostics are appended independently of the selected lint rules. In normal check mode these produce failure; `--exit-zero` and configured `fix-only` can alter the exit behavior. A verifier must retain read-only, diagnostic-producing operation rather than inherit automatic fixes. This establishes a useful future invalid-syntax control, but does not remove scope exclusion or read-error gaps. [Tagged parser-to-diagnostic conversion](https://github.com/astral-sh/ruff/blob/0.16.2/crates/ruff_linter/src/linter.rs#L309-L347), [tagged exit and fix handling](https://github.com/astral-sh/ruff/blob/0.16.2/crates/ruff/src/lib.rs#L256-L279).

**Explicit-file answer:** qualified regular `.py`/`.pyi` inputs bypass both kinds of exclusions when effective forced exclusion is off. When it is on, all supplied files can be omitted with exit zero. Unreadable/missing inputs do not universally fail. Therefore explicit arguments alone are not a sufficient proof while preserving unrestricted consumer settings. A positive Ruff adapter needs a narrow, verified configuration contract; unsupported settings or absent proof must yield unknown coverage. Do not silently add `--no-force-exclude`, `--isolated`, a rule reset, or a rewritten consumer config to obtain a green result.

No complete clean-file machine manifest was found in the inspected interfaces. SARIF also serializes diagnostic results, not all processed artifacts. `--show-settings` resolves only the first discovered file and renders settings as text. Test/helper paths excluded from Bandit therefore need another actual applicable check or a qualified Ruff adapter; broadly exempting `tests/` would hide the same problem. [Tagged SARIF emitter](https://github.com/astral-sh/ruff/blob/0.16.2/crates/ruff_linter/src/message/sarif.rs#L31-L96), [tagged settings display](https://github.com/astral-sh/ruff/blob/0.16.2/crates/ruff/src/commands/show_settings.rs#L16-L36).

## Bandit: obtain scope from the existing analysis run

Use its documented JSON formatter in the **normal single scan**, preserving the current target and exclusion policy. JSON has separate `results`, `errors`, and `metrics`; the absence of findings is independent of scope. The formatter records skipped files in `errors` and emits the manager's metrics even for a clean run; its implementation has no quiet-mode early return. No second Bandit scan or import of consumer modules is necessary. [Official JSON format](https://bandit.readthedocs.io/en/latest/formatters/json.html), [tagged 1.9.4 JSON formatter](https://github.com/PyCQA/bandit/blob/1.9.4/bandit/formatters/json.py#L86-L144).

The manager starts each file's metric block and counts LOC **before** AST processing. Syntax/processing failures add that file to `errors` without removing its metrics. I/O failures can add an error without a metric block. For the inspected version, a conservative successful-file set is normalized metric keys excluding `_totals`, minus every filename in `errors`, provided the report and invocation are complete. Never count `len(metrics) - 1` as successful files without this subtraction. Discovery also applies exclusions to explicitly supplied files and uses glob plus substring matching; do not substitute Ruff's rules. [Tagged manager](https://github.com/PyCQA/bandit/blob/1.9.4/bandit/core/manager.py#L186-L315).

That successful-file formula additionally requires absence of internal processing failures: the plugin runner catches individual plugin exceptions, logs an error and continues unless debug is enabled. Such exceptions need not populate JSON `errors`. Reject the known internal-error diagnostic or unclassified processing stderr as incomplete; separately permit understood advisory warnings such as a redundant `nosec`. Do not turn debug mode on merely to extract scope, and do not rerun the analysis. [Tagged plugin exception handling](https://github.com/PyCQA/bandit/blob/1.9.4/bandit/core/tester.py#L96-L154).

Bandit counts lines after stripping whitespace and omits empty lines and lines beginning with `#`. A zero total can describe no selected files or selected empty/comment-only files; a positive total can include a subsequently failed file. Preserve the metric's name and meaning. [Tagged metrics implementation](https://github.com/PyCQA/bandit/blob/1.9.4/bandit/core/metrics.py).

INI `.bandit` options, explicit YAML/TOML configuration, CLI flags, test selection and `nosec` suppressions are distinct controls. YAML/TOML require `-c`; `-x` adds exclusions; CLI/config test lists combine. The existing verifier only explicitly selects root `bandit.yaml`; it must not claim that it automatically honored arbitrary consumer `pyproject.toml` Bandit configuration. [Official configuration documentation](https://bandit.readthedocs.io/en/latest/config.html), [official CLI documentation](https://bandit.readthedocs.io/en/latest/man/bandit.html).

At 1.9.4, CLI setup searches input trees for `.bandit`; multiple matches fail. Its option-source helper generally prefers nondefault CLI values. Setting JSON format explicitly avoids a discovered INI choosing the formatter, but any output-file override also needs a controlled evidence sink. Preserve genuine nonzero exit codes. Conversely, zero does not prove absence of skipped files: final exit depends on filtered findings, while per-file errors remain in the JSON. Empty enabled-test sets fail during setup. [Tagged CLI selection and exit implementation](https://github.com/PyCQA/bandit/blob/1.9.4/bandit/cli/main.py#L438-L661).

## Recommended bounded integration contract

These are design recommendations derived from the above interfaces, not implemented behavior or new acceptance authority.

1. Keep analyzer outcome and product-coverage outcome separate. Retain analyzer failures. A required aggregate check can return `fail` with `incomplete_product_coverage` while individual genuinely irrelevant tools retain `skip`; existing overall `pass|fail` remains compatible.
2. Use the independently bounded change inventory to define relevant surviving source paths. Intersect normalized same-root evidence paths with those obligations; a large managed-stack file count cannot cover a consumer file by association. Deleted-only files, non-source assets and unchanged files need explicit policy, not guessed analyzer coverage.
3. Instrument Bandit's existing invocation with JSON once. Validate the complete bounded document before publishing a small summary. Reject malformed schemas, duplicate JSON keys, unsafe/outside-root names, ambiguous normalization, cancellation, unexpected process failure, truncation or output-size exhaustion as unknown. Record successful product file count separately from total metric file count and LOC.
4. For Ruff, a bounded `--show-files` pass can expose a missing/excluded candidate intersection without repeating AST linting. Do not upgrade a positive candidate intersection into analyzed evidence. The architect must choose either a narrowly validated positive Ruff contract or conservative unknown until such evidence exists. A new general configuration resolver or patched upstream tool is not required merely to stop false green.
5. If choosing a future explicit changed-file Ruff mode, document its different exclusion semantics. Do not issue one shell command per file or execute package/native build scripts for detection. Preserve effective consumer exclusions and expose any unsupported `force-exclude`, rule, extension or output behavior instead of silently overriding it. Use direct argv with bounded argument volume; do not build shell strings or ambiguous argfiles.
6. Apply hard deadlines, bounded captured bytes and bounded displayed samples to both inventory and tool output. Do not parse the existing 12,000-character tails as whole reports. Store machine-safe escaped relative paths; retain counts plus explicit `scope_complete=false`/reason when boundaries are exceeded. A report cannot claim empty merely because its sample is empty.
7. An unsupported consumer language or missing applicable checker needs no native execution to establish missing coverage. Keep native detection passive; do not install a toolchain or infer Swift/Apple validation from Python checks. Do not count an existing arbitrary successful package script as file-level proof without a separately defined evidence contract.
8. Report actual executable version and adapter capability at verification time under the parent's lane. Unsupported versions/interfaces mean scope unknown, not guessed compatibility. The Docker pins do not establish a minimum consumer version. Characterize the chosen supported versions before granting positive scope credit.

## Focused cases to preserve for the implementation/test plan

No case below has been executed in this research task.

| Case | Required distinction |
| --- | --- |
| Consumer Python under excluded `engineering/` | Relevant inventory nonempty; managed checks alone cannot qualify product |
| Ruff top-level exclude versus `lint.exclude` | Candidate listing can disagree with actual lint scope |
| Explicit Python file with forced exclusion off/on | Bypassed exclusions versus silently empty scope |
| Ruff unreadable/missing input with `E902` disabled | Warning/zero is incomplete analysis |
| Ruff clean cache hit | Missing debug `Checking:` does not mean excluded |
| Bandit syntax error with nonzero per-file LOC | Metric key is not successful AST analysis; subtract errors |
| Bandit plugin exception logged only on stderr | Metrics with empty JSON errors still cannot qualify analysis |
| Empty or comment-only Python file | Successful file processing can have zero LOC |
| JSON/listing truncation, path ambiguity, unknown version | Unknown scope cannot become empty/applicable success |
| Only stack files selected; mixed Python/Swift consumer | Evidence must match each relevant product obligation |
| No applicable SQL/contracts and no related changes | Legitimate not-applicable skips remain compatible |

## Reusable lesson for the parent to record in shared memory

Inspect the pinned analyzer implementation before assigning evidence semantics to a discovery flag. Ruff's candidate listing omits a later exclusion stage, and Bandit's pre-parse metrics include failed files; separating candidates, successful analysis and errors prevents scope instrumentation from creating another false pass. Keep unsupported evidence explicitly unknown rather than duplicating an entire analyzer's configuration engine.
