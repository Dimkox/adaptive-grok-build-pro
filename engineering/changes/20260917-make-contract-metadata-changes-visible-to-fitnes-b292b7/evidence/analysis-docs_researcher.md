# Documentation precedent for #120

## Existing architecture model

`architecture/system.yaml` is the registry of public contracts. Each record has a stable `id`, `kind`, path, version, role, and compatibility mode. `architecture/rules.yaml` then applies fitness policies by kind and mode: OpenAPI is bidirectional; event/JSON Schema consumer contracts use `consumer_accepts_old`; JSON Schema producer contracts use `producer_accepted_by_old`; signed payloads require `exact`. This is machine-readable policy, but the repository does not give a prose definition of the compatibility modes next to those declarations. The architecture links in `README.md` are the current human entry point.

## Relevant precedent and gap

The closest precedent is `tests/test_architecture_fitness.py::test_semantic_diff_covers_trust_signal_top_level_and_contract_metadata`. It proves that model-level metadata (contract version, role, compatibility, and signal description) changes appear in the architecture diff and revoke exemptions. It does **not** cover `title` or `description` inside the registered JSON Schema document. `_SUPPORTED_SCHEMA_KEYS` explicitly accepts both document keys, but `_compare_schema_direction` compares structural constraints and `$id`/`$schema`, not these descriptive fields. Thus the issue's observed asymmetry is consistent with current authoring and fitness surfaces.

Schema descriptions are in active use. For example, the registered landing failover configuration and backend capability schemas include `description`; these files are authoritative contract artifacts rather than an external prose guide. Issue #120 specifically establishes that descriptions may carry agreed meaning. The documentation should therefore avoid telling authors that these fields are decorative or non-normative unless the product decision deliberately changes that convention.

## Documentation and acceptance implications

If the selected behavior is to surface metadata edits distinctly (as the issue's option 1 proposes), update the architecture/contract authoring guidance—most naturally the existing architecture contract documentation and README architecture map—to state that schema `title`/`description` are governed document metadata, while remaining separate from wire-shape compatibility. Explain that fitness must report a reviewable metadata-change reason and continue to run the existing structural direction checks. Define the four mode names in that same guidance so authors can tell which producer/consumer direction is being evaluated.

Tests should have separate metadata-only and structural controls against the same registered schema and mode. Metadata-only should be reported as changed/reviewable, not claimed structurally incompatible; structural mutations must retain current verdict behavior. Keep signed payload exactness and architecture registry metadata checks independent. The existing model-level metadata regression should remain intact.

Do not broaden claims to OpenAPI/event behavior: issue #120 measured only JSON Schema metadata and explicitly says those other kinds were not tested. Any README/current-state edits should link the actual reviewed `architecture/system.yaml`, `architecture/rules.yaml`, and generated views per the repository's README contract.
