# Contractual CR Triage, PERT/CPM Monte Carlo & EVM Governance Playbook

> Use this playbook when classifying client requests against contractual precedence as **Defect vs Paid CR Candidate**, forecasting stochastic schedules via **PERT + CPM + seeded Monte Carlo (`P50/P80/P90`)**, or computing **Earned Value Management (`CPI/SPI/EAC`)**.

## 1. Core Concepts
PMO governance protects both project timeline integrity and contractual scope margins:
- **Contractual Precedence Hierarchy:** Scope disputes resolve strictly by document rank: **`Main Contract > Signed Addendum > KAK / TOR / SOW > Approved FSD / SRS > Meeting Minutes`**. Informal chat/emails cannot silently expand paid deliverables.
- **Deterministic CPM Underestimates Risk (Merge Bias):** Summing PERT means along one deterministic critical path systematically ignores parallel near-critical paths delaying join nodes. Seeded Monte Carlo simulation across the full WBS DAG reveals realistic `P80` contractual buffers.

## 2. Technical Rules & Decision Matrix

| Governance Trigger | Rule / Classification | Required Action |
| :--- | :--- | :--- |
| Client report violates signed FSD / KAK acceptance criterion | **Warranty / Defect** (In-Scope) | Route directly to fix + regression test; zero CR surcharge |
| Client request adds capability beyond signed KAK / Addendum | **Paid Change Request (`PAID_CR`) Candidate** | Assess schedule (`P80` delta) + effort impact -> route formally to Change Control Board (`CCB`) |
| WBS Schedule Commitment | **PERT (`O, M, P`) + Seeded Monte Carlo DAG** | Target **`P50`** internally; commit contractually at **`P80`**; budget risk reserve against **`P90`** |
| Mid-Project Cost / Schedule Health | **EVM Metrics (`CPI`, `SPI`, `EAC`)** | Flag recovery plan whenever `CPI < 0.90` or `SPI < 0.90` |

## 3. Implementation Examples

### Exact PERT, Monte Carlo & EVM Mathematical Reference (`pmo_governance_engine.py`)
- **PERT Expected Duration:** $E = \frac{O + 4M + P}{6}$, **Task Std Dev:** $\sigma = \frac{P - O}{6}$ *(strict constraint: $0 \le O \le M \le P$)*.
- **Critical Path Method (CPM):** Topological Forward Pass (`ES`, `EF`) + Backward Pass (`LS`, `LF`); `Total Float = LS - ES` (`0` = critical).
- **Earned Value Management (EVM):**
  - $\text{CPI} = \frac{\text{EV}}{\text{AC}}$ *(Cost efficiency; `< 1.0` over budget)*
  - $\text{SPI} = \frac{\text{EV}}{\text{PV}}$ *(Schedule efficiency; `< 1.0` behind schedule)*
  - $\text{EAC} = \frac{\text{BAC}}{\text{CPI}}$, $\text{VAC} = \text{BAC} - \text{EAC}$

### Acyclic WBS Schedule & CR Decision Record JSON (`scripts/pmo_governance_engine.py`)
```json
{
  "seed": 42,
  "monte_carlo_iterations": 2000,
  "tasks": [
    { "id": "T1", "name": "Signed API Contract", "optimistic": 2, "most_likely": 3, "pessimistic": 5, "predecessors": [] },
    { "id": "T2", "name": "Core Payment Flow", "optimistic": 5, "most_likely": 8, "pessimistic": 14, "predecessors": ["T1"] },
    { "id": "T3", "name": "UAT & BAST Closure", "optimistic": 3, "most_likely": 5, "pessimistic": 9, "predecessors": ["T2"] }
  ]
}
```
```powershell
python "shadow-pmo/scripts/pmo_governance_engine.py" --analyze-schedule wbs_dag.json
python "shadow-pmo/scripts/pmo_governance_engine.py" --evaluate-cr cr_request.json
```

## 4. Best Practices
- Reject circular task graphs upfront (`_topological_order` detects cycles before computing CPM floats).
- Keep a live **RAID Log (Risks, Assumptions, Issues, Dependencies)** linking overdue client UAT/data approvals to explicit schedule slippage ownership.

## 5. Anti-Patterns (`WRONG` vs `RIGHT`)
- **WRONG (Treating out-of-scope stakeholder Slack requests as free minor tweaks or committing at `P50`):** Accepting uncontracted features mid-sprint (erodes margins & breaks milestone dates), or promising deterministic PERT average as hard legal deadline despite parallel merge bias.
  **RIGHT:** Triage strictly via Contractual Precedence -> emit `PAID_CR` to CCB -> commit external milestones at Monte Carlo `P80` while managing teams to `P50`.
- **WRONG (Building bespoke PMO Word/PDF generators inside scripts):** Duplicating `.docx` exporters inside PMO scripts.
  **RIGHT:** Route `PROJECT_REPORT` / `CHANGE_REQUEST` deliverables cleanly via `shadow-doc/scripts/doc_orchestrator.py`.

## 6. Production Considerations
- **Official Deliverables:** Structure formal consulting outputs (*Laporan Pendahuluan, Laporan Antara, Laporan Akhir*) strictly around auditable EVM trends, CCB-signed CR logs, and RAID owners.
