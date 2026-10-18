# IT-PMO-GOVERNANCE — IT Project Management, Agile/Scrum, ITSM/ITIL & Governance/Compliance

Use when planning or managing IT projects, writing Work Breakdown Structures (WBS), sprint plans, RAID logs, Change
Requests (CR/RFC), SLA/OLA contracts, vendor/RFP evaluations, or conducting IT Governance, Risk & Compliance (GRC)
audits (UU PDP Indonesia, ISO 27001, SOC 2, ITIL). Pair with `PRODUCT-ANALYSIS.md` for product/functional specs.

## 1. Project planning, WBS & estimation (IT PM / PMO)

- **Work Breakdown Structure (WBS) discipline**:
  - Decompose work into deliverable-oriented phases: `1. Discovery & Analysis → 2. Design & Architecture → 3. Backend/DB Implementation → 4. Frontend/Mobile Implementation → 5. Integration & QA/UAT → 6. Deployment, Cutover & Hypercare`.
  - Every WBS task must have a **single accountable owner role**, **clear completion deliverable (Definition of Done)**,
    **predecessor dependencies**, and **effort estimate** (Optimistic $O$, Most Likely $M$, Pessimistic $P$, PERT $= \frac{O + 4M + P}{6}$).
- **Buffer & critical path**: account for code review, QA bug-fix cycles, security/UAT sign-off, and environment setup
  (never estimate 100% pure coding hours; realistic productive focus is ~6 hours/day).
- **RAID Log (Risks, Assumptions, Issues, Dependencies)**:
  - Structure as a table: `ID | Category (R/A/I/D) | Description | Impact (High/Med/Low) | Probability | Mitigation / Contingency Plan | Owner | Target Date | Status`.

## 2. Agile / Scrum & Engineering Delivery (Scrum Master / EM)

- **Definition of Ready (DoR)** before a ticket enters a Sprint:
  - User story + Gherkin Acceptance Criteria complete, UI/UX states ready, API/DB contract agreed, external blockers cleared,
    and story sized small enough to finish within $\le 3$–$5$ days.
- **Definition of Done (DoD)** before a ticket closes:
  - Code implemented with strict types and zero dead code, peer reviewed, unit/integration tests passing, documentation/specs
    updated, verified in staging, and accepted against all ACs.
- **Sprint metrics**: track **Sprint Goal completion**, **Cycle Time**, **Blocked Time**, and **Escaped Defect Rate** — never
  weaponize raw Story Point velocity across different teams.

## 3. ITSM / ITIL: Change, Incident & Problem Management

- **Request for Change (RFC) / Production Cutover Plan**:
  Every high-impact production release or DB migration document must specify:
  1. **Change Summary & Business Justification** (`Standard`, `Normal`, or `Emergency` change).
  2. **Blast Radius & Affected Systems / Downtime Window**.
  3. **Pre-Implementation Checklist** (backup verified, dry-run completed, feature flag ready, on-call notified).
  4. **Step-by-Step Execution Runbook** (with exact timestamps, commands, and executor role).
  5. **Verification / Smoke Test Criteria** (how we know it succeeded within 15 minutes).
  6. **Rollback Trigger & Step-by-Step Rollback Plan** (exact time cutoff when rollback is mandatory).
- **SLA / OLA / KPI Matrix**:
  - Define severity tiers (`P1 Critical / Outage`, `P2 High / Major Degradation`, `P3 Medium`, `P4 Low`) with explicit
    **Response Time**, **Update Frequency**, **Resolution/Mitigation Target**, and **Escalation Path**.

## 4. Change Request (CR) & Scope Governance (Vendor / Client Projects)

When evaluating a new client/stakeholder request mid-project:
- Classify whether it is an **In-Scope Defect** (fails signed FSD/SRS) or a **Change Request (CR)** (new field, new rule,
  new workflow, or altered contract).
- Document a formal **CR Impact Assessment**: `CR ID | Requested Change | Affected Modules (DB/API/FE/Mobile/Docs) | Effort (Man-Days) | Schedule Impact | Cost Impact | Technical Risk | Recommendation`.

## 5. IT Governance, Risk & Compliance (UU PDP Indonesia, ISO 27001, SOC 2)

- **Data Privacy (UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi / GDPR)**:
  - **Data Classification**: classify fields into *Public*, *Internal*, *Confidential*, and *Specific/Sensitive Personal Data*
    (finance, health, biometrics, NIK, children's data).
  - **Lawful Basis & Consent**: record explicit, revocable user consent (`timestamp`, `policy_version`, `purpose`).
  - **Data Subject Rights**: architecture must support right to access, correction, data portability, deletion/anonymization
    (with legal retention exceptions for financial/tax ledgers), and breach notification readiness ($3 \times 24$ hours under UU PDP).
- **Access Control & Segregation of Duties (SoD) (ISO 27001 / SOC 2)**:
  - Developers do not have unlogged write access to production databases; production changes go through reviewed CI/CD or
    audited break-glass procedures.
  - Maker-Checker (four-eyes principle) for sensitive actions: financial payouts, role grants, parameter changes.
  - Immutable audit logs (`who`, `what`, `when`, `source_ip`, `before_value`, `after_value`) retained per regulatory policy.

## 6. Anti-patterns

Estimating coding time only with zero QA/UAT/deployment buffer · starting a sprint with vague stories lacking API contracts ·
production cutover with "we will fix forward if it breaks" and no rollback cutoff time · treating scope changes as free bug
fixes without a CR impact assessment · storing sensitive PII without consent records, retention limits, or audit trails.
