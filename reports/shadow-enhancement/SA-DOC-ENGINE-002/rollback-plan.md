# SA-DOC-ENGINE-002 — Rollback Plan

## Safe Reversibility Guarantees
All changes target `shadow-doc/` and `reports/shadow-enhancement/SA-DOC-ENGINE-002/` cleanly without altering existing `v1.0` (`bagian`) or `v2.0` canonical schemas or mutating `~/.claude`, `~/.gemini`, `~/.codex`, or remote `origin/main`.

1. **Full Patch Rollback**:
   - Inspect uncommitted diff via `git diff --stat a957246`.
   - Restore any individual file safely with `git checkout -- <path>` only when explicitly instructed by the Monarch.
2. **Per-Feature Fallback**:
   - **Unicode PDF Fonts (`H01`)**: Automatically degrades to core `Helvetica` + `_ascii_clean` if system TTF fonts are unavailable.
   - **Diagram Rendering (`R07`)**: Automatically degrades to `FALLBACK_SOURCE_PRESERVED` / `CLI_MISSING` without corrupting canonical JSON when external CLI tools fail or timeout.
   - **Strict Domain Adapter Checks (`R08`)**: Non-strict mode remains callable (`strict=False`), attaching transparent `[UNVERIFIED]` / `[MISSING_EVIDENCE]` diagnostics in `x-shadow:data_integrity` without raising exceptions.
