# M2 documentation and release-evidence research

Route: `0156034c05bd`

Change: `20260826-m2-executable-architecture-015603`

Research is repository-only and read-only. The requested M2 architecture files are not present in the current tree, so the items below are implementation/release documentation requirements rather than claims that they already exist.

## Documentation authority checklist

The roadmap makes the machine-readable architecture model the authority and explicitly demotes the K16 graph to a decorative inventory. The implementation and docs should establish this authority chain:

1. `architecture/system.yaml` — canonical model of current local workflow and Trust CI components, edges, trust domains, data, secrets, runtime/deployment relationships.
2. `architecture/rules.yaml` — executable fitness/risk rules and explicit applicability/exemption semantics.
3. `schemas/architecture.schema.json` — strict schema for both documents. Follow the M1 convention: JSON-compatible YAML, bounded parsing, deterministic canonical bytes, and no arbitrary code or model-generated rules.
4. `.grok-stack/adaptive_grok/architecture.py` — repository-local loader, schema validation, canonical digest, path/contract drift checks, deterministic diagram generation, architecture diff and risk escalation.
5. `scripts/grok_architecture.py` — documented operator entry point. The CLI output and exit codes are evidence contracts, not merely convenience output.

The authority wording belongs in [`DARK_FACTORY_ROADMAP.md`](../../../DARK_FACTORY_ROADMAP.md), [`README.md`](../../../README.md), `QUICKSTART.md`, and the M2 package docs. Say explicitly that the M1 typed change spec remains the business intent/acceptance authority; an architecture digest is a separate exact-state constraint/evidence field and does not replace objective, criteria, approvals, or rollback. Do not claim live deployment topology: the initial model can document repository source and the independently deployed Trust CI boundary described in [`trust-ci/README.md`](../../../trust-ci/README.md), but must label unverified runtime facts as out of scope.

Update the M2 package (`brief.md`, `requirements.md`, `architecture.md`, `test-plan.md`, `rollback.md`, `release.md`, and the typed `change-spec.yaml`) with canonical paths, schema/model/rules digests, exact base/head SHAs, risk result, drift result, diagram generation/check command, and evidence locations. The current package spec is still a draft with no criteria and `UNKNOWN` success metric/target; Task 6 must not leave that state in release evidence.

## README and K16 wording

Preserve the 16-node complete graph and its structural test (currently 120 pairwise `---` edges). Do not add architecture files as K16 nodes or edit the graph to mirror the architecture model. Change the prose around the graph from “Simple complete graph” to language such as “decorative inventory graph; not architectural evidence.” Add a nearby link/table entry for the architecture model, rules, schema, CLI, and generated text views. State that architecture validity comes from schema validation, independent fitness checks, and exact-digest evidence.

The README’s current state is M1-local-source-ready and accurately limits claims about deployed Trust CI. After M2 implementation, add only source-local claims supported by receipts (model/rules validation, fitness, drift, diagrams, holdout fixture). Keep the explicit distinction between local preflight and the App-owned exact-SHA Trust CI check; do not call M2 deployed or merge-authoritative until external holdout/policy evidence exists. Preserve the current statement that historical schema-v1 YAML is unchanged-history compatibility only and add M2 tests/docs proving M1 schema-v2 behavior and old attestation verification remain compatible.

## Reproducible diagrams

`.grok-stack/config/toolchain.json` pins Python/Git and operational tools but no Graphviz, Mermaid renderer, or image tool. Therefore use committed text sources (Mermaid or DOT) generated from sorted canonical model data; do not make PNG/SVG or a renderer an authority. Emit the five roadmap views: C4 context, container, deployment, data-flow, and trust-boundary. Pick one format and document it consistently (Mermaid fits the existing README; DOT is also acceptable if generated text is deterministic).

Document a `generate`/`render` command and a `--check` mode that regenerates in memory or in a temporary location and compares bytes. Stable ordering, stable labels, normalized line endings, and no timestamps/random IDs are required. Generated files should live under a dedicated documented path (for example `architecture/generated/*.mmd`) and must be marked generated; manual diagram edits must fail the reproducibility check. The evidence should include model/rules digests and the exact source/head SHA. Renderer screenshots are optional presentation artifacts and never release evidence.

## CLI and operator documentation

`QUICKSTART.md` and README should document the actual subcommands and paths once implemented, with explicit examples for:

- `validate` (schema, bounded parse, path containment, declared public-contract checks);
- `summary` (stable machine-readable counts and digest);
- `generate`/`render --check` (all five views);
- `diff --base <sha> --head <sha>` (exact baseline/head, changed architecture edges/secrets/network/trust crossings);
- `fitness` (rules and independent-risk result);
- `drift` (repository paths/contracts versus declarations).

Specify that commands are read-only, operate inside the repository, use exact SHA inputs, sort output, and fail closed on malformed/unknown data. Document JSON output fields, exit-code meanings, and where evidence is saved. `grok_verify --mode pr` must have an explicit policy for architecture evidence and for fast mode; it must not silently treat missing architecture evidence as a pass when an architecture artifact is changed. The post-diff risk must be monotonic (`max(route pre-risk, architecture escalation)`).

The active route base `069fe8226addb8a1922dde3db4e753434baa3a3d` predates the completed M1 source evidence, while current HEAD is `25bfbe5` and the README records M1 source HEAD `98649e4e1e6a971fb802bc934eb5680de529e18a`. Before documenting an architecture diff, record the exact completed-M1 parent SHA/tree fingerprint as the comparison baseline; otherwise M1 changes will be misreported as M2 architecture drift. Never overwrite M1 receipts.

## Trust CI and internal contract references

Holdout documentation should require an independent `trust-ci/holdout.example/architecture_validate.py` that validates bytes/data/path relationships without importing the PR’s architecture module. It must run against the exact checked-out SHA, detect source mutation, and keep critical rules outside PR control. The repository must not edit deployed policy, holdout, PostgreSQL state, keys, GitHub App settings, or branch protection.

Use existing local contracts rather than inventing parallel APIs:

- `.grok-stack/adaptive_grok/util.py`: `find_root`, bounded subprocess execution, exact `git_head`/`changed_files`, SHA-256, tree fingerprints, safe relative paths and bounded reads;
- `.grok-stack/adaptive_grok/spec.py`: M1 `load_spec`, `validate_spec`, canonical digest, coverage and fingerprint semantics;
- `trust-ci/src/adaptive_trust_ci/models.py`: sorted compact UTF-8 canonical JSON used for signatures/digests;
- `trust-ci/src/adaptive_trust_ci/workspace.py`: exact-SHA checkout without executing repository code;
- `trust-ci/src/adaptive_trust_ci/sandbox.py`: isolated read-only/no-network runner;
- `trust-ci/src/adaptive_trust_ci/github.py`: injected transport/token-provider adapter boundary;
- existing contract fixtures under `examples/contracts/` and repository contract detection in verification.

Keep provider, deployment, systemd, Codex/Grok, and future factory abstractions out of M2. Trust CI’s current systemd unit is a Compose lifecycle service, not a local architecture supervisor; do not document it as a generic supervisor contract.

## Installer and release checklist

[`scripts/install_into.py`](../../../scripts/install_into.py) currently manages both M1 schemas, the local stack and selected scripts, while intentionally excluding runtime/private state and Trust CI deployment material. Decide and document whether M2 architecture is part of an installed consumer product:

- If yes, add and test the architecture module, schema, model/rules, CLI, and any generated text sources to the managed file set; update clean-target/install tests and ensure active packages, runtime state, receipts, holdout material and `trust-ci/` are not copied.
- If no, state that architecture is root-product-only and make verification/install behavior explicit so a consumer project does not unexpectedly fail for absent architecture files.

Update the README map, QUICKSTART, package release notes, and any installer manifest together. Confirm `VERSION` and README identity are unchanged unless the release decision explicitly versions them. Before release, run local verification and all route-selected reviews, record fingerprint-bound receipts, and document that these are preflight only. Release evidence must name the exact merged commit and then require the external App-owned check `adaptive-trust-ci/verified@<policy-sha12>` plus any required signed approvals.

## Non-goals and critical concerns

M2 does not add services, databases, queues, frameworks, provider/Codex/Grok/systemd/factory control planes, production writes, GitHub Actions, live-topology claims, image-generation dependencies, or modifications to deployed Trust CI policy/holdout/secrets. It does not replace M1 typed intent or authorize merge.

Critical concerns for implementation/release:

1. Establish the completed-M1 exact baseline before calculating architecture drift.
2. Make K16’s decorative-only status unmistakable while preserving its 120-edge inventory test.
3. Make text diagram generation byte-reproducible without an unpinned renderer.
4. Resolve installer scope explicitly; otherwise schema/CLI delivery will diverge between root and consumers.
5. Preserve M1 schema-v2 semantics, historical v1 compatibility, and old attestation verification.
6. Keep critical architecture validation in the independent holdout/server policy and bind every local result to exact SHA/digests.
