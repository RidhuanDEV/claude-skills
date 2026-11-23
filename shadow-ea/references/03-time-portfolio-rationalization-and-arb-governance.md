# 03. TIME Application Portfolio Rationalization, Duplicate Detection & ARB Governance

## 1. Purpose & Activation Conditions
Use this playbook when rationalizing a sprawling multi-application enterprise or agency portfolio (`>= 5` systems) using the **Gartner TIME Model (`Tolerate | Invest | Migrate | Eliminate`)**, detecting redundant overlapping capabilities (`EA-DUP-*`), and operating **Architecture Review Board (`ARB`) / Design Authority** compliance reviews that connect enterprise strategy cleanly to downstream engineering skills.

Activate this playbook when:
- Scoring an organization's application catalog (`SYS-*`) across **Business Value (`1–5`)** and **Technical Health (`1–5`)** via `ea_portfolio_engine.py --analyze-portfolio`.
- Identifying redundant shadow-IT or departmental applications duplicating the same business capability (`EA-DUP-*`) for consolidation or retirement.
- Conducting Architecture Review Board (`ARB`) compliance checks prior to funding new system builds.

## 2. Prerequisites
- Application Portfolio Catalog (`system_id`, `name`, `business_capability`, `business_value`, `tech_health`, `data_owner`, annual ops cost) — grounded in real operational/financial records (`[EVIDENCE]`), flagging estimated scores explicitly (`[ASSUMPTION]`).
- Deterministic portfolio engine [`../scripts/ea_portfolio_engine.py`](../scripts/ea_portfolio_engine.py) & templates [`../playbooks/EA-BLUEPRINT-AND-PORTFOLIO-TEMPLATES.md`](../playbooks/EA-BLUEPRINT-AND-PORTFOLIO-TEMPLATES.md).

## 3. Technical Principles & Constraints
1. **Deterministic TIME Quadrant Classification (`ea_portfolio_engine.py`)**:
   - **`INVEST`** (`business_value >= 3.5` AND `tech_health >= 3.0`): Strategic core — fund roadmap enhancements, API exposure, and reuse across divisions.
   - **`MIGRATE`** (`business_value >= 3.5` AND `tech_health < 3.0`): Mission-critical legacy — hand directly to **`/shadow-modernize`** (due diligence + Strangler Fig TCO) or consolidate into a target platform.
   - **`TOLERATE`** (`business_value < 3.5` AND `tech_health >= 3.0`): Stable low-differentiation utility — maintain minimally with security patches (`/shadow-maintain`), zero major feature investment.
   - **`ELIMINATE`** (`business_value < 3.5` AND `tech_health < 3.0`, OR redundant duplicate capability with `business_value < 4.0`): Schedule controlled data archival, user migration, and system decommission!
2. **Automated Duplicate-Capability Detection (`EA-DUP-*`)**:
   - Whenever `>= 2` applications map to the SAME `business_capability` (e.g., `SIMPEG-CORE` and `ABSEN-SILO` both owning `"Civil Servant Lifecycle"`), flag an explicit duplicate finding (`EA-DUP-*`) and designate ONE authoritative **System of Record (SoR)** while scheduling redundant siblings for `MIGRATE` / `ELIMINATE`.
3. **Traceable Downstream Handoffs (`SYS-*` IDs)**:
   - Every TIME verdict flows directly with stable `SYS-*` IDs into execution skills:
     - `MIGRATE` -> **`/shadow-modernize`** (business-rule archaeology & Strangler Fig vs Rewrite TCO)
     - `INVEST` / Consolidation BOM -> **`/shadow-presales`** (3-scenario capacity sizing & TCO/NPV)
     - Multi-Year Transition Waves -> **`/shadow-pmo`** (WBS, PERT/Monte Carlo `P80`, RAID)
     - Compliance & Security Gaps -> **`/shadow-grc`** (COBIT/ISO 27001/POJK/SPBE)
4. **Architecture Review Board (`ARB`) Gate & Single Document Engine**:
   - Require every new project funding request to pass an ARB check (`No duplicate capability? Aligned with ABB standards? Assigned Data Owner / Wali Data? Security & FinOps baseline addressed?`).
   - Export formal `ARCHITECTURE_REPORT` deliverables exclusively via `shadow-doc/scripts/doc_orchestrator.py` (`adapt_pmo_or_ea_payload`).

## 4. Architecture & Implementation
### Strict TypeScript TIME Classifier & Duplicate Capability Detector
```typescript
export type TimeQuadrant = 'INVEST' | 'MIGRATE' | 'TOLERATE' | 'ELIMINATE';

export interface PortfolioApp {
  readonly systemId: string;
  readonly name: string;
  readonly businessCapability: string;
  readonly businessValue: number; // 1.0..5.0
  readonly techHealth: number;    // 1.0..5.0
  readonly dataOwner: string;
}

export interface RationalizedApp {
  readonly systemId: string;
  readonly quadrant: TimeQuadrant;
  readonly duplicateCapabilityFlag: boolean;
}

export function classifyTimePortfolio(
  apps: readonly PortfolioApp[],
): readonly RationalizedApp[] {
  const capCounts = new Map<string, number>();
  for (const app of apps) {
    const key = app.businessCapability.trim().toLowerCase();
    capCounts.set(key, (capCounts.get(key) ?? 0) + 1);
  }

  return apps.map((app) => {
    const key = app.businessCapability.trim().toLowerCase();
    const isDuplicate = (capCounts.get(key) ?? 0) > 1;
    let quadrant: TimeQuadrant;
    if (app.businessValue >= 3.5 && app.techHealth >= 3.0) {
      quadrant = 'INVEST';
    } else if (app.businessValue >= 3.5 && app.techHealth < 3.0) {
      quadrant = 'MIGRATE';
    } else if (app.businessValue < 3.5 && app.techHealth >= 3.0) {
      quadrant = isDuplicate ? 'ELIMINATE' : 'TOLERATE';
    } else {
      quadrant = 'ELIMINATE';
    }
    return {
      systemId: app.systemId,
      quadrant,
      duplicateCapabilityFlag: isDuplicate,
    };
  });
}
```

### Portfolio Rationalization Verification Input (`ea_portfolio_engine.py`)
```json
{
  "org_type": "GOVERNMENT_SPBE",
  "spbe_domains_covered": [
    "PROSES_BISNIS", "DATA_DAN_INFORMASI", "INFRASTRUKTUR_SPBE",
    "APLIKASI_SPBE", "KEAMANAN_SPBE", "LAYANAN_SPBE"
  ],
  "applications": [
    { "system_id": "SIMPEG-CORE", "name": "HRIS Terintegrasi", "business_capability": "Civil Servant Lifecycle", "business_value": 4.5, "tech_health": 3.8, "data_owner": "BKD" },
    { "system_id": "ABSEN-SILO", "name": "Unit Attendance Legacy", "business_capability": "Civil Servant Lifecycle", "business_value": 2.9, "tech_health": 1.8, "data_owner": "Dinas-X" }
  ],
  "abb_sbb_gaps": [
    { "abb_id": "ABB-API-GW-01", "capability": "SPLP Compliant API Gateway", "candidate_sbb": "Kong / Apache APISIX" }
  ]
}
```

## 5. Platform / Vendor Variations
- **Government SPBE Consolidation (`Aplikasi Umum` Transition)**: Pair `ELIMINATE` verdicts with explicit citizen-service migration notices and statutory record archival (`ANRI` / `UU PDP` retention rules) before shutting down legacy regional apps.
- **Enterprise Cloud & SaaS Sprawl**: Combine TIME scoring with `/shadow-finops` FOCUS spend telemetry so duplicate SaaS subscriptions and idle legacy VMs quantify exact annual OPEX savings from retirement!

## 6. Decision Matrix & Trade-Offs
| TIME Verdict | Annual Budget Allocation | Downstream Skill Handoff | Risk if Ignored |
| :--- | :--- | :--- | :--- |
| **`INVEST`** | Growth CAPEX + platform APIs | `/shadow-architect`, `/shadow-plan` | Starving strategic core slows business growth |
| **`MIGRATE`** | Funded Strangler transition | `/shadow-modernize`, `/shadow-pmo` | Unaddressed EOL legacy becomes `SEV1` ticking time bomb |
| **`TOLERATE`** | Minimal security/Harwat OPEX | `/shadow-maintain` | Over-investing in low-value utilities wastes engineering capacity |
| **`ELIMINATE`** | Bounded decommission budget | `/shadow-data` (archive), `/shadow-finops` | Permanent shadow-IT licensing, security exposure, and data fragmentation |

## 7. Real Production Scenario
**Context:** A regional government discovered it was paying Harwat maintenance fees across `34` separate departmental web apps—including `6` overlapping attendance apps and `4` separate e-letter tracking apps—consuming `70%` of its annual IT budget on repetitive patching.
**Outcome:** Running `ea_portfolio_engine.py --analyze-portfolio` flagged `10` `EA-DUP-*` duplicates as `ELIMINATE`, designated `SIMPEG-CORE` and national `SRIKANDI` as authoritative Systems of Record (`INVEST`), routed 3 high-value aging revenue apps (`MIGRATE`) to `/shadow-modernize`, and instituted a mandatory ARB review gate blocking new silo procurements—freeing `38%` of annual IT OPEX over 24 months.

## 8. Failure Modes & Edge Cases
- **WRONG (Marking systems `ELIMINATE` without checking archival/retention obligations or hidden external consumers):** Triggers data loss or breaks external finance/regulatory feeds on shutdown day.
  **RIGHT:** Pair every `ELIMINATE` verdict with data-retention archival verification (`/shadow-privacy`, `/shadow-data`) and downstream consumer archaeology (`/shadow-modernize`) before decommission.
- **WRONG (Running `ARB` as an arbitrary political veto with zero objective rubric):** Encourages divisions to hide shadow-IT purchases outside IT governance.
  **RIGHT:** Publish clear, transparent 5-point ARB compliance criteria (Capability Duplication, `ABB` Standards, Data Owner, Security/GRC, FinOps TCO) with fast `<= 5` business-day turnaround.

## 9. Testing & Verification
- Run `python shadow-ea/scripts/ea_portfolio_engine.py --self-test` (`8/8` probes) and `--analyze-portfolio <portfolio.json>`.
- Verify every `MIGRATE`/`ELIMINATE` entry links to a named `data_owner` and explicit downstream transition wave.

## 10. Operational Considerations
- Refresh the Application Portfolio Catalog & TIME heatmap semi-annually; stale spreadsheets quickly diverge from shadow-IT reality unless tied to annual budget & procurement approval gates.

## 11. Authoritative References
- **Gartner** — *Application Rationalization TIME Model (`Tolerate, Invest, Migrate, Eliminate`)*.
- **The Open Group (2022)** — *TOGAF 10 Architecture Governance & Architecture Review Board (ARB)*.
- **Shadow EA Engine** — [`../scripts/ea_portfolio_engine.py`](../scripts/ea_portfolio_engine.py).

## 12. Limitations & When NOT to Use
- **Do NOT use** TIME portfolio rationalization to redesign internal classes/modules of a single application — route single-app architecture to `/shadow-architect` and code cleanup to `/shadow-refactor`.
- **Do NOT fabricate** `business_value` or `tech_health` scores without documenting scoring rubrics and stakeholder evidence (`[EVIDENCE]` vs `[ASSUMPTION]`).
