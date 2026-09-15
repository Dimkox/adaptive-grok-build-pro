# Analysis — integration_architect: durable version contract for third-party workflow components

Route: `1b0c02b8a134` (`Update third-party workflow components (superpowers, bmad, speckit) to latest
upstream versions; …`), base commit `7b147366a1f9b7e4b59f17e10283cc8ad67ba0c8`, domains `integration,api`,
write owner `integration_implementer`. Read-only analysis; no product file was changed by this report.

Investigated trees:

- main line of this task: `/home/pall/grok-projects/adaptive-grok-build-pro-third-party-sync`
  (branch `feature/third-party-components-sync`, HEAD `7b14736`, only untracked path is this change package)
- source epic worktree: `/home/pall/grok-projects/adaptive-grok-build-pro-workflow-adapters`
  (branch `feature/workflow-artifact-adapters`, HEAD `dccaeec`, adapters present as **untracked** files)

## 0. Headline facts that decide the contract shape

1. **The adapters are not in git at all.** `workflow_artifacts.py`, `scripts/grok_artifacts.py`,
   `schemas/workflow-*.schema.json` and `tests/test_workflow_artifacts*.py` appear as `??` (untracked) in
   the epic worktree, and no ref in the repository ever contained them:

   ```
   $ git log --all --oneline -- .grok-stack/adaptive_grok/workflow_artifacts.py        # empty
   $ git log --all --diff-filter=A --oneline -- 'schemas/workflow-source-v1.schema.json'   # empty
   $ git ls-tree -r origin/feature/workflow-artifact-adapters --name-only | grep -i workflow_artifacts  # empty
   ```

   Consequence: on the PR base `7b14736` there is **no adapter code, no adapter schema and no adapter
   test** to version-pin. Any contract that lives inside the adapters (a `source_version` check) cannot be
   delivered by this change without also landing the whole unmerged epic — that is scope creep and is
   rejected below.

2. **The repo vendors none of the three components.** `git ls-files | grep -ci superpowers` → 28, all of
   them repo-authored documents and SDD evidence (`docs/superpowers/plans|specs/…`,
   `.superpowers/sdd/2026-08-28-m3-controlled-knowledge-debt/task-*.md`). There is no `_bmad/`,
   `_bmad-output/` or `.specify/` tree on main (`ls -d _bmad _bmad-output .specify` → none), and neither
   name is gitignored, so a consumer project may track them but this repository does not.

   Consequence: "components at latest upstream versions" is **not** currently a fact about this product
   tree. It is a claim about the operator's harness plus the shape of documents the adapters accept. A
   version pin that asserts a tree fact that does not exist would be a false certificate.

3. **Adapters are deliberately version-agnostic.** `source_version` is a free-form bounded string; there is
   no semver regex, no accepted-version list, no compatibility branch keyed on it (see §1). Upstream
   compatibility is encoded **structurally** (allowlisted `source_type` × `role` × path prefix, plus
   content patterns), not by version.

## 1. How the adapters already encode component versions (epic worktree)

`schemas/workflow-source-v1.schema.json:10` — the whole of what the contract permits:

```json
"source_version":{"type":"string","minLength":1,"maxLength":32},
```

Note the sibling field *is* enumerated, so the omission of a version pattern is a design choice, not an
oversight:

```json
"source_type":{"enum":["spec-kit","bmad","superpowers"]},
```

`.grok-stack/adaptive_grok/workflow_artifacts.py:151-158` (validated identity):

```python
    required = {"schema_version", "source_type", "source_version", "role", "path", "size", "sha256"}
    ...
    if source_type not in ROLE_MAP or role not in ROLE_MAP[source_type]:
        raise WorkflowArtifactError("workflow source type or role is invalid", code="source-schema")
    _bounded_text(identity.get("source_version"), "source_version", maximum=32)
```

`.grok-stack/adaptive_grok/workflow_artifacts.py:366` (manifest ingestion) — same call, value is only
copied into the identity dict at line 396 and never branched on:

```python
        source_version = _bounded_text(entry["source_version"], "source_version", maximum=32)
```

`_bounded_text` (lines 256-265) enforces only length, NFC normalisation and absence of control characters:

```python
        not isinstance(value, str)
        or len(value) < minimum
        or len(value) > maximum
        or unicodedata.normalize("NFC", value) != value
        or CONTROL.search(value)
    ):
        raise WorkflowArtifactError(f"{name} is empty, unbounded, non-NFC, or contains controls", code="schema")
```

Everything that actually gates a framework is structural — `workflow_artifacts.py:66-96`:

```python
ROLE_MAP = {
    "spec-kit": {"constitution": ..., "spec": ..., "plan": ..., "tasks": ..., "checklist": ...},
    "bmad": {"prd": ..., "spec": ..., "architecture": ..., "project-context": ...,
             "epics": ..., "stories": ..., "sprint-status": "status-projection", "readiness": ...},
    "superpowers": {"spec": ..., "plan": ..., "sdd-evidence": "runtime-evidence"},
}
PATH_PREFIXES = {
    "spec-kit": (".specify/", "specs/"),
    "bmad": ("_bmad/", "_bmad-output/"),
    "superpowers": ("docs/superpowers/", ".superpowers/sdd/"),
}
```

plus content regexes `SPEC_TASK`, `BMAD_TASK`, `NATIVE_STATUS` (lines 112-118). No `VERSION_RE`,
`ACCEPTED_VERSIONS` or `semver` token exists in the module (grep for
`source_version|SOURCE_VERSION|VERSION_RE|SOURCE_TYPES|source_type` returns 24 hits, all structural or
length-bound).

**Fixture evidence — the version string is decorative today.** `tests/test_workflow_artifacts.py:189`
builds every compile fixture with a hard-coded `"source_version": "1"`; `:165` uses `"6"` for bmad in a
negative test:

```python
            {"source_type": "bmad", "source_version": "6", "role": "persona", "path": "_bmad/persona.md"},
```

`tests/test_workflow_artifacts_adversarial.py:149-172`
(`test_manifest_rejects_source_version_bounds_backslashes_and_casefold_collisions`) proves only the bounds
are enforced — the rejected values are `""` and `"x" * 33`; `"1"` is accepted as a valid version.

The only place a real upstream version string appears in adapter-adjacent evidence is the epic's own
opt-in manifest, `engineering/changes/20260830-…-d41aa6/workflow/manifest.json`:

```json
    {
      "source_type": "superpowers",
      "source_version": "6.3.0",
      "role": "spec",
      "path": "docs/superpowers/specs/2026-08-30-workflow-artifact-adapters-design.md"
    },
```

**Answer to Q1:** "updating components" does **not** require adapter product code. Adapters accept any
1-32-character version string; the accepted surface is `source_type`/`role`/path-prefix/regex. Updating
components therefore changes (a) declared pin metadata, (b) documentation evidence, and (c) — only when an
upstream *shape* changes — the `ROLE_MAP`/regex set, which is a real product-code change governed by the
design doc, not by a version bump.

## 2. Where version pins live today, and the one mechanism consistent with repo style

Existing declaration points, all for **CLI tools**, not for workflow frameworks:

| Surface | Content |
| --- | --- |
| `.grok-stack/config/toolchain.json` | `{schema_version, policy, tools:[{id,name,required,profile?,commands,version_args,built,minimum,fallback,install{linux,darwin,windows,generic}}]}` — 12 entries (`python3, git, grok, gh, node, npm, php, composer, docker, syft, trivy, cosign`) |
| `README.md:178-201` | `## Requirements` table "Tool / Minimum / Built / Fallback / Required"; `:201`: "Machine-readable local pins: `.grok-stack/config/toolchain.json`." |
| `Makefile` | only `python3 scripts/grok_*.py` targets; no version literals |
| `VERSION` | `2.0.16`, product identity only |

Loading and consumption of the pin file (`.grok-stack/adaptive_grok/toolchain.py:71-73, 154-156`):

```python
def load_toolchain(root: Path) -> dict[str, Any]:
    data = load_json(root / '.grok-stack/config/toolchain.json', {}) or {}
```
```python
def check_toolchain(root: Path, *, host: str | None = None) -> list[ToolCheck]:
    data = load_toolchain(root)
    return [check_tool(spec, host=host) for spec in data.get('tools') or [] if isinstance(spec, dict)]
```

Because `check_toolchain` reads only the `tools` key, a **new sibling key is additive and cannot break the
doctor / installer-advice path** (`scripts/install_into.py:612-651` likewise only reads
`data.get("tools")` and fails closed if that list is missing).

Config-pinning test precedent (this is exactly the pattern to copy) —
`tests/test_toolchain.py:109-119`:

```python
    def test_real_toolchain_json_required_and_optional_sets(self) -> None:
        data = load_toolchain(ROOT)
        tools = {item['id']: item for item in data['tools']}
        self.assertTrue(tools['python3']['required'])
```

and the identity-pinning precedent `tests/test_structure.py:270-288`
(`test_version_identity_matches_readme`) which asserts `VERSION == "2.0.16"`, README first line,
`Identity: **2.0.16**`, CHANGELOG head and roadmap string agree — i.e. this repo already makes "the pinned
number is consistent across the declared surfaces" a binary test. `test_structure.py:122-152`
(`test_core_product_files_exist`) is the existing "file must exist / must be registered" list, and
`tests/test_structure.py:105-143` pins frozen manifest digests and exact SHA-256 values — digest pinning
has precedent too.

**Recommendation (one mechanism):** add a `workflow_sources` block to
`.grok-stack/config/toolchain.json` — a sibling of `tools`, same "minimum_or_newer; verified on" policy,
no new file, no new config schema, already inside the shipped managed directory `.grok-stack/` (so it
reaches consumer projects with zero installer registration), and already rendered by README Requirements.

## 3. Installer / packaging impact — what must be registered where

Packaging (`scripts/package_stack.py`) inventories **tracked git objects**, not a list:
`_git_command(root, ['ls-tree', '-r', '-z', tree_oid])` (line 655), minus
`adaptive_grok.manifest.EXCLUDED_PARTS/EXCLUDED_FILES` (`.grok-stack/runtime/*`, `*.sha256`, secrets,
`__pycache__`, …), plus a generated in-archive `MANIFEST.sha256`:

```python
    members.append(('MANIFEST.sha256', 0o100644, manifest))
```

There is **no `MANIFEST.sha512`** in the repo; the sidecar is `<zip>.sha256` under `packages/`
(`dist/adaptive-grok-build-pro-v<VERSION>.zip`, `package_stack.py:1091`). `scripts/generate_manifest.py`
and `scripts/verify_manifest.py` are thin wrappers over `adaptive_grok.manifest.generate_manifest` /
`verify_manifest` for the working tree — they need no per-file registration either.
So: any committed file ships in the release zip automatically; `tests/` ship in the zip
(verified inside `packages/adaptive-grok-build-pro-v2.0.9.zip`: `adaptive-grok-build-pro/tests/test_toolchain.py`)
but are **not** installed into consumer projects.

Consumer install is the list-driven surface (`scripts/install_into.py:17-59`):

```python
MANAGED_DIRS = (".grok", ".agents", ".grok-stack", "factory/contracts", "factory/src")
MANAGED_FILES = ( ... "scripts/grok_spec.py", ...
    "schemas/change-spec.schema.json", "schemas/change-spec-v1.schema.json",
    "schemas/architecture-system.schema.json", "schemas/architecture-rules.schema.json",
    "schemas/governance-rule.schema.json", "schemas/debt-entry.schema.json",
    "schemas/canonical-example.schema.json", "schemas/governance-handoff-v1.schema.json", )
```

Registration rules, therefore:

| New artifact | Ships in zip | Installs to consumer | Required edit |
| --- | --- | --- | --- |
| `.grok-stack/config/toolchain.json` (new `workflow_sources` key) | yes | yes | none — inside `MANAGED_DIRS` |
| `tests/test_workflow_sources.py` | yes | no | none for packaging; `grok_verify` discovers `tests/test*.py` automatically |
| `docs/superpowers/specs/…-third-party-workflow-source-versions.md` (or an ADR) | yes | no | none |
| README / CHANGELOG / VERSION | yes | no | none |
| *If* the epic is later merged: `.grok-stack/adaptive_grok/workflow_artifacts.py` | yes | yes (`MANAGED_DIRS`) | none |
| *If* merged: `scripts/grok_artifacts.py` | yes | **no** | add to `install_into.py:MANAGED_FILES` **and** `managed.json:"scripts"` **and** `test_structure.py` required-list **and** `test_installer.py:155-178` payload assertions |
| *If* merged: `schemas/workflow-*.schema.json` | yes | **no** | add each to `install_into.py:MANAGED_FILES` **and** `test_structure.py` required-list **and** `test_installer.py` payload assertions |

The last two rows are exactly what the epic already does in its dirty worktree — verified diffs:

```
+    "scripts/grok_artifacts.py",                       (install_into.py MANAGED_FILES, test_structure.py required list)
+    "schemas/workflow-source-v1.schema.json",
+    "schemas/workflow-task-graph-v1.schema.json",
+    "schemas/workflow-convergence-report-v1.schema.json",
```
```diff
--- a/.grok-stack/config/managed.json
   "scripts": [
     "grok_approve.py",
+    "grok_artifacts.py",
...
     "grok_route.py",
+    "grok_spec.py",
```

**Judgement on the `managed.json` diff (asked explicitly):** it is *partly* unrelated noise. The epic adds
`grok_artifacts.py` (its own new CLI) **and** `grok_spec.py` — but `scripts/grok_spec.py` is already
tracked on main **and** already in `install_into.py:MANAGED_FILES` (line 40) while **absent** from
`managed.json` on main. So the `grok_spec.py` line is a genuine pre-existing main-side registration gap
that the epic fixes as a drive-by; it is in scope for a "components/contract registration" change and is
the only part of that diff worth landing independently. `grok_artifacts.py` is **not** relevant to this
PR: the script does not exist on the base commit, and an installer entry pointing at a missing file would
make `build_payload` fail closed at read time.

`managed.json` is consumed by `doctor.py:44-46` (existence/validity of `.grok/agents/<name>.toml` and
skills); the `scripts` array is the consumer-facing roster mirror, so it must stay in lockstep with
`install_into.py:MANAGED_FILES` — that pairing is documented in
`engineering/changes/20260910-historical-autonomy-evidence-accounting-78b680/evidence/analysis-architect.md:9`:

> "Enroll `scripts/grok_history.py` in `scripts/install_into.py:MANAGED_FILES` and `grok_history.py` in
> `.grok-stack/config/managed.json:scripts`. … General package inventory already includes ordinary source
> files automatically; no bespoke generated manifest is needed."

## 4. Recommended contract ("components at latest" made testable)

Define the claim as **three separable, individually falsifiable assertions**, and pin only what this
repository actually controls.

### 4.1 Assertion set

- **C1 — Declared supported versions (product metadata).** The repo states, in one machine-readable place,
  which upstream release each framework adapter was last verified against. Purely declarative; testable
  without network.
- **C2 — Verified shape coverage (executable).** For each pinned version there is at least one committed,
  named test that parses *unmodified upstream document shape* for that component. This is the only honest
  form of "we support 6.12.0".
- **C3 — Currency evidence (dated, non-asserting).** A dated observation of upstream latest, with the
  command that produced it. Must **never** be a test that fails on a new upstream release (that would
  wedge CI on someone else's release train); it is documentation plus a freshness bound.

Explicitly **rejected**: making `validate_workflow_source`/`load_source_manifest` reject unknown
`source_version` values. It would turn an advisory anti-corruption layer into a version gate, break every
existing fixture (`"1"`, `"6"`), and cannot be delivered in this PR at all (§0.1).

### 4.2 Exact entry shape — `.grok-stack/config/toolchain.json`, new sibling key

```json
{
  "schema_version": 1,
  "policy": "minimum_or_newer; built is the tested pin",
  "tools": [ ... unchanged ... ],
  "workflow_sources": {
    "policy": "verified_against; advisory parser, never an install target",
    "components": [
      {
        "id": "superpowers",
        "name": "Superpowers",
        "repository": "obra/superpowers",
        "pinned": "6.3.0",
        "upstream_tag": "v6.3.0",
        "release_published_at": "2026-08-12",
        "observed_latest": "6.3.0",
        "observed_at": "2026-09-15",
        "roles": ["spec", "plan", "sdd-evidence"],
        "tracked_prefixes": ["docs/superpowers/", ".superpowers/sdd/"],
        "verification_tests": ["test_workflow_artifacts.WorkflowCompileTests.test_unmodified_superpowers_plan_subset_compiles"]
      },
      {
        "id": "bmad",
        "name": "BMAD Method",
        "repository": "bmad-code-org/BMAD-METHOD",
        "pinned": "6.12.0",
        "upstream_tag": "v6.12.0",
        "release_published_at": "2026-09-04",
        "observed_latest": "6.12.0",
        "observed_at": "2026-09-15",
        "roles": ["prd", "spec", "architecture", "project-context", "epics", "stories", "sprint-status", "readiness"],
        "tracked_prefixes": ["_bmad/", "_bmad-output/"],
        "verification_tests": ["test_workflow_artifacts.WorkflowCompileTests.test_unmodified_bmad_story_subset_compiles_without_trusting_done_status"],
        "breaking_notes": ["persistent_facts ships empty (project-context.md no longer auto-loaded)", "{diff_output} renamed {diff_file}", "bmad-checkpoint-preview renamed bmad-walkthrough"]
      },
      {
        "id": "spec-kit",
        "name": "GitHub Spec Kit",
        "repository": "github/spec-kit",
        "pinned": "1.0.7",
        "upstream_tag": "v1.0.7",
        "release_published_at": "2026-09-15",
        "observed_latest": "1.0.7",
        "observed_at": "2026-09-15",
        "roles": ["constitution", "spec", "plan", "tasks", "checklist"],
        "tracked_prefixes": [".specify/", "specs/"],
        "verification_tests": ["test_workflow_artifacts.WorkflowCompileTests.test_unmodified_spec_kit_tasks_subset_compiles_phases_and_parallel_markers"]
      }
    ]
  }
}
```

`id` values are **exactly** the adapter's `source_type` enum (`schema.json:9`
`"source_type":{"enum":["spec-kit","bmad","superpowers"]}`) so the config and the parser vocabulary cannot
drift apart — that identity is what makes the contract checkable.

`verification_tests` strings use the same closed shape already validated by
`SAFE_UNITTEST_TARGET = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*(?::[A-Za-z_][A-Za-z0-9_]*)?$")`
(`workflow_artifacts.py:129`) — reuse it, do not invent a second pattern.

### 4.3 Test names and their binary assertions

New file `tests/test_workflow_sources.py` (auto-discovered; no registration needed):

1. `test_workflow_sources_declares_all_three_adapter_source_types` —
   `set(component["id"]) == {"spec-kit", "bmad", "superpowers"}`, i.e. the pin block can never drift from
   the `source_type` enum. Reads the enum from `schemas/workflow-source-v1.schema.json` if present on the
   base commit; on `7b14736` (no schema) assert against a module-level literal set and mark the schema
   lookup as the post-epic upgrade path.
2. `test_workflow_source_pins_are_semver_and_current` — every `pinned` matches
   `^\d+\.\d+\.\d+$`, `upstream_tag == "v" + pinned`, `observed_latest == pinned`, `pinned` ≥ the value in
   `README.md`, `release_published_at <= observed_at`. This single test makes "components are at latest"
   a one-line-diff obligation instead of prose.
3. `test_workflow_source_observed_freshness_within_window` —
   `(DATE(today) - observed_at).days <= 90`; makes stale currency evidence fail rather than lie. (Choose
   the window with the owner; 90 days matches the repo's habit of dated observations.)
4. `test_workflow_source_verification_tests_are_named_and_collected` — for each `verification_tests`
   entry, `unittest.TestLoader().loadTestsFromName(...)` resolves and is non-empty. This is the load-bearing
   one: a pin without an executable shape test is not allowed to pass.
5. `test_workflow_source_readme_table_matches_config` — parse the new README rows and assert equality with
   the JSON (mirrors `test_version_identity_matches_readme`, `tests/test_structure.py:270`).
6. `test_workflow_source_components_are_not_installed_content` — assert
   `_bmad/`, `_bmad-output/`, `.specify/` are absent **or** that every tracked file under them is
   reachable from a `tracked_prefixes` entry; keeps the claim honest about §0.2 and fails loudly if someone
   starts vendoring upstream trees into the product.

Extend existing tests (only if the epic lands in the same stack):
`tests/test_structure.py::StructureTests::test_core_product_files_exist` (required-list additions),
`tests/test_installer.py::…::test_payload_is_sorted_safe_duplicate_free_and_profile_explicit`
(payload assertions at `:155-178`), and `tests/test_toolchain.py::…::test_real_toolchain_json_required_and_optional_sets`
(unchanged for `tools`, plus a `workflow_sources` presence check).

### 4.4 Documentation shape

- `README.md` Requirements: one new short table after `:195`, "Workflow sources (advisory parsers — not
  installed by this stack)", columns `Component | Pinned | Upstream | Observed latest | Observed`, and
  extend the sentence at `:201` to name `workflow_sources` next to `toolchain.json`.
- `CHANGELOG.md` + `VERSION` only if the pin change is treated as a product-visible contract change
  (repo precedent: `test_version_identity_matches_readme` couples all four files, so bumping the pin
  without bumping identity is fine; bumping identity requires all four).
- `decisions.md` entry (format confirmed from the tail of the file — `## YYYY-MM-DD — <imperative title>`
  then one prose paragraph, ≤3 sentences per the AGENTS.md contract), recording the ruling that
  `source_version` stays free-form and that currency is expressed via config + named tests.

## 5. Where compatibility decisions must be recorded

`engineering/adr/` **exists and is empty** on main, and is provisioned for every consumer project —
`install_into.py:90-98`:

```python
EMPTY_DIRECTORIES = (
    "engineering/changes",
    "engineering/adr",
    ...
```

So the ADR slot is intended but unused; the repo's actual durable-memory convention is
`decisions.md`/`mistakes.md` (AGENTS.md "Agent self-learning") plus the change package. Per AGENTS.md
"Source-of-truth order", item 4 is "Machine-readable API/event/data contracts" and item 5 "ADRs and
repository-local instructions" — the machine-readable pin in §4.2 therefore ranks **above** prose, which
is precisely why the config block, not a README sentence, must be the authority, with README and
`decisions.md` as derived views.

Recommendation: record the ruling in `decisions.md` (required by the repo contract) **and** open the first
real ADR `engineering/adr/0001-workflow-source-version-contract.md` capturing the three assertions, the
"adapters stay version-agnostic" invariant, and the "never vendor upstream trees" boundary. One ADR is
proportionate — the empty directory plus `EMPTY_DIRECTORIES` provisioning shows the intent exists.

Prior art check (asked explicitly): `git log --all -S 'sprint-status' --oneline | head` → **empty**, and
`grep -rn 'sprint-status'` on main (excluding change packages) → **empty**. `sprint-status` exists only in
the unmerged epic (`ROLE_MAP`, `workflow_artifacts.py:662`
`if source.identity["source_type"] == "bmad" and source.identity["role"] == "sprint-status":`, and the
fixture `_bmad-output/sprint-status.yaml`). There is **no** existing upstream-tracking mechanism for these
three components anywhere in the repository.

## 6. Concrete compatibility risk the pin must actually cover (BMAD 6.10.0 → 6.12.0)

From the v6.12.0 release body (`gh api repos/bmad-code-org/BMAD-METHOD/releases/latest`, breaking section):

> * `persistent_facts` ships empty. Re-add `project-context.md` to your override if you relied on the auto-load.
> * `{diff_output}` is now `{diff_file}`. …
> * Deprecated shims are opt-in on fresh installs. Pass `--shims` to keep them.
> * `bmad-checkpoint-preview` is now `bmad-walkthrough` (`CK` → `WT`). The old ID still forwards.
> * `llms.txt` and `llms-full.txt` are no longer published.

Only the first touches this repo's contract surface: the adapter declares a `project-context` role
(`ROLE_MAP["bmad"]["project-context"] = "governance-candidate"`). Because a manifest entry that names a
missing file fails closed in `load_source_manifest` (`_read_regular`), a fresh 6.12.0 BMAD project simply
yields no `project-context` source — a *content availability* change, not a parser break. That is the
correct severity to record: pin 6.12.0, note the role's optional-ness in the ADR, and do **not** change
`ROLE_MAP`.

Superpowers v6.3.0 and spec-kit v1.0.7 notes (fetched) show behaviour/CLI changes (SDD controller conflict
handling; `specify artifact` introspection, `speckit.taskstoissues` deprecation notice) that do not alter
the `- [ ] TNNN [P] [USN] …` task-row shape matched by `SPEC_TASK` (`workflow_artifacts.py:116`) nor the
`## Phase N:` headings matched by the parser, so no parser change is implied. `/speckit.taskstoissues` is
documented as "planned to move out of Spec Kit core in a future release" — note it in the ADR as a
watched, not-yet-actionable item.

## 7. Appendix — host-side update (operator action, NOT this repository's PR scope)

Verified on this host, 2026-09-15, read-only:

```
$ head -3 /home/pall/grok-projects/mee/_bmad/_config/manifest.yaml
installation:
  version: 6.10.0
  installDate: 2026-07-26T02:24:32.691Z      # modules core 6.10.0, bmm 6.10.0; ides: [codex]
$ which bmad                    -> not found
$ ls ~/.npm-global              -> (absent)
$ npm ls -g --depth=0           -> claude-code, playwright/mcp, supabase/mcp, context7-mcp, agent-browser,
                                   corepack, figma-developer-mcp, npm@11.19.0, supergateway  (no bmad)
$ command -v specify            -> not found
$ uv tool list                  -> codex-pair-long v0.1.0   (no specify-cli)
$ ls /home/pall/.grok/installed-plugins/  -> registry.lock only   (no superpowers)
$ grok --version                -> grok 1.0.22 (8f40483ca2a5) [alpha]
$ ls -d /home/pall/grok-projects/mee/.specify  -> none
```

So: **BMAD is not installed via npm global**; it is a per-project install inside `mee` (v6.10.0).
**spec-kit is not installed at all** on this host. **Superpowers is not installed as a Grok plugin**; the
`docs/superpowers/` and `.superpowers/sdd/` trees in this repository are hand-authored artifacts of our own
workflow, not an installed plugin payload.

What an actual host update entails (upstream-documented commands, for the operator — nothing here belongs
in the PR diff):

- BMAD 6.10.0 → 6.12.0, inside `/home/pall/grok-projects/mee` (6.12 install route changed; the old
  `npx bmad-method install` path is no longer the documented one):
  `npx skills add bmad-code-org/BMAD-METHOD` (or `/plugin marketplace add bmad-code-org/bmad-plugins` for
  Claude Code / `codex plugin marketplace add bmad-code-org/bmad-plugins` for Codex, installing
  `bmad-method` + `bmad-toolbox`), then ask the `bmad` skill to run `bmad setup`, verify with `bmad update`
  / `npx skills update`, and run `bmad doctor` afterwards — upstream: *"Use `bmad update` to check
  versions; install updates with `npx skills update` or your plugin marketplace. After updating, ask for
  `bmad doctor` to repair the project's existing runtime."* Expect `_bmad/_config/manifest.yaml`
  `installation.version` to become `6.12.0`, and re-add `project-context.md` to the override if `mee`
  relied on the removed auto-load.
- Superpowers 6.3.0 (already latest as of this analysis; nothing to do). Grok route, per the upstream
  README §"Grok Build CLI": `grok plugin install superpowers@xai-official --trust` (marketplace:
  `xai-org/plugin-marketplace`; Claude routes: `/plugin install superpowers@claude-plugins-official` or
  `/plugin marketplace add obra/superpowers-marketplace` then
  `/plugin install superpowers@superpowers-marketplace`). Updating is harness-specific — upstream:
  *"Superpowers updates are somewhat coding-agent dependent, but are often automatic."* Verify with
  `ls /home/pall/.grok/installed-plugins/`.
- spec-kit 1.0.7, tag-pinned install command from the v1.0.7 release body itself:
  `uv tool install specify-cli --from git+https://github.com/github/spec-kit.git@v1.0.7` then
  `specify init <project>`; re-check with `uv tool list`.
- Refreshing the currency observation used by C3 (read-only, requires the `gh` auth already present):
  `gh api repos/obra/superpowers/releases/latest --jq '"\(.tag_name) \(.published_at)"'`,
  `gh api repos/bmad-code-org/BMAD-METHOD/releases/latest --jq '"\(.tag_name) \(.published_at)"'`,
  `gh api repos/github/spec-kit/releases/latest --jq '"\(.tag_name) \(.published_at)"'`
  → currently `v6.3.0 2026-08-12T16:58:30Z`, `v6.12.0 2026-09-04T02:31:25Z`,
  `v1.0.7 Spec Kit - 1.0.7 2026-09-15T13:45:03Z` (all three re-verified today; they match the brief).

## 8. Deliverable summary for the write owner

In-scope for this PR (all additive, none require the unmerged epic):

1. `.grok-stack/config/toolchain.json`: add `workflow_sources` (§4.2) — no change to `tools`.
2. `scripts/install_into.py:MANAGED_FILES` + `.grok-stack/config/managed.json:"scripts"`: add the missing
   `grok_spec.py` registration (already tracked and already in `MANAGED_FILES` on main but absent from
   `managed.json`; keep the two rosters in lockstep). Do **not** add `grok_artifacts.py` or the
   `workflow-*.schema.json` entries — those files do not exist on this base.
3. `tests/test_workflow_sources.py`: tests 1-6 (§4.3).
4. `README.md` Requirements: workflow-sources table + the `:201` sentence extension.
5. `decisions.md` ruling + `engineering/adr/0001-workflow-source-version-contract.md`; update
   `PROJECT_STATE.json`/`CHANGELOG.md` only if the owner decides the pin is a version-visible change.
6. This change package: dated upstream observation evidence (the three `gh api` outputs in §7).

Out-of-scope, must be stated rather than silently assumed: bumping any installed tool on the host (§7),
vendoring `_bmad/`/`.specify/`/plugin payloads into this repository, and any change to `ROLE_MAP`,
`PATH_PREFIXES`, the parser regexes or the `source_version` validation in `workflow_artifacts.py` — the
last of which cannot be touched here at all because the file is not in git on the base commit (§0.1).
