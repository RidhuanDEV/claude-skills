# 01. COBIT 2019 Capability vs Maturity & ISO/IEC 27001:2022 93-Control SoA

## 1. Purpose & Activation Conditions
Use this playbook when auditing IT governance maturity under **COBIT 2019** or designing/evaluating an Information Security Management System (**ISMS**) and **Statement of Applicability (`SoA`)** under **ISO/IEC 27001:2022**. Its objective is strict methodological precision: never collapse COBIT Process Capability and Focus Area Maturity into one synthetic average, never omit ISMS Clauses 4–10, and never claim official certification from an internal readiness review.

Activate this playbook when:
- Scoring COBIT 2019 governance/management objectives (`EDM`, `APO`, `BAI`, `DSS`, `MEA`) and validating capability/maturity evidence via `grc_assurance_engine.py --assess-cobit`.
- Authoring or reviewing an ISO/IEC 27001:2022 SoA covering Clauses 4–10 and all **93 Annex A controls** (`37` Organizational, `8` People, `14` Physical, `34` Technological) via `grc_assurance_engine.py --validate-soa`.
- Mapping technical security gaps from `/shadow-sec` or `/shadow-privacy` into board-level governance controls.

## 2. Prerequisites
- Defined assessment scope, legal jurisdiction, assessment date (`as_of_date`), control owners, and evidence review window (`evidence_period`).
- Deep companion methodology: [`../methodologies/AUDIT-LIFECYCLE-AND-REGULATORY-CROSSWALK.md`](../methodologies/AUDIT-LIFECYCLE-AND-REGULATORY-CROSSWALK.md) and [`../playbooks/WORKPAPERS-AND-ASSURANCE-TEMPLATES.md`](../playbooks/WORKPAPERS-AND-ASSURANCE-TEMPLATES.md).
- Deterministic engine: [`../scripts/grc_assurance_engine.py`](../scripts/grc_assurance_engine.py).

## 3. Technical Principles & Constraints
1. **COBIT 2019 Capability (`0–5`) vs Maturity (`0–5`) Separation**:
   - **Process Capability (`0–5`)** evaluates a **single governance/management objective** (e.g., `APO13 Managed Security`, `BAI06 Managed IT Changes`, `DSS05 Managed Security Services`) against explicit activity achievement.
   - **Focus Area Maturity (`0–5`)** evaluates a **collection of related objectives** at the enterprise focus-area level: a focus area achieves Maturity Level `N` ONLY when ALL required objectives in that focus area achieve at least Capability Level `N` (conservative minimum threshold — NEVER mask a Level 1 gap in `DSS05` by averaging it with Level 4 objectives!).
   - Assigning `evidence_confidence = HIGH` requires `>= 2` independent verified evidence artifacts per objective.
2. **ISO/IEC 27001:2022 Complete Scope (Clauses 4–10 + 93 Annex A Controls)**:
   - An ISMS assessment is **incomplete** if it only ticks Annex A checklists while ignoring **Clauses 4–10** (Context, Leadership, Risk Assessment/Treatment, Support, Operation, Internal Audit/Management Review, Continual Improvement).
   - Map all **93 Annex A Controls** accurately across the 4 themes (`A.5` Organizational: `37`, `A.6` People: `8`, `A.7` Physical: `14`, `A.8` Technological: `34`) — NEVER use outdated ISO 27001:2013's `114` controls for a 2022 assessment!
   - Every Annex A control marked `IMPLEMENTED` MUST attach **BOTH** `design_evidence_ref` AND `operating_evidence_ref`. Every excluded control (`NOT_APPLICABLE`) MUST state a written risk-based justification tied to Clauses 4–6 — blank justifications fail audit immediately.
3. **Copyright & Non-Certification Escalation Boundaries**:
   - Reference COBIT 2019 and ISO/IEC 27001:2022 control IDs and themes legitimately without reproducing proprietary full text verbatim.
   - **NEVER** declare an organization officially *"ISO 27001 Certified"* or *"COBIT Compliant"* from an advisory/internal assessment; label results strictly as **Readiness / Gap Assessment** pending an accredited Certification Body (KAN/IAF) audit.

## 4. Architecture & Implementation
### ISO/IEC 27001:2022 4-Theme Control Distribution & SoA Schema
| Annex A Theme | Control Count | Examples | SoA Requirement |
| :--- | :--- | :--- | :--- |
| **`A.5` Organizational** | `37` | `A.5.1` Policies, `A.5.19` Supplier Security, `A.5.23` Cloud Security | Include/Exclude + justification + DE & OE evidence refs |
| **`A.6` People** | `8` | `A.6.1` Screening, `A.6.3` Security Awareness, `A.6.5` Offboarding | Verified HR/IAM execution logs across review period |
| **`A.7` Physical** | `14` | `A.7.1` Physical Perimeters, `A.7.10` Storage Media | Data center / cloud SOC2 / ISO report + access logs |
| **`A.8` Technological** | `34` | `A.8.5` Secure Auth, `A.8.15` Logging, `A.8.25` Secure SDLC | Link directly to `/shadow-auth`, `/shadow-sec`, `/shadow-observe` |
| **Total Annex A (2022)** | **`93`** | Plus mandatory **ISMS Clauses 4–10** | Zero blank justifications; zero OE claims from policy alone |

### Strict TypeScript COBIT Focus-Area Maturity & SoA Completeness Guard
```typescript
export interface CobitObjectiveScore {
  readonly objectiveId: string;
  readonly capabilityLevel: 0 | 1 | 2 | 3 | 4 | 5;
  readonly verifiedArtifactCount: number;
  readonly isCriticalInFocusArea: boolean;
}

export function computeConservativeFocusAreaMaturity(
  objectives: readonly CobitObjectiveScore[],
): { readonly maturityLevel: number; readonly lowConfidenceIds: readonly string[] } {
  const critical = objectives.filter((obj) => obj.isCriticalInFocusArea);
  if (critical.length === 0) {
    return { maturityLevel: 0, lowConfidenceIds: ['NO_CRITICAL_OBJECTIVES'] };
  }
  let minCap = 5;
  const lowConfidenceIds: string[] = [];
  for (const obj of critical) {
    if (obj.capabilityLevel < minCap) {
      minCap = obj.capabilityLevel;
    }
    if (obj.verifiedArtifactCount < 2) {
      lowConfidenceIds.push(obj.objectiveId);
    }
  }
  return { maturityLevel: minCap, lowConfidenceIds };
}
```

### Deterministic Verification Commands (`grc_assurance_engine.py`)
```powershell
python "shadow-grc/scripts/grc_assurance_engine.py" --assess-cobit path/to/cobit_scores.json
python "shadow-grc/scripts/grc_assurance_engine.py" --validate-soa path/to/iso27001_soa.json
```

## 5. Platform / Vendor Variations
- **Cloud-Hosted Startups & SaaS (AWS / GCP / Azure)**: Physical controls (`A.7.*`) for cloud data centers are inherited via verified AWS/GCP/Azure ISO 27001 / SOC 2 Type II attestation reports (record shared-responsibility boundary explicitly in SoA, never mark `"N/A"` without citing cloud provider attestation!).
- **BUMN & Regulated Financial Institutions (Indonesia)**: Cross-map ISO 27001:2022 Annex A (`A.5.19` Supplier Security, `A.5.29` ICT Continuity, `A.8.15` Logging) directly to `POJK 11/2022`, `PADK OJK 1/2026`, and `UU PDP No. 27/2022` to avoid duplicate audit fieldwork (`02-indonesian-regulatory-assurance-pojk-padk-and-spbe-kami.md`).

## 6. Decision Matrix & Trade-Offs
| Governance Goal | Primary Standard | Complementary Standard | Anti-Pattern to Avoid |
| :--- | :--- | :--- | :--- |
| **Enterprise IT Governance & Value Alignment** | **COBIT 2019** | ITIL 4 / TOGAF 10 (`/shadow-ea`) | Averaging Process Capability into inflated Maturity |
| **Certifiable Security Management System** | **ISO/IEC 27001:2022** (Clauses 4–10 + 93 Annex A) | OWASP ASVS 5.0 (`/shadow-sec`), NIST SSDF | Checking Annex A only while ignoring Clauses 4–10 risk management |

## 7. Real Production Scenario
**Context:** A BUMN subsidiary presented an internal COBIT readiness slide claiming *"Overall IT Governance Maturity: 3.4 / 5"* by averaging 12 objectives—hiding `DSS05 Managed Security` at Capability `1` and `BAI06 Managed Changes` at Capability `1`. Simultaneously, their ISO 27001 SoA still listed `114` controls from the obsolete 2013 standard and marked `A.5.19` `IMPLEMENTED` citing only a draft Word policy.
**Correction:** Re-evaluating with `grc_assurance_engine.py` exposed conservative Focus Area Maturity = `1`, migrated the SoA to the exact `93` ISO/IEC 27001:2022 controls + Clauses 4–10, downgraded `A.5.19` operating effectiveness to `PENDING_SAMPLE`, and produced a prioritized 90-day remediation roadmap that later passed an accredited Stage 1 audit cleanly.

## 8. Failure Modes & Edge Cases
- **WRONG (Averaging COBIT Capability into Maturity or stamping "ISO 27001 Certified" from self-audit):** Reporting `"Maturity 3.5"` while critical change/security objectives sit at Level 1, or issuing certification claims without an accredited auditor.
  **RIGHT:** Report per-objective Capability separately from conservative Focus Area Maturity (`min` critical objective), require `>= 2` artifacts for `HIGH` confidence, and frame advisory outputs strictly as readiness/gap assurance.
- **WRONG (Using ISO 27001:2013's 114 controls or leaving blank SoA exclusion justifications):** Immediately fails ISO/IEC 27001:2022 Stage 1 documentation audit.
  **RIGHT:** Enforce exact 93-control Annex A (`37/8/14/34`) + Clauses 4–10 coverage with written risk justifications for every exclusion.

## 9. Testing & Verification
- Run `python shadow-grc/scripts/grc_assurance_engine.py --self-test` (`10/10` probes) and `python -m unittest discover -s shadow-grc/tests -v`.
- Validate SoA and COBIT scorecards via `--validate-soa` and `--assess-cobit` before generating client executive reports via `/shadow-doc`.

## 10. Operational Considerations
- Maintain a versioned **Regulatory & Control Crosswalk** so one collected quarterly evidence artifact (e.g., IAM privileged access review log) satisfies ISO `A.5.18`, COBIT `DSS05.04`, and `PADK OJK 1/2026` simultaneously ("test once, comply many").

## 11. Authoritative References
- **ISACA (2018)** — *COBIT 2019 Framework: Introduction and Methodology* (Capability vs Maturity model).
- **ISO/IEC 27001:2022** — *Information security, cybersecurity and privacy protection — Information security management systems — Requirements* (Clauses 4–10 & 93 Annex A controls).
- **Shadow GRC Methodology** — [`../methodologies/AUDIT-LIFECYCLE-AND-REGULATORY-CROSSWALK.md`](../methodologies/AUDIT-LIFECYCLE-AND-REGULATORY-CROSSWALK.md).

## 12. Limitations & When NOT to Use
- **Do NOT use** `/shadow-grc` for code-level SAST/SQLi/XSS/SSRF remediation — route technical AppSec fixes to `/shadow-sec` and auth implementation to `/shadow-auth`.
- **Do NOT use** advisory GRC reviews as a substitute for accredited third-party certification audits or statutory legal counsel.
