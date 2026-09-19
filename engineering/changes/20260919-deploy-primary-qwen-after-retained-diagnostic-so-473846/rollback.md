# Recovery

Use the current original5f6f6ce1 primary and a fresh complete pre-continuation snapshot. Before old-binary start, stop the new unit, disable it, preserve the entire new state/publication/artifact roots under unique target-bound names, and hold both existing state/publication writer locks across rename/restore. Validate the snapshot digest and stopped schema/counts against captured facts; refuse in-flight or unexplained concurrent changes.

Restore into absent original roots, start the old binary using a private disabled old configuration, verify original schema/counts and readiness, then restore the byte-identical original unit/config and read the existing historical artifact without POST. Never run old code on schema2 or reuse the previous26a0d3 snapshot/path for this new event. Partial/ambiguous operations remain stopped with evidence intact for bounded forward recovery.
