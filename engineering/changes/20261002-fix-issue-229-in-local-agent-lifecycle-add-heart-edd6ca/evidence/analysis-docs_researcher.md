# Documentation research

Route edd6ca692480; base e5856acfd4bc7a186f40a740b54ec86459462db5. Independent read-only docs_researcher report; no writes/tests/credentials/private transcript access.

Issue229 describes running/nonresponsive children manually recovered via interrupt_agent and followup_task on the same agent; lack of subprocesses alone is not a stall. Issue41 covers lost completion notifications; issue45 covers terminal failures without diagnostics. Closed issue190 is not proof of local/native heartbeat integration. Current local core has no demonstrated agent-result CLI/store/runbook; state contains only start/stop, stop output is deliberately empty, and grok_status returns raw records. Factory result-admission is a separate product surface.

Document installed commands/settings, timestamp meanings, bounded warning reasons, acknowledged safe recovery, workspace preservation and the native harness observability boundary. Local hooks or explicit adapter calls do not prove native message delivery or interruption. Persist only closed diagnostic classes/timestamps, never prompts/source/provider blobs/secrets. Update README/hooks instructions and applicable installed agent prompts consistently. Preserve empty stop output.
