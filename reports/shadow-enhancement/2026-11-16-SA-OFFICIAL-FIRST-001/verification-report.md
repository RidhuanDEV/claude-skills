# Verification Report: Official-First Project Initialization & Dependency Verification (`SA-OFFICIAL-FIRST-001`)

- **Run ID:** `2026-11-16-SA-OFFICIAL-FIRST-001`
- **Repository:** `<repo>` (`main`, base commit `ad007dd`)
- **Readiness Level:** `VERIFIED-LOCAL` (all deterministic Official-First, dependency-verification, auth/SSO SDK preservation, approval-gate, router, eval, and quality-gate checks executed locally and passed; global home install via `./install.ps1` and `git commit`/`git push` remain `NOT_RUN` awaiting explicit Monarch approval).

---

## 1. Centralized Governance Architecture (Single Policy Source Across `16` Skills / `27` Modified Tracked Files)
- **Authoritative Policy Document:** `shadow-monarch/reference/OFFICIAL-FIRST-DEPENDENCY-POLICY.md` (`55` total reference modules: `33` Role & Domain, `9` `lang-*`, `13` `sub-*`). Covers all `7` Core Principles, `6`-Phase Mandatory Workflow, non-destructive `npm view` inspection, `5`-Tier Selection Hierarchy, mandatory `8`-Field Decision Record (`Technology | Source | Version | Trust status | Compatibility | Existing alternative | Decision | Approval`), Special Authentication/SSO & `your-org-sso` (`file:../sdk/sso-client`) Rule, and `8` Failure Conditions.
- **Deterministic Verifier Script:** `shadow-monarch/scripts/official_first_verifier.py` (`--verify-decision`, `--check-auth-sdk`, `--out`, `--self-test`, `--help`, UTF-8/UTF-8-BOM safe via `utf-8-sig`), verified on `12/12` self-test probes (`OF-NEG-01`..`OF-NEG-08` + `OF-POS-01`..`OF-POS-04`).
- **Orchestrator & Global Sync:**
  - `shadow-monarch/SKILL.md` (`330` lines `<= 500`): Rule 26 + Role FK row pointing to `OFFICIAL-FIRST-DEPENDENCY-POLICY.md`.
  - `shadow-monarch/GLOBAL.md`: Rule 26 enforcing official CLI generators for token savings, non-destructive package metadata checks, pinned versions, and local SSO SDK preservation.
  - `shadow-monarch/scripts/execution_approval_gate.py`: added `replace_auth_sdk` (`L4`) and `change_framework_or_package_manager`, `add_unrequested_infrastructure`, `major_architecture_dependency` (`L2`) checks (`16/16` self-test probes).
  - `shadow-monarch/scripts/skill_router.py`: auto-attaches `OFFICIAL-FIRST-DEPENDENCY-POLICY.md` and `shadow-bootstrap` / `shadow-auth` on new-project scaffolding, dependency adoption, and `your-org-sso` / SDK tasks (`37/37` probes).
  - `shadow-quality/scripts/shadow_gate.py`: integrated `official_first_verifier.py --self-test` check (`official_first_gate_verified: true`).
  - `README.md` & `shadow-monarch.zip` (`311,258` bytes) updated cleanly (`55` references).
- **Specialist Skills & Reference Integration (Zero Duplication):**
  - Updated `shadow-bootstrap`, `shadow-architect`, `shadow-auth` (dedicated Section 5 for existing SSO/Auth SDK & `your-org-sso`), `shadow-integrate`, `shadow-supplychain`, `shadow-compat`, `shadow-sec`, `shadow-ops`, `shadow-release`, `shadow-quality`, `context7`, `shadow-modernize`, `shadow-refactor`, `shadow-api`, `shadow-mobile`, plus `shadow-monarch/reference/FRONTEND.md` & `BACKEND.md`.
- **Eval Scenario `#37`:** Added `official-first-scaffolding-dependency-and-sso-sdk-verification` across `evals/evals.json`, `evals/README.md`, and `evals/run_evals.py`.

---

## 2. Reproducible Verification Results

| Gate / Check | Command | Exit Code | Result | Observed Evidence |
|---|---|---:|---|---|
| Official-First Self-Test (`8` Negative + `4` Positive) | `python "shadow-monarch/scripts/official_first_verifier.py" --self-test` | `0` | `PASS` | `passed: 12/12`, `all_passed: true` |
| Official-First CLI Blocked Modes (`--verify-decision`, `--check-auth-sdk`, `--out`) | PowerShell temp JSON harness | `2` (blocked) | `PASS` | Manual scaffold & unverified npm `your-org-sso` replacement fail closed with exit `2` & JSON output file created |
| Execution Approval Gate (`NEG-01`..`NEG-12` + `POS-01`..`POS-04`) | `python "shadow-monarch/scripts/execution_approval_gate.py" --self-test` | `0` | `PASS` | `passed: 16/16`, `all_passed: true` |
| Frontmatter Description Audit | `python "shadow-monarch/scripts/skill_router.py" --audit-descriptions` | `0` | `PASS` | `total_skills: 52`, `all_passed: true` |
| Topic & Official-First Router Probes | `python "shadow-monarch/scripts/skill_router.py" --self-test` | `0` | `PASS` | `passed: 37/37`, `all_passed: true` (`OFFICIAL-1`, `OFFICIAL-2` pass) |
| Eval Catalog & Self-Test Probes | `python "evals/run_evals.py" --validate` & `--self-test` | `0` | `PASS` | `eval_count: 37`; `passed: 46/46`, `all_passed: true` |
| Repo Quality & Integrated Gates | `python "shadow-quality/scripts/shadow_gate.py" --repo .` & `--self-test` | `0` | `PASS` | `passed: true`, `approval_gate: true`, `official_first: true`, `blocking: 0`, `warnings: 0`; self-test `14/14` |
| New Policy & Report Safety Scan | `reference_verifier.py scan` on `OFFICIAL-FIRST-DEPENDENCY-POLICY.md` & report dir | `0` | `PASS` | `all_safe: true` on both |
| Global Install / Git Commit & Push / Live Agent CLI | `./install.ps1`, `git commit`/`push`, `evals/run_evals.py --agent ...` | `—` | `NOT_RUN` | Withheld awaiting explicit Monarch authorization for this enhancement |
