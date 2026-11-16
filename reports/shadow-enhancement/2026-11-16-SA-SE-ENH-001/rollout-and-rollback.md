# Phase 5 — Rollout & Rollback Plan (`SA-SE-ENH-001`)

## 1. Authorized Global Rollout Procedure (Wait for Monarch Approval)
1. **Verify Working Tree Cleanly:**
   ```powershell
   python "shadow-quality/scripts/shadow_gate.py" --repo .
   python "shadow-monarch/scripts/skill_router.py" --self-test
   python "evals/run_evals.py" --self-test
   ```
2. **Sync Local Cross-Agent Installations (Windows):**
   - For Claude Code / Antigravity / Gemini CLI / Codex copies + global `CLAUDE.md` / `AGENTS.md` / `GEMINI.md` blocks:
     ```powershell
     powershell -ExecutionPolicy Bypass -File .\install.ps1
     ```
   - Or if using directory junctions for Codex (`%USERPROFILE%\.agents\skills`):
     ```powershell
     powershell -ExecutionPolicy Bypass -File .\install-codex.ps1
     ```
   - For Claude Desktop / `claude.ai`, upload the rebuilt local `shadow-monarch.zip` and paste updated `shadow-monarch/GLOBAL.md` into personal preferences if desired.
3. **Commit & Push (Only If Explicitly Requested by Monarch):**
   ```powershell
   git status -sb
   git add -A
   git commit -m "feat(shadow-army): expand to 52 skills with 7 engineering specialists and progressive router"
   git push origin main
   ```

## 2. Deterministic Rollback Procedure
Because global home folders and `origin/main` were NOT modified during execution, rollback before global rollout requires zero home-directory cleanup:

1. **Rollback Repo Changes Only (If Requested Before Commit):**
   ```powershell
   # Inspect first
   git status -sb
   # Remove untracked new skills & enhancement reports, and restore tracked files to 185c42a
   # (Run ONLY on explicit Monarch instruction — destructive on uncommitted work)
   ```
   Directories added by `SA-SE-ENH-001`:
   `shadow-debug/`, `shadow-refactor/`, `shadow-concurrency/`, `shadow-domain/`, `shadow-realtime/`, `shadow-search/`, `shadow-supplychain/`, `reports/shadow-enhancement/2026-11-16-SA-SE-ENH-001/`.
2. **Rollback Global Home Install (If Rolled Out Earlier):**
   - Delete the `7` new skill folders from `%USERPROFILE%\.gemini\skills`, `.gemini\config\skills`, `.claude\skills`, `.agents\skills`, and `.codex\skills`.
   - Restore `.bak.<timestamp>` backups created automatically by `install.ps1` for `CLAUDE.md`, `AGENTS.md`, and `GEMINI.md`.
   - Re-run `install.ps1` from commit `185c42a2fa8e520293b3819a56b681fd60b9fe18`.
