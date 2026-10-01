"""Reviewed byte literals extracted from the pinned ailev/FPF source tree."""

from types import MappingProxyType

FPF_FRAGMENT_BYTES = {
    "A.2.4": """#### A.2.4:4.7 - Shortcut cost and reopen condition

A.2.4 is the inexpensive first-use classifier. It may identify the episteme, target claim or status, effective source scheme when material, ClaimScope, polarity or value, window, intended use, applicable definition or constraint, and any unsupported overread grounded under F.19:4. It does not decide the source work, local result, provenance, currentness, assurance, causal support, gate passage, permission, commitment, publication interpretation, or receiving action.

Open only the exact subject question whose predicate decides the use: A.13 for the actual performer; A.15.1 for independent Work admission; F.6 when the result must also identify the assignment under which that Work was performed; A.6.1 for actual bindings; the domain result predicate plus C.2.1 for result content; A.10/G.6 for provenance and bounded reliance; G.11 for currentness; B.3 for assurance; C.28 for causal use; F.10 for a status family; or E.17 for publication. Reopen the A.2.4 classification when the episteme, target claim/status, scope, polarity/value, window, or intended use changes.

""".encode("utf-8"),
    "A.3.1": """#### A.3.1:4.1 - Thin first-use method identification

Start with the least apparatus that lets another reader recognize the same method:

1. **Ordinary use.** State the reusable way of doing, the kinds of participants it is for, when it applies, what it is meant to achieve or preserve, and any applicable use limits or stop conditions. If that sentence is enough for the decision at hand, stop.
2. **Later comparison or reliance.** Use the needed entries in the Plain aid below when the ordinary statement is insufficient for another person to distinguish same-named methods, compare descriptions or variants, cite one edition in a plan, or audit why this method was selected.
3. **Organization of several methods or uses.** Open `A.22`, `B.1.5`, or another direct composition pattern only when the question is about the organization itself—for example, which methods were composed, selected, used as fallbacks, or enacted in the reviewed work.

Moving to a heavier level must solve one of those concrete problems.

The following is a Plain identification aid, not a record kind, ontic, serialization, or mandatory form. Omit every optional line that the stated decision does not use.

```text
Method identification aid:
  MethodRef:
  SemanticBasisIfMeaningVaries:
  Applicability:
  GenericParticipantMeanings:
  MethodConcern:
  Preconditions:
  IntendedResultOrPreservedCondition:
  MethodDescriptionIfReliedOn:
  WorkRelationIfReliedOn:
  SelectedStructureOrModelUseIfReliedOn:
  RelationsThatMustObtain:
  RelianceWindow:
  ReviewIf:
  NotEstablished (ClaimBoundary):
```

Use `NotEstablished` only for a stronger reading that passes F.19:4's plausible-reader guard test. State the smallest clear correction; omit the entry when the positive identification suffices. Use the FPF term `ClaimBoundary` when a named neighboring subject assertion depends on that boundary.

Add `SemanticBasisIfMeaningVaries` only when the same words have different meanings under another effective reference scheme or set of local senses. Add a claim scope, context slice, selected structure, or model-use relation only when its own predicate obtains and changing it would change the method identification or the later decision.

For every relied-on relation, name its participants, the relation that must obtain, and the pattern that defines or constrains it. A generic `source`, `support`, `evidence`, or `current use` entry is not a replay basis. `RelianceWindow` states the temporal conditions under which the comparison is relied on. Identify the compared Method variants and relied-on description editions separately. `ReviewIf` names the concrete change that would make that comparison unsafe.

""".encode("utf-8"),
}


FPF_FRAGMENT_MANIFEST = {
    "schema_version": 1,
    "source_repository": "https://github.com/ailev/FPF",
    "source_revision": "86226dcb42d8ba340ebc86d7660fce165ac0722a",
    "source_tree": "bbef238ca28d3ec6c3ea51ade228255d1304dc03",
    "source_author": "Anatoly Levenchuk, with AI-agent assistance",
    "license_id": "CC-BY-4.0",
    "license_url": "https://creativecommons.org/licenses/by/4.0/",
    "extraction_method": "exact-utf8-byte-range-v1",
    "fragments": {
        "A.2.4": {
            "locator": "FPF-Spec.md",
            "anchor": "A.2.4:4.7",
            "sha256": "f1ff88a20808cca841d645b6782fafdc99e38a81dba475e2f4d7889d06559d0f",
            "required": (),
            "optional": (
                "A.10", "A.13", "A.15.1", "A.6.1", "B.3", "C.2.1", "C.28",
                "E.17", "F.10", "F.19:4", "F.6", "G.11", "G.6",
            ),
            "dependency_rationale": (
                "The excerpt is a complete bounded first-use classifier. Its own wording says "
                "to open only the exact subject question whose predicate decides the use; those "
                "cross-references are conditional escalation routes, not prerequisites for applying "
                "the stated classifier."
            ),
            "dependency_evidence": "Open only the exact subject question whose predicate decides the use",
        },
        "A.3.1": {
            "locator": "FPF-Spec.md",
            "anchor": "A.3.1:4.1",
            "sha256": "dafa2df5eaa9f33b82a9a3141be17441a1baaea41431b63ae3a90e19be265c8d",
            "required": (),
            "optional": ("A.22", "B.1.5", "F.19:4"),
            "dependency_rationale": (
                "The excerpt supplies the complete thin first-use identification. It directs the reader "
                "to heavier composition patterns only when organization itself is the question, and "
                "F.19:4 only when a stronger reading needs a ClaimBoundary."
            ),
            "dependency_evidence": "Moving to a heavier level must solve one of those concrete problems.",
        },
    },
}

FPF_FRAGMENT_BYTES = MappingProxyType(FPF_FRAGMENT_BYTES)
FPF_FRAGMENT_MANIFEST = MappingProxyType({
    **FPF_FRAGMENT_MANIFEST,
    "fragments": MappingProxyType({
        key: MappingProxyType(value)
        for key, value in FPF_FRAGMENT_MANIFEST["fragments"].items()
    }),
})
