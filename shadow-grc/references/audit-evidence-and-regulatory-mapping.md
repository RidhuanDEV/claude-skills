# Audit Evidence, COBIT/ISO 27001 & Sectoral Regulatory Assurance Playbook

> Use this playbook when conducting IT governance audits (`COBIT 2019`), `ISO/IEC 27001:2022` ISMS/SoA reviews, Indonesia `SPBE / Indeks KAMI BSSN` assessments, or banking IT compliance (`POJK 11/2022` + `PADK OJK 1/2026`).

## 1. Core Concepts
Evidence-based IT assurance separates **whether a control exists on paper (`Design Effectiveness`)** from **whether staff/systems execute it consistently over time (`Operating Effectiveness`)**:
- **Dated Regulatory Baseline (`as_of_date`):** Always evaluate compliance against regulations active on the assessment date (e.g., effective **1 March 2026**, **`PADK OJK 1/2026`** operationalizes `POJK 11/2022` and revokes **`SEOJK 21/2017`** for Commercial Bank IT Governance, ATI/RSTI, PPJTI outsourcing due diligence & OJK inspection access, and UU PDP alignment).
- **Zero Self-Certification Claim:** Internal/consulting readiness reviews MUST NOT declare official ISO 27001 certification without an accredited certification body audit report.

## 2. Technical Rules & Decision Matrix

| Framework / Sector | Structural Rules | Evidence Verdict Gate |
| :--- | :--- | :--- |
| **COBIT 2019** | Assess **Process Capability (`0–5`)** per objective separately from **Focus Area Maturity (`0–5`)** (`min` critical objective threshold) | `evidence_confidence = HIGH` requires `>= 2` verified artifacts per objective |
| **ISO/IEC 27001:2022** | Cover **Clauses 4–10** + **93 Annex A Controls** (`37` Organizational, `8` People, `14` Physical, `34` Technological) with SoA justifications | `IMPLEMENTED` requires BOTH `design_evidence_ref` AND `operating_evidence_ref` |
| **Banking IT (Indonesia)** | **`POJK 11/2022` + `PADK OJK 1/2026`** (revokes `SEOJK 21/2017` effective 2026-03-01) | Check ATI/RSTI, PPJTI vendor materiality & OJK access rights, PDP/cyber resilience |
| **Public Sector (Indonesia)** | **SPBE (`Perpres 95/2018` & `132/2022`) + Indeks KAMI BSSN** | Require score + primary evidence log; policy PDF alone only proves Design Effectiveness |

## 3. Implementation Examples

### 6-Part Audit Finding & Incomplete Quarterly Sample (`grc_assurance_engine.py`)
```json
{
  "assessment_as_of_date": "2026-04-15",
  "sector": "BANKING",
  "active_regulations": ["POJK 11/POJK.03/2022", "PADK OJK No. 1/2026", "UU No. 27/2022 (UU PDP)"],
  "findings": [
    {
      "finding_id": "GRC-BNK-004",
      "criteria": "PADK OJK 1/2026 PPJTI Vendor Materiality & ISO 27001:2022 A.5.19",
      "condition": "Vendor security policy approved (DE); Q2 access-review sample incomplete (only 1 of 3 months collected).",
      "cause": "Automated IAM quarterly extract job disabled during cloud migration.",
      "consequence": "Operating effectiveness of privileged PPJTI vendor offboarding cannot be verified across the full audit period.",
      "corrective_action": "Re-enable automated IAM review log retention and complete Q2/Q3 population sampling.",
      "design_effectiveness": "EFFECTIVE",
      "operating_effectiveness": "PENDING_SAMPLE",
      "evidence_ref": "docs/audit/2026-q2/ppjti-policy-v2.pdf"
    }
  ]
}
```
```powershell
python "shadow-grc/scripts/grc_assurance_engine.py" --validate-soa iso27001_soa.json
python "shadow-grc/scripts/grc_assurance_engine.py" --validate-findings findings.json --sector BANKING --as-of-date 2026-04-15
```

## 4. Best Practices
- Enforce the **6-Part Finding Discipline**: every audit finding MUST state `Criteria | Condition | Cause | Consequence | Corrective Action | Evidence Ref` without fabricating log IDs.
- Validate ISO 27001 Annex A exclusions strictly against Clauses 4–10 risk assessments (`"not applicable"` requires written justification, never blank cells).

## 5. Anti-Patterns (`WRONG` vs `RIGHT`)
- **WRONG (Marking `OE = EFFECTIVE` from policy PDFs or citing revoked rules):** Concluding "Quarterly Access Review is Operating Effectively" from an SOP document alone, or citing `SEOJK 21/2017` for post-March-2026 Indonesian banking IT audits.
  **RIGHT:** Separate `design_effectiveness = EFFECTIVE` vs `operating_effectiveness = PENDING_SAMPLE` until multi-period samples are inspected, and anchor post-March-2026 banking audits to **`POJK 11/2022` + `PADK OJK 1/2026`**.
- **WRONG (Conflating COBIT Process Capability with Maturity or declaring official ISO certification):** Averaging scores into fake maturity levels or stamping "Officially ISO 27001 Certified" inside a gap-assessment report.
  **RIGHT:** Track Capability (`0–5`) per objective, derive Focus Area Maturity conservatively, and label self-assessments strictly as readiness / gap findings.

## 6. Production Considerations
- **Document Boundary:** Render formal GRC deliverables through `shadow-doc/scripts/doc_orchestrator.py` (`adapt_grc_payload`) so every `evidence_ref` remains traceable across Word/PDF exports.
