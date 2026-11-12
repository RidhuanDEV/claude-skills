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

### D. Intended-vs-Implemented Drift Audit & 12-Domain Adversarial Scenarios
Before handing the Staging environment to client testers, run an internal **Intended-vs-Implemented Audit** ([`pm-ai-shipping/commands/ship-check.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/pm-skills/pm-ai-shipping/commands/ship-check.md), [`design-qa-checklist/SKILL.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/designer-skills/design-ops/skills/design-qa-checklist/SKILL.md), and [`pm-execution/skills/test-scenarios/SKILL.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/pm-skills/pm-execution/skills/test-scenarios/SKILL.md)):
1. **State Machine Parity**: Verify all **9 UI states** specified in `FEATURE-DESIGN.md` exist in the live build (including distinct Empty vs No-Results vs Error states, `403` Permission-Denied, Offline, and `409`/`ETag` Stale Conflict recovery).
2. **Async (`HTTP 202`) Honesty**: Verify background jobs show `Submitted / Queued / Processing` and never display a premature green `"Completed"` toast before worker indexing/settlement finishes.
3. **Adversarial & Double-Submit Protection**: Verify double-clicking submit, refreshing mid-flight, or submitting invalid fields preserves user input and prevents duplicate records.
4. **Privacy-Safe Outcome Telemetry (HEART / GSM)**: Verify success and error instrumentation events ([`ghaida-intent/skills/measure/SKILL.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/ghaida-intent/skills/measure/SKILL.md)) fire without logging raw PII or secrets.

---

## 3. UAT Exit Gate Checklist (To Unlock Production Release / `/shadow-handover`)
- [ ] $100\%$ of P0/P1 requirements mapped in the Requirement Traceability Matrix (`RTM`: `FR-ID -> US-ID -> FLOW-ID -> SCR/STATE-ID -> UAT-ID -> TEST-ID`).
- [ ] Intended-vs-Implemented Drift Audit passed (all 9 states and `HTTP 202` async contracts verified).
- [ ] Zero open `Blocker` or `Critical` UAT defects (Severity-First Gate: critical blockers override any numeric score).
- [ ] All UAT scenarios have verified screenshot/document evidence attached (`NOT TESTED` explicitly labeled if any manual check was skipped).
- [ ] Formal UAT Sign-Off sheet (`Berita Acara UAT`) ready for client signature.
