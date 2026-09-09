REVOKE UPDATE ON factory.capacity_counters, factory.intake_identities FROM factory_runtime;
GRANT UPDATE (active_count) ON factory.capacity_counters TO factory_runtime;
