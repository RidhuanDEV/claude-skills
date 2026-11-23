# 01. Read-Only Static Forensics & Multi-Dimensional Risk Vectors

## 1. Purpose & Activation Conditions
Use this playbook at the start of any legacy modernization engagement, inherited codebase takeover, or M&A technical due diligence audit (`/shadow-modernize`). Its objective is to produce an **evidence-anchored, multi-dimensional risk vector** using read-only forensics (`L0_READ_ONLY`) rather than an opaque single `"tech debt = 7.8/10"` score that misleads executives into destructive big-bang rewrites.

Activate this playbook when:
- Auditing an inherited vendor repository, legacy enterprise monolith, or undocumented system before proposing refactoring vs modernization budgets.
- Scoring technical, operational, security, and business-criticality risks with explicit `evidence_confidence` levels and access-limitation disclosures.
- Running `shadow-modernize/scripts/modernize_forensics_engine.py --scan-repo`.

## 2. Prerequisites
- Read-only access to the target codebase (manifests, lockfiles, migrations, CI/CD, Dockerfiles, tests).
- Explicit list of **what IS accessible vs NOT accessible** (e.g., no live production DB read access, no APM/SLO telemetry, no incident ticket history) so unobserved dimensions carry `evidence_confidence = LOW`.
- Companion deep docs: [`../methodologies/TECHNICAL-FORENSICS-AND-MIGRATION-ECONOMICS.md`](../methodologies/TECHNICAL-FORENSICS-AND-MIGRATION-ECONOMICS.md) & [`../playbooks/DUE-DILIGENCE-AND-CUTOVER-TEMPLATES.md`](../playbooks/DUE-DILIGENCE-AND-CUTOVER-TEMPLATES.md).

## 3. Technical Principles & Constraints
1. **Strict `L0_READ_ONLY` Forensics First**:
   - Inspect files, lockfiles, schema migrations, git commit churn, and dependency graphs strictly read-only. Record `SHA-256` evidence digests of inspected lockfiles/manifests and NEVER mutate production databases, upgrade packages, or run destructive commands during due diligence.
2. **Multi-Dimensional Risk Vector (Never One Black-Box Score)**:
   - Score **6 explicit core risk axes** independently (`1.0–5.0`, configurable weights) across the 8-area due diligence scope:
     1. `code_dependencies` (runtime EOL, unmaintained frameworks, transitive CVE surface)
     2. `architecture_coupling` (cyclic imports, shared global DB writes, tight UI-to-DB coupling)
     3. `data_integrity` (missing FK/unique constraints, undocumented triggers/stored procs, dirty historical rows)
     4. `operations_slo` (manual deployments, missing observability, backup/DR gaps)
     5. `security_supply_chain` (auth weaknesses, plaintext secrets, outdated TLS/crypto)
     6. `business_criticality` (revenue/regulatory impact, downtime cost, undocumented statutory rules)
   - Pair EVERY axis with **`evidence_confidence` (`HIGH | MEDIUM | LOW`)** and inspectable `evidence_refs`. An axis scored without production telemetry or DB inspection MUST carry `confidence: "LOW"` and an explicit access-limitation note!
3. **Zero-Tests != Automatic Full Rewrite**:
   - Absence of automated tests (`has_automated_tests: false`) NEVER automatically justifies a `FULL_REWRITE`. High-stability legacy cores carrying complex undocumented business rules and high downtime costs are almost always safer to stabilize via **Characterization Tests + Strangler Fig** (`02` & `03`).
4. **Internal SDK & Framework Preservation Gate**:
   - Under `OFFICIAL-FIRST-DEPENDENCY-POLICY.md`, preserve verified internal auth/SSO adapters (e.g., `ridhuan-sso` / `file:../sdk/sso-client`) and working framework conventions unless proven insecure or unmaintainable with explicit Monarch authorization.

## 4. Architecture & Implementation
### Multi-Dimensional Risk Vector Contract (Strict TypeScript)
```typescript
export type EvidenceConfidence = 'HIGH' | 'MEDIUM' | 'LOW';

export type RiskAxisName =
  | 'code_dependencies'
  | 'architecture_coupling'
  | 'data_integrity'
  | 'operations_slo'
  | 'security_supply_chain'
  | 'business_criticality';

export interface RiskAxisAssessment {
  readonly axis: RiskAxisName;
  readonly score: number; // 1.0 (low risk) to 5.0 (severe risk)
  readonly confidence: EvidenceConfidence;
  readonly evidenceRefs: readonly string[];
  readonly accessLimitation: string | null;
}

export function auditRiskVectorHonesty(
  assessments: readonly RiskAxisAssessment[],
): readonly string[] {
  const issues: string[] = [];
  for (const item of assessments) {
    if (item.score < 1 || item.score > 5) {
      issues.push(`${item.axis}: score ${item.score} out of 1..5 bounds.`);
    }
    if (item.evidenceRefs.length === 0 && item.confidence !== 'LOW') {
      issues.push(
        `${item.axis}: zero evidenceRefs cannot claim ${item.confidence} confidence; downgrade to LOW.`,
      );
    }
    if (item.confidence === 'LOW' && (item.accessLimitation === null || item.accessLimitation.trim() === '')) {
      issues.push(`${item.axis}: LOW confidence must explicitly state accessLimitation.`);
    }
  }
  return issues;
}
```

### Static Forensics Execution (`modernize_forensics_engine.py`)
```powershell
python "shadow-modernize/scripts/modernize_forensics_engine.py" --scan-repo path/to/legacy_repo
python "shadow-modernize/scripts/modernize_forensics_engine.py" --evaluate-options path/to/system_profile.json
```

## 5. Platform / Vendor Variations
- **PHP / Java / .NET Legacy Monoliths**: Prioritize checking PHP/JDK/.NET runtime End-of-Life dates, direct SQL queries inside templates/controllers, stored procedures/triggers in DB dumps, and session storage mechanics before touching UI frameworks.
- **Inherited Agency / Outsourced Node.js & Python Repos**: Inspect `package-lock.json` / `requirements.txt` abandonment, git blame bus-factor (`1` ex-contractor), unversioned hotfix scripts on production servers, and shadow cron jobs outside Git.

## 6. Decision Matrix & Trade-Offs
| Observed Forensics Profile | Recommended Modernization Posture | Why |
| :--- | :--- | :--- |
| Stable core, low change velocity, EOL PHP/Node dependency only | **Isolate + Runtime Patch / Containerize** | Avoids destroying stable business rules for cosmetic stack preference |
| Tightly coupled DB/SOAP monolith blocking new partner/mobile channels | **Encapsulate Behind Typed Anti-Corruption Facade** | Unlocks new consumers fast while isolating legacy internals |
| High-value evolving system, complex undocumented rules, 0% tests | **Characterization Tests + Strangler Fig Incremental Refactor** | Eliminates big-bang rewrite failure while retiring legacy slice by slice |
| Unpatchable EOL runtime + small well-documented rule surface + full spec | **Scoped Modular Rewrite** | Bounded scope keeps risk & dual-run cost predictable |

## 7. Real Production Scenario
**Context:** A private equity due diligence team inherited a 12-year-old PHP 7.4 billing monolith with zero automated tests and asked whether to budget a 9-month full rewrite in Next.js + Microservices.
**Forensics Outcome:** Running `modernize_forensics_engine.py --scan-repo` + multi-dimensional scoring revealed `code_dependencies = 4.5 (HIGH confidence)` due to PHP 7.4 EOL, `operations_slo = 2.5 (LOW confidence — no prod APM access)`, and `business_criticality = 4.9 (HIGH)` because 19 SQL triggers encoded regional tax exemptions undocumented anywhere else. Instead of a catastrophic big-bang rewrite, the team upgraded PHP incrementally behind an API gateway and strangled only the customer portal first, cutting 3-year risk-adjusted TCO by 44%.

## 8. Failure Modes & Edge Cases
- **WRONG (Collapsing forensics into a single black-box score like `"Tech Debt = 7.8/10 -> Rewrite Now"`):** Hides missing telemetry access, confuses runtime EOL with business-rule fragility, and rubber-stamps high-failure rewrites.
  **RIGHT:** Present all 6 risk dimensions separately with `evidence_confidence`, inspectable `evidence_refs`, and explicit access limitations.
- **WRONG (Mutating packages or deleting "unused" files during read-only due diligence):** Corrupts forensic baseline and violates `L0_READ_ONLY` audit boundaries.
  **RIGHT:** Keep due diligence strictly read-only until the Monarch approves a concrete modernization roadmap.

## 9. Testing & Verification
- Run `python shadow-modernize/scripts/modernize_forensics_engine.py --self-test` (`8/8` probes).
- Confirm every axis in the generated Technical Risk Register includes non-empty `evidence_refs` (or explicit `confidence: "LOW"` + `access_limitation`).

## 10. Operational Considerations
- Archive exact repo commit SHA and lockfile `SHA-256` hashes in the System Archaeology Report so M&A / executive stakeholders can trace every finding back to the exact due diligence snapshot date.

## 11. Authoritative References
- **Martin Fowler** — *Strangler Fig Application* (`https://martinfowler.com/bliki/StranglerFigApplication.html`).
- **Michael Feathers (2004)** — *Working Effectively with Legacy Code* (Seam Model & Characterization Tests).
- **Shadow Modernize Methodology** — [`../methodologies/TECHNICAL-FORENSICS-AND-MIGRATION-ECONOMICS.md`](../methodologies/TECHNICAL-FORENSICS-AND-MIGRATION-ECONOMICS.md).

## 12. Limitations & When NOT to Use
- **Do NOT use** `/shadow-modernize` for routine single-module cleanup inside a healthy active codebase — route tactical refactors to `/shadow-refactor`.
- **Do NOT use** for multi-agency SPBE / TOGAF portfolio rationalization across 20+ systems — route portfolio strategy to `/shadow-ea`.
