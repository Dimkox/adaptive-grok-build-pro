# Architecture and compatibility boundary

Typed authority: [change-spec.yaml](change-spec.yaml).

The baseline source has nine identical eight-line wrappers. Runtime ownership is `.grok/hooks/` and `.grok-stack/adaptive_grok/`; configurations try canonical hooks, consumer aliases and their existing inline fallback. The installer owns consumer compatibility names, while the consumer owns its target architecture and governance.

`_SourceTree.inventory()` appends every `MANAGED_FILES` entry even when an alias has no source file. `build_payload()` skips source reads for `ROOT_HOOK_SHIMS`, then renders those aliases from the already validated template content/mode. Removing physical source wrappers therefore requires no installer or template change. Generic and Bitrix payloads retain the same compatibility aliases; the existing minimal-source snapshot regression protects this seam.

The proposed source model removes only nine obsolete `NODE-LOCAL-ROUTE-POLICY.repository_paths`. Renderer projections exclude that field, so generated views should remain byte-identical; `diagram --check` validates this assumption. Canonical hook/config/template bytes and installer runtime are frozen against the exact base. HTTP/event/schema contracts, Bitrix modules/events/cache and installation semantics remain unchanged.

Risk is confusing virtual managed inventory with physical source inventory, or accidentally testing wrapper existence instead of installed behavior. The mitigation is literal consumer alias expectations, byte/mode assertions and execution against materialized generic/Bitrix consumers. No temporary adapter or debt is introduced. Rollback uses a revert PR and fresh verification/review/Trust CI; deployed policy and holdout remain outside this repository change.
