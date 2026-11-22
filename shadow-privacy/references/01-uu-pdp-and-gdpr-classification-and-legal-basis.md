# 01. UU PDP & GDPR Classification & Lawful Basis

## 1. Purpose & Activation Conditions
Classify personal data fields accurately under Indonesia **UU No. 27 Tahun 2022 (UU PDP — full enforcement since 17 October 2024, Pasal 74)** and **EU GDPR (Regulation (EU) 2016/679)**, and map every processing activity to an explicit lawful basis. Load when designing database schemas, onboarding forms, API payloads, or privacy audits.

## 2. Prerequisites
- Schema inventory of tables, API DTOs, third-party SaaS/analytics payloads, and logs (`privacy_pdp_auditor.py --scan`).

## 3. Technical Principles & Constraints
- **Mandatory Statutory Classification (`UU PDP Pasal 4` / `GDPR Art. 4 & 9`):**
  - **Data Pribadi yang Bersifat Spesifik (`Pasal 4 Ayat (2)`):** Health/medical records (`rekam_medis`, diagnoses), biometric data (fingerprints, face embeddings), genetic data, criminal records, children's data, **personal financial data** (`nomor_rekening`, card/credit profiles, salaries), and other statutory sensitive data -> mandates **field/envelope encryption (`AES-256-GCM` + KMS)**, strict RBAC, masked UI display, zero plaintext in logs/analytics, and **DPIA (`Pasal 34`)** when processed at scale!
  - **Data Pribadi yang Bersifat Umum (`Pasal 4 Ayat (3)`):** Full name, gender, nationality, religion, marital status, and combined identifying data (`NIK`, `NPWP`, phone, email, address, IP/device IDs) -> mandates TLS 1.2+/1.3, encryption at rest, purpose limitation, log redaction, and retention TTL.
- **6 Explicit Lawful Bases (`UU PDP Pasal 20 Ayat (2)` / `GDPR Art. 6`):** Every field/table MUST map to at least one documented lawful basis BEFORE collection:
  1. `huruf a` — Explicit valid Consent (`Pasal 21–26`),
  2. `huruf b` — Contractual obligation with Data Subject,
  3. `huruf c` — Statutory legal obligation (tax/e-Faktur, AML/KYC, BPJS/SatuSehat reporting),
  4. `huruf d` — Vital interest (life/physical safety),
  5. `huruf e` — Public interest / official statutory authority,
  6. `huruf f` — Balanced legitimate interest (document balancing test!).
- **Legal Escalation Boundary:** Technical engineering controls implement statutory requirements; jurisdiction-specific legal interpretation, contract clauses, and regulatory filings MUST be escalated to qualified Legal Counsel / DPO.

## 4. Architecture & Implementation
| Statutory Class | Legal Citation | Example Fields | Mandatory Engineering Baseline |
| :--- | :--- | :--- | :--- |
| **Data Spesifik** | `UU PDP Pasal 4(2)` / `GDPR Art. 9` | `rekam_medis`, `diagnosis`, `face_embedding`, `nomor_rekening`, child DOB | Column/KMS `AES-256-GCM` + AAD, strict RBAC, DPIA (`Pasal 34`), 0 raw logs/analytics |
| **Data Umum** | `UU PDP Pasal 4(3)` / `GDPR Art. 4(1)` | `full_name`, `nik`, `npwp`, `email`, `phone`, `address`, `device_id` | TLS 1.2+/1.3, disk encryption, masked logs (`3174********0001`), retention TTL |
| **Non-Personal / Aggregated** | Outside personal scope only if truly irreversible | Anonymized cohort counts (`k >= 10` buckets) | Verify re-identification risk before publishing |

Typed Data-Field Classification Registry:
```typescript
export type PersonalDataClass = 'SPECIFIC_PASAL_4_2' | 'GENERAL_PASAL_4_3' | 'NON_PERSONAL';
export type LawfulBasisCode = 'CONSENT' | 'CONTRACT' | 'LEGAL_OBLIGATION' | 'VITAL_INTEREST' | 'PUBLIC_INTEREST' | 'LEGITIMATE_INTEREST';

export interface FieldPrivacyMetadata {
  readonly table: string;
  readonly column: string;
  readonly dataClass: PersonalDataClass;
  readonly lawfulBasis: LawfulBasisCode;
  readonly retentionDays: number;
  readonly requiresColumnEncryption: boolean;
  readonly allowedInAppLogs: false | 'MASKED_ONLY';
}

export function validateFieldPrivacyContract(meta: FieldPrivacyMetadata): readonly string[] {
  const errors: string[] = [];
  if (meta.dataClass === 'SPECIFIC_PASAL_4_2' && !meta.requiresColumnEncryption) {
    errors.push(`${meta.table}.${meta.column}: UU PDP Pasal 4(2) Specific Data requires column/envelope encryption.`);
  }
  if (meta.dataClass === 'SPECIFIC_PASAL_4_2' && meta.allowedInAppLogs !== false) {
    errors.push(`${meta.table}.${meta.column}: Specific Data must NEVER appear in application logs.`);
  }
  if (meta.retentionDays <= 0) {
    errors.push(`${meta.table}.${meta.column}: Explicit positive retentionDays TTL is required.`);
  }
  return errors;
}
```

## 5. Platform / Vendor Variations
| Industry Sector (Indonesia) | Key Specific-Data Focus | Overlapping Regulator |
| :--- | :--- | :--- |
| **Fintech / Banking** | `NIK`, `NPWP`, `nomor_rekening`, biometric e-KYC, credit scoring (`Pasal 10`) | OJK (`POJK 11/2022`, `PADK OJK 1/2026` -> `/shadow-grc`) |
| **Healthtech / Clinic** | `rekam_medis`, lab results, prescriptions (`Pasal 4(2)`) | Kemenkes / SatuSehat + mandatory DPIA (`Pasal 34`) |
| **EdTech / Family Apps** | Children's data (`Pasal 25`) | Verifiable parent/guardian consent required |

## 6. Decision Matrix & Trade-Offs
| Processing Purpose | Right Lawful Basis | Why NOT Consent? |
| :--- | :--- | :--- |
| Issuing paid tax invoice (`e-Faktur`) | `LEGAL_OBLIGATION` (`Pasal 20(2)(c)`) | User cannot opt out of statutory tax retention via consent withdrawal |
| Delivering ordered physical package | `CONTRACT` (`Pasal 20(2)(b)`) | Strictly required to perform the purchase contract |
| Marketing newsletters / behavioral analytics | **`CONSENT`** (`Pasal 20(2)(a)`) | Optional; MUST allow granular opt-in & instant withdrawal (`Pasal 9`) |

## 7. Real Production Scenario
A clinic booking app stores `nik`, `diagnosis`, and `nomor_rekening` in plaintext columns, logs `logger.info({ patient })` on every booking, and bundles marketing consent inside the mandatory Terms of Service checkbox. Running `privacy_pdp_auditor.py --scan .` flags unencrypted `Pasal 4(2)` specific data and raw PII logs; splitting granular consent, adding `AES-256-GCM` column encryption, and redacting logger paths closes both statutory exposures.

## 8. Failure Modes & Edge Cases
- **WRONG:** Treating `NIK` or `nomor_rekening` as harmless "order metadata" and printing them in debug logs or sending them to analytics tools.
- **RIGHT:** Classify every personal field upfront (`validateFieldPrivacyContract`), encrypt Specific Data at column/envelope level, and mask/omit PII from all logs and analytics (`/shadow-analytics`).
- **WRONG:** Claiming automated tool scans prove `"100% UU PDP legally compliant"` without Legal/DPO review.
- **RIGHT:** Present scanner results strictly as technical engineering leads and escalate statutory interpretation to Legal/DPO.

## 9. Testing & Verification
- Run `python shadow-privacy/scripts/privacy_pdp_auditor.py --self-test` and `--scan .` on every schema/logging PR.

## 10. Operational Considerations
- Maintain a versioned machine-readable field inventory (`docs/privacy/data-inventory.yaml`) reviewed whenever new DB columns or third-party integrations are added.

## 11. Authoritative References
- Undang-Undang Nomor 27 Tahun 2022 tentang Pelindungan Data Pribadi (`https://peraturan.bpk.go.id/Details/229798/uu-no-27-tahun-2022`).
- EU Regulation 2016/679 (GDPR) — Articles 4, 6, 9 (`https://eur-lex.europa.eu/eli/reg/2016/679/oj`).

## 12. Limitations & When NOT to Use
- Static field-name scanners (`privacy_pdp_auditor.py`) cannot detect personal data hidden inside generic column names like `payload_json` or `notes`; always review actual runtime data flows alongside static scans.
