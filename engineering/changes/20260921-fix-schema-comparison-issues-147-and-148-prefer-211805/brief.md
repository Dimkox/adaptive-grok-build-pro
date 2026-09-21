# Schema path precedence and bounded diagnostics: issues 147/148

Typed authority: [change-spec.yaml](change-spec.yaml). Route 21180522da37.

The user explicitly requested all remaining issue fixes; the coordinator adopted these bounded designs. The route has no named human gate. Local implementation and evidence are authorized; external writes, publication, merge, tag, release and deployment retain separate exact-operation authorization and external Trust CI requirements. Baseline: frozen PR170 head 1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48.

Resolve concrete declared paths before competing schema IDs, then deduplicate and cap unattributed-reference presentation without altering closure traversal or refusal semantics.

Allowed product files: .grok-stack/adaptive_grok/architecture.py; .grok-stack/adaptive_grok/architecture_fitness.py; tests/test_architecture_model.py; tests/test_architecture_fitness.py. Change-package evidence is in scope; coordinator owns concise append-only shared-memory updates.

Outside scope: shipped schemas/contracts, architecture model/rules, producer policy, migrations, global path-like-ID rejection, PR137 metadata behavior, runtime and deployed CI policy.
