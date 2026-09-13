# Delivery

Deliver D as a stacked branch/PR based on C after local verification and all selected independent reviews. Source extraction does not deploy or enable a provider. Runtime remains disabled until explicit configured opt-in. Immutable source state is frozen before verification; final reports live in the separate evidence checkout so report collection cannot change the tested source fingerprint. Local receipts are not external merge authority.
