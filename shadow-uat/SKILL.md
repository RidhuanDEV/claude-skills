---
name: shadow-uat
description: User Acceptance Testing (UAT) Governance: Requirement Traceability Matrix (RTM), UAT Test Scenarios from Acceptance Criteria, Defect Triage Log, Evidence Capture, Retest Verification, and Client Sign-Off (Staging UAT -> Production Release -> Production Smoke Test). Trigger with /shadow-uat.
---

# Shadow UAT (`/shadow-uat`) — Requirement Traceability, Staging UAT & Client Sign-Off

Automated unit tests prove the code works as written; **`/shadow-uat` proves the application solves the client's actual business requirement**. Use this skill to prepare, execute, track, and sign off User Acceptance Testing.

---

## 1. Staging-First UAT Execution Flow

> [!IMPORTANT]
> **Standard Safe Delivery Order**:
> 1. **Staging UAT**: Deploy candidate release to **Staging** (with realistic anonymized/seed data) and execute full UAT scenarios with client/QA testers.
> 2. **Defect Fix & Retest Loop**: Triage UAT findings (`Blocker/Critical/Major/Minor`), patch, run regression tests (`/shadow-test`), and re-verify in Staging until all P0/P1 criteria pass.
> 3. **Production Go-Live Approval**: Once Staging UAT is signed off, execute `/shadow-release` to deploy to Production.
> 4. **Production Post-Deploy Smoke / Acceptance Check**: Run non-destructive production smoke verification (and final production UAT sign-off if required by government/enterprise contract).

---

## 2. Mandatory UAT Artifacts (Compatible with `/shadow-doc` -> `.docx` & `.xlsx`)

### A. Requirement Traceability Matrix (`RTM`)
Every Functional Requirement (`FR-*`) from `/shadow-discovery` MUST map to at least one UAT Scenario (`UAT-*`) and automated test:

| Req ID | Requirement Summary | Role / Actor | UAT Scenario ID | Precondition & Test Data | Expected Business Outcome | Evidence File | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `FR-ORD-01` | Submit purchase order for approval | `Operator` | `UAT-ORD-001` | Active vendor & budget $\ge$ Rp 10.000.000 | Status changes to `WAITING_APPROVAL`; approver notified | `bukti/uat-ord-001.png` | `PASS` |

### B. UAT Scenario Structure (Business Language, Not Code Jargon)
Write UAT steps in clear, human-readable operational language for client testers:
- **Scenario ID & Title** (`UAT-MOD-001`)
- **Business Objective & Acceptance Criteria**
- **Test Role & Login Account**
- **Step-by-Step User Actions & Input Values**
- **Expected Result (Screen Display + Document/Notification/Status Outcome)**
- **Actual Result, Screenshot Evidence (`bukti/*.png`), Tester Name, Date & Verdict (`DITERIMA` / `REVISI`)**

### C. UAT Defect & Change Request (CR) Triage Log
During UAT, strictly separate **Defects (Bugs)** from **New Scope / Change Requests (CR)**:
- **Defect (Bug)**: Behavior deviates from agreed PRD/SRS (`FR-*`) -> Fix immediately before sign-off.
- **Change Request (CR)**: Client requests a new field/workflow not in the agreed SRS -> Log in the CR backlog with impact analysis so UAT sign-off of the current scope is not derailed.

---

## 3. UAT Exit Gate Checklist (To Unlock Production Release / `/shadow-handover`)
- [ ] $100\%$ of P0/P1 requirements mapped in the Requirement Traceability Matrix (`RTM`).
- [ ] Zero open `Blocker` or `Critical` UAT defects.
- [ ] All UAT scenarios have verified screenshot/document evidence attached.
- [ ] Formal UAT Sign-Off sheet (`Berita Acara UAT`) ready for client signature.
