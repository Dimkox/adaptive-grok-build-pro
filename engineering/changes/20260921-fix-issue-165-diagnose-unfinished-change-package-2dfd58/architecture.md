# Adopted bounded design

Use one focused pure package inspector plus a bounded NUL-safe Git snapshot. Read only the selected package and explicit current evidence references through ancestor-safe bounded regular-file reads. Do not reuse recursive no-Git discovery or HEAD-as-base fallbacks. Preserve old status fields and current receipt validation.

Record actual start HEAD separately from route.base_commit, then append first implementation checkpoint through the existing lifecycle. Explicit local obligations distinguish not_run with reason from recorded references; neither grants success. Do not infer obligations from arbitrary prose or duplicate retained PR141 completeness / PR134 structured report work.

Status must not create runtime directories, pycache or refresh the Git index. Stop stays soft; fail review recording remains possible and current review preflight cannot require its own receipt. Freeze documentation/checkpoints before final verification, since every repository change stales local receipts.

Adopt [architecture analysis](evidence/analysis-architect.md) and [integration analysis](evidence/analysis-integration_architect.md) with their explicit limits and test matrix.

Filesystem identity survives the entire durable path: valid UTF-8 filenames and branches remain strings, while non-UTF-8 bytes use an explicit `{"encoding":"hex","value":"..."}` object containing the original byte sequence. Literal hex/escape-looking names remain ordinary strings and cannot collide with tagged identities. The collector uses a4096-byte individual-name bound and32768-byte total JSON path-representation budget; overflow yields `git_path_representation_limit` and an explicit unknown observation. The canonical parser, shared serializer and receipt authority are unchanged.
