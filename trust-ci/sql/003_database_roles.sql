REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC;
REVOKE ALL ON FUNCTION trust_ci_claim_job(text, integer) FROM PUBLIC;

GRANT USAGE ON SCHEMA public TO trust_ci_api, trust_ci_worker, trust_ci_backup;

GRANT SELECT, INSERT, UPDATE ON trust_ci_jobs TO trust_ci_api;
GRANT SELECT ON trust_ci_job_attempts TO trust_ci_api;
GRANT SELECT, INSERT ON trust_ci_approvals TO trust_ci_api;
GRANT SELECT ON trust_ci_attestations TO trust_ci_api;
GRANT SELECT ON trust_ci_events TO trust_ci_api;
GRANT SELECT ON trust_ci_schema_migrations TO trust_ci_api;

GRANT SELECT, UPDATE ON trust_ci_jobs TO trust_ci_worker;
GRANT SELECT, INSERT, UPDATE ON trust_ci_job_attempts TO trust_ci_worker;
GRANT SELECT ON trust_ci_approvals TO trust_ci_worker;
GRANT SELECT, INSERT ON trust_ci_attestations TO trust_ci_worker;
GRANT SELECT, INSERT ON trust_ci_events TO trust_ci_worker;
GRANT USAGE, SELECT ON SEQUENCE trust_ci_events_event_id_seq TO trust_ci_worker;
GRANT SELECT ON trust_ci_schema_migrations TO trust_ci_worker;
GRANT EXECUTE ON FUNCTION trust_ci_claim_job(text, integer) TO trust_ci_worker;

GRANT SELECT ON ALL TABLES IN SCHEMA public TO trust_ci_backup;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO trust_ci_backup;

ALTER DEFAULT PRIVILEGES FOR ROLE trust_ci_migrator IN SCHEMA public
    REVOKE ALL ON TABLES FROM PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE trust_ci_migrator IN SCHEMA public
    REVOKE ALL ON SEQUENCES FROM PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE trust_ci_migrator IN SCHEMA public
    REVOKE ALL ON FUNCTIONS FROM PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE trust_ci_migrator IN SCHEMA public
    GRANT SELECT ON TABLES TO trust_ci_backup;
ALTER DEFAULT PRIVILEGES FOR ROLE trust_ci_migrator IN SCHEMA public
    GRANT SELECT ON SEQUENCES TO trust_ci_backup;
