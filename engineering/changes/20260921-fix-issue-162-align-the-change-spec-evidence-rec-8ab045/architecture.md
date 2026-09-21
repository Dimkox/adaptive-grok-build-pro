# Architecture — receipt vocabulary compatibility

The router and receipt registries produce seven receipt kind names; the v2 typed change specification consumes them through a closed enum. Preserve the architecture and widen that enum only to the two already-existing names. The exact parity regression is the future drift detector. No service, dependency, state migration, API operation, or runtime configuration is introduced.

The issue suggestion to validate a completed spec at scaffold creation is excluded: a fresh draft deliberately lacks gate evidence. This ruling is shared by all four analysis reports.
