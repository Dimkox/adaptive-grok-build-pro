# Source exploration — repo_explorer

Read-only findings on a730ee9, no checks run. Existing landing_runtime composes render/evaluate/seal; landing_sqlite_store already provides WAL/FULL durable state and bounded recovery. server.build_app instead constructs InMemoryLandingJobStore + UnavailableLandingProvider.

landing_live_executors ignores image_bytes, uses constant usage 1/1 and elapsed time at most 25 ms, buffers the complete HTTP body, accepts arbitrary HTTPS origins and does not bind profiles to actual provider/model. Publication is only an unavailable Never-returning port and v1 live_url is null.

Scope recommendation: truthful bounded transport, durable explicit composition, then a separate publication target/contract and explicit source refresh. PDF/audio are deliberate needs_human outcomes, service work is serialized, and digest-only artifact result is not an operational publication interface.
