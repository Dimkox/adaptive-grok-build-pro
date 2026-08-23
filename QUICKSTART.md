# Quickstart — Adaptive Grok Build Pro

0. Check tools. Minimum-or-newer versions are accepted locally; doctor offers a fallback install when something is missing:

   ```bash
   python3 scripts/grok_doctor.py --offer-install
   ```

1. Install Grok Build:

   - Windows: `irm https://x.ai/cli/install.ps1 | iex`
   - macOS/Linux: `curl -fsSL https://x.ai/cli/install.sh | bash`

2. Run `grok` once and sign in with a SuperGrok account.

3. Install the stack into the target repository:

   ```bash
   python3 scripts/install_into.py /path/to/repo
   # installs the stack and missing required tools
   # use --no-deps to copy only
   ```

   To install the independent GitHub CI and protected release contour too, explicitly name the target repository owner:

   ```bash
   python3 scripts/install_into.py /path/to/repo \
     --with-ci \
     --codeowner @user

   # an organization team is also valid:
   # --codeowner @org/team
   ```

   The installer renders that identity into the target `CODEOWNERS` file and trust-boundary runbook. It never exports `@Dimkox` as the owner of another repository. Then apply the solo-owner or split-identity GitHub settings from `docs/TRUST-BOUNDARY.md`.

4. Work:

   ```bash
   cd /path/to/repo
   grok
   ```

   Prompt example: `Добавь обработчик события OnAfterUserAdd в local-модуль`.

5. Optional explicit controller skill: `/adaptive-delivery`.

6. Verify before delivery:

   ```bash
   python3 scripts/grok_verify.py --mode pr
   python3 scripts/grok_verify.py --mode pr --strict --json
   ```

   Local output is feedback. Delivery is feature branch → pull request → exact-SHA `trusted-ci` → configured human gate → protected merge. Release runs only through the protected `production` Environment.

7. Trust project hooks in the TUI: `/hooks-trust`.
