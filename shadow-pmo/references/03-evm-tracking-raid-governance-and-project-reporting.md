# 03. Earned Value Management (`CPI`/`SPI`/`EAC`), RAID Governance & Project Reporting

## 1. Purpose & Activation Conditions
Use this playbook to monitor mid-project cost and schedule health objectively via **Earned Value Management (`EVM`)**, manage client and vendor blockers in an auditable **RAID Log (Risks, Assumptions, Issues, Dependencies)**, and assemble formal institutional reports (**Laporan Pendahuluan, Laporan Antara, Laporan Akhir** & **BAST Acceptance Evidence Packs**) routed cleanly through `/shadow-doc`.

Activate this playbook when:
- Calculating `PV`, `EV`, `AC`, `CPI`, `SPI`, `EAC`, and `VAC` to trigger objective recovery plans instead of subjective *"90% done"* status updates.
- Attributing schedule delays transparently between vendor execution variance and overdue client dependencies (`FSD sign-off`, `staging credentials`, `data migration sign-off`).
- Preparing executive project reports via `shadow-doc/scripts/doc_orchestrator.py` (`adapt_pmo_or_ea_payload`).

## 2. Prerequisites
- Approved WBS Cost & Schedule Baseline (`BAC` Budget at Completion and time-phased `PV` Planned Value).
- Actual recorded expenditure (`AC`) and objectively verified deliverable completion (`EV` — strictly grounded in completed `Done` deliverables or signed UAT milestones, NEVER subjective developer percentage guesses!).
- Companion templates: [`../playbooks/PMO-DELIVERABLES-AND-CR-TEMPLATES.md`](../playbooks/PMO-DELIVERABLES-AND-CR-TEMPLATES.md).

## 3. Technical Principles & Constraints
1. **Exact EVM Formulas & Red-Line Thresholds**:
   - **Cost Performance Index:** $\text{CPI} = \frac{\text{EV}}{\text{AC}}$ (`>= 1.0` under/on budget; `< 0.90` triggers mandatory cost recovery review).
   - **Schedule Performance Index:** $\text{SPI} = \frac{\text{EV}}{\text{PV}}$ (`>= 1.0` ahead/on schedule; `< 0.90` triggers mandatory critical-path recovery plan).
   - **Estimate at Completion:** $\text{EAC} = \frac{\text{BAC}}{\text{CPI}}$ (typical recurring variance), **Variance at Completion:** $\text{VAC} = \text{BAC} - \text{EAC}$, **To-Complete Performance Index:** $\text{TCPI} = \frac{\text{BAC} - \text{EV}}{\text{BAC} - \text{AC}}$.
   - Guard against zero-division (`AC == 0` or `PV == 0` -> return explicit `NOT_APPLICABLE / ZERO_DENOMINATOR`, never `Infinity` or fake `1.0`!).
2. **Binary `0/100` or Weighted Milestone EV Rule (Eliminate "90% Done" Syndrome)**:
   - Count `EV` strictly from verified milestone exits (e.g., `0%` until a vertical story/deliverable passes DoD/UAT, or `20/80` milestone gates backed by evidence) so stalled tasks cannot report `"90% complete"` for 6 consecutive weeks while burning `AC`.
3. **Auditable RAID Governance**:
   - Link every delayed external/client action (`D-01: Client UAT Environment Provisioning`) directly to the WBS predecessor node it blocks, with exact original due date, actual delay days, owner, and escalation date — providing indisputable evidence if a contractual time extension (**Perpanjangan Waktu / Addendum Waktu**) is later required.
4. **Single Document Engine Rendering (`SA-DOC-ENGINE-001`)**:
   - NEVER duplicate `.docx`/`.pdf` exporters inside `shadow-pmo`; feed structured PMO JSON into `shadow-doc/scripts/doc_orchestrator.py` (`domain_adapters.py::adapt_pmo_or_ea_payload`).

## 4. Architecture & Implementation
### Strict TypeScript EVM Calculator & Health Threshold Classifier
```typescript
export interface EvmSnapshotInput {
  readonly bac: number; // Budget at Completion
  readonly pv: number;  // Planned Value to date
  readonly ev: number;  // Earned Value (verified deliverables only)
  readonly ac: number;  // Actual Cost to date
}

export type ProjectHealthBand = 'GREEN' | 'AMBER' | 'RED';

export interface EvmReport {
  readonly cpi: number | null;
  readonly spi: number | null;
  readonly eac: number | null;
  readonly vac: number | null;
  readonly health: ProjectHealthBand;
  readonly recoveryPlanRequired: boolean;
}

export function computeEvmReport(input: EvmSnapshotInput): EvmReport {
  const cpi = input.ac > 0 ? input.ev / input.ac : null;
  const spi = input.pv > 0 ? input.ev / input.pv : null;
  const eac = cpi !== null && cpi > 0 ? input.bac / cpi : null;
  const vac = eac !== null ? input.bac - eac : null;

  let health: ProjectHealthBand = 'GREEN';
  if ((cpi !== null && cpi < 0.9) || (spi !== null && spi < 0.9)) {
    health = 'RED';
  } else if ((cpi !== null && cpi < 0.97) || (spi !== null && spi < 0.97)) {
    health = 'AMBER';
  }

  return {
    cpi,
    spi,
    eac,
    vac,
    health,
    recoveryPlanRequired: health === 'RED',
  };
}
```

### Institutional Indonesian Consulting Deliverables Map
| Deliverable Report | Contract Stage | Mandatory Contents | Collaborating Skills |
| :--- | :--- | :--- | :--- |
| **Laporan Pendahuluan** | Kickoff (`M1`) | Verified scope baseline, stakeholder/RACI matrix, WBS + `P80` baseline schedule, initial RAID log | `/shadow-discovery`, `/shadow-doc` |
| **Laporan Antara** | Mid-Point (`M3–M4`) | EVM dashboard (`CPI`/`SPI`/`EAC`), CCB-signed CR Register, Architecture/Prototype evidence, active RAID blockers | `/shadow-architect`, `/shadow-doc` |
| **Laporan Akhir & BAST Pack** | Closure (`Final`) | Final EVM/scope reconciliation, signed `Berita Acara UAT`, SBOM/handover receipt, open minor punch-list & warranty SLA | `/shadow-uat`, `/shadow-handover`, `/shadow-doc` |

## 5. Platform / Vendor Variations
- **Indonesian Government / BUMN Term-Based Payments (`Termin 1 / 2 / 3`)**: Tie `EV` explicitly to contractual payment deliverables (`Laporan Pendahuluan`, `Laporan Antara`, `UAT + BAST`) so cashflow milestones match verified physical progress (`bobot fisik %`).
- **Enterprise Agile Portfolio Programs**: Measure `EV` via completed vertical Epics/Stories passing Definition of Done (`shadow-plan`) rather than hours logged, exposing velocity drop early via `SPI` trendlines.

## 6. Decision Matrix & Trade-Offs
| EVM Signal | Interpretation | Mandatory PMO Action |
| :--- | :--- | :--- |
| `CPI >= 1.0`, `SPI >= 1.0` | On/under budget and on/ahead of schedule | Maintain cadence; audit scope baseline compliance |
| `CPI >= 1.0`, `SPI < 0.90` | Under budget but behind schedule (often blocked on client approvals or understaffing) | Check RAID dependencies; fast-track critical path or escalate client delay formally |
| `CPI < 0.90`, `SPI < 0.90` | **Over budget AND behind schedule** (`RED`) | Trigger formal Corrective Recovery Plan: freeze scope creep, review CR backlog, re-baseline with sponsor/CCB |
| `CPI < 0.90`, `SPI >= 1.0` | Fast execution but burning budget unsustainably (overtime / rework) | Inspect defect rework rate (`/shadow-quality`, `/shadow-test`) and cap unapproved effort |

## 7. Real Production Scenario
**Context:** A 6-month enterprise portal reported `"Status: GREEN — 80% complete"` in weekly status emails during Month 4, while actual contractor burn (`AC`) reached `88%` of `BAC`.
**EVM Intervention:** Switching to verified milestone `EV` revealed only `62%` of deliverables had actually passed DoD (`PV = 70%`, `EV = 62%`, `AC = 88%` -> `SPI = 0.89`, `CPI = 0.70`, projected `EAC = 142%` of budget!). Exposing the `RED` trend in Month 4 enabled immediate CCB scope triage (moving 4 uncontracted dashboards to a Paid CR) and saved the project from a severe Month 6 overrun.

## 8. Failure Modes & Edge Cases
- **WRONG (Computing `EV` from subjective self-reported percentages or hiding `RED` `CPI`/`SPI` under "Watermelon Reporting" — green outside, red inside):** Conceals cost overruns until budget is exhausted.
  **RIGHT:** Derive `EV` strictly from verified completed deliverables, trigger formal recovery whenever `CPI < 0.90` or `SPI < 0.90`, and report real variance transparently.
- **WRONG (Reporting `CPI = 1.0` when `AC = 0` or writing bespoke Word exporters inside `shadow-pmo`):** Corrupts math edge cases and violates `SA-DOC-ENGINE-001`.
  **RIGHT:** Guard zero denominators cleanly and render all formal project reports through `shadow-doc/scripts/doc_orchestrator.py`.

## 9. Testing & Verification
- Run `python shadow-pmo/scripts/pmo_governance_engine.py --self-test` (`8/8` probes).
- Validate exported `PROJECT_REPORT` and `CHANGE_REQUEST` documents via `shadow-doc/scripts/doc_scaffold.py validate --doc <report.json> --strict` (zero fabricated metrics or unresolved `[TBD]` claims).

## 10. Operational Considerations
- Archive weekly EVM snapshots and RAID change logs chronologically so `Laporan Antara` and `Laporan Akhir` show authentic historical trend curves rather than reconstructed end-of-project numbers.

## 11. Authoritative References
- **PMI Practice Standard for Earned Value Management (ANSI/EIA-748)** — `PV`, `EV`, `AC`, `CPI`, `SPI`, `EAC`, `VAC`, `TCPI`.
- **Shadow PMO Templates** — [`../playbooks/PMO-DELIVERABLES-AND-CR-TEMPLATES.md`](../playbooks/PMO-DELIVERABLES-AND-CR-TEMPLATES.md).

## 12. Limitations & When NOT to Use
- **Do NOT use** EVM to track operational cloud/LLM unit spend — delegate cloud & token cost optimization to `/shadow-finops`.
- **Do NOT use** `/shadow-pmo` to draft raw tender BoQ/RAB bids prior to contract award — route pre-award commercial pricing to `/shadow-presales`.
