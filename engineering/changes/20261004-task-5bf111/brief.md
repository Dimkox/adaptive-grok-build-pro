# Remove redundant source-root hook wrappers

Typed authority: [change-spec.yaml](change-spec.yaml). Change `20261004-task-5bf111`, route `5bf1112b5ccc`, medium risk, standard complexity; isolated branch `refactor/remove-source-root-hook-shims` starts at `ee3911869419204154e02900e58bf31492ee744c`.

Nine identical source-root wrappers duplicate a shared shim template. Canonical source hooks live in `.grok/hooks/`; installer payloads synthesize consumer root aliases from `.grok-stack/templates/hook_root_shim.py` independently of source wrapper existence.

The approved outcome is a smaller source root with unchanged installed hook compatibility. Scope includes exactly nine wrapper deletions, their root-inventory test and architecture path bindings, generated-consumer characterization tests and concise documentation. Installer runtime, managed inventory, alias names, canonical hooks, template, configurations, generated architecture views, VERSION, released ZIPs and historical evidence remain outside the product edit scope.

The five selected analyses are summarized in [controller-analysis.md](evidence/controller-analysis.md). No named human gate applies. The user approved targeted observations, then both independent reviews, complete report persistence and commit/freeze, then one final full PR verification. This package does not authorize deployed Trust CI changes, protected pushes, merge, tag, publish, deployment or history rewrite.
