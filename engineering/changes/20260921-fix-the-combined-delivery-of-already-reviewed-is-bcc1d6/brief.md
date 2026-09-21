# Combined delivery of eight reviewed issue repairs

Typed scope: [change-spec.yaml](change-spec.yaml). Exact source inputs: [candidates.json](candidates.json). Main is839d3aa2 after PR170 delivered155/164 with external App success.

User explicitly instructed remaining fixes in parallel, their repository delivery and closure: «делай всё и закрывай». This package changes delivery packaging of those same bounded reviewed repairs, with no additional behavior or operational scope. The inherited scope/design consent applies to exactly the listed candidate paths and acceptance criteria. The named external-write gate remains separate: each push/PR/merge needs an exact local grant, and the external App check plus any required signed human scopes remain mandatory. No migration/deployment is requested by this integration package.

Six disjoint source candidates already have measured regression evidence and independent reviews. Combining them on the newly delivered main gives one actual integrated source tree for full verification, five independent reviews and external exact-head CI. Individual earlier full runs are historical evidence; pending corrected candidate final gates are satisfied only by the upcoming combined run and review, not by relabeling earlier runs. Existing171/172 stay open until the successor is delivered, then are closed with the actual successor evidence.
