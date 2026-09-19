# Local runtime identity observation

Route `473846f79243`; observed `2026-09-19T19:14:00.656167+00:00` on local Claw. Read-only observation using `sudo -n systemctl show`, SHA-256 of the named non-secret config/unit files, allowlisted config fields, and `git rev-parse HEAD` in each control repository. No SSH, environment/credential reads, runtime writes, provider calls, or repeated tests/old analysis.

All three units are `active/running`, `enabled`, `live_enabled=true`, and have no drop-ins. Each loaded executable is `/opt/adaptive-l5/releases/<installed_sha>/venv/bin/adaptive-landing-server`; its config names `/opt/adaptive-l5/releases/<installed_sha>/repository`, whose Git HEAD equals that installed SHA. Unit fragments are `/etc/systemd/system/<unit>`.

| Unit | Installed SHA / control HEAD | Profile | Main PID | Start UTC |
| --- | --- | --- | --- | --- |
| `adaptive-l5.service` | `5f6f6ce1ecb0cef8e1b3910b037af983c5fb8f8a` | `qwen-intl` | `2326158` | `2026-09-19 12:55:12` |
| `adaptive-l5-grok.service` | `26a0d3db8fa9f3e8ad69caafd02a5ef4e9613960` | `grok-vision` | `2287703` | `2026-09-19 12:39:08` |
| `adaptive-l5-omni.service` | `e7d0f72bf834b75eb543d9424ee47c7829cc65c0` | `qwen-omni-intl` | `2204064` | `2026-09-17 06:47:54` |

Primary config: `/opt/adaptive-l5/releases/5f6f6ce1ecb0cef8e1b3910b037af983c5fb8f8a/landing-host.json`.
Config SHA-256: `f80b12107136d473ce06ffc12ea0817e960d137380fb12f60017bfc54e2a5ad6`.
Unit SHA-256: `c0fd42ba8dd576323ba677df82fbcf27e9c4df7c8a2a0fbd4312b6caa187d5a6`.

Grok config: `/opt/adaptive-l5/releases/26a0d3db8fa9f3e8ad69caafd02a5ef4e9613960/grok-host.json`.
Config SHA-256: `f4bb012578f53b559e491c9d340094f6c6e29ba6ec39fe996e11d2277b9a46b2`.
Unit SHA-256: `3df99c0168103e691e7571c162609c5859914ca8963aeb2c4cf03718572b08c0`.

Separate Omni config: `/etc/adaptive-l5/omni-host.json`.
Config SHA-256: `6c661ed3ba5737e2fb733a99139e954cd077a4771fffc7931953a61cefc6e34f`.
Unit SHA-256: `1d501478e343fb61e369513cff7d340c2f260877b4343bbdd45236f838879de8`.

No divergence from the expected identities, profiles, PIDs, active/enabled states, or three unit hashes in the previous package's `evidence/final-runtime.json`. The primary config also exactly matches its preserved pre-upgrade SHA. Grok and Omni config hashes above establish fresh no-op baselines; the cited final-runtime record did not contain those hashes.

The primary remains on its restored old source/profile; this observation does not establish acceptance of the candidate. Grok and separate Omni require no operation. Controller must wait for the exact externally attested merged revision containing `a4023258047a03e1176daa3a35695c9d9b49f8be` before any primary activation; candidate deployment and provider acceptance were not attempted here.
