---
name: shadow-privacy
description: "Data Privacy & Regulatory Compliance (UU PDP & GDPR). Use when classifying Data Spesifik vs Umum (UU No. 27/2022 Pasal 4), verifying consent (Pasal 20), DSAR/erasure, DPIA (Pasal 34), cross-border transfers (Pasal 56), PII log redaction, or 3x24h breach readiness (Pasal 46)."
---

# `/shadow-privacy` — Data Privacy, UU PDP (UU No. 27/2022) & GDPR Compliance Auditor

Use this skill whenever the **Monarch** invokes `/shadow-privacy`, designs/modifies schemas storing personal data, builds auth/consent/onboarding flows, integrates third-party cloud/analytics processors, or prepares for Staging UAT / Production Go-Live.

Grounded in verified statutory and international standards documented in [`references/UU-PDP-27-2022-AND-GDPR-CONTROLS.md`](references/UU-PDP-27-2022-AND-GDPR-CONTROLS.md):
1. **Undang-Undang Nomor 27 Tahun 2022 tentang Pelindungan Data Pribadi (UU PDP)** — Full enforcement effective **17 October 2024** (`Pasal 74`). Official text: `https://peraturan.bpk.go.id/Details/229798/uu-no-27-tahun-2022`.
2. **EU General Data Protection Regulation (GDPR — Regulation (EU) 2016/679)** & **ISO/IEC 27701:2019** (Privacy Information Management System).

---

## 1. The 6-Stage Privacy Engineering & Audit Workflow

### Stage 1: Personal Data Inventory & Classification (`UU PDP Pasal 4`)
Classify every field in databases, payloads, logs, and analytics events:
- **Data Pribadi yang Bersifat Spesifik (`Pasal 4 Ayat (2)`)**: Health/medical records, biometric data, genetic data, criminal records, children's data, personal financial data, and other data per statutory regulations -> **mandatory field-level encryption/tokenization, strict RBAC, and mandatory DPIA (`Pasal 34`) when processed at scale**.
- **Data Pribadi yang Bersifat Umum (`Pasal 4 Ayat (3)`)**: Full name, gender, nationality, religion, marital status, and/or combined data that identifies an individual (NIK, phone, email, IP/device ID).

### Stage 2: Lawful Basis & Consent Lifecycle (`UU PDP Pasal 20–26` & `GDPR Art. 6–7`)
Every collection point MUST record an explicit lawful basis (`Pasal 20 Ayat (2)`): explicit consent (`huruf a`), contract performance (`huruf b`), legal obligation (`huruf c`), vital interest (`huruf d`), public interest/authority (`huruf e`), or balanced legitimate interest (`huruf f`).
- When relying on **Consent**, store immutable proof (`user_id`, `purpose_code`, `consent_version`, `granted_at`, `withdrawn_at`, `source_channel`) and block processing once `withdrawn_at` is set (`Pasal 9`).
- For children or persons with disabilities, enforce verifiable parent/guardian consent (`Pasal 25–26`).

### Stage 3: Data Subject Rights API & Retention/Erasure (`UU PDP Pasal 5–13` & `Pasal 42–44`)
Verify engineering support for Data Subject Rights (`BAB IV`):
- **Transparency & Access (`Pasal 5 & 7`)**: Privacy notice detailing controller identity, legal basis, purpose, and accountability + self-service/API data export.
- **Rectification (`Pasal 6`)**: Endpoint/UI for users to update/correct inaccurate data.
- **Withdrawal, Erasure & Restriction (`Pasal 8, 9, 11, 43`)**: Automated retention TTL jobs and safe anonymization/deletion pipelines (preserving financial/tax audit records required by `Pasal 20 Ayat (2) huruf c` via cryptographic erasure or pseudonymization).
- **Automated Decision Profiling Objection (`Pasal 10`)**: Human-review override for automated credit/fraud/scoring decisions that produce legal or significant effects.
- **Data Portability (`Pasal 13`)**: Machine-readable JSON/CSV export endpoint.

### Stage 4: Technical Safeguards, PII Log Redaction & Encryption (`UU PDP Pasal 35–39`)
- **Zero Raw PII in Logs/Traces**: Never log raw NIK, NPWP, BPJS, bank account numbers, biometrics, health diagnoses, or tokens in application logs, APM spans, or error trackers.
- **Encryption & Access Control**: Encrypt Specific Personal Data at column/envelope level (AES-256-GCM / KMS) in addition to disk TDE and TLS 1.2+/1.3 in transit; enforce tenant isolation and least privilege.

### Stage 5: Governance — ROPA, DPIA, DPO & Cross-Border Transfer (`Pasal 31, 34, 51–56`)
- **ROPA (`Pasal 31`)**: Maintain a machine-checked Record of Processing Activities mapping dataset -> purpose -> lawful basis -> retention -> processor.
- **DPIA (`Pasal 34`)**: Require a Data Protection Impact Assessment for high-risk processing (specific data at scale, automated profiling, systematic monitoring, new AI/biometric tech).
- **Processors & DPO (`Pasal 51–54`)**: Verify Data Processing Agreements (DPA) and written approval for sub-processors; flag DPO appointment requirement when processing public services, large-scale systematic monitoring, or large-scale Specific Personal Data.
- **Cross-Border Transfer Gate (`Pasal 56`)**: Before routing data to non-Indonesian cloud regions, LLM APIs, or SaaS processors, enforce the 3-step statutory cascade: (1) equivalent/higher adequacy in destination country -> (2) adequate & binding contractual safeguards (SCC/BCR) -> (3) explicit Data Subject consent.

### Stage 6: 3 x 24 Hour Breach Notification & Sanctions Awareness (`Pasal 46 & 57`)
- Maintain an incident runbook guaranteeing written breach notification within **3 x 24 hours (72 hours)** to affected Data Subjects and the PDP Authority containing: (a) exposed data categories, (b) time and chronology of exposure, and (c) containment/remediation steps (`Pasal 46 Ayat (1)–(2)`), plus public notice if public services or broad public interests are impacted (`Ayat (3)`).
- Flag non-compliance risk explicitly: administrative fines up to **2% of annual revenue** (`Pasal 57 Ayat (3)`), temporary processing suspension, data destruction, and criminal liability (`Pasal 65–70`).

---

## 2. Automated PII & Privacy Gate Script

Run the deterministic auditor against any repository before UAT or release:

```powershell
python "shadow-privacy/scripts/privacy_pdp_auditor.py" --scan .
python "shadow-privacy/scripts/privacy_pdp_auditor.py" --self-test
```

Treat scanner matches as leads. Trace a synthetic subject across primary data, downstream processors, caches, logs and backups. Record purpose, owner, retention and lawful-hold evidence per store. For erasure, verify identity and scope, distinguish live deletion from backup expiry, and require processor receipts or mark the affected stores pending. Exercise the workflow with synthetic data and explicit mutation authorization. Never put raw personal data into evidence.

Report confirmed findings ordered by severity (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) with exact `UU PDP Pasal / GDPR Article`, `file:line`, exposed personal data category, and concrete technical fix.

Run `scripts/privacy_pdp_auditor.py --assess-erasure manifest.json` for synthetic rehearsals. Supply `synthetic: true`, an independently established `expected_stores` inventory of redacted system aliases, and a `receipts` object keyed by those aliases. Use evidence references only. A retained archive remains pending review and an absent processor receipt keeps the rehearsal open. Owners must independently inspect each referenced receipt.
