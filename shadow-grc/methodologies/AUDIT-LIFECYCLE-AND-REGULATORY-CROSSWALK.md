# Audit Lifecycle, Control Testing & Regulatory Crosswalk Methodology

## 1. Risk-Based Audit Lifecycle

1. **Scoping & Audit Universe**: Define systems, third-party vendors (`PPJTI`), legal entities, and regulatory boundaries (`SPBE`, `OJK`, `UU PDP`, `ISO 27001`).
2. **Risk Methodology**: Calibrate **Risk Appetite**, **Inherent Risk** (`Likelihood x Impact` before controls), **Control Effectiveness**, and **Residual Risk** (`Accept`, `Mitigate`, `Transfer`, `Avoid`).
3. **Sampling & Evidence Sufficiency**: Require primary corroboration (system config, immutable logs, signed minutes, CI records) — never treat verbal interview answers alone as `HIGH` confidence evidence.
4. **6-Part Defensible Finding Structure**:
   - **Criteria**: Specific statutory/standard clause (`PADK OJK 1/2026`, `ISO 27001 Clause 8.2`, `UU PDP Pasal 35`).
   - **Condition**: Observed gap with exact location/sample rate.
   - **Cause**: Root governance, process, or technical failure.
   - **Effect / Risk**: Business, operational, legal, or financial impact.
   - **Recommendation**: Actionable, owner-assigned remediation.
   - **Evidence Reference**: Verifiable `EVD-*` hash/path + confidence & limitations.

---

## 2. Control Testing: Design vs Operating Effectiveness

| Test Type | Question Answered | Typical Evidence |
|---|---|---|
| **Design Effectiveness (DE)** | If operated as intended, does the control mitigate the risk and satisfy the regulation? | Written SOP, RBAC matrix, system architecture config, contract DPA clauses |
| **Operating Effectiveness (OE)** | Did the control actually operate consistently across the audit period? | Sampled change tickets, access review sign-offs, SIEM alert logs, backup restore logs |

An implemented control with `DE = PASS` and `OE = FAIL` is **NOT effective**.

---

## 3. Framework Accuracy Rules

### COBIT 2019 (40 Objectives across 5 Domains)
- Domains: `EDM` (5), `APO` (14), `BAI` (11), `DSS` (6), `MEA` (4).
- **Capability vs Maturity Separation**:
  - **Capability Level (0–5)** measures how well a **single Governance/Management Objective process** performs (Levels 0 Incomplete .. 5 Optimizing).
  - **Maturity Level (0–5)** evaluates the **enterprise/focus area holistically** across multiple interrelated objectives. Do not average arbitrary objective scores into one headline maturity claim without explicit domain weighting and target-state criteria.

### ISO/IEC 27001:2022 (Clauses 4–10 + 93 Annex A Controls)
- **Mandatory ISMS Management Clauses (4–10)**: Clause 4 Context, Clause 5 Leadership, Clause 6 Planning (Risk Assessment & Treatment), Clause 7 Support, Clause 8 Operation, Clause 9 Performance Evaluation (Internal Audit & Management Review), Clause 10 Improvement.
- **93 Annex A Controls**:
  - Clause 5 **Organizational**: `37` controls (`A.5.1`–`A.5.37`)
  - Clause 6 **People**: `8` controls (`A.6.1`–`A.6.8`)
  - Clause 7 **Physical**: `14` controls (`A.7.1`–`A.7.14`)
  - Clause 8 **Technological**: `34` controls (`A.8.1`–`A.8.34`)
- **Statement of Applicability (SoA)**: Must justify every included/excluded control and record actual implementation status backed by DE + OE evidence.

### Indonesian Banking (`POJK 11/POJK.03/2022` & `PADK OJK No. 1 Tahun 2026`)
- **PADK OJK No. 1 Tahun 2026** (enacted 23 January 2026, effective **1 March 2026**) implements POJK 11/POJK.03/2022 and **revokes `SEOJK 21/SEOJK.03/2017`**.
- Key assurance areas: Direksi/Komisaris/Komite Pengarah TI accountability, IT Architecture & RSTI stages, cyber risk & communication security, **PPJTI (Third-Party IT Service Provider) due diligence & materiality re-assessment (including offshore supervisory access)**, PDP alignment (`UU 27/2022`), and DC/DRC placement licensing & reporting.

### Regulatory Crosswalk Summary
| Control Theme | COBIT 2019 | ISO 27001:2022 | SPBE / Indeks KAMI | UU PDP / OJK Banking |
|---|---|---|---|---|
| **IT & Security Governance** | `EDM01`, `APO01` | `Clauses 4, 5, 7` | Tata Kelola Keamanan | `PADK OJK 1/2026` (Direksi/Komite TI) |
| **Risk & DPIA** | `EDM03`, `APO12` | `Clause 6.1, 8.2, 8.3` | Manajemen Risiko SPBE | `UU PDP Pasal 34`, `POJK 11/2022` |
| **Access & Cyber Tech** | `APO13`, `DSS05` | `A.5.15`, `A.8.1–A.8.34` | Pengamanan Teknis | `UU PDP Pasal 35`, `PADK OJK 1/2026` |
| **Vendor / PPJTI Risk** | `APO10` | `A.5.19–A.5.23` | Suplemen Pihak Ketiga | `UU PDP Pasal 51–52`, `PADK OJK 1/2026` PPJTI |
| **Incident & Breach** | `DSS02` | `A.5.24–A.5.28` | Penanganan Insiden | `UU PDP Pasal 46` (3x24h), `OJK` incident report |
