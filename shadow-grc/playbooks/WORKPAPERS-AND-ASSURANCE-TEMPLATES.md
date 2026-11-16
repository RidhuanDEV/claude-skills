# GRC Workpapers & Assurance Deliverable Templates

## 1. Audit Workpaper Header
- `Engagement ID` · `Audit Period` · `Scope & Systems` · `Applicable Regulations` · `Limitations / Unaccessible Evidence` · `Preparer` · `Independent Reviewer`.

## 2. Control Test Sheet (Design vs Operating Effectiveness)
| Control ID | Standard / Regulation Ref | Control Owner | Design Test Result (`PASS/FAIL`) | Sample Size & Population | Operating Test Result (`PASS/FAIL`) | Evidence Refs (`EVD-*`) | Exception Notes |
|---|---|---|---|---:|---|---|---|

## 3. ISO/IEC 27001:2022 Statement of Applicability (SoA) Matrix
| Control ID | Theme (`Org/People/Phys/Tech`) | Applicable (`Y/N`) | Inclusion / Exclusion Justification | Status (`Implemented/Partial/Planned`) | DE + OE Evidence Refs |
|---|---|---|---|---|---|

## 4. 6-Part Audit Finding Record
```yaml
finding_id: GRC-BNK-001
criteria: "PADK OJK No. 1/2026 & POJK 11/POJK.03/2022 (PPJTI Materiality Re-assessment)"
condition: "2 out of 5 material cloud/payment vendors lack annual materiality & exit-plan review."
cause: "Procurement vendor tracker is disconnected from IT Risk & Compliance register."
effect_risk: "Regulatory non-compliance risk and unmitigated operational concentration failure."
recommendation: "Establish semi-annual PPJTI materiality review gate before contract renewal."
evidence_refs: ["EVD-VEND-01", "EVD-VEND-02"]
confidence: HIGH
management_response_owner: "Head of IT Governance & Procurement"
target_remediation_date: "2026-12-31"
```

## 5. Evidence Sufficiency Matrix & Executive Assurance Report
Distinguish **Verified by Primary Evidence**, **Corroborated via Interview Only (Low Confidence)**, and **Evidence Missing / Not Tested**. Never issue an unqualified assurance or certification claim when critical evidence is missing.
