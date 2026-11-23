# 02. Indonesian Sectoral Regulatory Assurance (`POJK 11/2022` + `PADK OJK 1/2026`, SPBE & Indeks KAMI)

## 1. Purpose & Activation Conditions
Use this playbook when performing regulatory IT governance, cyber-resilience, or outsourcing assurance for Indonesian **Commercial Banks (`Bank Umum`)**, **Public Sector / Government Agencies (`SPBE`)**, or **BUMN / Regulated Enterprises**. Regulatory applicability is **date-sensitive** (`as_of_date`): citing revoked circulars (such as `SEOJK 21/SEOJK.03/2017` after 1 March 2026) invalidates an audit workpaper immediately.

Activate this playbook when:
- Auditing Commercial Bank IT Governance, `ATI`/`RSTI`, `PPJTI` IT outsourcing materiality & OJK inspection access rights under **`POJK 11/POJK.03/2022`** and **`PADK OJK Nomor 1 Tahun 2026`**.
- Scoring or preparing evidence for **SPBE (`Perpres 95/2018` & `Perpres 132/2022`)** and **Indeks KAMI BSSN** readiness assessments.
- Cross-checking regulatory obligations against `UU No. 27 Tahun 2022 (UU PDP)` (`/shadow-privacy`).

## 2. Prerequisites
- Explicit engagement metadata recorded upfront: **Jurisdiction (`ID`)**, **Sector (`BANKING | GOVERNMENT_SPBE | BUMN | FINTECH | ENTERPRISE`)**, **Assessment Effective Date (`as_of_date`)**, **Control Owners**, and **Audit Evidence Period**.
- Baseline regulatory registry check via `shadow-monarch/scripts/consulting_core.py --check-regulations` and `shadow-grc/scripts/grc_assurance_engine.py --validate-findings ... --sector BANKING --as-of-date YYYY-MM-DD`.

## 3. Technical Principles & Constraints
1. **Strict Dated Regulatory Baseline (`as_of_date` Rule — `test_grc_dated_register.py`)**:
   - **Indonesian Commercial Banking (Effective 1 March 2026 onward):** Apply **`POJK 11/POJK.03/2022`** (Penyelenggaraan Teknologi Informasi oleh Bank Umum) operationalized by **`PADK OJK Nomor 1 Tahun 2026`**, which **REVOKES `SEOJK 21/SEOJK.03/2017`**! Never cite `SEOJK 21/2017` as active criteria for assessments dated `>= 2026-03-01`.
   - Core Banking IT assurance pillars under `POJK 11/2022` + `PADK OJK 1/2026`:
     - **Tata Kelola TI & Komite Pengarah TI** (Board/Director accountability, `ATI` Arsitektur TI & `RSTI` Rencana Strategis TI alignment).
     - **Manajemen Risiko & Ketahanan Siber** (Cyber resilience maturity, DRP/BCP periodic testing, incident reporting to OJK within statutory windows).
     - **`PPJTI` (Penyedia Jasa Teknologi Informasi) Outsourcing Governance**: Materiality assessment, vendor due diligence, exit strategy, data protection, and **mandatory contractual right of OJK inspection/audit access**.
     - **Pelindungan Data Pribadi (`UU PDP` Alignment)**: Specific vs General data classification, consent, breach readiness (`3x24h` via `/shadow-privacy`).
2. **Indonesian Public Sector (`SPBE` & `Indeks KAMI BSSN`) Precision**:
   - Anchor SPBE governance to **Perpres 95/2018** (SPBE), **Perpres 132/2022** (Arsitektur SPBE Nasional), **PermenPANRB 59/2020** (Pemantauan & Evaluasi SPBE), and **Perpres 39/2019** (Satu Data Indonesia, collaborating with `/shadow-ea`).
   - Verify the **exact Indeks KAMI BSSN workbook version** (e.g., v4.2 / v5.0) before calculating scores across *Kategori Sistem Elektronik*, *Tata Kelola*, *Pengelolaan Risiko*, *Kerangka Kerja*, *Pengelolaan Aset*, *Teknologi & Keamanan*, plus supplements (*Keterlibatan Pihak Ketiga*, *Cloud*, *Pelindungan Data Pribadi*).
   - Remember: uploading a signed Surat Keputusan (`SK`) or SOP PDF alone proves **Design Effectiveness** (Level 2–3 max), NEVER full operational maturity without dated execution logs, review minutes, and audit follow-up evidence!
3. **Escalation Boundary (Not Statutory Legal Opinion)**:
   - Flag ambiguous statutory interpretations or regulatory penalty exposure for qualified **Legal Counsel / Compliance Director / OJK Liaison** review (`escalation_required: true`).

## 4. Architecture & Implementation
### Dated Regulatory Applicability Crosswalk (`Indonesia`)
| Sector | Effective Window | Active Primary Criteria | Revoked / Watch-Out Rule | Key Audit Evidence |
| :--- | :--- | :--- | :--- | :--- |
| **Commercial Bank (`BANKING`)** | `>= 2026-03-01` | `POJK 11/POJK.03/2022`, `PADK OJK No. 1/2026`, `UU PDP 27/2022` | **DO NOT cite revoked `SEOJK 21/2017`** as active! | `RSTI`/KPTI minutes, `PPJTI` OJK access clause, DRP drill report, cyber resilience self-assessment |
| **Government (`GOVERNMENT_SPBE`)** | Active | `Perpres 95/2018`, `Perpres 132/2022`, `Perpres 39/2019`, `Indeks KAMI BSSN` | Verify exact Indeks KAMI edition before scoring | Signed `Arsitektur SPBE` 6-Domain, BSSN KAMI evidence bundle, CSIRT/incident logs |
| **Cross-Sector Data Privacy** | Active (`2024-10-17+`) | `UU No. 27 Tahun 2022 (UU PDP)` | Enforce Pasal 4 Specific PII + Pasal 46 `3x24h` breach rule | ROPA, DPIA, consent ledger, DSAR fulfillment logs (`/shadow-privacy`) |

### Strict TypeScript Dated Regulatory Currency Validator
```typescript
export type RegulatedSector = 'BANKING' | 'GOVERNMENT_SPBE' | 'BUMN' | 'ENTERPRISE';

export interface RegulatoryValidationInput {
  readonly sector: RegulatedSector;
  readonly asOfDateIso: string;
  readonly citedRegulations: readonly string[];
}

const PADK_OJK_1_2026_EFFECTIVE = '2026-03-01';

export function validateRegulatoryCurrency(
  input: RegulatoryValidationInput,
): { readonly valid: boolean; readonly violations: readonly string[] } {
  const violations: string[] = [];
  if (input.sector === 'BANKING' && input.asOfDateIso >= PADK_OJK_1_2026_EFFECTIVE) {
    const citesRevoked = input.citedRegulations.some((ref) =>
      /SEOJK\s*21(?:\/SEOJK\.03)?\/2017/i.test(ref),
    );
    const citesPadk = input.citedRegulations.some((ref) =>
      /PADK\s*OJK\s*(?:No\.?\s*)?1\s*(?:\/|Tahun\s*)2026/i.test(ref),
    );
    if (citesRevoked) {
      violations.push(
        'REVOKED_REGULATION_CITED: SEOJK 21/SEOJK.03/2017 was revoked effective 2026-03-01 by PADK OJK No. 1 Tahun 2026.',
      );
    }
    if (!citesPadk) {
      violations.push(
        'MISSING_ACTIVE_REGULATION: Banking IT assessments on/after 2026-03-01 must evaluate against PADK OJK No. 1 Tahun 2026 alongside POJK 11/2022.',
      );
    }
  }
  return { valid: violations.length === 0, violations };
}
```

## 5. Platform / Vendor Variations
- **Cloud Outsourcing in Banking (`PPJTI` Cloud)**: Verify cloud contract addenda explicitly grant OJK inspection rights, exit/portability plans, data localization/residency controls where required, and incident SLA reporting aligned with `PADK OJK 1/2026`.
- **Regional Agencies (`Pemda` SPBE)**: Pair `shadow-grc` KAMI/SPBE evidence auditing with `/shadow-ea` (`6-Domain Arsitektur SPBE`) so architectural artifacts and security maturity scores align without contradiction.

## 6. Decision Matrix & Trade-Offs
| Audit Situation | Action | Consequence if Skipped |
| :--- | :--- | :--- |
| Banking IT audit dated `>= 2026-03-01` | Run `grc_assurance_engine.py --validate-findings ... --sector BANKING --as-of-date <date>` | Citing revoked `SEOJK 21/2017` fails regulator/audit committee review immediately |
| Government agency claims SPBE Security Level 4 with SOP PDFs only | Cap assessment at Design Effectiveness; mark Operating Effectiveness `PENDING_SAMPLE` until live SIEM/incident/patch logs exist | Inflated self-assessment fails KemenPANRB / BSSN external verification |

## 7. Real Production Scenario
**Context:** A regional bank hired consultants in April 2026 to review its cloud payment-gateway vendor (`PPJTI`). The initial draft checklist was recycled from a 2023 engagement citing `SEOJK 21/SEOJK.03/2017` and missed checking OJK contractual inspection access and updated cyber-resilience reporting obligations.
**Fix:** Running `grc_assurance_engine.py --sector BANKING --as-of-date 2026-04-15` immediately flagged the revoked circular, switched criteria to `POJK 11/2022` + `PADK OJK 1/2026`, surfaced the missing `PPJTI` OJK inspection clause in the vendor MSA, and enabled legal/procurement to amend the contract before OJK supervisory review.

## 8. Failure Modes & Edge Cases
- **WRONG (Recycling obsolete checklists without recording `as_of_date` or citing revoked `SEOJK 21/2017` post-March-2026):** Produces legally stale audit findings that embarrass the engagement team in front of regulators.
  **RIGHT:** Always bind every workpaper to explicit `jurisdiction`, `sector`, and `as_of_date`, verifying active rules via `grc_assurance_engine.py`.
- **WRONG (Treating Indeks KAMI self-score as a certified BSSN clearance):** Telling an agency *"Indeks KAMI score 580 means you are BSSN certified."*
  **RIGHT:** Frame Indeks KAMI as a diagnostic security readiness index requiring primary operational evidence and official BSSN evaluation where mandated.

## 9. Testing & Verification
- Run `python -m unittest discover -s shadow-grc/tests -v` (`test_grc_dated_register.py` enforces dated regulatory applicability and operating-effectiveness evidence boundaries).
- Run `python shadow-grc/scripts/grc_assurance_engine.py --validate-findings <findings.json> --sector BANKING --as-of-date <YYYY-MM-DD>`.

## 10. Operational Considerations
- Maintain a dated **Regulatory Change Watchlist** inside the client's Obligations Register so upcoming OJK, BI, BSSN, or UU PDP implementing regulations (`PP PDP`) trigger proactive gap reviews before enforcement deadlines.

## 11. Authoritative References
- **POJK Nomor 11/POJK.03/2022** — *Penyelenggaraan Teknologi Informasi oleh Bank Umum*.
- **PADK OJK Nomor 1 Tahun 2026** — *Tata Kelola & Penyelenggaraan TI Bank Umum* (effective 1 March 2026, revoking `SEOJK 21/SEOJK.03/2017`).
- **Perpres 95/2018 & Perpres 132/2022** — *SPBE & Arsitektur SPBE Nasional*; **BSSN Indeks KAMI**; **UU No. 27/2022 (UU PDP)**.

## 12. Limitations & When NOT to Use
- **Do NOT use** `/shadow-grc` for technical UU PDP code implementation (DSAR erasure tombstones, PII log redaction) — delegate engineering to `/shadow-privacy`.
- **Do NOT issue** binding statutory legal opinions; escalate regulatory enforcement or licensing interpretations to qualified legal counsel.
