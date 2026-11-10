---
name: shadow-maintain
description: Post-Production Maintenance, Bug Triage, Incident Root-Cause Analysis (Blameless Postmortem / RCA), Hotfix Workflow, Security Patch Management, SLA Tracking, and Maintenance Backlog Governance (Harwat / OMKT). Trigger with /shadow-maintain.
---

# Shadow Maintain (`/shadow-maintain`) — Post-Production Maintenance (Harwat), Incident RCA & SLA Governance

Use this skill after go-live during the warranty or **Pemeliharaan & Perawatan (Harwat / OMKT)** phase to manage production incidents, hotfixes, dependency patching, and monthly SLA reporting.

---

## 1. Severity Classification & SLA Response Matrix

| Severity | Definition | Response / Triage Target | Mitigation / Hotfix Target |
| :--- | :--- | :--- | :--- |
| **P0 / Sev-1 (Critical Outage)** | Production down, login/payment/core workflow completely blocked, or active security/data breach. | `< 15 minutes` | Rollback or hotfix within `< 1–2 hours` |
| **P1 / Sev-2 (Major Degradation)** | Core feature broken for a subset of users/tenants with no easy workaround, or severe latency spike. | `< 30 minutes` | Fix deployed within `< 4–8 hours` |
| **P2 / Sev-3 (Moderate Bug)** | Non-critical bug or edge case with an operational workaround available. | `< 4 business hours` | Scheduled in next regular patch release (`< 3–5 days`) |
| **P3 / Sev-4 (Minor / Cosmetic / Enhancement)** | UI alignment, wording tweak, or minor UX improvement. | Next backlog grooming | Scheduled in monthly maintenance sprint |

---

## 2. Production Hotfix Protocol (Zero-Regression Emergency Fix)

When a `P0` or `P1` bug requires an urgent production fix:
1. **Stabilize First**: If caused by the latest deploy, roll back immediately (`/shadow-release`) before debugging code.
2. **Reproduce & Pinpoint Root Cause**: Trace using `requestId` logs (`/shadow-observe`) and separate **Symptom**, **Contributing Factor**, and **Root Cause**.
3. **Minimal Surgical Patch + Regression Test**:
   - Write the smallest possible fix on a clean hotfix branch (`fix/hotfix-<issue>`).
   - **Mandatory**: Add a regression test (`/shadow-test`) that fails without the fix and passes with the fix so the exact bug can never return silently.
4. **Verify & Document in Maintenance Log**:
   - Record the commit SHA, before/after evidence screenshots, and resolution summary for the monthly **Laporan Harwat** (`/shadow-doc`).

---

## 3. Blameless Incident Postmortem (RCA Template)

After every `P0` or `P1` incident, generate `docs/incidents/RCA-YYYY-MM-DD-<slug>.md`:
- **Incident Summary & Customer Impact** (Duration, affected requests/tenants, error budget consumed).
- **Timeline (UTC / WIB)** (Detection time, escalation, mitigation applied, full recovery verified).
- **Root Cause & 5-Whys Analysis** (Focus on systemic/architectural gaps, never blaming individuals).
- **What Went Well vs What Went Wrong** (Why didn't automated tests or staging catch it?).
- **Corrective & Preventive Action Items** (Concrete tasks with owner and priority: e.g., new alert rule, DB constraint, regression test).

---

## 4. Routine Preventive Maintenance Checklist (Monthly Harwat Cycle)
- **Corrective Maintenance**: Resolving reported bugs/tickets with commit & screenshot evidence.
- **Adaptive Maintenance**: OS/runtime security patches, expiring TLS certificate checks, third-party API adjustments.
- **Perfective Maintenance**: Slow query index tuning (`/shadow-db`), disk/log cleanup, dependency security updates (`npm/pip/composer audit`), and monthly restore drill (`/shadow-resilience`).
