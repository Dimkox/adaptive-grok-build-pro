# Untracked scratch fingerprint repair: issue 168

Typed authority: [change-spec.yaml](change-spec.yaml). Route 582c39d6afb6.

The user explicitly requested all remaining issue fixes; the coordinator adopted these bounded designs. The route has no named human gate. Local implementation and evidence are authorized; external writes, publication, merge, tag, release and deployment retain separate exact-operation authorization and external Trust CI requirements. Baseline: frozen PR170 head 1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48.

Exclude only proven-untracked generated .qwen/tmp files from local evidence fingerprints while preserving all tracked changes and meaningful agent configuration.

Allowed product files: .grok-stack/adaptive_grok/util.py; tests/test_util_fingerprint.py (new focused utility suite); narrowly scoped receipt integration tests in tests/test_verification_doctor.py or tests/test_change_receipts.py when present. The coordinator approved a bounded review repair adding scripts/grok_verify.py JSON output escaping. Change-package evidence is in scope; coordinator owns concise append-only shared-memory updates.

Review repair scope: preserve literal Git pathname bytes through dedicated binary enumeration, filesystem decoding/encoding, exact slash-delimited classification and symlink hashing. POSIX literal backslashes must never become subtree separators. Non-UTF-8 filename bytes must remain distinguishable and bind changes; escaped JSON in dump_json and verifier --json must round-trip both those names and ordinary Unicode without changing JSON values, schema or receipt authority. Shared command execution behavior remains unchanged. Initial failed review reports remain historical evidence.

Outside scope: arbitrary ignore configuration, whole-agent-directory exclusions, receipt-format changes, deployed Trust CI/policy changes, external writes and unrelated Git hardening.
