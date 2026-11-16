# UU PDP (UU No. 27 Tahun 2022), GDPR & ISO/IEC 27701 Engineering Control Matrix

> **Primary Indonesian Legal Authority**: **Undang-Undang Republik Indonesia Nomor 27 Tahun 2022 tentang Pelindungan Data Pribadi (UU PDP)**, promulgated 17 October 2022, full compliance effective **17 October 2024** (`Pasal 74` 2-year transition period). Official source: [peraturan.bpk.go.id — UU No. 27 Tahun 2022](https://peraturan.bpk.go.id/Details/229798/uu-no-27-tahun-2022).
> **International Counterparts**: **Regulation (EU) 2016/679 (GDPR)** and **ISO/IEC 27701:2019**.

---

## 1. Personal Data Classification (`UU PDP Pasal 4` / `GDPR Art. 4 & 9`)

| Statutory Class | Legal Citation | Data Types Covered | Mandatory Engineering Controls |
|---|---|---|---|
| **Data Pribadi yang Bersifat Spesifik** | `UU PDP Pasal 4 Ayat (2)` / `GDPR Art. 9` | Health/medical records, biometric data, genetic data, criminal records, children's data, personal financial data, other statutory sensitive data | Envelope/column encryption (`AES-256-GCM` + KMS), strict RBAC/ABAC, masked UI display, explicit consent or statutory basis, **DPIA (`Pasal 34`)** for large-scale processing, zero plaintext in logs/analytics |
| **Data Pribadi yang Bersifat Umum** | `UU PDP Pasal 4 Ayat (3)` / `GDPR Art. 4(1)` | Full name, gender, nationality, religion, marital status, and combined identifying data (NIK, NPWP, phone, email, address, IP/device identifiers) | TLS 1.2+/1.3 in transit, encryption at rest, purpose-bound access, log redaction/tokenization, retention TTL |

---

## 2. Lawful Bases (`UU PDP Pasal 20 Ayat (2)` / `GDPR Art. 6`)

Before storing or processing personal data, verify which of the **6 lawful bases** applies:
1. **`Pasal 20 Ayat (2) huruf a` — Explicit Consent**: Written or recorded affirmative opt-in per specific purpose (`Pasal 21–24`); pre-ticked checkboxes or bundled dark patterns are invalid. Parent/guardian consent required for children and persons with disabilities (`Pasal 25–26`).
2. **`Pasal 20 Ayat (2) huruf b` — Contractual Obligation**: Strictly necessary to fulfill a contract with the Data Subject or pre-contractual steps requested by the Data Subject.
3. **`Pasal 20 Ayat (2) huruf c` — Legal Obligation**: Mandated by Indonesian law (e.g., tax retention, AML/KYC, e-Faktur, BPJS/SatuSehat statutory reporting).
4. **`Pasal 20 Ayat (2) huruf d` — Vital Interest**: Protecting life or physical safety of the Data Subject.
5. **`Pasal 20 Ayat (2) huruf e` — Public Interest / Official Authority**: Public service delivery or statutory government mandate.
6. **`Pasal 20 Ayat (2) huruf f` — Legitimate Interest**: Balanced against the Data Subject's rights and reasonable expectations (document balancing test).

### Recommended PostgreSQL Consent & Audit Schema
```sql
CREATE TABLE consent_records (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  subject_id      UUID NOT NULL,
  purpose_code    TEXT NOT NULL,        -- e.g. 'marketing_email', 'ai_scoring'
  lawful_basis    TEXT NOT NULL,        -- 'CONSENT' | 'CONTRACT' | 'LEGAL_OBLIGATION' | ...
  policy_version  TEXT NOT NULL,
  granted_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  withdrawn_at    TIMESTAMPTZ,
  evidence_hash   TEXT NOT NULL,        -- hash of notice text + capture metadata
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_consent_active ON consent_records (subject_id, purpose_code)
  WHERE withdrawn_at IS NULL;
```

---

## 3. Data Subject Rights (`UU PDP BAB IV Pasal 5–13` / `GDPR Art. 15–22`)

| Article | Right | Required Software Capability |
|---|---|---|
| `Pasal 5` | **Right to Information** | Clear privacy notice showing controller identity, legal basis, purpose, retention, and accountability prior to data capture |
| `Pasal 6` | **Right to Rectification** | Authenticated profile/data correction endpoints with audit log of changes |
| `Pasal 7` | **Right of Access & Copy** | DSAR endpoint returning user's stored personal data (excluding third-party secrets/other subjects' data) |
| `Pasal 8` | **Right to Erasure / Termination** | Hard-delete or irreversible anonymization pipeline + cascade to search indexes, caches, and backups TTL; retain only legally mandated accounting/tax records under `Pasal 20(2)(c)` |
| `Pasal 9` | **Right to Withdraw Consent** | 1-click preference center setting `withdrawn_at = now()` and halting non-essential processing pipelines immediately |
| `Pasal 10` | **Right to Object to Automated Profiling** | Human-in-the-loop appeal workflow & explainability metadata for automated credit, hiring, fraud, or eligibility decisions |
| `Pasal 11` | **Right to Restrict Processing** | `processing_restricted = true` flag freezing mutations/analytics while preserving evidence during disputes |
| `Pasal 12` | **Right to Sue & Compensation** | Incident accountability logs supporting root cause verification |
| `Pasal 13` | **Right to Data Portability** | Structured machine-readable export (`JSON`/`CSV`) in standard interoperable format |

---

## 4. Operational Obligations, Transfers & Sanctions

| UU PDP Article | GDPR Equivalent | Requirement & Engineering Verification |
|---|---|---|
| `Pasal 31` | `Art. 30` | **ROPA**: Maintain versioned `docs/privacy/ropa.yaml` or database registry mapping every table/API to lawful basis, retention period, and processors |
| `Pasal 34` | `Art. 35` | **DPIA**: Required before launching high-risk features (large-scale `Pasal 4(2)` specific data, biometric auth, automated legal-impact profiling, systematic tracking) |
| `Pasal 35–39` | `Art. 25, 32` | **Technical Security**: Privacy by design/default, redaction middleware on loggers (`nik`, `npwp`, `bpjs`, `rekam_medis`, `nomor_rekening`), KMS key rotation |
| `Pasal 42–44` | `Art. 5(1)(e), 17` | **Retention & Destruction**: Enforce automated TTL jobs per data category; scrub PII from expired staging/QA snapshots |
| `Pasal 46` | `Art. 33–34` | **3 x 24 Hour Breach Notification**: Written notice within **72 hours** to Data Subjects & PDP Authority detailing (a) exposed data, (b) time & chronology, (c) remediation; plus public notice if public services/broad public interest impacted |
| `Pasal 51–52` | `Art. 28` | **Processors & Sub-Processors**: Written DPA + explicit written Controller approval before adding new sub-processors (e.g., third-party LLM/analytics APIs) |
| `Pasal 53–54` | `Art. 37` | **DPO Requirement**: Mandatory DPO when core activity involves public services, large-scale systematic monitoring, or large-scale specific/criminal personal data |
| `Pasal 56` | `Art. 44–46` | **Cross-Border Data Transfer**: Enforce 3-tier sequence: (1) equivalent/higher adequacy in destination country -> (2) adequate & binding safeguards (SCC/BCR) -> (3) explicit Data Subject consent |
| `Pasal 57` | `Art. 83` | **Administrative Sanctions**: Written warning, temporary suspension, data deletion/destruction, and/or **administrative fine up to 2% of annual revenue** |
| `Pasal 65–70` | National Criminal Law | **Criminal Provisions**: Unlawful acquisition/collection/disclosure/use/forgery carries 4–6 years imprisonment and/or IDR 4B–6B fine; corporate fines up to **10x** maximum criminal fine (`Pasal 70`) |
