# PR 239 cleanup repair

Restore a verifiable source cleanup. The original cleanup moved 19 historical packages, removed repository ZIPs/logs/root shims, and redacted public infrastructure. This successor fixes affected bindings.

Scope: architecture hook ownership, explicit historical-spec migration, prompt-independent directory IDs, introduced whitespace, README first-run commands and package storage text. Preserve installer output. History rewrite, deployed Trust CI policy and publication are outside this repair.

One application-code writer: cleanup_general_implementer. Four independent read-only analyses completed. Root owns this active package, verification, review persistence and delegated branch transport. Reviews follow successful verification.
