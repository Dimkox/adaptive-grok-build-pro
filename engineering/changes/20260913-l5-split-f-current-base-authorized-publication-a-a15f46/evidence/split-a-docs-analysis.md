# Slice A: local documentation and evidence contract research

Read-only source research for route `d20205a1a318`, worktree `/home/pall/grok-projects/adaptive-grok-build-pro-l5-split-a`. Observed `HEAD` and `route.base_commit` are both `4b3ad5e8ec1e9fc426caaacd3cbf3f4d6e72c102`. Reconstruction source is sibling L5 commit `f31406e`; the seven-unit design is a reconstruction plan, not transferred verification or merge authority. No repository files, refs, grants, secrets or external services were changed by this analysis.

## Genuine predecessor and comparison semantics

- The current A route is correctly attached to the actual starting tree. For B onward, each change package must identify its actual reconstructed predecessor and source selection; local preparation is not acceptance or merging of that predecessor.
- `router.build_route` defaults `base_commit` to `util.git_default_base` (`router.py:433`, `util.py:120`): origin/main, origin/master, main, master, then HEAD. Creating a route on a stacked worktree does **not** automatically choose that worktree's predecessor HEAD. Inspect route metadata instead of assuming that relationship.
- Architecture fitness is evaluated against `select_architecture_comparison_base(route.base_commit)` (`architecture_diff.py:280`, `verification.py:82`). With a fully adopted model, comparison base is exactly the route base, not an inferred merge base or the verification changed-file union.
- PR/release verification separately checks the route SHA is available and an ancestor, discovers the local target, obtains its unique merge base, and unions both commit ranges with index/worktree/untracked paths (`verification.py:375–513`). This keeps ancestor changes visible to generic scans even when a genuine slice has a narrower architecture comparison. Stacked preparation does not erase main-relative inventory. A green A result cannot establish green B–G or final combined behavior.
- Parent implementation ruling: B onward will create genuinely new routes through the existing `build_route(base_commit_override=actual checked-out predecessor)` API, rather than changing any active route or relying on the default-main CLI. Record the predecessor when the new bounded task begins and retain the independent main-relative inventory.
- Preserve existing refs, target discovery, code budgets and the old monolith's reported failure. The report should name the actual route base and local target inventory separately, with no claim of a fresh remote main lookup.

## Per-slice source and review binding

The mandatory flow in `.agents/skills/adaptive-delivery/SKILL.md` requires focused regression evidence, full `python3 scripts/grok_verify.py --mode pr`, then both selected independent reviews. Reports must inspect the actual A diff and surrounding current implementation, not merely copy prior monolith conclusions.

`tree_fingerprint` includes exact HEAD and changed-path content (`util.py:183`). Verification compares that fingerprint before/after checks (`verification.py:963–1044`). Receipts also bind route ID, acceptance-criterion/spec identity, architecture model/schema/rules/contracts and governance evidence, and reject state changes during recording (`receipts.py:495–547`). Validation rejects stale tree/spec/architecture/governance bindings (`receipts.py:560–610`); the spec digest explicitly includes route base and HEAD (`spec.py:674–683`). A commit, predecessor/base change, code edit, or tracked documentation edit invalidates a prior complete local receipt. Source-hash manifests can establish scoped code identity across evidence-only edits but do not turn a stale full-route receipt into a current one.

Recommended report fields: exact route/base/HEAD, reconstructed source reference, changed product/test/schema SHA256 map, full verifier JSON identity and result, relevant red/green commands, independent report paths, explicit residual failures. Populate durable scope/docs before final verification where practical; do not record passing review receipts against a failed full route. Local completion still provides no authority to merge: each actual PR needs external exact-SHA App-owned Trust CI and separately required signed scopes.

## Existing schema exception protocol

At base, `schemas/architecture-rules.schema.json` path boundaries use `additionalProperties: false` and four required fields (`id`, `source_prefixes`, `forbidden_dependency_prefixes`, `severity`); there is no generic waiver, TTL-based exception or external-approval field (`schema:144`). Base checker treats forbidden dependencies as prefix families (`architecture_fitness.py:729–778`).

The reconstruction source adds only optional `allowed_dependency_modules` to that existing path-boundary object: unique array, at most 32 bounded dotted Python module identifiers, each at most 256 characters (`source schema:147`). Absence preserves old rules. Source evaluator applies equality to the resolved module in the current rule, with no prefix-family expansion (`source architecture_fitness.py:803–826`). This is versioned local rule/checker functionality, not a grant and not a deployed Trust CI policy edit. Ship schema, checker and meaningful compatibility/negative tests together. A can introduce support with no live exception activation; publication's actual `urllib.parse` rule belongs to F. No future modules need ownership in A's current inventory.

The intended defensive contract must be explicit in tests: qualified relative/module-less imports, aliases, mixed imports, ambiguous package identities and source-root shadowing cannot evade a forbidden family. An allowed parser spelling is not general networking permission, and direct AST analysis plus inventory does not prove arbitrary dynamic/transitive isolation.

## Rollback wording

Current `rollback.md` appropriately limits A to source-only revert before dependent slices are integrated, or a bounded forward repair. Add operational clarity when dependencies exist: withdraw/revert dependent slice use in reverse order before removing its checker/schema prerequisite, or forward-fix the prerequisite and reverify/review the dependent tree. Do not roll back only the schema while any rule still uses the new optional field; the old closed schema rejects it. A introduces no data migration, provider request, service activation or operational restore procedure. Existing scope accurately promises no public API behavior change.

Research limitation: this is source-contract analysis, not independent post-implementation review, a completed verifier run or confirmation that all seven reconstructed slices fit their unchanged budgets.
