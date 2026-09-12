# Five-minute investor demo

This is a truthful local product tour of Adaptive Grok Build Pro. It demonstrates how reviewed software intent becomes bounded execution policy and inspectable evidence without running an agent, verifier, Git operation, provider, or external service. Demo routing uses a fixed non-authoritative seed rather than querying Git; `--open` may ask the operating system to open the configured local browser.

## Start

Requirements: Python 3.10 or newer and this complete source or packaged checkout. No package install, frontend build, database, account, credential, or network connection is needed.

```bash
cd /path/to/adaptive-grok-build-pro
python3 scripts/grok_demo.py --open
```

The launcher prints `http://127.0.0.1:8765/` and opens it when the local browser permits. Without `--open`, copy the printed URL into a browser. Press `Ctrl-C` in the terminal to stop.

If port 8765 is occupied:

```bash
python3 scripts/grok_demo.py --port 8766 --open
```

## What the evidence labels mean

- `bundled_sample`: bundled sample fixtures reviewed and included only to illustrate evidence shape.
- `computed_preview`: route and draft specification calculated in memory by repository code for the entered prompt.
- `live_repository`: read-only architecture or governance summary derived from this checkout.
- `not_run`: no verifier ran for the entered prompt.

Bundled and local evidence is not merge authority. It does not represent an App-owned exact-SHA Trust CI result, approval, merge eligibility, release, or deployment. Those remain separate operator-controlled steps.

## The five-minute story

### 0:00–0:30 — Start with the control system

Point to the local/read-only badge and the provenance statement. Explain: “Most coding-agent demos show generated code. This shows the control system around it—what may run, who may write, and what proof is still required.”

### 0:30–1:20 — Intent becomes a deterministic route

Use the bundled secure API dashboard prompt. In Route & ownership, show intent, risk, domains, workflow skills, and the selected write owner. Then select the contrasting documentation-review route. Its button label is derived from the computed alternate route and currently reads “Use contrasting review route · medium risk · no write owner”; the resulting panel truthfully shows `review` intent, `medium` risk from this API-contract repository, the `api` domain, and no write owner. This demonstrates real deterministic reclassification rather than a canned animation or a fabricated low-risk claim.

### 1:20–2:05 — Typed intent is inspectable

In Typed specification, show stable criterion coverage, invariants, forbidden outcomes, objective, and digest. Explain that the bundled specification is complete, while a newly entered prompt produces a clearly labelled draft that still requires design and has verification `not_run`.

### 2:05–2:50 — Architecture is executable evidence

In Architecture, show model-derived component, edge, trust-domain, and contract counts. Explain that the browser and local demo server are explicit local nodes and have no edge to GitHub, Trust CI authority, production trust, or deployment.

### 2:50–3:35 — Learning stays governed

In Governance, show rules, debt, examples, findings, digest, and live-repository provenance. Explain that an observation can become a candidate but cannot promote itself into active policy; repository text is not independent authority.

### 3:35–4:25 — Evidence is scoped, not overstated

In Verification evidence, show pass/fail/skip counts and the persistent bundled-sample label. State explicitly: “This is illustrative local evidence, not a live CI verdict. An entered prompt never inherits it; its verification status is `not_run`.”

### 4:25–5:00 — Close on the moat

Return to the full pipeline: deterministic control, domain-specialist selection, one writer, typed criteria, trust-aware architecture, governed learning, and independent evidence. The demo’s constraint is the point: it can explain decisions but cannot approve, merge, publish, or deploy.

## Recovery and accessibility checks

- Empty submission stays on the prompt and shows inline validation.
- Stop the server after a successful load: the browser keeps only its in-memory last-good result and labels it `Stale — local server unavailable`; Retry reconnects after restart.
- If architecture or governance cannot be read, only that card is unavailable and other cards remain visible.
- The dashboard stacks into one column at mobile widths, is keyboard reachable, supports Ctrl+Enter, has visible focus, uses text and icons in addition to color, and respects reduced-motion/forced-color preferences.
- No service worker or persistent browser storage is used.

## Boundary

Only the loopback dashboard, four allowlisted assets, `GET /api/v1/health`, `GET /api/v1/snapshot`, and `POST /api/v1/preview` exist. The server accepts no caller-selected path, root, command, URL, profile, session, Git ref, credential, or output destination. It performs no external request or write.
