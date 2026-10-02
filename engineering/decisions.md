# Moved

Canonical log is /decisions.md. Do not append here.
## 2026-10-02 — Bind dormant dispatch rows with a composite foreign key

Redundant outbox identity is constrained to the immutable result source across repository, task,
run, fence, packet, attempt and envelope, so neither fixtures nor future enqueue code can create a
cross-authority handoff. Claim/start/record additionally revalidate live run authority.
