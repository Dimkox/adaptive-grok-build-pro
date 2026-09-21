# Shared-memory facts for the coordinator

Proposed `decisions.md` entry after independent review: A socket that must start after an ordinary network/guard service cannot keep its implicit `Before=sockets.target` dependency; the candidate removes default socket dependencies, explicitly retains sysinit/shutdown ordering, and enables under `multi-user.target`. Installed systemd validation accepted the resulting dependency graph without a cycle; startup, guard-stop propagation, and cold boot still need their distinct operational evidence.

Useful bounded control: namespace `vpn` already owns `100.119.249.65`, whose route to `10.200.200.1` uses `veth-vpn-n`, while the authorized peer is `10.200.200.2`. A source-bound GET and the dedicated wrong-source drop counter can prove that boundary without new addresses, raw sockets, or firewall probes affecting other destinations. This route fact is measured; successful filtering remains unmeasured until activation.

Preserve the transient observation: one public baseline GET timed out before HTTP status, followed by a bounded timing diagnostic returning 502 in 0.771730 s. Do not report uninterrupted 502 responses or treat a timeout as successful path/HTTP acceptance; the underlying transient cause was not established.
