# Design

Existing trust-ci/ build context, runner.Dockerfile and OperationsTests own this source preparation. No new service, architecture node, edge, import, contract or runtime configuration is needed. Pin duplication is intentional because the isolated build context cannot COPY the separate implementation requirements outside trust-ci; the two prerequisites are reviewed together and delivered separately.
