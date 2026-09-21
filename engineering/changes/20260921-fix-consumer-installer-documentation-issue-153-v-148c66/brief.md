# Consumer documentation: issues 153/161

Typed authority: [change-spec.yaml](change-spec.yaml). Route 148c66d20768.

The user explicitly requested all remaining issue fixes; the coordinator adopted these bounded designs. The route has no named human gate. Local implementation and evidence are authorized; external writes, publication, merge, tag, release and deployment retain separate exact-operation authorization and external Trust CI requirements. Baseline: frozen PR170 head 1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48.

Install consumer-specific instruction and README templates while retaining managed README ownership and existing-target safety.

Allowed product files: scripts/install_into.py; .grok-stack/templates/consumer-AGENTS.md.tmpl; .grok-stack/templates/consumer-factory-README.md.tmpl; tests/test_installer.py. The coordinator-approved review correction renames the newly introduced `.md` rendering inputs to explicit `.md.tmpl` source while retaining them in the installed inventory. A necessary explicit required-file check may narrowly change .grok-stack/adaptive_grok/doctor.py and tests/test_verification_doctor.py. Change-package evidence is in scope; coordinator owns concise append-only shared-memory updates.

Outside scope: factory-root instructions, policy changes, hook registration, language coverage, live consumer writes and in-place upgrades.
