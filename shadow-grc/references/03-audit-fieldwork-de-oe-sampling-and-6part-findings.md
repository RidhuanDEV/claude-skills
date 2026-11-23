# 03. Risk-Based Audit Fieldwork, DE vs OE Sampling & 6-Part Defensible Findings

## 1. Purpose & Activation Conditions
Use this playbook when planning audit fieldwork, issuing PBC (Provided-By-Client) evidence requests, testing **Design Effectiveness (DE)** separately from **Operating Effectiveness (OE)** across defined populations and samples, and authoring audit-committee-grade **6-Part Findings** ready for rendering via `/shadow-doc`.

Activate this playbook when:
- Executing internal IT audit fieldwork or pre-certification readiness testing.
- Determining whether available client documents prove only `DE` (policy exists) or genuine `OE` (consistent execution across the audit period).
- Writing defensible findings and Management Action Plans (MAP) that survive external auditor or regulator scrutiny.

## 2. Prerequisites
- Defined Audit Universe, risk-based scoping, jurisdiction, `as_of_date`, and evidence review period (`start_date..end_date`).
- Companion templates in [`../playbooks/WORKPAPERS-AND-ASSURANCE-TEMPLATES.md`](../playbooks/WORKPAPERS-AND-ASSURANCE-TEMPLATES.md) and deterministic validator [`../scripts/grc_assurance_engine.py`](../scripts/grc_assurance_engine.py).

## 3. Technical Principles & Constraints
1. **End-to-End 9-Stage Audit Lifecycle**:
   `Scoping -> Audit Universe -> Risk-Based Plan -> Evidence Request (PBC) -> Sampling Rationale -> Fieldwork -> 6-Part Finding -> Management Response (MAP) -> Remediation & Follow-Up`.
2. **Design Effectiveness (`DE`) vs Operating Effectiveness (`OE`) Separation**:
   - **Design Effectiveness (`DE`)**: Evaluates whether a policy, architecture, or automated control *if operated as prescribed* adequately mitigates the stated risk. A signed policy PDF + walkthrough can substantiate `DE = EFFECTIVE`.
   - **Operating Effectiveness (`OE`)**: Evaluates whether the control *actually operated consistently throughout the defined evidence period*. Requires **4 mandatory elements**: (1) verified complete **population** (`N` occurrences during the period), (2) documented **sampling rationale** (e.g., 100% for quarterly controls = 4/4 quarters, statistically/risk-sized sample for daily/change tickets), (3) inspected **workpaper** with primary artifacts, and (4) independent **reviewer sign-off**.
   - If the population is incomplete (e.g., only 1 of 3 months collected) or only a policy PDF was provided, mark `operating_effectiveness = PENDING_SAMPLE` (NEVER `EFFECTIVE`!).
3. **Mandatory 6-Part Defensible Finding Schema**:
   Every finding MUST document all 6 fields with explicit `evidence_confidence` (`HIGH | MEDIUM | LOW`):
   1. **`Criteria`**: Exact normative/regulatory/policy clause (`PADK OJK 1/2026`, `ISO 27001:2022 A.5.18`, internal SOP §3.2).
   2. **`Condition`**: Exact observed factual gap during the evidence period (counts, dates, sample misses — zero fabricated IDs!).
   3. **`Cause`**: Systemic control or process failure allowing the gap.
   4. **`Effect / Risk` (`Consequence`)**: Concrete security, operational, financial, or regulatory exposure.
   5. **`Recommendation` (`Corrective Action`)**: Specific, verifiable remediation + owner + target due date.
   6. **`Evidence Ref`**: Inspectable workpaper path or primary log reference (or explicit `MISSING / PENDING` marker).
4. **Single Document Engine Rendering (`SA-DOC-ENGINE-001`)**:
   - Render formal `GRC_ASSESSMENT` reports strictly via `shadow-doc/scripts/doc_orchestrator.py` (`domain_adapters.py::adapt_grc_payload`) preserving 100% of `evidence_ref` links.

## 4. Architecture & Implementation
### Control Frequency & Minimum Audit Sampling Guidelines
| Control Frequency | Annual Population | Recommended Minimum Sample Size | Example Primary Evidence |
| :--- | :--- | :--- | :--- |
| **Annual** | `1` | `1` (100%) | Signed annual DRP test report & attendance log |
| **Quarterly** | `4` | `2` (or `4` for critical banking/SOX controls) | Complete Q1–Q4 IAM access review exports + removal tickets |
| **Monthly** | `12` | `2–5` months across full period | Monthly vulnerability scan + patch closure evidence |
| **Daily / Per-Change** | `250+` | `25–40` stratified risk-based samples | CI PR approvals (`author != approver`), production change tickets |
| **Automated Preventive Control** | Continuous | `1` test-of-one + config-change log verification over full period | DB RLS policy / GitHub branch protection + zero unapproved override logs |

### Strict TypeScript DE vs OE Workpaper & 6-Part Finding Gate
```typescript
export type ControlEffectiveness =
  | 'EFFECTIVE'
  | 'INEFFECTIVE'
  | 'PENDING_SAMPLE'
  | 'NOT_TESTED';

export interface OperatingWorkpaper {
  readonly controlId: string;
  readonly evidencePeriod: string;
  readonly populationCount: number | null;
  readonly sampleTestedCount: number;
  readonly samplePassedCount: number;
  readonly workpaperRef: string | null;
  readonly reviewerName: string | null;
}

export function evaluateOperatingEffectiveness(
  wp: OperatingWorkpaper,
): ControlEffectiveness {
  if (
    wp.populationCount === null ||
    wp.populationCount <= 0 ||
    wp.sampleTestedCount <= 0 ||
    wp.workpaperRef === null ||
    wp.reviewerName === null
  ) {
    return 'PENDING_SAMPLE';
  }
  if (wp.samplePassedCount < wp.sampleTestedCount) {
    return 'INEFFECTIVE';
  }
  return 'EFFECTIVE';
}
```

### Sample 6-Part Finding JSON (`grc_assurance_engine.py --validate-findings`)
```json
{
  "assessment_as_of_date": "2026-04-15",
  "sector": "BANKING",
  "evidence_period": "2026-01-01..2026-03-31",
  "findings": [
    {
      "finding_id": "GRC-BNK-004",
      "criteria": "PADK OJK 1/2026 PPJTI Vendor Access & ISO/IEC 27001:2022 A.5.19",
      "condition": "Vendor security policy approved (DE); Q1 privileged access review sample incomplete (1 of 3 months provided).",
      "cause": "Automated IAM quarterly extract job disabled during cloud migration.",
      "consequence": "Operating effectiveness of privileged PPJTI vendor offboarding cannot be verified across Q1.",
      "corrective_action": "Re-enable automated IAM review extract, retain immutable logs, and complete full quarterly review.",
      "design_effectiveness": "EFFECTIVE",
      "operating_effectiveness": "PENDING_SAMPLE",
      "evidence_ref": "docs/audit/2026-q1/ppjti-policy-v2.pdf"
    }
  ]
}
```

## 5. Platform / Vendor Variations
- **Automated DevSecOps / Cloud-Native Environments**: Leverage "Test-of-One" plus immutable configuration change-log inspection (CloudTrail, GitHub Audit Log, Terraform plan history) to prove continuous `OE` more reliably than manual screenshot sampling.
- **Traditional On-Premise / Hybrid Enterprises**: Explicitly document **population completeness testing** (how the auditor proved the client didn't hand-pick only "clean" tickets from an Excel sheet!).

## 6. Decision Matrix & Trade-Offs
| Evidence Supplied by Auditee | `DE` Verdict | `OE` Verdict | Auditor Action |
| :--- | :--- | :--- | :--- |
| Signed SOP PDF only (no execution logs) | `EFFECTIVE` (if aligned with criteria) | `PENDING_SAMPLE` | Request full population & sampled execution logs |
| Signed SOP + 1 of 3 monthly logs clean | `EFFECTIVE` | `PENDING_SAMPLE` | Keep finding open until remaining months sampled |
| Signed SOP + complete population + 25/25 clean + reviewer sign-off | `EFFECTIVE` | `EFFECTIVE` | Close control test cleanly with archived workpaper |
| 3 of 25 sampled production changes lacked peer approval | `EFFECTIVE` | `INEFFECTIVE` | Raise 6-part finding + Management Action Plan |

## 7. Real Production Scenario
**Context:** During a pre-audit readiness check of quarterly privileged access reviews, the IT manager submitted a beautifully formatted 20-page IAM Policy PDF and asked the consultant to mark `A.5.18` `"Effective"`.
**Audit Discipline:** Separating `DE` from `OE` and demanding the full Q1–Q4 population revealed that Q2 and Q3 reviews had never been executed after an IAM admin resigned, leaving 7 terminated contractor accounts active! Recording `DE = EFFECTIVE`, `OE = INEFFECTIVE` with a 6-part finding triggered immediate revocation and automated alerts before the external statutory audit began.

## 8. Failure Modes & Edge Cases
- **WRONG (Marking `OE = EFFECTIVE` from policy PDFs or cherry-picked client screenshots):** Leaves silent operational control failures undetected until external regulators or attackers find them.
  **RIGHT:** Require complete population verification, explicit sample rationale, primary system logs, and independent reviewer sign-off before concluding `OE = EFFECTIVE`; otherwise mark `PENDING_SAMPLE`.
- **WRONG (Writing 2-sentence findings missing `Cause`, `Consequence`, or `Evidence Ref`, or inventing ticket IDs):** Fails quality assurance and undermines audit committee credibility.
  **RIGHT:** Enforce all 6 parts on every finding via `grc_assurance_engine.py --validate-findings` and mark missing evidence honestly as `PENDING`.

## 9. Testing & Verification
- Run `python shadow-grc/scripts/grc_assurance_engine.py --validate-findings <findings.json> --sector <SECTOR> --as-of-date <YYYY-MM-DD>`.
- Run `python -m unittest discover -s shadow-grc/tests -v` (`test_grc_dated_register.py`).

## 10. Operational Considerations
- Track Management Action Plans (`MAP`) with explicit executive owners and verification retest dates (`30 / 60 / 90` days) so remediation follow-up tests **actual operating evidence** after the fix, not just an updated policy document.

## 11. Authoritative References
- **IIA Global Internal Audit Standards (2024)** — *Performing Engagement Work, Sampling, and Communicating Defensible Findings*.
- **AICPA Audit Sampling Guide** & **ISACA ITAF (IT Audit Framework) 4th Edition** — *Design vs Operating Effectiveness Testing*.
- **Shadow GRC Playbooks** — [`../playbooks/WORKPAPERS-AND-ASSURANCE-TEMPLATES.md`](../playbooks/WORKPAPERS-AND-ASSURANCE-TEMPLATES.md).

## 12. Limitations & When NOT to Use
- **Do NOT use** `/shadow-grc` audit sampling to perform technical penetration testing or exploit validation — route technical security assessments to `/shadow-sec`.
- **Do NOT use** `/shadow-grc` scripts to directly build `.docx`/`.pdf` files — render deliverables cleanly through `/shadow-doc` (`doc_orchestrator.py`).
