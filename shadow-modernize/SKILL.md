---
name: shadow-modernize
description: "Technical Due Diligence & Legacy Modernization. Use when auditing inherited/legacy systems, performing business-rule archaeology, scoring multi-dimensional risk vectors, or comparing Strangler Fig Refactor vs Full Rewrite TCO including coexistence costs."
---

# `/shadow-modernize` — Technical Due Diligence & Migration Intelligence

Use this skill whenever the **Monarch** invokes `/shadow-modernize`, audits an inherited/legacy codebase or vendor system, performs M&A/handover technical due diligence, or evaluates **Strangler Fig Refactor vs Rewrite** modernization economics.

Integrates with [`shadow-monarch/reference/CONSULTING-INTELLIGENCE-CORE.md`](../shadow-monarch/reference/CONSULTING-INTELLIGENCE-CORE.md) and deep methodologies:
- [`methodologies/TECHNICAL-FORENSICS-AND-MIGRATION-ECONOMICS.md`](methodologies/TECHNICAL-FORENSICS-AND-MIGRATION-ECONOMICS.md) — 8-Area Technical Due Diligence, Multi-Dimensional Risk Vectors with Evidence Confidence, Business-Rule Archaeology, and Migration Economics (coexistence & transition cost).
- [`playbooks/DUE-DILIGENCE-AND-CUTOVER-TEMPLATES.md`](playbooks/DUE-DILIGENCE-AND-CUTOVER-TEMPLATES.md) — System Archaeology Report, Technical Risk Register, Migration Dependency Map, Modernization Business Case, Cutover Plan, and Rollback Playbook.

---

## 1. Execution Contract (Never Produce Opaque Single Tech-Debt Scores)

1. **Read-Only Forensics by Default**: Inspect repositories, schemas, dependency lockfiles, CI/CD, and operational telemetry read-only, recording `SHA-256` evidence digests and explicit **access limitations** (e.g., no prod telemetry or DB access).
2. **Multi-Dimensional Risk Vector (Not One Black-Box Score)**:
   - Score **8 dimensions separately** (`code_dependencies`, `architecture_coupling`, `data_integrity`, `operations_slo`, `security_supply_chain`, `business_criticality`) with configurable weights and explicit **`evidence_confidence`** (`HIGH`/`MEDIUM`/`LOW`).
   - **Critical Rule**: Absence of automated tests does **NOT** automatically mandate a `FULL_REWRITE`. A stable core system carrying complex undocumented business rules and high downtime cost is frequently safer to preserve via **Characterization Tests + Strangler Fig / Branch by Abstraction**.
3. **Business-Rule Archaeology**:
   - Before proposing migration cuts, cross-reference database triggers/constraints/stored procedures, API validators, batch cron jobs, and historical incident workarounds to surface hidden domain invariants.
4. **Migration Economics (Refactor vs Rewrite TCO)**:
   - Model `build_transition_cost + dual_run_coexistence_cost + data_reconciliation_cost + risk_adjusted_delay_cost` across 3–5 years for `STRANGLER_FIG_REFACTOR`, `PHASED_MODULARIZATION`, `ENCAPSULATE_RETAIN`, and `FULL_REWRITE`.

---

## 2. Deterministic Forensics & Economics Engine

```powershell
python "shadow-modernize/scripts/modernize_forensics_engine.py" --self-test
python "shadow-modernize/scripts/modernize_forensics_engine.py" --scan-repo path/to/legacy_repo
python "shadow-modernize/scripts/modernize_forensics_engine.py" --evaluate-options path/to/system_profile.json
```

- **Reuse & Preservation Gate (`OFFICIAL-FIRST-DEPENDENCY-POLICY.md`):** Preserve established framework routing, auth/SSO SDKs (`file:../sdk/sso-client`), and package patterns unless verified insecure/obsolete or explicitly approved for replacement by the Monarch (`official_first_verifier.py`).
