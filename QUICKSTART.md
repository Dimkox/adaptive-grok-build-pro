# Quickstart — Adaptive Grok Build Pro

1. Install Grok Build:
   - Windows: `irm https://x.ai/cli/install.ps1 | iex`
   - macOS/Linux: `curl -fsSL https://x.ai/cli/install.sh | bash`

2. Auth: run `grok` once, sign in with SuperGrok account.

3. Install this stack into your repo:
   ```bash
   python3 scripts/install_into.py /path/to/repo
   ```

4. Work:
   ```bash
   cd /path/to/repo
   grok
   ```
   Prompt example: `Добавь обработчик события OnAfterUserAdd в local-модуль`

5. Optional explicit skill: `/adaptive-delivery`

6. Verify before finish:
   ```bash
   python3 scripts/grok_verify.py --mode pr
   ```
   Then `/release-readiness` and `python3 scripts/grok_deploy.py` to prepare human-owned publish commands (`--record` only with production approval).

7. Trust project hooks in the TUI: `/hooks-trust`
