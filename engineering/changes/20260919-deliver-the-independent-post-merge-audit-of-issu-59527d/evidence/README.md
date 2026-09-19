# Evidence

Store human-readable review reports here. Machine receipts live under `.grok-stack/runtime/receipts/` and are bound to the current repository fingerprint.

## What this package's evidence holds (AC-001)

Five analysis reports, the controller's tables, and the harness that reproduces them:

| file | lane / role | selected by |
| --- | --- | --- |
| `analysis-repo_explorer.md` | comparator-site inventory | route `59527d5a28f8` (this change) |
| `analysis-architect.md` | adversarial soundness hunt; found CAR-5 / issue #147 | route `59527d5a28f8` (this change) |
| `analysis-docs_researcher.md` | primary-source `anyOf`/`oneOf`/`allOf` semantics | route `59527d5a28f8` (this change) |
| `analysis-integration_architect.md` | blast radius of `unsupported` on a failed run | route `59527d5a28f8` (this change) |
| `analysis-ai_architect.md` | measured end-state on the landing/AI closure | route `4c524b83df59` (the #133 delivery wave; not in this route's `allowed_agents`) |
| `controller-declared-inventory-table.md` | authoritative before/after tables + CAR-1…CAR-5 + the CAR↔`R-n` mapping | controller |
| `measurement-harness.md` | blocks A–H: scripts, invocations, printed output for every number above | controller |

Agent reports are not rewritten. Where a later measurement contradicts one, the controller's file records the
disagreement and, when the contradiction is inside the agent's own conclusion, an annotated
`[SUPERSEDED …]`/`[ANNOTATION …]` blockquote is placed next to the passage with the agent's text left verbatim.
