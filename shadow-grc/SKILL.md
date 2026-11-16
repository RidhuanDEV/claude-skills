---
name: shadow-grc
description: "Evidence-Based IT Governance, Risk & Regulatory Assurance. Use when auditing COBIT 2019 (Capability vs Maturity), ISO/IEC 27001:2022 (Clauses 4-10 + 93 Annex A SoA), SPBE & Indeks KAMI BSSN, or banking IT rules (POJK 11/2022 & PADK OJK 1/2026)."
---

# `/shadow-grc` — Evidence-Based Governance & Regulatory Assurance

Use this skill whenever the **Monarch** invokes `/shadow-grc`, executes IT governance/security readiness assessments, designs risk registers, builds a Statement of Applicability (`SoA`), or prepares audit workpapers for Banking, Government SPBE, BUMN, or Enterprise engagements.

Integrates with [`shadow-monarch/reference/CONSULTING-INTELLIGENCE-CORE.md`](../shadow-monarch/reference/CONSULTING-INTELLIGENCE-CORE.md) and deep methodologies:
- [`methodologies/AUDIT-LIFECYCLE-AND-REGULATORY-CROSSWALK.md`](methodologies/AUDIT-LIFECYCLE-AND-REGULATORY-CROSSWALK.md) — Risk-based audit lifecycle, Design vs Operating control testing, COBIT 2019 capability vs maturity rules, ISO/IEC 27001:2022 Clauses 4–10 + 93 Annex A controls, SPBE/Indeks KAMI, and **POJK 11/POJK.03/2022 + PADK OJK Nomor 1 Tahun 2026**.
- [`playbooks/WORKPAPERS-AND-ASSURANCE-TEMPLATES.md`](playbooks/WORKPAPERS-AND-ASSURANCE-TEMPLATES.md) — Audit Workpaper, Regulatory Obligations Register, Control Test Sheet, SoA Matrix, Evidence Sufficiency Matrix, Management Action Plan, and Executive Assurance Report.

---

## 1. Execution Contract (Evidence & Regulatory Precision)

1. **Context & Regulatory Applicability First**: Query `consulting_core.py --check-regulations` for the client's sector.
   - For Indonesian Banking after **1 March 2026**, apply **POJK 11/POJK.03/2022** + **PADK OJK No. 1 Tahun 2026** (never cite revoked `SEOJK 21/SEOJK.03/2017` as active).
   - For SPBE/Government, verify exact **Indeks KAMI BSSN** workbook version before scoring.
2. **Full Audit Lifecycle & Control Testing**:
   - Follow `Scoping -> Audit Universe -> Risk-Based Plan -> Evidence Request (PBC) -> Sampling Rationale -> Fieldwork -> 6-Part Finding -> Management Response -> Remediation & Follow-Up`.
   - Test **Design Effectiveness** (does the policy/control address the risk?) separately from **Operating Effectiveness** (evidence of consistent execution across sampled periods).
3. **Methodological Precision**:
   - **COBIT 2019**: Evaluate **Process Capability (0–5 per objective)** separately from **Focus Area Maturity (0–5 systemic aggregate)** — never collapse both into one unverified number.
   - **ISO/IEC 27001:2022**: Cover **Management System Clauses 4–10** alongside the **93 Annex A Controls** (`37` Organizational, `8` People, `14` Physical, `34` Technological) with explicit SoA justification for inclusions/exclusions.
   - Respect copyright boundaries: map and reference standards legitimately without reproducing proprietary full text.
4. **6-Part Defensible Findings & Escalation Boundary**:
   - Every finding MUST carry: `Criteria`, `Condition`, `Cause`, `Effect/Risk`, `Recommendation`, and `Evidence Ref` + confidence level.
   - Never declare an organization officially "ISO 27001 Certified" or "Regulator Approved" based on internal/advisory self-assessment.

---

## 2. Deterministic Assurance Engine

```powershell
python "shadow-grc/scripts/grc_assurance_engine.py" --self-test
python "shadow-grc/scripts/grc_assurance_engine.py" --assess-cobit path/to/cobit_scores.json
python "shadow-grc/scripts/grc_assurance_engine.py" --validate-soa path/to/iso27001_soa.json
python "shadow-grc/scripts/grc_assurance_engine.py" --validate-findings path/to/findings.json --sector BANKING
```
