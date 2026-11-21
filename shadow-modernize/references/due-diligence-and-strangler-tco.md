# Technical Due Diligence, Legacy Archaeology & Strangler TCO Playbook

> Use this playbook when auditing inherited/legacy systems (`L0_READ_ONLY` static forensics first), scoring multi-dimensional risk vectors, uncovering hidden business rules, or evaluating **Strangler Fig Refactor vs Modularize vs Rewrite** economics.

## 1. Core Concepts
Big-bang rewrites on undocumented, business-rule-heavy legacy cores frequently fail because the legacy codebase *is* the only complete specification of edge cases, rounding quirks, and statutory workflows:
- **Multi-Dimensional Risk Vector (No Single Opaque Score):** Express risk across 6 explicit axes (`code_dependencies`, `architecture_coupling`, `data_integrity`, `operations_slo`, `security_supply_chain`, `business_criticality`) paired with per-axis **Evidence Confidence** (`HIGH`/`MEDIUM`/`LOW`).
- **Coexistence Economics:** Multi-year migrations run two systems in parallel. Realistic TCO MUST include **dual-run operations, data synchronization, and anti-corruption gateway costs** during cutover.

## 2. Technical Rules & Decision Matrix

| Legacy Archetype | Recommended Strategy | Reject / Guard Condition |
| :--- | :--- | :--- |
| Stable core, infrequent change, isolated security risk | **Maintain / Patch / Isolate Behind Proxy** | Do not churn stable code merely because stack feels dated |
| Tightly coupled UI/integrations blocking partner APIs | **Encapsulate / Anti-Corruption Facade** | Wrap DB/SOAP core behind typed REST/OpenAPI gateway first |
| High-value evolving system, complex undocumented rules, 0% tests | **Strangler Fig Incremental Refactor** (Default) | Write characterization tests (`/shadow-refactor`) -> peel 1 bounded vertical slice -> retire legacy route |
| EOL unpatchable runtime + clean small rule surface + full spec | **Scoped Modular Rewrite** | Never greenlight Big-Bang Full Rewrite while `business_rule_complexity == HIGH` and `has_automated_tests == false` |

## 3. Implementation Examples

### Risk-Adjusted 3-Year Coexistence TCO Formulas (`modernize_forensics_engine.py`)
$$\text{TCO}_{\text{Strangler}} = B_{\text{strangler}} + R_{\text{penalty}}(0.15 \cdot B_{\text{strangler}}) + C_{\text{dual}}(0.35 \cdot O_{\text{legacy}} \cdot Y)$$
$$\text{TCO}_{\text{Rewrite}} = B_{\text{rewrite}} + R_{\text{penalty}}(0.45 \cdot B_{\text{rewrite}} \text{ if rule\_complexity=HIGH}) + C_{\text{dual}}(0.65 \cdot O_{\text{legacy}} \cdot Y)$$

### Multi-Dimensional Risk Profile (`modernize_forensics_engine.py`)
```json
{
  "horizon_years": 3,
  "business_rule_complexity": "HIGH",
  "production_stability_high": true,
  "has_automated_tests": false,
  "annual_legacy_ops_cost": 1000000000,
  "strangler_build_cost": 1800000000,
  "rewrite_build_cost": 3000000000,
  "risk_dimensions": {
    "code_dependencies": { "score": 4.2, "confidence": "HIGH", "evidence_refs": ["package-lock.json", "php-7.4-eol"] },
    "data_integrity": { "score": 3.8, "confidence": "MEDIUM", "evidence_refs": ["sql/triggers.sql"] },
    "operations_slo": { "score": 2.5, "confidence": "LOW", "evidence_refs": [] }
  }
}
```
```powershell
python "shadow-modernize/scripts/modernize_forensics_engine.py" --scan-repo path/to/legacy_repo
python "shadow-modernize/scripts/modernize_forensics_engine.py" --evaluate-options system_profile.json
```

## 4. Best Practices
- Always execute `scan_repo_forensics` (`L0_READ_ONLY` static manifest + migration + test inventory) BEFORE recommending architectural action, and flag static limitations (`live DB triggers`, `runtime SLO`) explicitly when runtime telemetry is absent.
- Schedule mandatory **slice retirement dates** in every Strangler Fig roadmap so teams finish deleting deprecated legacy paths instead of running two permanently forked systems.

## 5. Anti-Patterns (`WRONG` vs `RIGHT`)
- **WRONG (Single weighted "tech debt = 7.8/10" score & unverified Big-Bang Rewrite):** Telling management "Legacy score is 7.8, rewrite everything from scratch in Next.js + Microservices" when business rules have zero tests.
  **RIGHT:** Report 6 separate risk dimensions + evidence confidence gaps, build characterization tests around high-risk rules, and price Strangler Fig vs Rewrite including dual-run coexistence costs.
- **WRONG (Replacing working internal auth/SSO SDKs during due diligence):** Swapping `ridhuan-sso` (`file:../sdk/sso-client`) or established routing frameworks opportunistically.
  **RIGHT:** Preserve verified internal adapters under `OFFICIAL-FIRST-DEPENDENCY-POLICY.md` unless proven insecure/unmaintainable with explicit Monarch sign-off.

## 6. Production Considerations
- **Cutover Parity Gate:** Shadow-compare outputs of each strangled domain slice against legacy calculations (cents/Rupiah exact match, state transitions, permissions) before flipping production routing permanently.
