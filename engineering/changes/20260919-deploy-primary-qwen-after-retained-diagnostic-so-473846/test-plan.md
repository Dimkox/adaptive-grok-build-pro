# Verification scope

Source tests and exact-head external checks belong to PR154. Reuse prior source migration/backup coverage because those product files are unchanged; verify operational script syntax and every changed guard without provider or service calls before independent review. At execution, verify exact installed bytes/dependencies, backup manifest, disabled capability, schema/count preservation, one bounded durable acceptance and read-only observation or complete recovery. No whole development suite is rerun just for this operational paperwork.
