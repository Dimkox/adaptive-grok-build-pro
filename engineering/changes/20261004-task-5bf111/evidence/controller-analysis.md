# Bounded source-root shim cleanup

Base: ee3911869419204154e02900e58bf31492ee744c; route5bf1112b5ccc.
Capacity: startup snapshot2026-10-04T19:51:32Z and child remeasurement21:55:49Z:14physical/28online logical CPUs, default affinity0,1,8-27, child-only0-27 probe succeeds, effective cpuset0-27, no finite ancestor quota. Chosen capacity28; platform13slots; route analysis5/10; test allocation at most8 while external checks may run. Original dirty checkout is untouched; this isolated branch has exactly one selected general_implementer write owner.

All five selected analyses completed read-only before implementation.

- repo_explorer: nine identical eight-line source wrappers, SHA256e0cbf978ceeccbdab870665e27bc06e71e44793b9cf458cefab6f576164ccc6e. Keep installer MANAGED_FILES/ROOT_HOOK_SHIMS, canonical hooks and template unchanged. Current configs try canonical hooks, consumer aliases, then inline fallback.
- task_analyst: remove exactly nine files; generic and Bitrix payloads must retain nine aliases with bound-template bytes/mode; exercise delegation and missing-canonical fallback. Preserve released ZIPs, VERSION and history. Rollback is a revert PR.
- architect: remove nine entries only from NODE-LOCAL-ROUTE-POLICY.repository_paths in architecture/system.yaml:1969-1977. Renderer excludes repository_paths; in-memory probe found unchanged views. Validate diagram --check rather than mechanically rewriting generated views.
- docs_researcher: clarify source canonical hooks versus installed generated aliases in .grok/hooks/README.md; add one README inventory bullet. Preserve dated CHANGELOG and historical evidence.
- integration_architect: adapt test_installer:81-104 to generated aliases; keep template-snapshot regression106-133 and inventory/consumer reinstallation contracts. Root-structure test reads committed HEAD, so verify that invariant after committing the deletion candidate, not by weakening it to a filesystem check.

Resolved analysis contradiction: inventory() unconditionally includes MANAGED_FILES at scripts/install_into.py:474; build_payload excludes alias source reads at608 and renders them from the validated template at614-617. No physical source-root wrappers or installer runtime adjustment is needed. A warning inferred source existence from inventory membership without reading its producer; it was corrected before edits.

Dependencies: scope/spec and characterization tests precede deletion; targeted controls precede both selected independent reviews; report persistence and commit/freeze precede one qualifying final full local PR gate. User explicitly approved this one-final-full order. New external App exact-head check and required approvals remain mandatory. PR242 is separate and its local success is historical evidence, not reuse for this candidate.

Out of scope: history rewrite, force-push, deleting180remote branches, deployed policy/holdout/trust stores, GitHub Actions, immutable release bytes, VERSION, tags/releases/deployment. The old97a7581ancestor and oldZIP/history remain until a separately scoped irreversible cleanup.
