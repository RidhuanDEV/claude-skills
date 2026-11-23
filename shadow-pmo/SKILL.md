---
name: shadow-pmo
description: "Contractual IT Delivery & PMO Governance. Use when triaging client requests across contractual hierarchy (Contract/Addendum/KAK/SOW/FSD) as Defect vs Paid CR candidate, computing PERT + CPM + Monte Carlo (P50/P80/P90), EVM (CPI/SPI), or Laporan Proyek."
---

# `/shadow-pmo` — Contractual & Delivery Governance

Use this skill whenever the **Monarch** invokes `/shadow-pmo`, evaluates a mid-project client request (Defect vs Paid CR), builds WBS & PERT/CPM schedules, runs P50/P80 schedule risk simulations, tracks Earned Value (`CPI`/`SPI`), or prepares **Laporan Pendahuluan / Antara / Akhir** and **BAST** acceptance packages.

Integrates with [`shadow-monarch/reference/CONSULTING-INTELLIGENCE-CORE.md`](../shadow-monarch/reference/CONSULTING-INTELLIGENCE-CORE.md) and deep methodologies:
- [`methodologies/CONTRACTUAL-GOVERNANCE-AND-SCHEDULE-RISK.md`](methodologies/CONTRACTUAL-GOVERNANCE-AND-SCHEDULE-RISK.md) — Contractual document precedence, CR decision logic, PERT + Critical Path + Monte Carlo P50/P80/P90, and EVM math.
- [`playbooks/PMO-DELIVERABLES-AND-CR-TEMPLATES.md`](playbooks/PMO-DELIVERABLES-AND-CR-TEMPLATES.md) — Scope Baseline Register, CR Decision Record, Schedule Impact Assessment, RAID Log, Earned Value Dashboard, and Acceptance Evidence Pack.

---

## 1. Execution Contract (No Unauthorized Legal Verdicts)

1. **Contractual Precedence Before CR Classification**:
   - Never classify a client request as `IN_SCOPE_DEFECT` or `PAID_CHANGE_REQUEST` solely by comparing SRS text.
   - Always evaluate against the full **Contractual Hierarchy**: `Master Contract & Change Clauses -> Approved Addendum -> KAK / SOW -> Signed FSD / SRS -> UAT Baseline & Warranty Clauses`, plus **implicit statutory/baseline obligations**.
   - Any recommendation impacting commercial billing (`PAID_CHANGE_REQUEST_CANDIDATE`) MUST explicitly route through **Change Control Board (CCB) / Contract Counsel / Authorized Client PPK or Sponsor** (`requires_human_approval: true`).
2. **Schedule & Risk Engineering (PERT + CPM + Monte Carlo)**:
   - Compute activity expected duration $E = \frac{O + 4M + P}{6}$ and $\sigma = \frac{P - O}{6}$ across dependency DAGs.
   - Compute deterministic **Critical Path (`ES`, `EF`, `LS`, `LF`, `Total Float`)** AND run **Monte Carlo simulation** (fixed seed for reproducibility) to report realistic **`P50` / `P80` / `P90` completion dates** rather than naive summed averages.
3. **Earned Value & Traceable Audit Trail**:
   - Track `PV`, `EV`, `AC`, `CPI = EV/AC`, `SPI = EV/PV`, and `EAC`, plus an immutable `CR Decision Record` linking request -> baseline reference -> impact assessment -> CCB sign-off.

---

## 2. Deterministic PMO Governance Engine

```powershell
python "shadow-pmo/scripts/pmo_governance_engine.py" --self-test
python "shadow-pmo/scripts/pmo_governance_engine.py" --analyze-schedule path/to/wbs_dag.json
python "shadow-pmo/scripts/pmo_governance_engine.py" --evaluate-cr path/to/cr_request.json
```

## 3. Document Rendering Boundary (`SA-DOC-ENGINE-001`)

- `/shadow-pmo` owns PERT/CPM/Monte Carlo/EVM calculations and CR contractual governance; NEVER duplicate `.docx`/`.pdf`/`.html` rendering inside `pmo_governance_engine.py`.
- Route formal `PROJECT_REPORT` / `CHANGE_REQUEST` deliverables through `shadow-doc/scripts/doc_orchestrator.py` (reusing existing repo generators first, or bridging PMO JSON outputs via `domain_adapters.py::adapt_pmo_or_ea_payload`).

## Reference Guide

Load only the specific playbook or methodology matching your active PMO governance subtask:

| Task / Scenario | Load Reference |
| :--- | :--- |
| 5-Rank Contractual Precedence Hierarchy, Defect vs `PAID_CR` Candidate Triage & CCB/PPK Escalation | [references/01-contractual-precedence-and-defect-vs-paid-cr-triage.md](references/01-contractual-precedence-and-defect-vs-paid-cr-triage.md) |
| Three-Point PERT (`O/M/P`), CPM Merge Bias, Cycle Validation & Seeded Monte Carlo (`P50`/`P80`/`P90`) | [references/02-pert-cpm-merge-bias-and-monte-carlo-p50-p80-p90.md](references/02-pert-cpm-merge-bias-and-monte-carlo-p50-p80-p90.md) |
| Earned Value Management (`CPI`/`SPI`/`EAC`/`VAC`), RAID Attribution & Institutional Project Reports | [references/03-evm-tracking-raid-governance-and-project-reporting.md](references/03-evm-tracking-raid-governance-and-project-reporting.md) |
| Deep Methodology & PMO Templates | [methodologies/CONTRACTUAL-GOVERNANCE-AND-SCHEDULE-RISK.md](methodologies/CONTRACTUAL-GOVERNANCE-AND-SCHEDULE-RISK.md) & [playbooks/PMO-DELIVERABLES-AND-CR-TEMPLATES.md](playbooks/PMO-DELIVERABLES-AND-CR-TEMPLATES.md) |
| Deterministic PMO Governance Engine & Specialist Eval Suite | [scripts/pmo_governance_engine.py](scripts/pmo_governance_engine.py) & [evaluations.md](evaluations.md) |

Do not load unrelated references unnecessarily.
