# Recovery

Stop/disable only adaptive-trust-ci-webhook-bridge.socket and stop its service and guard service, in dependency-safe order so the listener closes before removing the dedicated nft table. Remove only newly installed named artifacts if rollback is selected; never remove existing firewall tables or change the API/Tailscale configuration. Confirm127.0.0.1:18080/health/ready remains200. Network recreation stops the bridge through device dependency; explicit reactivation after wg-vpn-namespace is healthy is the bounded forward recovery.
